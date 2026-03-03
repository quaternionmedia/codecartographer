import json
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from codecarto.util.exceptions import CodeCartoException, proc_exception
from codecarto.util.utilities import generate_return

CParserRouter = APIRouter()


class CFileRequest(BaseModel):
    path: str
    cache_dir: Optional[str] = None


class CDirectoryRequest(BaseModel):
    path: str
    compile_commands: Optional[str] = None
    subsystem: Optional[str] = None
    max_files: Optional[int] = None
    cache_dir: Optional[str] = None


class CGithubRequest(BaseModel):
    url: str
    max_files: Optional[int] = 200


@CParserRouter.post("/file")
async def parse_c_file(request: CFileRequest) -> dict:
    """Parse a single C/H source file into a semantic graph."""
    from codecarto.services.c_parser_service import CParserService

    try:
        graph = CParserService.parse_file(request.path, cache_dir=request.cache_dir)
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


_VISUALIZER_HTML = (
    Path(__file__).parent.parent.parent
    / ".github" / "development" / "chrestromathy_branch" / "c-visualizer.html"
)

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
            cache_dir=request.cache_dir,
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
