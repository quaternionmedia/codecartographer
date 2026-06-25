"""
Unified Parser Router
=====================
Endpoints for the unified codebase graph architecture.

POST /parse/unified       — parse a full directory tree to a given depth
POST /parse/stream        — SSE streaming parse (nodes sent one-by-one)
POST /parse/expand        — expand a single node (file → symbols)
GET  /parse/languages     — list registered parser extensions
GET  /parse/cache         — list cached graphs
DELETE /parse/cache/{key} — evict a cached graph
"""

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from codecarto.models.source_data import Directory, RepoInfo, Folder, File
from codecarto.util.exceptions import CodeCartoException, proc_exception
from codecarto.util.utilities import generate_return

UnifiedParserRouter = APIRouter()


# ── Request bodies ─────────────────────────────────────────────────────────────

MODE_TO_DEPTH: dict[str, int] = {
    'directory':    1,
    'ast':          2,
    'dependencies': 2,
}


class UnifiedParseRequest(BaseModel):
    directory: Directory
    depth: int = 2
    mode: Optional[str] = None   # 'directory' | 'ast' | 'dependencies'
    extensions: Optional[list[str]] = None
    layout: str = "Spring"


class ExpandNodeRequest(BaseModel):
    directory: Directory
    node_id: str
    depth: int = 2


class StreamUrlRequest(BaseModel):
    url: str
    depth: int = 2
    mode: Optional[str] = None
    extensions: Optional[list[str]] = None
    layout: str = "Spring"


# ── Endpoints ──────────────────────────────────────────────────────────────────

def _repo_url(request: UnifiedParseRequest) -> str:
    """Extract a stable URL string from the request for use as a cache key."""
    info = request.directory.info
    if info and info.url:
        return info.url
    if info and info.owner and info.name:
        return f"github:{info.owner}/{info.name}"
    return ""


@UnifiedParserRouter.post("/unified")
async def parse_unified(request: UnifiedParseRequest) -> dict:
    """Parse a directory tree to the requested depth and return a gJGF graph.

    Parameters (JSON body)
    ----------------------
    directory : Directory
        The source directory (files + folder hierarchy).
    depth : int
        0 = directories, 1 = files, 2 = symbols, 3 = sub-symbols.
    extensions : list[str] | null
        File extensions to include.  Null = all registered parsers.
    layout : str
        Layout algorithm (Spring, Spectral, …).
    """
    from codecarto.services.unified_parser_service import UnifiedParserService
    from codecarto.services.cache_service import CacheService

    try:
        effective_depth = (
            MODE_TO_DEPTH.get(request.mode, request.depth)
            if request.mode else request.depth
        )
        mode_key = request.mode or str(effective_depth)
        url = _repo_url(request)

        # Check cache when a stable URL is available
        cache_hit = False
        if url:
            key = CacheService.cache_key(
                url=url,
                mode=mode_key,
                layout=request.layout,
                extensions=request.extensions or [],
            )
            cached = CacheService.get(key)
            if cached is not None:
                cached["from_cache"] = True
                return generate_return(200, "parse/unified - Cache hit", cached)

        result = UnifiedParserService.parse(
            directory=request.directory,
            depth=effective_depth,
            extensions=request.extensions,
            layout=request.layout,
        )

        # Persist to cache
        if url:
            info = request.directory.info
            label = (
                f"{info.owner}/{info.name}" if info and info.owner and info.name
                else url
            )
            CacheService.set(
                key=key,
                data=result,
                label=label,
                url=url,
                mode=mode_key,
                layout=request.layout,
            )

        return generate_return(200, "parse/unified - Success", result)
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc, exc.status_code)
    except Exception as exc:
        return proc_exception(
            "parse/unified",
            "Unexpected error during unified parse",
            {"depth": request.depth},
            exc,
        )


