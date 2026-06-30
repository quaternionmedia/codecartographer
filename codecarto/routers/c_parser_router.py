import asyncio
import json
import math
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from codecarto.util.exceptions import CodeCartoException, proc_exception
from codecarto.util.threaded_feeder import start_threaded_feeder
from codecarto.util.utilities import generate_return

CParserRouter = APIRouter()


class CFileRequest(BaseModel):
    path: str


class CDirectoryRequest(BaseModel):
    path: str
    compile_commands: Optional[str] = None
    subsystem: Optional[str] = None
    max_files: Optional[int] = None


class CGithubRequest(BaseModel):
    url: str
    max_files: Optional[int] = 200


class CStreamGithubRequest(BaseModel):
    url: str
    max_files: Optional[int] = 200
    layout: Optional[str] = "Spring"


@CParserRouter.post("/file")
async def parse_c_file(request: CFileRequest) -> dict:
    """Parse a single C/H source file into a semantic graph."""
    from codecarto.services.c_parser_service import CParserService

    try:
        graph = CParserService.parse_file(request.path)
        return generate_return(200, "c-parser/file - Success", {"graph": graph})
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc, exc.status_code)
    except Exception as exc:
        return proc_exception(
            "c-parser/file",
            "Unexpected error parsing C file",
            {"path": request.path},
            exc,
        )


@CParserRouter.post("/github")
async def parse_c_github(request: CGithubRequest) -> dict:
    """Download a GitHub repo and parse all C/H files as a semantic graph."""
    from codecarto.services.c_parser_service import CParserService

    try:
        graph = CParserService.parse_github(request.url, max_files=request.max_files)
        return generate_return(200, "c-parser/github - Success", {"graph": graph})
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc, exc.status_code)
    except Exception as exc:
        return proc_exception(
            "c-parser/github",
            "Unexpected error parsing GitHub C repo",
            {"url": request.url},
            exc,
        )


@CParserRouter.get("/cache")
async def list_c_repo_cache() -> dict:
    """List extracted GitHub repos in the C-parser's repo cache (newest first).

    Counterpart to GET /parse/cache — that one lists cached *parsed graphs*;
    this one lists cached *extracted source trees* (a different cache, see
    docs/llm/ARCHITECTURE.md). Repos here are re-parsed fresh on every
    request; only the download+extract step is skipped on a hit.
    """
    from codecarto.services.c_parser_service import CParserService
    entries = CParserService.list_cached_repos()
    return generate_return(200, "c-parser/cache - Success", {"entries": entries})


@CParserRouter.delete("/cache/{key}")
async def evict_c_repo_cache(key: str) -> dict:
    """Evict a single cached repo by its `{owner}-{repo}` key."""
    from codecarto.services.c_parser_service import CParserService
    deleted = CParserService.evict_repo_cache(key)
    if deleted:
        return generate_return(200, "c-parser/cache - Evicted", {"key": key})
    return generate_return(404, "c-parser/cache - Not found", {"key": key})


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


async def _stream_cached_c_graph(cached: dict):
    """Replay a cached C-parser result as SSE events.

    The cached dict shape is the raw CParserService result augmented with a
    'positions' dict and a 'layout' string that were computed at parse time.
    """
    nodes: list[dict] = cached.get("nodes", [])
    edges: list[dict] = cached.get("edges", [])
    positions: dict = cached.get("positions", {})
    layout: str = cached.get("layout", "Spring")
    meta: dict = cached.get("meta", {})

    yield _sse("meta", {
        "fileCount": meta.get("total_files", len({n.get("file") for n in nodes if n.get("file")})),
        "from_cache": True,
    })
    await asyncio.sleep(0)

    for node in nodes:
        pos = positions.get(node["id"], {})
        yield _sse("node", {**node, "language": "c", "depth": 2,
                             "x": pos.get("x", 0.0), "y": pos.get("y", 0.0)})
        await asyncio.sleep(0)

    if positions:
        yield _sse("reposition", positions)
        await asyncio.sleep(0)

    node_ids = {n["id"] for n in nodes}
    for e in edges:
        if e["src"] in node_ids and e["dst"] in node_ids:
            yield _sse("edge", {
                "source": e["src"], "target": e["dst"],
                "label": e["kind"], "weight": e.get("weight"),
            })
            await asyncio.sleep(0)

    yield _sse("done", {
        "elapsed_ms": 0,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "from_cache": True,
    })


def _c_cache_key(url: str, layout: str) -> str:
    from codecarto.services.cache_service import CacheService
    return CacheService.cache_key(url=url, mode="c", layout=layout, extensions=[".c", ".h"])


