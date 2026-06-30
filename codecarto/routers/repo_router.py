import os
from pathlib import Path
from fastapi import APIRouter
from codecarto.models.source_data import Directory, Folder, RepoInfo
from codecarto.services.github_service import (
    get_raw_from_repo,
    get_owner_repo_from_url,
    create_headers,
    get_subtree,
    expand_all_tree,
    is_github_url
)
from codecarto.services.local_repo_service import get_local_repo
from codecarto.util.exceptions import CodeCartoException, proc_exception
from codecarto.util.utilities import Log, generate_return

RepoReaderRouter = APIRouter()


def _find_folder_at_path(root: Folder, path: str) -> Folder | None:
    """Walk a cached Folder tree to the folder at *path* (e.g. 'src/utils').

    Returns None if any segment is missing — caller falls through to GitHub.
    """
    if not path:
        return root
    segments = [s for s in path.split("/") if s]
    node = root
    for seg in segments:
        match = next((f for f in node.folders if f.name == seg), None)
        if match is None:
            return None
        node = match
    return node


@RepoReaderRouter.get("/tree")
async def get_repo_directory_tree(url: str) -> dict:
    """
    Read a directory tree from either a GitHub repo URL or a local filesystem path.
    The 'url' query param is parsed to decide which.
    """
    # Get the GitHub repo directory tree (falls back to shallow mode for large repos)
    try:
        if is_github_url(url):
            Log.info(f"Reading GitHub URL: {url}")
            data = await get_raw_from_repo(url)
            return generate_return(200, "read_github_url - Success", data.model_dump())
        else:
            Log.info(f"Reading local path: {url}")
            data = get_local_repo(url)
            return generate_return(200, "read_local_path - Success", data.model_dump())
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc, exc.status_code)
    except Exception as exc:
        return proc_exception(
            "get_repo_directory_tree",
            "Error reading source",
            {"input": url},
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

        # If the full tree is already cached, return it directly.
        from codecarto.services.cache_service import CacheService
        cached_tree = CacheService.get_tree(url)
        if cached_tree is not None:
            try:
                directory = Directory.model_validate(cached_tree)
                if not directory.is_partial:
                    return generate_return(200, "expand_all_repo - Cache hit", directory.model_dump())
            except Exception:
                pass  # corrupt cache entry — fall through to live fetch

        owner, repo_name = get_owner_repo_from_url(url)
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        root_folder = await expand_all_tree(owner, repo_name, token, max_depth)
        root_folder.name = f"{owner}/{repo_name}"
        info = RepoInfo(owner=owner, name=repo_name, url=url)
        directory = Directory(info=info, size=root_folder.size, root=root_folder, is_partial=False)
        return generate_return(200, "expand_all_repo - Success", directory.model_dump())
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc, exc.status_code)
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
    Checks the source-tree cache first — if the repo's full tree was already
    fetched, the subfolder data is served directly without hitting GitHub.
    """
    try:
        if is_github_url(url):
            Log.info(f"Fetching subtree: {url} @ {path!r}")
            normalized_url = url if url.endswith("/") else url + "/"

            # Serve from cached tree when available and non-partial.
            from codecarto.services.cache_service import CacheService
            cached_tree = CacheService.get_tree(normalized_url)
            if cached_tree is not None:
                try:
                    directory = Directory.model_validate(cached_tree)
                    if not directory.is_partial:
                        folder = _find_folder_at_path(directory.root, path)
                        if folder is not None:
                            return generate_return(200, "get_repo_subtree - Cache hit", folder.model_dump())
                except Exception:
                    pass  # corrupt cache entry — fall through to live fetch

            if not url.endswith("/"):
                url += "/"
            owner, repo_name = get_owner_repo_from_url(url)
            headers = create_headers(url)
            folder = await get_subtree(owner, repo_name, path, url, headers)
            return generate_return(200, "get_repo_subtree - Success", folder.model_dump())
        else:
            # Local: re-walk the subdirectory and return it as a Folder
            full_path = (Path(url) / path).resolve()
            sub_dir = get_local_repo(str(full_path))
            folder = sub_dir.root
            folder.name = full_path.name
            return generate_return(200, "get_repo_subtree - Success", folder.model_dump())
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc, exc.status_code)
    except Exception as exc:
        return proc_exception(
            "get_repo_subtree",
            "Error fetching subtree",
            {"url": url, "path": path},
            exc,
        )