@UnifiedParserRouter.post("/stream")
async def stream_parse(request: UnifiedParseRequest):
    """Stream a parsed graph as Server-Sent Events.

    Sends one SSE event per node (after a `meta` header event),
    then all edges, then a final `done` event.  The client can close
    the connection at any time to cancel.
    """
    from codecarto.services.unified_parser_service import UnifiedParserService
    from codecarto.services.cache_service import CacheService

    effective_depth = (
        MODE_TO_DEPTH.get(request.mode, request.depth)
        if request.mode else request.depth
    )
    mode_key = request.mode or str(effective_depth)
    url = _repo_url(request)

    # Stream from cache if available
    if url:
        key = CacheService.cache_key(
            url=url,
            mode=mode_key,
            layout=request.layout,
            extensions=request.extensions or [],
        )
        cached = CacheService.get(key)
        if cached is not None:
            import json, asyncio

            async def stream_cached():
                nodes_raw = cached.get("graph", {}).get("nodes", {})
                edges = cached.get("graph", {}).get("edges", [])
                nodes_list = []
                if isinstance(nodes_raw, dict):
                    for nid, nd in nodes_raw.items():
                        if not isinstance(nd, dict):
                            continue
                        meta_attrs = nd.get("metadata", {})
                        flat: dict = {"id": nid}
                        for k, v in nd.items():
                            if k != "metadata":
                                flat[k] = v
                        flat.update(meta_attrs)
                        nodes_list.append(flat)
                meta = {"nodeCount": len(nodes_list), "edgeCount": len(edges), "layout": request.layout, "from_cache": True}
                yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
                await asyncio.sleep(0)
                for node in sorted(nodes_list, key=lambda n: (n.get("depth", 9), n.get("id", ""))):
                    yield f"event: node\ndata: {json.dumps(node)}\n\n"
                    await asyncio.sleep(0)
                for edge in edges:
                    yield f"event: edge\ndata: {json.dumps(edge)}\n\n"
                    await asyncio.sleep(0)
                yield f"event: done\ndata: {json.dumps({'elapsed_ms': 0, 'from_cache': True})}\n\n"

            return StreamingResponse(
                stream_cached(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

    async def generate():
        try:
            async for chunk in UnifiedParserService.stream_parse(
                directory=request.directory,
                depth=effective_depth,
                extensions=request.extensions,
                layout=request.layout,
            ):
                yield chunk
        except Exception as exc:
            import json
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@UnifiedParserRouter.post("/stream-url")
async def stream_from_url(request: StreamUrlRequest):
    """Fetch a GitHub repo and stream parse results as SSE — no separate fetch step.

    Combines the GitHub repo fetch and parse into a single streaming response.
    Phase 1 streams directory/file nodes as soon as the structure is fetched.
    Phase 2 concurrently fetches file contents and streams symbol nodes as they arrive.
    """
    from codecarto.services.unified_parser_service import UnifiedParserService
    from codecarto.services.cache_service import CacheService

    effective_depth = (
        MODE_TO_DEPTH.get(request.mode, request.depth)
        if request.mode else request.depth
    )
    mode_key = request.mode or str(effective_depth)

    # Check cache first
    key = CacheService.cache_key(
        url=request.url,
        mode=mode_key,
        layout=request.layout,
        extensions=request.extensions or [],
    )
    cached = CacheService.get(key)
    if cached is not None:
        import json, asyncio

        async def stream_cached_url():
            nodes_raw = cached.get("graph", {}).get("nodes", {})
            edges = cached.get("graph", {}).get("edges", [])
            nodes_list = []
            if isinstance(nodes_raw, dict):
                for nid, nd in nodes_raw.items():
                    if not isinstance(nd, dict):
                        continue
                    meta_attrs = nd.get("metadata", {})
                    flat: dict = {"id": nid}
                    for k, v in nd.items():
                        if k != "metadata":
                            flat[k] = v
                    flat.update(meta_attrs)
                    nodes_list.append(flat)
            meta = {"nodeCount": len(nodes_list), "edgeCount": len(edges), "layout": request.layout, "from_cache": True}
            yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
            await asyncio.sleep(0)
            for node in sorted(nodes_list, key=lambda n: (n.get("depth", 9), n.get("id", ""))):
                yield f"event: node\ndata: {json.dumps(node)}\n\n"
                await asyncio.sleep(0)
            for edge in edges:
                yield f"event: edge\ndata: {json.dumps(edge)}\n\n"
                await asyncio.sleep(0)
            yield f"event: done\ndata: {json.dumps({'elapsed_ms': 0, 'from_cache': True})}\n\n"

        return StreamingResponse(
            stream_cached_url(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def generate():
        try:
            async for chunk in UnifiedParserService.stream_parse_url(
                url=request.url,
                depth=effective_depth,
                extensions=request.extensions,
                layout=request.layout,
            ):
                yield chunk
        except Exception as exc:
            import json
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@UnifiedParserRouter.post("/expand")
async def expand_node(request: ExpandNodeRequest) -> dict:
    """Return the sub-graph for a file node expanded to *depth*.

    Parameters (JSON body)
    ----------------------
    directory : Directory
        The source directory that was originally parsed.
    node_id : str
        ID of the file node to expand (e.g. ``file::src/main.py``).
    depth : int
        Target depth after expansion (2 or 3).
    """
    from codecarto.services.unified_parser_service import UnifiedParserService

    try:
        result = UnifiedParserService.expand_node(
            directory=request.directory,
            node_id=request.node_id,
            depth=request.depth,
        )
        return generate_return(200, "parse/expand - Success", result)
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc, exc.status_code)
    except Exception as exc:
        return proc_exception(
            "parse/expand",
            "Unexpected error during node expansion",
            {"node_id": request.node_id},
            exc,
        )


@UnifiedParserRouter.get("/languages")
async def list_languages() -> dict:
    """Return the registered parser extensions and their language names."""
    from codecarto.services.parsers.language_parser import ParserRegistry
    # Trigger registration
    import codecarto.services.parsers.python_language_parser  # noqa: F401
    import codecarto.services.parsers.c_language_parser       # noqa: F401

    parsers = ParserRegistry.all_parsers()
    data = {
        p.language: p.extensions  # type: ignore[attr-defined]
        for p in parsers
    }
    return generate_return(200, "parse/languages - Success", {"languages": data})


@UnifiedParserRouter.get("/cache")
async def list_cache() -> dict:
    """Return the list of cached graphs (newest first)."""
    from codecarto.services.cache_service import CacheService
    entries = CacheService.list_cached()
    return generate_return(200, "parse/cache - Success", {"entries": entries})


@UnifiedParserRouter.delete("/cache/{key}")
async def evict_cache(key: str) -> dict:
    """Evict a single cached graph by its key."""
    from codecarto.services.cache_service import CacheService
    deleted = CacheService.evict(key)
    if deleted:
        return generate_return(200, "parse/cache - Evicted", {"key": key})
    return generate_return(404, "parse/cache - Not found", {"key": key})