def _file_cluster_center(file_index: int, cols: int, spacing: float = 220.0) -> tuple[float, float]:
    """Deterministic grid position for the Nth file's symbol cluster.

    The dedicated C pipeline streams bare symbol nodes with no directory/file
    skeleton (unlike the unified pipeline, which precomputes a NetworkX
    layout before streaming) — without this, every node arrives with no x/y
    and StreamingGraphRenderer._renderNode() falls back to the exact center
    of the canvas for ALL of them, so thousands of nodes stack on one pixel
    and the graph looks empty even though nodes are "arriving".
    """
    row, col = divmod(file_index, cols)
    return col * spacing, row * spacing


def _position_file_nodes(nodes: list[dict], cx: float, cy: float) -> None:
    """Arrange one file's symbols in a small circle around its cluster center."""
    n = len(nodes)
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / max(n, 1)
        radius = 30 + 8 * (i % 3)
        node["x"] = cx + radius * math.cos(angle)
        node["y"] = cy + radius * math.sin(angle)


def _compute_layout_positions(nodes: list[dict], edges: list[dict], layout: str) -> dict[str, dict[str, float]]:
    """Run the user's selected layout algorithm on the complete C graph.

    Reuses the same Positions service + scaling GraphSerializer applies for
    every other parse path, so a C repo streamed through this endpoint ends
    up laid out identically to one parsed through /parse/unified with the
    same layout choice — see docs/llm/ARCHITECTURE.md.
    """
    if not nodes:
        return {}

    import networkx as nx
    from codecarto.services.position_service import Positions

    graph = nx.DiGraph()
    for n in nodes:
        graph.add_node(n["id"])
    node_ids = {n["id"] for n in nodes}
    for e in edges:
        if e["src"] in node_ids and e["dst"] in node_ids:
            graph.add_edge(e["src"], e["dst"])

    layout_name = f"{layout.lower()}_layout"
    try:
        raw_positions = Positions().get_node_positions(graph=graph, layout_name=layout_name)
    except Exception:
        return {}

    # Same spread scaling as GraphSerializer.serialize_to_gjgf, so a C repo
    # streamed here visually matches one parsed via /parse/unified.
    spread = 500 if layout_name in ("spectral_layout", "kamada_kawai_layout") else 100

    return {
        node_id: {"x": float(x) * spread, "y": float(y) * spread}
        for node_id, (x, y) in raw_positions.items()
    }


