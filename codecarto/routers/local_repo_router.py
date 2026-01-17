"""
Local repository router for parsing local git repositories via API.
"""
from fastapi import APIRouter, Query
from typing import List, Optional
from codecarto.services.local_repo_service import get_local_repo, get_file_stats
from codecarto.services.parser_service import ParserService
from codecarto.services.parsers.ASTs.python_custom_ast import PythonCustomAST
from codecarto.util.exceptions import CodeCartoException, proc_exception
from codecarto.util.utilities import Log, generate_return

LocalRepoRouter = APIRouter()


@LocalRepoRouter.get("/scan")
async def scan_local_repo(
    path: str = Query(..., description="Path to local repository"),
    extensions: Optional[List[str]] = Query(default=[".py"], description="File extensions to include")
) -> dict:
    """
    Scan a local repository and return its structure.
    """
    try:
        Log.info(f"Scanning local repo: {path}")
        directory = get_local_repo(path, extensions=extensions)
        stats = get_file_stats(directory)
        
        return generate_return(200, "scan_local_repo - Success", {
            "info": directory.info.model_dump(),
            "stats": stats,
            "structure": directory.root.model_dump()
        })
    except FileNotFoundError as exc:
        return proc_exception("scan_local_repo", str(exc), {"path": path}, exc)
    except Exception as exc:
        return proc_exception(
            "scan_local_repo",
            "Error scanning local repo",
            {"path": path},
            exc,
        )


@LocalRepoRouter.get("/tree")
async def get_local_repo_tree(
    path: str = Query(..., description="Path to local repository"),
    extensions: Optional[List[str]] = Query(default=[".py"], description="File extensions to include")
) -> dict:
    """
    Get the directory tree structure of a local repository.
    """
    try:
        Log.info(f"Getting tree for local repo: {path}")
        directory = get_local_repo(path, extensions=extensions)
        
        return generate_return(200, "get_local_repo_tree - Success", {
            "info": directory.info.model_dump(),
            "root": directory.root.model_dump()
        })
    except FileNotFoundError as exc:
        return proc_exception("get_local_repo_tree", str(exc), {"path": path}, exc)
    except Exception as exc:
        return proc_exception(
            "get_local_repo_tree",
            "Error getting repo tree",
            {"path": path},
            exc,
        )


@LocalRepoRouter.get("/graph/ast")
async def get_local_repo_ast_graph(
    path: str = Query(..., description="Path to local repository"),
    extensions: Optional[List[str]] = Query(default=[".py"], description="File extensions to include")
) -> dict:
    """
    Parse a local repository and return AST graph data.
    """
    try:
        Log.info(f"Generating AST graph for local repo: {path}")
        directory = get_local_repo(path, extensions=extensions)
        
        parser = PythonCustomAST()
        graph = parser.parse(directory.root)
        graph.name = directory.info.name
        
        nodes = [{"id": n[0], **n[1]} for n in graph.nodes(data=True)]
        edges = [{"source": e[0], "target": e[1], **e[2]} for e in graph.edges(data=True)]
        
        return generate_return(200, "get_local_repo_ast_graph - Success", {
            "name": graph.name,
            "nodes": nodes,
            "edges": edges
        })
    except FileNotFoundError as exc:
        return proc_exception("get_local_repo_ast_graph", str(exc), {"path": path}, exc)
    except Exception as exc:
        return proc_exception(
            "get_local_repo_ast_graph",
            "Error generating AST graph",
            {"path": path},
            exc,
        )


@LocalRepoRouter.get("/graph/directory")
async def get_local_repo_directory_graph(
    path: str = Query(..., description="Path to local repository"),
    extensions: Optional[List[str]] = Query(default=[".py"], description="File extensions to include")
) -> dict:
    """
    Parse a local repository and return directory structure graph.
    """
    try:
        Log.info(f"Generating directory graph for local repo: {path}")
        directory = get_local_repo(path, extensions=extensions)
        
        graph = await ParserService.parse_directory(directory)
        
        nodes = [{"id": n[0], **n[1]} for n in graph.nodes(data=True)]
        edges = [{"source": e[0], "target": e[1], **e[2]} for e in graph.edges(data=True)]
        
        return generate_return(200, "get_local_repo_directory_graph - Success", {
            "name": graph.name,
            "nodes": nodes,
            "edges": edges
        })
    except FileNotFoundError as exc:
        return proc_exception("get_local_repo_directory_graph", str(exc), {"path": path}, exc)
    except Exception as exc:
        return proc_exception(
            "get_local_repo_directory_graph",
            "Error generating directory graph",
            {"path": path},
            exc,
        )


@LocalRepoRouter.get("/graph/dependency")
async def get_local_repo_dependency_graph(
    path: str = Query(..., description="Path to local repository"),
    extensions: Optional[List[str]] = Query(default=[".py"], description="File extensions to include")
) -> dict:
    """
    Parse a local repository and return import dependency graph.
    """
    try:
        Log.info(f"Generating dependency graph for local repo: {path}")
        directory = get_local_repo(path, extensions=extensions)
        
        graph = await ParserService.parse_dependancy(directory)
        
        nodes = [{"id": n[0], **n[1]} for n in graph.nodes(data=True)]
        edges = [{"source": e[0], "target": e[1], **e[2]} for e in graph.edges(data=True)]
        
        return generate_return(200, "get_local_repo_dependency_graph - Success", {
            "name": graph.name,
            "nodes": nodes,
            "edges": edges
        })
    except FileNotFoundError as exc:
        return proc_exception("get_local_repo_dependency_graph", str(exc), {"path": path}, exc)
    except Exception as exc:
        return proc_exception(
            "get_local_repo_dependency_graph",
            "Error generating dependency graph",
            {"path": path},
            exc,
        )
