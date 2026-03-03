"""
Unified Parser Router
=====================
Endpoints for the unified codebase graph architecture.

POST /parse/unified   — parse a full directory tree to a given depth
GET  /parse/expand    — expand a single node (file → symbols)
GET  /parse/languages — list registered parser extensions
"""

from typing import Optional

from fastapi import APIRouter, Query
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


# ── Endpoints ──────────────────────────────────────────────────────────────────

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

    try:
        effective_depth = (
            MODE_TO_DEPTH.get(request.mode, request.depth)
            if request.mode else request.depth
        )
        result = UnifiedParserService.parse(
            directory=request.directory,
            depth=effective_depth,
            extensions=request.extensions,
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
