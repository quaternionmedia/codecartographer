"""
Python Language Parser
======================
Implements the LanguageParser protocol for Python source files.
Wraps PythonCustomAST and converts its output to the unified node schema.

Node schema mapping
-------------------
AST type     → unified kind    depth
Module       → (not emitted: the walk's file node stands for it)
Class        → 'class'         2
Function     → 'function'      2
Import       → 'import'        2
Call         → 'call'          3
Argument     → 'argument'      3
Name         → 'name'          3
Constant     → 'constant'      3
For          → 'loop'          3
<other>      → 'symbol'        3

Edges: `contains` from what holds a node, `imports` to an import, and the
links between a file's functions and variables:

- `uses` -- a function or class to a name it reads and does not hold: a
  module-level variable, which its file holds, or a variable a function
  before it holds (the parser names a variable once per module).
- `calls` and `flows` -- read from the source by `python_links.links`: a
  function to what it calls, and a variable to each one assigned from it.
"""

from __future__ import annotations

import os
from typing import ClassVar

import networkx as nx

from codecarto.models.source_data import File, Folder
from codecarto.services.parsers.language_parser import (
    LanguageParser,
    ParserRegistry,
    make_node,
    make_edge,
)
from codecarto.services.parsers.python_links import links


# ── Type → (kind, depth) mapping ─────────────────────────────────────────────

_TYPE_MAP: dict[str, tuple[str, int]] = {
    "Module":         ("module",   1),
    "Class":          ("class",    2),
    "Function":       ("function", 2),
    "Import":         ("import",   2),
    "Call":           ("call",     3),
    "Argument":       ("argument", 3),
    "Name":           ("name",     3),
    "Constant":       ("constant", 3),
    "For":            ("loop",     3),
    "JoinedStr":      ("string",   3),
    "FormattedValue": ("string",   3),
}


# The AST's Module root is never emitted -- see `_convert` for why.
_SKIPPED_TYPES = frozenset({"Module"})
_FALLBACK_KIND = "symbol"

# Every `kind` this adapter can emit. `constructs.yaml` maps each one, or says
# why it is not a construct, and a test holds the two to each other in both
# directions.
KINDS = tuple(sorted(
    {kind for ast_type, (kind, _) in _TYPE_MAP.items() if ast_type not in _SKIPPED_TYPES}
    | {_FALLBACK_KIND}
))


def _ast_type_to_kind_depth(ast_type: str) -> tuple[str, int]:
    return _TYPE_MAP.get(ast_type, (_FALLBACK_KIND, 3))


def extract_python_imports(raw: str) -> list[str]:
    """Return the dotted module names referenced by this file's
    import/from-import statements (e.g. ``"os.path"``, ``"requests"``).

    Used by unified_parser_service.py's _add_python_dependency_edges to
    resolve real file-to-file dependency edges — kept separate from
    PythonCustomAST's own import bookkeeping (self.imports /
    _resolve_cross_module_links), which tracks each file's *last-seen*
    module name for its own cross-reference purposes and isn't a reliable
    source of "what did file X import" once multiple files have been
    visited. Relative imports (``from . import x``) are skipped — there's
    no absolute dotted name to resolve without full package context.
    """
    import ast

    try:
        tree = ast.parse(raw)
    except SyntaxError:
        return []

    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                modules.append(node.module)
    return modules


# ── Python visual grammar ─────────────────────────────────────────────────────
# Shape and colour per Python kind.  Parsers own visual intent; renderers just
# draw whatever shape/color arrives on the node.

_PY_SHAPE: dict[str, str] = {
    "module":   "diamond",
    "class":    "square",
    "function": "hexagon",
    "import":   "triangle",
    "call":     "hexagon",
}

_PY_COLOR: dict[str, str] = {
    "module":   "#4f9e94",   # a file, drawn as the canvas draws one
    "class":    "#00d4ff",
    "function": "#00ff41",
    "import":   "#facc15",
    "call":     "#00aa2a",
}


# ── Adapter class ─────────────────────────────────────────────────────────────

