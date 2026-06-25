"""
C/C++ Language Parser
=====================
Implements the LanguageParser protocol for C and C++ source files.
Wraps CParser (libclang-based) and converts its {nodes, edges, meta} dict
to the unified nx.DiGraph node schema.  libclang handles C++ natively, so
the same adapter covers .c/.h as well as .cpp/.cc/.cxx/.hpp/.hxx.

Node schema mapping
-------------------
C kind          → unified kind      depth
function        → 'function'        2
struct          → 'struct'          2
union           → 'union'           2
enum            → 'enum'            2
typedef         → 'typedef'         2
macro           → 'macro'           2
variable        → 'variable'        2
field           → 'field'           3
enum_constant   → 'enum_constant'   3
"""

from __future__ import annotations

from typing import ClassVar
from pathlib import Path

import networkx as nx

from codecarto.models.source_data import File
from codecarto.services.parsers.language_parser import (
    LanguageParser,
    ParserRegistry,
    make_node,
    make_edge,
)


# ── Depth assignment ──────────────────────────────────────────────────────────

_DEPTH_2_KINDS = {
    "function", "struct", "union", "enum", "typedef", "macro", "variable",
}
_DEPTH_3_KINDS = {
    "field", "enum_constant",
}

# ── C visual grammar ──────────────────────────────────────────────────────────
# Shape and colour per C kind, matching the c-visualizer reference design.
# The renderer reads these directly — no language logic belongs in the renderer.

_C_SHAPE: dict[str, str] = {
    "struct":        "ngon",      # sides derived from field_count (see meta['sides'])
    "union":         "ngon",
    "function":      "diamond",
    "enum":          "circle",
    "enum_constant": "diamond",
    "typedef":       "circle",
    "field":         "square",
    "variable":      "circle",
    "macro":         "circle",
}

_C_COLOR: dict[str, str] = {
    "struct":        "#4a9eff",
    "union":         "#6ab0e8",
    "function":      "#ff9d3d",
    "enum":          "#a855f7",
    "enum_constant": "#6d28d9",
    "typedef":       "#22d3ee",
    "field":         "#3d5070",
    "variable":      "#607090",
    "macro":         "#7f8c8d",
}

# C edge kind → unified edge kind
_EDGE_KIND_MAP: dict[str, str] = {
    "FIELD_OF":  "field_of",
    "CALLS":     "calls",
    "POINTS_TO": "type_of",
    "ALIASES":   "aliases",
}


class CLangaugeParser:
    """LanguageParser implementation for C/H source files.

    Falls back gracefully when libclang is not installed: parse_files()
    returns an empty graph rather than raising an ImportError.
    """

    language: ClassVar[str] = "c"
    extensions: ClassVar[list[str]] = [".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx"]

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        """Parse C/H files and return a unified-schema graph.

        Parameters
        ----------
        files : list[File]
            C/H source files. Each must have a non-empty ``url`` field
            that is a valid filesystem path (the CParser needs real files).
        depth : int
            Maximum depth (2 = top-level symbols, 3 = fields/enum constants).

        Returns
        -------
        nx.DiGraph with unified node schema.
        """
        try:
            from codecarto.services.parsers.c_parser import CParser
        except ImportError:
            # libclang not available; return empty graph
            return nx.DiGraph()

        # Resolve filesystem paths from File.url (real paths) or File.name
        paths = []
        for f in files:
            candidate = Path(f.url) if f.url else Path(f.name)
            if candidate.exists():
                paths.append(candidate)

        if not paths:
            return nx.DiGraph()

        raw: dict = CParser().parse_files(paths)
        return self._convert(raw, depth)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _convert(self, raw: dict, max_depth: int) -> nx.DiGraph:
        """Convert CParser {nodes, edges, meta} dict to unified schema graph."""
        out = nx.DiGraph()

        c_nodes: list[dict] = raw.get("nodes", [])
        c_edges: list[dict] = raw.get("edges", [])

        # ── Pass 1: nodes ─────────────────────────────────────────────────────
        for n in c_nodes:
            nid       = n["id"]
            c_kind    = n.get("kind", "")
            name      = n.get("name", nid)
            file_stem = n.get("file", "")
            line      = n.get("line", 0)

            if c_kind in _DEPTH_2_KINDS:
                node_depth = 2
                unified_kind = c_kind
            elif c_kind in _DEPTH_3_KINDS:
                node_depth = 3
                unified_kind = c_kind
            else:
                node_depth = 2
                unified_kind = c_kind or "symbol"

            if node_depth > max_depth:
                continue

            # Collect C-specific metadata
            meta: dict = {
                "qualifiers": n.get("qualifiers", []),
                "type_str":   n.get("type_str", ""),
            }
            if "field_count"  in n: meta["field_count"]  = n["field_count"]
            if "member_count" in n: meta["member_count"] = n["member_count"]
            if "param_count"  in n: meta["param_count"]  = n["param_count"]
            if "is_definition" in n: meta["is_definition"] = n["is_definition"]

            # For ngon shapes (struct/union), expose sides so the renderer can
            # draw the correct polygon without knowing it is a C struct.
            if c_kind in ("struct", "union"):
                meta["sides"] = min(max(int(n.get("field_count", 4)), 3), 10)

            attrs = make_node(
                nid,
                depth=node_depth,
                language="c",
                kind=unified_kind,
                label=name,
                file=file_stem,
                line=line,
                meta=meta,
                shape=_C_SHAPE.get(c_kind),
                color=_C_COLOR.get(c_kind),
            )
            out.add_node(nid, **attrs)

        # ── Pass 2: edges ─────────────────────────────────────────────────────
        for e in c_edges:
            src  = e.get("src")
            dst  = e.get("dst")
            kind = e.get("kind", "")
            weight = float(e.get("weight", 1.0))

            if not (out.has_node(src) and out.has_node(dst)):
                continue

            unified_kind = _EDGE_KIND_MAP.get(kind, "contains")
            out.add_edge(src, dst, **make_edge(unified_kind, weight))

        return out


# ── Register on import ────────────────────────────────────────────────────────
_instance = CLangaugeParser()
ParserRegistry.register(_instance)
