"""
Language Parser Protocol and Registry
======================================
Defines the interface that all language-specific parsers must implement,
and a registry for looking up parsers by file extension.

Unified Node Schema
-------------------
All parsers emit nodes with these attributes:

    depth    : int   0=directory, 1=file, 2=symbol, 3=sub-symbol
    language : str   'python' | 'c' | 'unknown'
    kind     : str   'directory' | 'file' | 'class' | 'function' |
                     'struct' | 'enum' | 'field' | 'import' | ...
    label    : str   display name
    file     : str   source file path (empty for directories)
    line     : int   source line (0 if not tracked)
    meta     : dict  language-specific extras (may include 'sides' for ngon shapes)
    shape    : str   visual shape hint for renderers ('circle' | 'square' | 'diamond' |
                     'hexagon' | 'triangle' | 'ngon' | 'star' | 'cross')
    color    : str   hex colour hint for renderers (e.g. '#4a9eff')

Parsers are responsible for setting shape and color so that language-specific
visual grammar lives in the parser, not in the renderer.  Renderers use these
hints directly and only fall back to their own logic when the fields are absent.

Edge kinds: 'contains' | 'calls' | 'imports' | 'inherits' |
            'type_of' | 'field_of' | 'aliases' | 'depends_on'

'depends_on' is a depth-1 (file-to-file) edge, distinct from 'imports'
(depth-1-to-depth-2, a module containing one of its own import
statements) — it's the resolved target of that import: another file in
this same parse, or a synthetic depth-1 node (kind='external_module',
language='external') for stdlib/third-party modules not present in the
parsed tree. See unified_parser_service.py's _add_python_dependency_edges.
"""

from __future__ import annotations

from typing import Protocol, ClassVar, runtime_checkable

import networkx as nx

from codecarto.models.source_data import File


@runtime_checkable
class LanguageParser(Protocol):
    """Protocol that all language-specific parsers must implement."""

    language: ClassVar[str]       # e.g. 'python', 'c'
    extensions: ClassVar[list[str]]  # e.g. ['.py'] or ['.c', '.h']

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        """Parse a list of files and return a graph with the unified node schema.

        Parameters
        ----------
        files : list[File]
            Files to parse (all of the same language).
        depth : int
            Maximum depth to parse (2 = symbols, 3 = sub-symbols).

        Returns
        -------
        nx.DiGraph
            Graph using the unified node schema.
        """
        ...


class ParserRegistry:
    """Registry mapping file extensions → LanguageParser implementations."""

    _parsers: dict[str, LanguageParser] = {}

    @classmethod
    def register(cls, parser: LanguageParser) -> None:
        """Register a parser for its declared file extensions."""
        for ext in parser.extensions:
            cls._parsers[ext.lower()] = parser

    @classmethod
    def get(cls, extension: str) -> LanguageParser | None:
        """Return the parser for *extension*, or None if not registered."""
        return cls._parsers.get(extension.lower())

    @classmethod
    def all_extensions(cls) -> list[str]:
        return list(cls._parsers.keys())

    @classmethod
    def all_parsers(cls) -> list[LanguageParser]:
        return list({id(p): p for p in cls._parsers.values()}.values())


# ── Unified schema helpers ────────────────────────────────────────────────────

def make_node(
    node_id: str,
    *,
    depth: int,
    language: str,
    kind: str,
    label: str,
    file: str = "",
    line: int = 0,
    meta: dict | None = None,
    shape: str | None = None,
    color: str | None = None,
) -> dict:
    """Return a node-attribute dict conforming to the unified schema.

    ``shape`` and ``color`` are visual hints consumed by the active renderer.
    Parsers should set these according to their language's visual grammar so
    that no language-specific logic is needed inside the renderer.
    """
    attrs: dict = {
        "depth": depth,
        "language": language,
        "kind": kind,
        "label": label,
        "file": file,
        "line": line,
        "meta": meta or {},
    }
    if shape is not None:
        attrs["shape"] = shape
    if color is not None:
        attrs["color"] = color
    return attrs


def make_edge(kind: str, weight: float = 1.0) -> dict:
    """Return an edge-attribute dict conforming to the unified schema."""
    return {"kind": kind, "weight": weight}
