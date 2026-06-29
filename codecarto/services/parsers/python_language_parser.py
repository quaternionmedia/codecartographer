"""
Python Language Parser
======================
Implements the LanguageParser protocol for Python source files.
Wraps PythonCustomAST and converts its output to the unified node schema.

Node schema mapping
-------------------
AST type     → unified kind    depth
Module       → 'module'        1
Class        → 'class'         2
Function     → 'function'      2
Import       → 'import'        2
Call         → 'call'          3
Argument     → 'argument'      3
Name         → 'name'          3
Constant     → 'constant'      3
For          → 'loop'          3
<other>      → 'symbol'        3
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


def _ast_type_to_kind_depth(ast_type: str) -> tuple[str, int]:
    return _TYPE_MAP.get(ast_type, ("symbol", 3))


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
    "module":   "#9b59b6",
    "class":    "#00d4ff",
    "function": "#00ff41",
    "import":   "#e74c3c",
    "call":     "#00aa2a",
}


# ── Adapter class ─────────────────────────────────────────────────────────────

class PythonLanguageParser:
    """LanguageParser implementation for Python (.py) files."""

    language: ClassVar[str] = "python"
    extensions: ClassVar[list[str]] = [".py"]

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

        return self._convert(raw_graph, depth)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _convert(self, raw: nx.DiGraph, max_depth: int) -> nx.DiGraph:
        """Convert PythonCustomAST graph to unified schema graph."""
        out = nx.DiGraph()

        # ── Pass 1: nodes ─────────────────────────────────────────────────────
        for node_id, data in raw.nodes(data=True):
            ast_type = data.get("type", "")
            label    = data.get("label", node_id)
            module   = data.get("module", "")

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
                meta={"module": module, "ast_type": ast_type},
                shape=_PY_SHAPE.get(kind),
                color=_PY_COLOR.get(kind),
            )
            out.add_node(node_id, **attrs)

        # ── Pass 2: edges ─────────────────────────────────────────────────────
        for src, dst, edata in raw.edges(data=True):
            if not (out.has_node(src) and out.has_node(dst)):
                continue

            # Determine edge kind from context
            src_kind = out.nodes[src].get("kind", "")
            dst_kind = out.nodes[dst].get("kind", "")

            if dst_kind == "import":
                edge_kind = "imports"
            elif dst_kind == "class" and src_kind in ("module", "class"):
                edge_kind = "contains"
            elif dst_kind == "function":
                edge_kind = "contains"
            else:
                edge_kind = "contains"

            out.add_edge(src, dst, **make_edge(edge_kind))

        return out


# ── Register on import ────────────────────────────────────────────────────────
_instance = PythonLanguageParser()
ParserRegistry.register(_instance)
