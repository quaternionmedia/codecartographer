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
from typing import AsyncIterator, Callable, Iterable, Optional, TypeVar

import networkx as nx

from codecarto.models.source_data import Directory, File, Folder
from codecarto.models.plot_data import PlotOptions
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.services.lexicon_bridge import annotate_graph_with_lexicon
from codecarto.services.lexicon_service import LexiconService
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
        annotate_lexicon: bool = False,
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
        annotate_lexicon : bool
            Stamp Lexicon abstraction-layer data onto nodes whose language
            has one (see lexicon_bridge.py). Opt-in: off by default so
            parses nobody asked to annotate pay no extra cost. Not (yet)
            threaded through stream_parse/stream_parse_url — deliberately
            scoped to this non-streaming entry point for its first pass.

        Returns
        -------
        dict
            gJGF graph dict (same shape as other plot endpoints).
        """
        graph = UnifiedParserService.build_graph(
            directory, depth, extensions, annotate_lexicon=annotate_lexicon
        )
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
        annotate_lexicon: bool = False,
    ) -> AsyncIterator[str]:
        """Parse *directory* and yield SSE-formatted lines for each node/edge.

        SSE event format::

            event: meta
            data: {"nodeCount": N, "edgeCount": M, "layout": "Spring"}

            event: node
            data: {"id": "...", "x": 0.0, "y": 0.0, ...}

            event: edge
            data: {"source": "...", "target": "...", "metadata": {"kind": "contains", ...}}

            event: done
            data: {"elapsed_ms": 123}

        The generator is an async generator so FastAPI's StreamingResponse
        can yield to the event loop between items.
        """
        import time
        start = time.monotonic()

        graph = UnifiedParserService.build_graph(
            directory, depth, extensions, annotate_lexicon=annotate_lexicon
        )
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
        annotate_lexicon: bool = False,
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
            _CONTENT_FETCH_LIMIT_KB,
        )
        from codecarto.services.cache_service import CacheService
        from codecarto.models.source_data import RepoInfo, Directory as Dir
        from codecarto.util.exceptions import GithubError

        # If github_service.get_raw_from_repo (the /repo/tree Source-tab
        # fetch) already cached this repo's tree with content baked in, skip
        # the live GitHub fetch entirely and parse the cached tree offline —
        # this is the common case since the frontend always fetches the
        # repo tree before plotting it. Structure-only/partial cache entries
        # (medium/huge repos) fall through to the live fetch below, since
        # they don't carry the file content parsing needs.
        cached_tree = CacheService.get_tree(url)
        if cached_tree is not None:
            cached_dir = Dir.model_validate(cached_tree)
            if not cached_dir.is_partial and cached_dir.size < _CONTENT_FETCH_LIMIT_KB:
                async for chunk in UnifiedParserService.stream_parse(
                    cached_dir, depth=depth, extensions=extensions, layout=layout
                ):
                    yield chunk
                return

        _fetching_msg = json.dumps({"message": "Fetching repo tree\u2026"})
        yield f"event: fetching\ndata: {_fetching_msg}\n\n"
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
            tree_items, default_branch, _size_kb, truncated = await fetch_tree_fast(
                owner, repo_name, headers, url
            )
            if truncated:
                raise GithubError("Tree response truncated", {"url": url})
        except Exception:
            # Fallback: very large / rate-limited / truncated → shallow root at depth=1
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

        # Build depth=1 graph and compute layout positions. depth=1 never
        # dispatches to a language parser, so there's nothing to batch.
        g_structure = nx.DiGraph()
        UnifiedParserService._walk_folder(
            g_structure, structure_root, None, depth=1, allowed_exts=allowed_exts, pending={}
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
        _collect_parseable(structure_root, allowed_exts, parseable)

        if not parseable:
            elapsed = int((time.monotonic() - start) * 1000)
            yield f"event: done\ndata: {json.dumps({'elapsed_ms': elapsed})}\n\n"
            return

        yield f"event: phase\ndata: {json.dumps({'phase': 'symbols', 'fileCount': len(parseable)})}\n\n"
        await asyncio.sleep(0)

        semaphore = asyncio.Semaphore(8)

        # Collected across every fetch_and_parse_file call below (Python is
        # never batch_whole_tree, so it always goes through that path) —
        # used once all files have arrived to resolve real depends_on edges
        # the same way _add_python_dependency_edges does for the in-memory
        # path. Can't resolve incrementally per-file: a file imported by an
        # earlier-completing file might not have arrived yet, same reason
        # C's cross-file calls edges wait for the full batch.
        python_raw_by_file_id: dict[str, str] = {}
        dependency_file_id_by_stem: dict[str, str] = {}

        async def fetch_raw(dl_url: str) -> Optional[str]:
            async with semaphore:
                try:
                    return await get_raw_from_url(dl_url)
                except Exception:
                    return None

        def position_for(file_id: str) -> tuple[float, float]:
            return positions.get(file_id, (0.0, 0.0))

        def node_events_for(sub: nx.DiGraph, file_id_by_stem: dict[str, str]) -> list[str]:
            """Place each node near its origin file's position (grouped, so
            files batched together don't all collapse onto the same point),
            then emit node events followed by edge events."""
            events: list[str] = []
            by_file: dict[str, list[tuple[str, dict]]] = {}
            for nid, ndata in sub.nodes(data=True):
                fid = file_id_by_stem.get(ndata.get("file", ""), "")
                by_file.setdefault(fid, []).append((nid, ndata))

            for file_id, sym_nodes in by_file.items():
                px, py = position_for(file_id)
                n_sym = len(sym_nodes)
                for i, (nid, ndata) in enumerate(sym_nodes):
                    angle = 2 * math.pi * i / max(n_sym, 1)
                    depth_val = ndata.get("depth", 2)
                    radius = 25 + 12 * max(depth_val - 2, 0)
                    flat: dict = {"id": nid}
                    flat.update(ndata)
                    flat["x"] = px + radius * math.cos(angle)
                    flat["y"] = py + radius * math.sin(angle)
                    events.append(f"event: node\ndata: {json.dumps(flat)}\n\n")

            for src, tgt, edata in sub.edges(data=True):
                fe: dict = {"source": src, "target": tgt}
                fe.update(edata)
                events.append(f"event: edge\ndata: {json.dumps(fe)}\n\n")

            # depth=2 nodes get a direct file->symbol contains edge (same
            # rule as _merge_batch_subgraph); depth=3 nodes already have a
            # structural edge from their parent (e.g. FIELD_OF).
            for nid, ndata in sub.nodes(data=True):
                if ndata.get("depth") != 2:
                    continue
                fid = file_id_by_stem.get(ndata.get("file", ""))
                if fid:
                    events.append(f"event: edge\ndata: {json.dumps({'source': fid, 'target': nid, 'kind': 'contains'})}\n\n")

            return events

        async def fetch_and_parse_file(
            folder_name: str, file_name: str, dl_url: str, parser
        ) -> list[str]:
            """Per-file dispatch for parsers that don't need the whole tree
            at once — same progressive-streaming behavior as before."""
            raw = await fetch_raw(dl_url)
            if raw is None:
                return []
            file_id = f"file::{folder_name}/{file_name}"
            if getattr(parser, "language", None) == "python":
                python_raw_by_file_id[file_id] = raw
                dependency_file_id_by_stem[Path(file_name).stem] = file_id
            try:
                sf = File(url=dl_url, name=file_name, size=0, raw=raw)
                sub = parser.parse_files([sf], depth=depth)
            except Exception:
                return []
            if sub.number_of_nodes() == 0:
                return []
            if annotate_lexicon:
                annotate_graph_with_lexicon(sub, getattr(parser, "language", ""))
            return node_events_for(sub, {Path(file_name).stem: file_id})

        async def fetch_and_parse_batch(
            parser, entries: list[tuple[str, str, str]]
        ) -> list[str]:
            """batch_whole_tree dispatch: fetch every file first, THEN parse
            them together in one call so cross-file references resolve —
            see CLangaugeParser.batch_whole_tree. Less progressive (nothing
            streams until the whole batch's fetches finish) but structurally
            correct, same trade-off as the pre-fetched-directory path."""
            raws = await asyncio.gather(*(fetch_raw(du) for _, _, du in entries))
            files: list[File] = []
            file_id_by_stem: dict[str, str] = {}
            for (folder_name, file_name, dl_url), raw in zip(entries, raws):
                if raw is None:
                    continue
                files.append(File(url=dl_url, name=file_name, size=0, raw=raw))
                file_id_by_stem[Path(file_name).stem] = f"file::{folder_name}/{file_name}"

            if not files:
                return []
            try:
                # parser.parse_files() is synchronous, CPU-bound libclang
                # work that can take tens of seconds for a large batch — run
                # it off the event loop so it doesn't freeze every other
                # request this server is handling (same reasoning as
                # c_parser_router.py's /c-parser/stream-github thread).
                sub = await asyncio.to_thread(parser.parse_files, files, depth=depth)
            except Exception:
                return []
            if sub.number_of_nodes() == 0:
                return []
            if annotate_lexicon:
                annotate_graph_with_lexicon(sub, getattr(parser, "language", ""))
            return node_events_for(sub, file_id_by_stem)

        # Split into per-file (progressive) vs batch_whole_tree (correctness
        # over progressiveness — e.g. C, for cross-file CALLS resolution).
        per_file, batched = _split_by_batch_mode(
            parseable,
            ext_of=lambda item: Path(item[1]).suffix.lower(),
        )

        tasks = [
            asyncio.create_task(fetch_and_parse_file(*item, parser))
            for item, parser in per_file
        ] + [
            asyncio.create_task(fetch_and_parse_batch(parser, entries))
            for parser, entries in batched.values()
        ]

        for coro in asyncio.as_completed(tasks):
            file_events = await coro
            for ev in file_events:
                yield ev
                await asyncio.sleep(0)

        # Now that every Python file has arrived, resolve real depends_on
        # edges (and synthetic external-module nodes) the same way
        # _add_python_dependency_edges does for the in-memory path — see
        # _resolve_python_dependencies for the shared resolution logic.
        if python_raw_by_file_id:
            internal_edges, external_refs = _resolve_python_dependencies(
                dependency_file_id_by_stem, python_raw_by_file_id
            )

            # _resolve_python_dependencies returns one entry per import
            # statement, undeduped (a file importing the same module twice,
            # or two submodules of the same package, is common) — the
            # in-memory path dedupes via graph.has_edge(); SSE events have
            # no such backing store, so dedupe explicitly here.
            seen_edges: set[tuple[str, str]] = set()

            for src, tgt in internal_edges:
                if (src, tgt) in seen_edges:
                    continue
                seen_edges.add((src, tgt))
                yield f"event: edge\ndata: {json.dumps({'source': src, 'target': tgt, 'kind': 'depends_on'})}\n\n"
                await asyncio.sleep(0)

            external_ids: dict[str, str] = {}
            for src, top_level in external_refs:
                ext_id = external_ids.get(top_level)
                if ext_id is None:
                    ext_id = f"external::{top_level}"
                    external_ids[top_level] = ext_id
                    ext_px, ext_py = position_for(src)
                    ext_node = {
                        "id": ext_id,
                        **make_node(
                            ext_id, depth=1, language="external", kind="external_module",
                            label=top_level, file="", line=0, shape="circle", color="#5a5a5a",
                        ),
                        "x": ext_px, "y": ext_py,
                    }
                    yield f"event: node\ndata: {json.dumps(ext_node)}\n\n"
                    await asyncio.sleep(0)
                if (src, ext_id) in seen_edges:
                    continue
                seen_edges.add((src, ext_id))
                yield f"event: edge\ndata: {json.dumps({'source': src, 'target': ext_id, 'kind': 'depends_on'})}\n\n"
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
        full_graph = UnifiedParserService.build_graph(
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
    def build_graph(
        directory: Directory,
        depth: int,
        extensions: Optional[list[str]],
        annotate_lexicon: bool = False,
    ) -> nx.DiGraph:
        """Walk the directory tree and build the unified graph.

        Public (not underscore-prefixed) since callers outside parse()/
        stream_parse()/expand_node() legitimately want the raw nx.DiGraph
        before gJGF serialization — e.g. cli.py's `repo graph` command.
        """
        allowed_exts = (
            {e.lower() for e in extensions}
            if extensions
            else set(ParserRegistry.all_extensions())
        )

        graph = nx.DiGraph()

        # Parsers that opt into batch_whole_tree (see CLangaugeParser) need
        # every one of their files at once to resolve cross-file references
        # — e.g. C's CALLS edges. Collected here during the walk, parsed
        # together once the whole tree (not just one folder) is known.
        # Keyed by id(parser), not extension — a parser can own several
        # extensions (CLangaugeParser handles .c/.h/.cpp/...) that must all
        # land in the SAME batch, or cross-file/cross-extension references
        # (a .c file's #include of a sibling .h) won't resolve.
        pending: dict[int, tuple[object, list[tuple[File, str]]]] = {}

        # Recursively walk; returns node_id of each folder added
        UnifiedParserService._walk_folder(
            graph,
            folder=directory.root,
            parent_id=None,
            depth=depth,
            allowed_exts=allowed_exts,
            pending=pending,
        )

        if pending:
            _parse_pending_batches(graph, pending, depth)

        if depth >= 2:
            _add_python_dependency_edges(graph, directory.root, allowed_exts)

        if annotate_lexicon:
            # A single graph can span multiple languages (a repo isn't
            # mono-language) - annotate each one present that also has a
            # lexicon, rather than assuming a single language for the
            # whole graph.
            languages = {data.get("language") for _, data in graph.nodes(data=True)}
            for language in languages & set(LexiconService.available()):
                annotate_graph_with_lexicon(graph, language)

        return graph

    @staticmethod
    def _walk_folder(
        graph: nx.DiGraph,
        folder: Folder,
        parent_id: Optional[str],
        depth: int,
        allowed_exts: set[str],
        pending: dict[int, tuple[object, list[tuple[File, str]]]],
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

        # First pass: add all file nodes to the graph.
        # Collect items that need depth-2 parsing for a separate dispatch step.
        parseable_files: list[tuple[File, str]] = []
        for ext, file_list in files_by_ext.items():
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

                if depth >= 2 and file.raw:
                    parseable_files.append((file, file_id))

        # Second pass: split by batch mode and dispatch.
        if parseable_files:
            per_item, batch_items = _split_by_batch_mode(
                parseable_files,
                ext_of=lambda item: Path(item[0].name).suffix.lower(),
            )
            for (file, file_id), parser in per_item:
                try:
                    sub = parser.parse_files([file], depth=depth)
                    _merge_subgraph(graph, sub, file_id)
                except Exception:
                    pass  # Best-effort; directory structure still present
            for key, (parser, items) in batch_items.items():
                if key not in pending:
                    pending[key] = (parser, [])
                pending[key][1].extend(items)

        # ── Subfolders ────────────────────────────────────────────────────────
        for subfolder in folder.folders:
            UnifiedParserService._walk_folder(
                graph, subfolder, folder_id, depth, allowed_exts, pending
            )

        return folder_id


# ── Helpers ───────────────────────────────────────────────────────────────────

_T = TypeVar("_T")


def _split_by_batch_mode(
    items: Iterable[_T],
    ext_of: Callable[[_T], str],
) -> tuple[list[tuple[_T, object]], dict[int, tuple[object, list[_T]]]]:
    """Group items by whether their registered parser uses ``batch_whole_tree``.

    Returns
    -------
    per_item : list of (item, parser)
        Items whose parser should be dispatched file-by-file (progressive).
    batched : dict mapping id(parser) → (parser, [items])
        Items whose parser requires the full set at once (e.g. C, for
        cross-file CALLS/type resolution — see CLangaugeParser.batch_whole_tree).

    The two call sites' downstream handling is intentionally kept separate:
    the GitHub-streaming path emits SSE events via ``node_events_for``; the
    local-directory path merges into an ``nx.DiGraph`` via ``_merge_subgraph``
    / ``_parse_pending_batches``.  Only the *grouping step* is shared here.
    """
    per_item: list[tuple[_T, object]] = []
    batched: dict[int, tuple[object, list[_T]]] = {}
    for item in items:
        parser = ParserRegistry.get(ext_of(item))
        if parser is None:
            continue
        if getattr(parser, "batch_whole_tree", False):
            key = id(parser)
            if key not in batched:
                batched[key] = (parser, [])
            batched[key][1].append(item)
        else:
            per_item.append((item, parser))
    return per_item, batched

def _collect_parseable(
    folder: Folder,
    allowed_exts: set[str],
    result: list[tuple[str, str, str]],
) -> None:
    """Collect (folder_name, file_name, download_url) for parseable files."""
    for owning_folder, f in folder.iter_files():
        ext = Path(f.name).suffix.lower()
        if ext in allowed_exts and f.url:
            result.append((owning_folder.name, f.name, f.url))


def _ext_to_language(ext: str) -> str:
    parser = ParserRegistry.get(ext)
    return parser.language if parser is not None else "unknown"


def _resolve_python_dependencies(
    file_id_by_stem: dict[str, str],
    raw_by_file_id: dict[str, str],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Resolve each file's import statements against the other Python files
    already known in this parse (*file_id_by_stem*) — the shared resolution
    core behind both build_graph()'s in-memory pass
    (_add_python_dependency_edges) and stream_parse_url's incremental SSE
    pass, the unified-pipeline counterpart to the old standalone
    DependencyParser.

    Resolution is stem-based (filename without extension), matching this
    module's existing id scheme (file_id = "file::{parent_dir}/{name}", not
    a full repo-relative path) — two files sharing a stem (e.g. two
    packages each with their own __init__.py) can't be disambiguated; the
    last one registered in *file_id_by_stem* wins. Pre-existing limitation
    of this id scheme, not introduced here.

    Returns
    -------
    internal_edges : list of (source_file_id, target_file_id)
        Imports that resolved to another file already in *file_id_by_stem*.
    external_refs : list of (source_file_id, top_level_module_name)
        Imports that didn't resolve (stdlib, third-party, or just not part
        of this parse) — caller decides how to dedupe / create nodes for
        these (one entry per import statement, not deduped here).
    """
    from codecarto.services.parsers.python_language_parser import extract_python_imports

    internal_edges: list[tuple[str, str]] = []
    external_refs: list[tuple[str, str]] = []

    for file_id, raw in raw_by_file_id.items():
        for module in extract_python_imports(raw):
            target_stem = module.rsplit(".", 1)[-1]
            target_id = file_id_by_stem.get(target_stem)
            if target_id and target_id != file_id:
                internal_edges.append((file_id, target_id))
                continue
            top_level = module.split(".", 1)[0]
            external_refs.append((file_id, top_level))

    return internal_edges, external_refs


def _add_python_dependency_edges(
    graph: nx.DiGraph,
    root: Folder,
    allowed_exts: set[str],
) -> None:
    """Resolve each Python file's imports to real file-to-file 'depends_on'
    edges, mutating *graph* in place — the in-memory (non-streaming)
    counterpart to stream_parse_url's incremental version below. Both share
    _resolve_python_dependencies for the actual resolution.

    Unresolved imports (stdlib, third-party, or anything not present in
    this parse) get a synthetic depth-1 'external_module' node instead,
    one per top-level package name — e.g. 'requests.adapters' and
    'requests.models' both point at a single 'external::requests' node,
    coarser than per-submodule, deliberately, to keep the dependency view
    legible for repos that import a lot of stdlib.

    No-op if '.py' isn't in *allowed_exts*, or the graph has no python
    depth=1 nodes (e.g. a pure-C repo).
    """
    if ".py" not in allowed_exts:
        return

    # kind == "file" specifically — PythonCustomAST also emits its own
    # depth=1 "module" node per file (id like "a.a", same stem as the
    # structural file:: node) which is NOT what dependency edges should
    # point at, or every internal import would resolve to a redundant
    # module node alongside (or instead of) the real file:: node.
    file_id_by_stem: dict[str, str] = {}
    for node_id, data in graph.nodes(data=True):
        if data.get("depth") == 1 and data.get("kind") == "file" and data.get("language") == "python":
            stem = Path(data.get("label", "")).stem
            if stem:
                file_id_by_stem[stem] = node_id

    if not file_id_by_stem:
        return

    raw_by_file_id: dict[str, str] = {}
    for _, file in root.iter_files():
        if Path(file.name).suffix.lower() != ".py" or not file.raw:
            continue
        file_id = file_id_by_stem.get(Path(file.name).stem)
        if file_id:
            raw_by_file_id[file_id] = file.raw

    internal_edges, external_refs = _resolve_python_dependencies(file_id_by_stem, raw_by_file_id)

    for src, tgt in internal_edges:
        if not graph.has_edge(src, tgt):
            graph.add_edge(src, tgt, **make_edge("depends_on"))

    external_ids: dict[str, str] = {}
    for src, top_level in external_refs:
        ext_id = external_ids.get(top_level)
        if ext_id is None:
            ext_id = f"external::{top_level}"
            external_ids[top_level] = ext_id
            graph.add_node(ext_id, **make_node(
                ext_id,
                depth=1,
                language="external",
                kind="external_module",
                label=top_level,
                file="",
                line=0,
                shape="circle",
                color="#5a5a5a",
            ))
        if not graph.has_edge(src, ext_id):
            graph.add_edge(src, ext_id, **make_edge("depends_on"))


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


def _parse_pending_batches(
    graph: nx.DiGraph,
    pending: dict[int, tuple[object, list[tuple[File, str]]]],
    depth: int,
) -> None:
    """Parse each batch_whole_tree parser's files together (one call per
    parser, covering every extension it owns across the whole tree) and
    merge the results.

    Unlike _merge_subgraph's per-file dispatch, a batch's resulting nodes
    can come from any of its files, so attribution back to the right
    depth-1 file node uses each node's `file` attribute (a stem, set by the
    language parser — see CLangaugeParser) rather than assuming the whole
    subgraph belongs to one file.
    """
    for parser, file_entries in pending.values():
        files = [f for f, _ in file_entries]
        file_id_by_stem = {Path(f.name).stem: fid for f, fid in file_entries}

        try:
            sub = parser.parse_files(files, depth=depth)
        except Exception:
            continue  # Best-effort; directory structure still present

        _merge_batch_subgraph(graph, sub, file_id_by_stem)


def _merge_batch_subgraph(
    graph: nx.DiGraph,
    sub: nx.DiGraph,
    file_id_by_stem: dict[str, str],
) -> None:
    """Merge a whole-tree batch's subgraph, attributing each top-level
    (depth=2) node to its origin file via the node's `file` stem.

    Depth=3 nodes (fields, enum constants, …) are deliberately NOT given a
    direct file edge — they already have a structural edge from their
    depth-2 parent (e.g. FIELD_OF), same as the single-file path.
    """
    graph.add_nodes_from(sub.nodes(data=True))
    graph.add_edges_from(sub.edges(data=True))

    for node_id, data in sub.nodes(data=True):
        if data.get("depth") != 2:
            continue
        file_id = file_id_by_stem.get(data.get("file", ""))
        if file_id and not graph.has_edge(file_id, node_id):
            graph.add_edge(file_id, node_id, **make_edge("contains"))