@CParserRouter.post("/stream-github")
async def stream_c_github(request: CStreamGithubRequest) -> StreamingResponse:
    """Stream a GitHub C/H repo parse as Server-Sent Events.

    libclang parsing is synchronous, CPU-bound work, so it runs in a
    background thread (see util/threaded_feeder.py — same pattern as
    pam_router.py's log tailer) while this coroutine drains an asyncio.Queue
    the thread feeds via asyncio.run_coroutine_threadsafe. Nodes stream in
    real time, file by file, as CParser.parse_files() works through pass 1.
    Edges need the complete cross-file node set to resolve CALLS/FIELD_OF
    targets, so they're only available — and only streamed — after the
    thread finishes.

    On cache hit the saved positions and layout are replayed verbatim — no
    re-parse, no GitHub fetch.
    """
    from codecarto.services.c_parser_service import CParserService
    from codecarto.services.cache_service import CacheService

    layout = request.layout or "Spring"
    cache_key = _c_cache_key(request.url, layout)

    # Cache hit — replay immediately
    cached = CacheService.get(cache_key)
    if cached is not None:
        return StreamingResponse(
            _stream_cached_c_graph(cached),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    result_box: dict = {}
    error_box: dict = {}
    started_at = time.monotonic()

    def make_worker(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        def on_progress(event_type: str, payload: dict) -> None:
            asyncio.run_coroutine_threadsafe(queue.put((event_type, payload)), loop)

        def worker() -> None:
            try:
                result_box["value"] = CParserService.parse_github(
                    request.url, max_files=request.max_files, on_progress=on_progress
                )
            except Exception as exc:
                error_box["exc"] = exc
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(("__done__", None)), loop)

        return worker

    queue = start_threaded_feeder(make_worker)

    async def generate():
        cols = 1
        file_index_by_name: dict[str, int] = {}

        while True:
            event_type, payload = await queue.get()
            if event_type == "__done__":
                break
            if event_type == "fetching":
                yield _sse("fetching", payload)
            elif event_type == "meta":
                cols = max(1, math.ceil(math.sqrt(payload["total_files"])))
                yield _sse("meta", {
                    "fileCount": payload["total_files"],
                    "skippedCount": len(payload["skipped_files"]),
                })
            elif event_type == "nodes":
                file_name = payload["file"]
                if file_name not in file_index_by_name:
                    file_index_by_name[file_name] = len(file_index_by_name)
                cx, cy = _file_cluster_center(file_index_by_name[file_name], cols)
                _position_file_nodes(payload["nodes"], cx, cy)

                for node in payload["nodes"]:
                    yield _sse("node", {**node, "language": "c", "depth": 2})
                    await asyncio.sleep(0)

        if "exc" in error_box:
            yield _sse("error", {"message": str(error_box["exc"])})
            return

        result = result_box.get("value") or {"nodes": [], "edges": [], "meta": {}}
        node_ids = {n["id"] for n in result["nodes"]}

        # Nodes were placed in a placeholder grid as they streamed in (see
        # _file_cluster_center above) because the chosen layout algorithm
        # needs the complete edge set to mean anything, and edges aren't
        # known until every file has been parsed. Now that they are, compute
        # the real layout and move everything there in one shot — see
        # StreamingGraphRenderer.repositionAll on the frontend.
        positions = _compute_layout_positions(result["nodes"], result["edges"], request.layout or "Spring")
        if positions:
            yield _sse("reposition", positions)
            await asyncio.sleep(0)

        # Same filter the frontend's adaptCGraphToGJGF applies for the
        # non-streaming endpoints: the C parser can emit edges to nodes
        # outside the target file set (e.g. a FIELD_OF edge whose parent
        # struct lives in a system header).
        for e in result["edges"]:
            if e["src"] in node_ids and e["dst"] in node_ids:
                yield _sse("edge", {
                    "source": e["src"], "target": e["dst"],
                    "label": e["kind"], "weight": e.get("weight"),
                })
                await asyncio.sleep(0)

        meta = result.get("meta", {})
        yield _sse("done", {
            "elapsed_ms": int((time.monotonic() - started_at) * 1000),
            "node_count": len(result["nodes"]),
            "edge_count": len(result["edges"]),
            "diagnostics": meta.get("diagnostics", {}),
            "skipped_files": meta.get("skipped_files", []),
        })

        # Persist so the next request for the same repo is a cache hit.
        if result["nodes"]:
            try:
                label = request.url.rstrip("/").rsplit("github.com/", 1)[-1]
                cache_entry = {**result, "positions": positions, "layout": layout}
                CacheService.set(
                    key=cache_key,
                    data=cache_entry,
                    label=label,
                    url=request.url,
                    mode="c",
                    layout=layout,
                )
            except Exception:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_VISUALIZER_HTML = Path(__file__).parent.parent / "static" / "c-visualizer.html"

# Matches the entire `const GRAPH = { ... };` block (non-greedy across lines)
_GRAPH_PATTERN = re.compile(r"const GRAPH = \{[\s\S]*?\};", re.MULTILINE)


@CParserRouter.get("/visualizer")
async def c_visualizer(path: Optional[str] = Query(None, description="Filesystem path to a C file or directory")) -> HTMLResponse:
    """Serve the C Semantic Visualizer HTML.

    When *path* is supplied the target is parsed with libclang and the result
    is injected into the page in place of the built-in demo graph.  Without a
    *path* the demo linux/mm/ graph is shown as-is.
    """
    if not _VISUALIZER_HTML.exists():
        return HTMLResponse(
            "<h1>C Visualizer not found</h1>"
            f"<p>Expected at: {_VISUALIZER_HTML}</p>",
            status_code=404,
        )

    html = _VISUALIZER_HTML.read_text(encoding="utf-8")

    if path:
        try:
            from codecarto.services.c_parser_service import CParserService

            target = Path(path)
            graph_data = (
                CParserService.parse_directory(path)
                if target.is_dir()
                else CParserService.parse_file(path)
            )
            # graph_data has {nodes, edges, meta}; c-visualizer only needs nodes + edges
            inject = {"nodes": graph_data["nodes"], "edges": graph_data["edges"]}
            html = _GRAPH_PATTERN.sub(
                f"const GRAPH = {json.dumps(inject, ensure_ascii=False)};",
                html,
                count=1,
            )
            # Update the header label to reflect the parsed target
            stem = target.name
            html = html.replace(
                "<span class=\"pill sub\">linux/mm/</span>",
                f"<span class=\"pill sub\">{stem}</span>",
            )
        except Exception:
            pass  # Fall back to built-in demo graph on any error

    return HTMLResponse(html)


@CParserRouter.post("/directory")
async def parse_c_directory(request: CDirectoryRequest) -> dict:
    """Parse a directory of C/H files (or compile_commands.json) into a semantic graph."""
    from codecarto.services.c_parser_service import CParserService

    try:
        graph = CParserService.parse_directory(
            path=request.path,
            compile_commands=request.compile_commands,
            subsystem=request.subsystem,
            max_files=request.max_files,
        )
        return generate_return(200, "c-parser/directory - Success", {"graph": graph})
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc, exc.status_code)
    except Exception as exc:
        return proc_exception(
            "c-parser/directory",
            "Unexpected error parsing C directory",
            {"path": request.path},
            exc,
        )