class PythonLanguageParser:
    """LanguageParser implementation for Python (.py) files."""

    language: ClassVar[str] = "python"
    extensions: ClassVar[list[str]] = [".py"]
    kinds: ClassVar[tuple[str, ...]] = KINDS

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        """Parse Python files and return a unified-schema graph.

        Parameters
        ----------
        files : list[File]
            Python source files to parse.
        depth : int
            Maximum depth (2 = symbols, 3 = sub-symbols).

        Returns
        -------
        nx.DiGraph with unified node schema.
        """
        from codecarto.services.parsers.ASTs.python_custom_ast import PythonCustomAST

        # Build a synthetic Folder so PythonCustomAST.parse() can iterate
        folder = Folder(name="__unified__", size=len(files), files=files, folders=[])

        parser = PythonCustomAST()
        raw_graph: nx.DiGraph = parser.parse(folder)

        graph = self._convert(raw_graph, depth)
        # The calls and flows the source states, between the nodes parsed.
        for file in files:
            if not file.name.endswith(".py") or not isinstance(file.raw, str):
                continue
            for source, target, kind in links(file.raw, os.path.splitext(file.name)[0]):
                if not (graph.has_node(source) and graph.has_node(target)):
                    continue
                if graph.has_edge(source, target):
                    # A name a function reads and calls: the call says more.
                    if kind == "calls" and graph.edges[source, target].get("kind") == "uses":
                        graph.edges[source, target]["kind"] = "calls"
                elif not graph.has_edge(target, source):
                    graph.add_edge(source, target, **make_edge(kind))
        return graph

    # ── Internal ──────────────────────────────────────────────────────────────

    def _convert(self, raw: nx.DiGraph, max_depth: int) -> nx.DiGraph:
        """Convert PythonCustomAST graph to unified schema graph."""
        out = nx.DiGraph()

        # ── Pass 1: nodes ─────────────────────────────────────────────────────
        for node_id, data in raw.nodes(data=True):
            ast_type = data.get("type", "")
            label    = data.get("label", node_id)
            module   = data.get("module", "")

            # The AST's own Module root duplicates the depth=1 file node
            # unified_parser_service.py's directory walker already created
            # and connected to its parent directory — including it here
            # produced a second, disconnected depth=1 node with every real
            # symbol attached underneath it instead of the file node,
            # permanently landing the whole file's contents on
            # compound_layout's orphan fallback ring. Skipping it here lets
            # its direct children (classes/functions/imports) surface as
            # in-degree-0 roots, which _merge_subgraph already connects
            # straight to the real file node.
            if ast_type in _SKIPPED_TYPES:
                continue

            kind, node_depth = _ast_type_to_kind_depth(ast_type)

            # Respect max_depth — skip deeper nodes
            if node_depth > max_depth:
                continue

            attrs = make_node(
                node_id,
                depth=node_depth,
                language="python",
                kind=kind,
                label=label,
                file=f"{module}.py" if module else "",
                line=0,
                # `chars`: the source it spans (`PythonCustomAST.create_node`),
                # which a Showcase sizes its dot by.
                meta={"module": module, "ast_type": ast_type,
                      **({"chars": data["chars"]} if data.get("chars") else {})},
                shape=_PY_SHAPE.get(kind),
                color=_PY_COLOR.get(kind),
            )
            out.add_node(node_id, **attrs)

        # ── Pass 2: edges ─────────────────────────────────────────────────────
        # **A NODE IS HELD ONCE, AND USED FROM ELSEWHERE.** The AST walker
        # joins every function that reads a name to it, and what a module
        # defines or assigns at its top level to the module: all as one kind,
        # so a module's variable, or a function another reads, was held by
        # whichever function read it first, and every function after held it
        # again. Its module -- the file -- holds it now, and a function that
        # reads it uses it; a variable two functions share (one node per
        # module) is held by the first.
        module_level = {dst for src, dst in raw.edges()
                        if raw.nodes[src].get("type") in _SKIPPED_TYPES}
        held: set[str] = set()
        for src, dst, edata in raw.edges(data=True):
            if not (out.has_node(src) and out.has_node(dst)):
                continue

            # Determine edge kind from context
            dst_kind = out.nodes[dst].get("kind", "")

            if dst_kind == "import":
                edge_kind = "imports"
            elif dst in module_level or dst in held:
                edge_kind = "uses"
            else:
                edge_kind = "contains"
                held.add(dst)

            out.add_edge(src, dst, **make_edge(edge_kind))

        return out


# ── Register on import ────────────────────────────────────────────────────────
_instance = PythonLanguageParser()
ParserRegistry.register(_instance)
