import os
from fastapi import APIRouter
from codecarto.models.source_data import Directory, RepoInfo
from codecarto.services.github_service import (
    get_raw_from_repo,
    get_owner_repo_from_url,
    create_headers,
    get_subtree,
    expand_all_tree,
)
from codecarto.util.exceptions import CodeCartoException, proc_exception
from codecarto.util.utilities import Log, generate_return

RepoReaderRouter = APIRouter()


@RepoReaderRouter.get("/tree")
async def get_repo_directory_tree(url: str) -> dict:
    # Get the GitHub repo directory tree (falls back to shallow mode for large repos)
    try:
        Log.info(f"Reading GitHub URL: {url}")
        data = await get_raw_from_repo(url)
        return generate_return(200, "read_github_url - Success", data.model_dump())
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc)
    except Exception as exc:
        return proc_exception(
            "read_github_url",
            "Error when reading GitHub URL",
            {"github_url": url},
            exc,
        )


@RepoReaderRouter.get("/expand-all")
async def expand_all_repo(url: str, max_depth: int = 3) -> dict:
    """Expand all folders in a partial repo to *max_depth* without downloading file content.

    Returns a full Directory model (is_partial=False) whose Folder tree covers
    all directories up to the requested depth.  Files are listed as stubs (raw='').
    """
    try:
        Log.info(f"Expanding all folders: {url} (max_depth={max_depth})")
        if not url.endswith("/"):
            url += "/"
        owner, repo_name = get_owner_repo_from_url(url)
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        root_folder = await expand_all_tree(owner, repo_name, token, max_depth)
        root_folder.name = f"{owner}/{repo_name}"
        info = RepoInfo(owner=owner, name=repo_name, url=url)
        directory = Directory(info=info, size=root_folder.size, root=root_folder, is_partial=False)
        return generate_return(200, "expand_all_repo - Success", directory.model_dump())
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc)
    except Exception as exc:
        return proc_exception(
            "expand_all_repo",
            "Error expanding repo tree",
            {"url": url, "max_depth": max_depth},
            exc,
        )


@RepoReaderRouter.get("/subtree")
async def get_repo_subtree(url: str, path: str = "") -> dict:
    """Fetch one level of a specific folder path in a GitHub repo.

    Used to lazily expand stub folders returned by the shallow-mode /tree endpoint.
    """
    try:
        Log.info(f"Fetching subtree: {url} @ {path!r}")
        if url[len(url) - 1] != "/":
            url += "/"
        owner, repo_name = get_owner_repo_from_url(url)
        headers = create_headers(url)
        folder = await get_subtree(owner, repo_name, path, url, headers)
        return generate_return(200, "get_repo_subtree - Success", folder.model_dump())
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc)
    except Exception as exc:
        return proc_exception(
            "get_repo_subtree",
            "Error fetching subtree",
            {"url": url, "path": path},
            exc,
        )
