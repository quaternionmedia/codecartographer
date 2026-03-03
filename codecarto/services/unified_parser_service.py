"""
Unified Parser Service
======================
Parses a directory tree (or individual files) into a single nx.DiGraph
using the unified node schema.  Language-specific parsers are looked up
in the ParserRegistry; the directory/file skeleton is always emitted as
depth-0 / depth-1 nodes so callers get a coherent hierarchy even when
no language parser is available for a given extension.

Depth levels
------------
0 : directory
1 : file
2 : top-level symbols (class, function, struct, enum, …)
3 : sub-symbols (arguments, fields, enum constants, …)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import networkx as nx

from codecarto.models.source_data import Directory, File, Folder
from codecarto.models.plot_data import PlotOptions
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.services.parsers.language_parser import (
    ParserRegistry,
    make_node,
    make_edge,
)

# ── Ensure parsers are registered ────────────────────────────────────────────
# Importing the adapters has the side-effect of calling ParserRegistry.register()
import codecarto.services.parsers.python_language_parser  # noqa: F401
import codecarto.services.parsers.c_language_parser       # noqa: F401
import codecarto.services.parsers.regex_language_parser   # noqa: F401


class UnifiedParserService:
    """Parse a Directory into a unified-schema graph and serialise to gJGF."""

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    def parse(
        directory: Directory,
        depth: int = 2,
        extensions: Optional[list[str]] = None,
        layout: str = "Spring",
    ) -> dict:
        """Parse *directory* up to *depth* and return a gJGF dict.

        Parameters
        ----------
        directory : Directory
            Source directory model (may be partial / shallow).
        depth : int
            0 = directories only, 1 = files, 2 = symbols, 3 = sub-symbols.
        extensions : list[str] | None
            File extensions to include (e.g. ['.py', '.c']).  When None,
            all registered extensions are included.
        layout : str
            Layout algorithm name passed to GraphSerializer.

        Returns
        -------
        dict
            gJGF graph dict (same shape as other plot endpoints).
        """
        graph = UnifiedParserService._build_graph(directory, depth, extensions)
        options = PlotOptions(layout=layout, type="d3")
        gjgf = GraphSerializer.serialize_to_gjgf(graph, options)
        meta = GraphSerializer.create_metadata(graph, options)
        return {"graph": gjgf, "metadata": meta}

    @staticmethod
    def expand_node(
        directory: Directory,
        node_id: str,
        depth: int = 2,
    ) -> dict:
        """Return ONLY the new nodes/edges revealed when expanding *node_id*.

        Currently re-parses the whole directory and returns the sub-graph
        rooted at *node_id*.  A future optimisation can cache partial results.

        Parameters
        ----------
        directory : Directory
        node_id : str
            ID of the node to expand (must be a file-level node, depth=1).
        depth : int
            Target depth after expansion (2 or 3).

        Returns
        -------
        dict
            Partial gJGF (only the new nodes + edges).
        """
        full_graph = UnifiedParserService._build_graph(
            directory, depth, extensions=None
        )

        if node_id not in full_graph:
            return {"graph": {}, "metadata": {"nodeCount": 0, "edgeCount": 0}}

        # Collect descendants
        descendants = nx.descendants(full_graph, node_id)
        sub = full_graph.subgraph({node_id} | descendants).copy()

        options = PlotOptions(layout="Spring", type="d3")
        gjgf = GraphSerializer.serialize_to_gjgf(sub, options)
        meta = GraphSerializer.create_metadata(sub, options)
        return {"graph": gjgf, "metadata": meta}

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_graph(
        directory: Directory,
        depth: int,
        extensions: Optional[list[str]],
    ) -> nx.DiGraph:
        """Walk the directory tree and build the unified graph."""
        allowed_exts = (
            {e.lower() for e in extensions}
            if extensions
            else set(ParserRegistry.all_extensions())
        )

        graph = nx.DiGraph()

        # Recursively walk; returns node_id of each folder added
        UnifiedParserService._walk_folder(
            graph,
            folder=directory.root,
            parent_id=None,
            depth=depth,
            allowed_exts=allowed_exts,
        )

        return graph

    @staticmethod
    def _walk_folder(
        graph: nx.DiGraph,
        folder: Folder,
        parent_id: Optional[str],
        depth: int,
        allowed_exts: set[str],
    ) -> str:
        """Add a depth-0 directory node and recurse into its contents."""
        folder_id = f"dir::{folder.name}"

        graph.add_node(
            folder_id,
            **make_node(
                folder_id,
                depth=0,
                language="unknown",
                kind="directory",
                label=folder.name,
                file="",
                line=0,
            ),
        )

        if parent_id is not None:
            graph.add_edge(parent_id, folder_id, **make_edge("contains"))

        if depth < 1:
            return folder_id

        # ── Files in this folder ──────────────────────────────────────────────
        files_by_ext: dict[str, list[File]] = {}
        for file in folder.files:
            ext = Path(file.name).suffix.lower()
            if ext not in allowed_exts:
                continue
            files_by_ext.setdefault(ext, []).append(file)

        for ext, file_list in files_by_ext.items():
            parser = ParserRegistry.get(ext) if depth >= 2 else None

            for file in file_list:
                file_id = f"file::{folder.name}/{file.name}"

                graph.add_node(
                    file_id,
                    **make_node(
                        file_id,
                        depth=1,
                        language=_ext_to_language(ext),
                        kind="file",
                        label=file.name,
                        file=file.url or file.name,
                        line=0,
                    ),
                )
                graph.add_edge(folder_id, file_id, **make_edge("contains"))

                # Dispatch to language parser for depth-2+ nodes
                if parser is not None and depth >= 2 and file.raw:
                    try:
                        sub = parser.parse_files([file], depth=depth)
                        _merge_subgraph(graph, sub, file_id)
                    except Exception:
                        pass  # Best-effort; directory structure still present

        # ── Subfolders ────────────────────────────────────────────────────────
        for subfolder in folder.folders:
            UnifiedParserService._walk_folder(
                graph, subfolder, folder_id, depth, allowed_exts
            )

        return folder_id


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ext_to_language(ext: str) -> str:
    parser = ParserRegistry.get(ext)
    return parser.language if parser is not None else "unknown"


def _merge_subgraph(
    graph: nx.DiGraph,
    sub: nx.DiGraph,
    file_node_id: str,
) -> None:
    """Merge *sub* into *graph*, connecting depth-1 file node to depth-2 roots."""
    graph.add_nodes_from(sub.nodes(data=True))
    graph.add_edges_from(sub.edges(data=True))

    # Connect file node → top-level symbols (depth=2 nodes with no parents in sub)
    sub_roots = {n for n in sub.nodes if sub.in_degree(n) == 0}
    for root in sub_roots:
        if not graph.has_edge(file_node_id, root):
            graph.add_edge(file_node_id, root, **make_edge("contains"))
