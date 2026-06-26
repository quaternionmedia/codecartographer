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

import asyncio
import json
import math
import os
from pathlib import Path
from typing import AsyncIterator, Optional

import networkx as nx

from codecarto.models.source_data import Directory, File, Folder
from codecarto.models.plot_data import PlotOptions
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.services.parsers.language_parser import (
    ParserRegistry,
    make_node,
    make_edge,
)



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
    async def stream_parse(
        directory: Directory,
        depth: int = 2,
        extensions: Optional[list[str]] = None,
        layout: str = "Spring",
    ) -> AsyncIterator[str]:
        """Parse *directory* and yield SSE-formatted lines for each node/edge.

        SSE event format::

            event: meta
            data: {"nodeCount": N, "edgeCount": M, "layout": "Spring"}

            event: node
            data: {"id": "...", "x": 0.0, "y": 0.0, ...}

            event: edge
            data: {"source": "...", "target": "...", "relation": "..."}

            event: done
            data: {"elapsed_ms": 123}

        The generator is an async generator so FastAPI's StreamingResponse
        can yield to the event loop between items.
        """
        import time
        start = time.monotonic()

        graph = UnifiedParserService._build_graph(directory, depth, extensions)
        options = PlotOptions(layout=layout, type="d3")
        gjgf = GraphSerializer.serialize_to_gjgf(graph, options)

        # gJGF nodes is a dict {node_id: {"metadata": {...attrs...}}} (gravis format).
        # Flatten to a list of dicts matching what the streaming renderer expects:
        # {id: str, depth: int, kind: str, x: float, y: float, color: str, ...}
        nodes_raw: dict = gjgf.get("nodes", {})
        edges_raw: list = gjgf.get("edges", [])

        nodes_list = []
        for nid, nd in nodes_raw.items():
            if not isinstance(nd, dict):
                continue
            # gravis stores NetworkX node attrs under 'metadata'
            meta = nd.get("metadata", {})
            flat: dict = {"id": nid}
            # Direct attrs first (x, y, label may live here in some gravis versions)
            for k, v in nd.items():
                if k != "metadata":
                    flat[k] = v
            # metadata attrs override / supplement (depth, kind, shape, color, etc.)
            flat.update(meta)
            nodes_list.append(flat)

        # Yield meta event
        meta_event = {"nodeCount": len(nodes_list), "edgeCount": len(edges_raw), "layout": layout}
        yield f"event: meta\ndata: {json.dumps(meta_event)}\n\n"
        await asyncio.sleep(0)

        # Yield nodes sorted by depth (shallowest first = roots appear first)
        sorted_nodes = sorted(nodes_list, key=lambda n: (n.get("depth", 9), n.get("id", "")))
        for node in sorted_nodes:
            yield f"event: node\ndata: {json.dumps(node)}\n\n"
            await asyncio.sleep(0)

        # Yield edges
        for edge in edges_raw:
            yield f"event: edge\ndata: {json.dumps(edge)}\n\n"
            await asyncio.sleep(0)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        yield f"event: done\ndata: {json.dumps({'elapsed_ms': elapsed_ms})}\n\n"

    @staticmethod
    async def stream_parse_url(
        url: str,
        depth: int = 2,
        extensions: Optional[list[str]] = None,
        layout: str = "Spring",
    ) -> AsyncIterator[str]:
        """Two-phase SSE streaming directly from a GitHub URL.

        Phase 1 (fast): fetch directory tree structure (no file content) →
            compute layout → stream dir/file nodes with positions immediately.
        Phase 2 (concurrent): fetch each file's content in parallel →
            parse symbols → stream them with positions relative to parent.

        The client sees the skeleton graph within seconds and watches symbols
        fill in file-by-file, with no separate blocking repo-fetch step.
        """
        import time
        start = time.monotonic()

        from codecarto.services.github_service import (
            get_owner_repo_from_url,
            create_headers,
            get_raw_from_url,
            fetch_tree_fast,
            build_folder_from_tree_items,
            get_shallow_root,
        )
        from codecarto.models.source_data import RepoInfo, Directory as Dir

        yield f"event: fetching\ndata: {json.dumps({'message': 'Fetching repo tree\u2026'})}\n\n"
        await asyncio.sleep(0)

        try:
            owner, repo_name = get_owner_repo_from_url(url)
            headers = create_headers(url)
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
            return

        info = RepoInfo(owner=owner, name=repo_name, url=url)

        # ── Phase 1: full tree in TWO GitHub API calls ────────────────────────
        # fetch_tree_fast: GET /repos/{owner}/{repo} + GET /git/trees/HEAD?recursive=1
        # This replaces N+1 sequential calls with 2 parallel-ish calls.
        try:
            tree_items, default_branch = await fetch_tree_fast(owner, repo_name, headers, url)
        except Exception:
            # Fallback: very large / rate-limited → shallow root at depth=1
            try:
                root = await get_shallow_root(owner, repo_name, url, headers)
                root.name = f"{owner}/{repo_name}"
                directory = Dir(info=info, size=0, root=root, is_partial=True)
            except Exception as exc2:
                yield f"event: error\ndata: {json.dumps({'message': str(exc2)})}\n\n"
                return
            async for chunk in UnifiedParserService.stream_parse(
                directory, depth=1, extensions=extensions, layout=layout
            ):
                yield chunk
            return

        structure_root = build_folder_from_tree_items(tree_items, owner, repo_name)

        allowed_exts = (
            {e.lower() for e in extensions}
            if extensions
            else set(ParserRegistry.all_extensions())
        )

        # Build depth=1 graph and compute layout positions
        g_structure = nx.DiGraph()
        UnifiedParserService._walk_folder(
            g_structure, structure_root, None, depth=1, allowed_exts=allowed_exts
        )
        options = PlotOptions(layout=layout, type="d3")
        gjgf_struct = GraphSerializer.serialize_to_gjgf(g_structure, options)

        # Flatten structure nodes (positions are inside gjgf metadata)
        nodes_raw = gjgf_struct.get("nodes", {})
        edges_raw = gjgf_struct.get("edges", [])
        struct_nodes: list[dict] = []
        positions: dict[str, tuple[float, float]] = {}

        for nid, nd in (nodes_raw.items() if isinstance(nodes_raw, dict) else []):
            if not isinstance(nd, dict):
                continue
            meta = nd.get("metadata", {})
            flat: dict = {"id": nid}
            for k, v in nd.items():
                if k != "metadata":
                    flat[k] = v
            flat.update(meta)
            struct_nodes.append(flat)
            x, y = flat.get("x"), flat.get("y")
            if x is not None and y is not None:
                positions[nid] = (float(x), float(y))

        sorted_struct = sorted(struct_nodes, key=lambda n: (n.get("depth", 9), n.get("id", "")))

        yield f"event: meta\ndata: {json.dumps({'nodeCount': len(sorted_struct), 'edgeCount': len(edges_raw), 'layout': layout, 'phase': 'structure'})}\n\n"
        await asyncio.sleep(0)

        for node in sorted_struct:
            yield f"event: node\ndata: {json.dumps(node)}\n\n"
            await asyncio.sleep(0)

        for edge in edges_raw:
            yield f"event: edge\ndata: {json.dumps(edge)}\n\n"
            await asyncio.sleep(0)

        if depth < 2:
            elapsed = int((time.monotonic() - start) * 1000)
            yield f"event: done\ndata: {json.dumps({'elapsed_ms': elapsed})}\n\n"
            return

        # ── Phase 2: fetch content + parse symbols concurrently ───────────────
        parseable: list[tuple[str, str, str]] = []
        _collect_parseable(structure_root, structure_root.name, allowed_exts, parseable)

        if not parseable:
            elapsed = int((time.monotonic() - start) * 1000)
            yield f"event: done\ndata: {json.dumps({'elapsed_ms': elapsed})}\n\n"
            return

        yield f"event: phase\ndata: {json.dumps({'phase': 'symbols', 'fileCount': len(parseable)})}\n\n"
        await asyncio.sleep(0)

        semaphore = asyncio.Semaphore(8)

        async def fetch_and_parse_file(
            folder_name: str, file_name: str, dl_url: str
        ) -> list[str]:
            ext = Path(file_name).suffix.lower()
            parser = ParserRegistry.get(ext)
            if parser is None:
                return []
            async with semaphore:
                try:
                    raw = await get_raw_from_url(dl_url)
                except Exception:
                    return []
            try:
                sf = File(url=dl_url, name=file_name, size=0, raw=raw)
                sub = parser.parse_files([sf], depth=depth)
            except Exception:
                return []

            if sub.number_of_nodes() == 0:
                return []

            file_id = f"file::{folder_name}/{file_name}"
            px, py = positions.get(file_id, (0.0, 0.0))

            sym_nodes = list(sub.nodes(data=True))
            n_sym = len(sym_nodes)
            events: list[str] = []

            for i, (nid, ndata) in enumerate(sym_nodes):
                angle = 2 * math.pi * i / max(n_sym, 1)
                depth_val = ndata.get("depth", 2)
                radius = 25 + 12 * max(depth_val - 2, 0)
                flat: dict = {"id": nid, "x": px + radius * math.cos(angle), "y": py + radius * math.sin(angle)}
                flat.update(ndata)
                flat["x"] = px + radius * math.cos(angle)  # ensure override
                flat["y"] = py + radius * math.sin(angle)
                events.append(f"event: node\ndata: {json.dumps(flat)}\n\n")

            for src, tgt, edata in sub.edges(data=True):
                fe: dict = {"source": src, "target": tgt}
                fe.update(edata)
                events.append(f"event: edge\ndata: {json.dumps(fe)}\n\n")

            sub_roots = {n for n in sub.nodes if sub.in_degree(n) == 0}
            for root_id in sub_roots:
                events.append(f"event: edge\ndata: {json.dumps({'source': file_id, 'target': root_id, 'relation': 'contains'})}\n\n")

            return events

        tasks = [
            asyncio.create_task(fetch_and_parse_file(fn, fname, du))
            for fn, fname, du in parseable
        ]

        for coro in asyncio.as_completed(tasks):
            file_events = await coro
            for ev in file_events:
                yield ev
                await asyncio.sleep(0)

        elapsed = int((time.monotonic() - start) * 1000)
        yield f"event: done\ndata: {json.dumps({'elapsed_ms': elapsed})}\n\n"

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

def _collect_parseable(
    folder: Folder,
    folder_name: str,
    allowed_exts: set[str],
    result: list[tuple[str, str, str]],
) -> None:
    """Recursively collect (folder_name, file_name, download_url) for parseable files."""
    for f in folder.files:
        ext = Path(f.name).suffix.lower()
        if ext in allowed_exts and f.url:
            result.append((folder_name, f.name, f.url))
    for sub in folder.folders:
        _collect_parseable(sub, sub.name, allowed_exts, result)


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
