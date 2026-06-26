import httpx
from pathlib import Path
from codecarto.models.source_data import Directory, File, Folder, RepoInfo
from codecarto.util.exceptions import (
    GithubError,
    Github404Error,
    GithubNoDataError,
    GithubSizeError,
    GithubAPIError,
    ImportSourceUrlError,
)

# Size tiers (GitHub reports repo size in KB):
#   < _CONTENT_FETCH_LIMIT_KB  → full recursive fetch with file content (registered exts only)
#   < _STRUCTURE_FETCH_LIMIT_KB → full recursive fetch, structure only (no file content)
#   ≥ _STRUCTURE_FETCH_LIMIT_KB → shallow root listing only (is_partial=True)
_CONTENT_FETCH_LIMIT_KB   = 5_000   # ~5 MB
_STRUCTURE_FETCH_LIMIT_KB = 50_000  # ~50 MB

def is_github_url(input_str: str) -> bool:
    """
    True if input looks like a GitHub URL. False otherwise (local path).
    Rule: GitHub URLs always contain 'github.com'. Everything else → local.
    """
    return 'github.com' in input_str.strip().lower()


async def get_raw_from_url(url: str) -> str:
    """Fetch raw content from a URL (any file type)."""
    client = httpx.AsyncClient()
    response = await client.get(url)

    if response.status_code == 200:
        return response.text

    raise handle_status_code(response, url)


async def get_raw_from_repo(url: str) -> Directory:
    """Read raw data from a repo URL.

    For repos within the size limit, fetches the full tree with file content.
    For large repos, falls back to a shallow top-level listing marked ``is_partial=True``.
    """
    owner, repo_name = get_owner_repo_from_url(url)
    headers = create_headers(url)

    size_kb = await check_repo_size(owner, repo_name, url, headers)

    if size_kb >= _STRUCTURE_FETCH_LIMIT_KB:
        # Very large repo (≥ 50 MB): return only the root-level structure
        root = await get_shallow_root(owner, repo_name, url, headers)
        root.name = f"{owner}/{repo_name}"
        return Directory(
            info=RepoInfo(owner=owner, name=repo_name, url=url),
            size=size_kb,
            root=root,
            is_partial=True,
        )

    # Medium/small repo: full recursive fetch
    fetch_content = size_kb < _CONTENT_FETCH_LIMIT_KB
    content = await get_repo_content(url, owner, repo_name)
    tree = await build_content_tree(content, owner, repo_name)
    root = await reduce_repo_structure(tree, fetch_content=fetch_content)
    root.name = f"{owner}/{repo_name}"

    size = sum(file.size for file in root.files)
    size += sum(folder.size for folder in root.folders)

    return Directory(
        info=RepoInfo(owner=owner, name=repo_name, url=url),
        size=size,
        root=root,
    )


async def get_shallow_root(
    owner: str, repo: str, url: str, headers: dict
) -> Folder:
    """Fetch only the root-level listing of a repo without recursing into subdirectories.

    Directories become stub Folders with no children; files are listed without
    downloading their raw content.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers)

    if response.status_code != 200:
        raise handle_status_code(response, url, api_url)

    items = response.json()
    files: list[File] = []
    folders: list[Folder] = []

    for item in items:
        if item["type"] == "file":
            files.append(
                File(
                    url=item.get("download_url", ""),
                    name=item["name"],
                    size=item.get("size", 0),
                    raw="",  # not downloaded in shallow mode
                )
            )
        elif item["type"] == "dir":
            # Stub folder — no children fetched yet
            folders.append(
                Folder(
                    name=item["name"],
                    size=0,
                    files=[],
                    folders=[],
                )
            )

    return Folder(name="", size=0, files=files, folders=folders)


async def get_subtree(
    owner: str, repo: str, path: str, url: str, headers: dict
) -> Folder:
    """Fetch one level of content at a specific path in the repo (shallow).

    Returns a Folder containing the immediate children (files + stub sub-folders).
    Python files have their raw content downloaded; other files are listed with URL only.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers)

    if response.status_code != 200:
        raise handle_status_code(response, url, api_url)

    items = response.json()
    if not isinstance(items, list):
        raise GithubNoDataError(
            "Expected directory listing",
            {"github_url": url, "path": path},
        )

    from codecarto.services.parsers.language_parser import ParserRegistry
    registered_exts = set(ParserRegistry.all_extensions())

    files: list[File] = []
    folders: list[Folder] = []

    for item in items:
        if item["type"] == "file":
            download_url = item.get("download_url", "")
            ext = Path(item["name"]).suffix.lower()
            if download_url and ext in registered_exts:
                try:
                    raw = await get_raw_from_url(download_url)
                except Exception:
                    raw = ""
            else:
                raw = ""
            files.append(
                File(
                    url=download_url,
                    name=item["name"],
                    size=item.get("size", 0),
                    raw=raw,
                )
            )
        elif item["type"] == "dir":
            folders.append(
                Folder(
                    name=item["name"],
                    size=0,
                    files=[],
                    folders=[],
                )
            )

    folder_name = path.split("/")[-1] if path else ""
    return Folder(name=folder_name, size=0, files=files, folders=folders)


async def fetch_tree_fast(
    owner: str,
    repo: str,
    headers: dict,
    url: str,
) -> tuple[list[tuple[str, str, str]], str]:
    """Fetch the complete repo tree in TWO GitHub API calls.

    Call 1: GET /repos/{owner}/{repo} → default branch name.
    Call 2: GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1 → full flat tree.

    Returns
    -------
    items : list of (path, type, download_url)
        type is ``"blob"`` (file) or ``"tree"`` (directory).
        download_url is the raw.githubusercontent.com URL for blobs, ``""`` for trees.
    default_branch : str
        e.g. ``"main"`` or ``"master"``
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Call 1: repo metadata → default branch
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}", headers=headers
        )
    if resp.status_code != 200:
        raise handle_status_code(resp, url)

    default_branch = resp.json().get("default_branch", "main")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Call 2: full recursive tree
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
            headers=headers,
        )
    if resp.status_code != 200:
        raise handle_status_code(resp, url)

    data = resp.json()
    tree = data.get("tree", [])
    base = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/"

    items: list[tuple[str, str, str]] = []
    for item in tree:
        path = item.get("path", "")
        item_type = item.get("type", "")  # "blob" or "tree"
        dl_url = (base + path) if item_type == "blob" else ""
        items.append((path, item_type, dl_url))

    return items, default_branch


def build_folder_from_tree_items(
    items: list[tuple[str, str, str]],
    owner: str,
    repo: str,
) -> Folder:
    """Build a Folder hierarchy from the flat Git Trees API item list.

    Parameters
    ----------
    items : list of (path, type, download_url)
        As returned by ``fetch_tree_fast``.

    Returns
    -------
    Folder
        Root folder named ``"{owner}/{repo}"`` containing the full tree.
        File objects have ``raw=""`` (content is fetched later).
    """
    root = Folder(name=f"{owner}/{repo}", size=0, files=[], folders=[])
    folder_map: dict[str, Folder] = {"": root}

    # Process tree entries first (dirs), then blobs (files), maintaining depth order
    for path, item_type, dl_url in sorted(items, key=lambda x: (x[0].count("/"), x[1] != "tree", x[0])):
        parts = path.split("/")
        name = parts[-1]
        parent_path = "/".join(parts[:-1])

        # Ensure all ancestor folders exist
        for depth in range(1, len(parts)):
            anc_path = "/".join(parts[:depth])
            if anc_path not in folder_map:
                anc_name = parts[depth - 1]
                anc_parent = "/".join(parts[:depth - 1])
                f = Folder(name=anc_name, size=0, files=[], folders=[])
                folder_map[anc_path] = f
                folder_map.get(anc_parent, root).folders.append(f)

        if item_type == "tree":
            if path not in folder_map:
                f = Folder(name=name, size=0, files=[], folders=[])
                folder_map[path] = f
                folder_map.get(parent_path, root).folders.append(f)
        elif item_type == "blob":
            parent_folder = folder_map.get(parent_path, root)
            parent_folder.files.append(
                File(url=dl_url, name=name, size=0, raw="")
            )

    return root


async def get_repo_content(
    url: str, owner: str, repo: str, path: str = ""
) -> dict:
    """Fetches content of a GitHub repo (files and directories)."""
    headers = create_headers(url)

    # Fetch content from the repo
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    client = httpx.AsyncClient()
    response = await client.get(api_url, headers=headers)

    if response.status_code == 200:
        json_data = response.json()
        if not json_data:
            raise GithubNoDataError("No content in the repo", {"github_url": url})
        return json_data
    else:
        raise handle_status_code(response, url, api_url)


async def check_repo_size(owner: str, repo: str, url: str, headers: dict) -> int:
    """Return the GitHub repo size in KB. Raises on API error."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    client = httpx.AsyncClient()
    response = await client.get(api_url, headers=headers)

    if response.status_code == 200:
        json_data = response.json()
        return json_data.get("size", 0)
    else:
        raise handle_status_code(response, url, api_url)


async def build_content_tree(content: dict, owner: str, repo: str) -> dict:
    """Build a content directory tree from the GitHub API response."""
    results = {}

    for item in content:
        item.pop("sha", None)
        item.pop("url", None)
        item.pop("git_url", None)
        item.pop("_links", None)
        if item["type"] == "dir":
            dir_content = await get_repo_content("", owner, repo, item["path"])
            parsed_content = await build_content_tree(dir_content, owner, repo)
            results[item["name"]] = parsed_content
        elif item["type"] == "file":
            results.setdefault("files", []).append(item)

    return results


async def reduce_repo_structure(repo_data: dict, fetch_content: bool = True) -> Folder:
    """Go through the repo structure and reduce it to just needed content.

    Parameters
    ----------
    repo_data : dict
        Tree dict from build_content_tree().
    fetch_content : bool
        When True (small repos), download raw file content for registered
        parser extensions.  When False (medium repos), include file nodes
        but leave raw=''.
    """
    from codecarto.services.parsers.language_parser import ParserRegistry
    registered_exts = set(ParserRegistry.all_extensions())

    data = Folder(size=0, name="", files=[], folders=[])
    folders_size = 0
    files_size = 0

    for key, value in repo_data.items():
        if key == "files":
            files = []

            for file in value:
                size = file.get("size", 0)

                # Ensure the file has the required attributes
                if file.get("name") and file.get("download_url"):
                    ext = Path(file["name"]).suffix.lower()
                    if fetch_content and ext in registered_exts:
                        try:
                            raw = await get_raw_from_url(file["download_url"])
                        except Exception:
                            raw = ""
                    else:
                        raw = ""

                    files_size += size

                    # Construct a File object
                    files.append(
                        File(
                            url=file.get("download_url"),
                            name=file.get("name"),
                            size=size,
                            raw=raw,
                        )
                    )

            data.files = files

        else:  # Everything else would be a directory
            sub_dir = await reduce_repo_structure(value, fetch_content=fetch_content)

            # Gather files and calculate total files size
            size = sum(file.size for file in sub_dir.files)

            # Gather folders and calculate folder size
            size += sum(folder.size for folder in sub_dir.folders)

            folders_size += size

            # Construct a Folder object
            folder = Folder(
                name=key,  # name of folder
                size=size,
                files=sub_dir.files,
                folders=sub_dir.folders,
            )

            # Add the folder to the directory root's list of folders
            data.folders.append(folder)

    data.size = folders_size + files_size
    return data


async def _expand_folder(
    owner: str,
    repo: str,
    path: str,
    headers: dict,
    max_depth: int,
    current_depth: int,
) -> Folder:
    """Recursively fetch directory structure without file content.

    Files are included as stubs (raw='').  Sub-folders beyond *max_depth* are
    returned as empty stub Folders (no children fetched).
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(api_url, headers=headers)

    if resp.status_code != 200:
        # Return a stub on error rather than crashing the whole expansion
        folder_name = path.split("/")[-1] if path else repo
        return Folder(name=folder_name, size=0, files=[], folders=[])

    items = resp.json()
    if not isinstance(items, list):
        folder_name = path.split("/")[-1] if path else repo
        return Folder(name=folder_name, size=0, files=[], folders=[])

    files: list[File] = []
    folders: list[Folder] = []

    for item in items:
        if item["type"] == "file":
            files.append(
                File(
                    url=item.get("download_url", ""),
                    name=item["name"],
                    size=item.get("size", 0),
                    raw="",
                )
            )
        elif item["type"] == "dir":
            if current_depth + 1 < max_depth:
                sub = await _expand_folder(
                    owner, repo, item["path"], headers, max_depth, current_depth + 1
                )
            else:
                sub = Folder(name=item["name"], size=0, files=[], folders=[])
            folders.append(sub)

    folder_name = path.split("/")[-1] if path else repo
    return Folder(name=folder_name, size=len(files), files=files, folders=folders)


async def expand_all_tree(
    owner: str, repo: str, github_token: str | None = None, max_depth: int = 3
) -> Folder:
    """Expand all folders in a repo tree to *max_depth* without downloading file content."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    return await _expand_folder(owner, repo, "", headers, max_depth, 0)


def get_owner_repo_from_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL."""
    if not url.startswith("https://github.com"):
        raise GithubError("Invalid GitHub URL", {"url": url})

    parts = url.split("/")
    if len(parts) < 5:
        raise GithubError("Invalid GitHub repo URL", {"url": url})

    return parts[3], parts[4]


def create_headers(url: str) -> dict:
    """Create headers for GitHub API request with optional authorization token."""
    import os

    # Try multiple sources for GitHub token (in order of priority):
    # 1. Environment variable
    # 2. Docker secrets file
    # 3. No token (unauthenticated - limited rate)
    GIT_API_KEY = None

    # Try environment variable first
    GIT_API_KEY = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    # Try Docker secrets file if env var not found
    if not GIT_API_KEY:
        try:
            with open("/run/secrets/github_token", "r") as file:
                GIT_API_KEY = file.read().strip()
        except (FileNotFoundError, PermissionError):
            pass  # File doesn't exist or can't be read - will use unauthenticated

    # Build headers
    headers = {"Accept": "application/vnd.github.v3+json"}

    # Add authorization if token found
    if GIT_API_KEY:
        headers["Authorization"] = f"token {GIT_API_KEY}"

    return headers


def handle_status_code(
    response: httpx.Response, url: str, api_url: str = ""
) -> Exception:
    """Handle GitHub API response status codes."""
    if response.status_code == 404:
        return GithubNoDataError(
            "Resource not found", {"github_url": url, "api_url": api_url}
        )
    elif response.status_code == 403:
        error_message = f"GitHub API returned 403: {response.text}"
        if "rate_limit" in response.text:
            error_message = f"GitHub API rate limit exceeded: {response.text}"
        return Github404Error(
            "API rate limit", {"github_url": url, "api_url": api_url}, error_message
        )
    else:
        return GithubError(
            "GitHub API error", {"url": url, "status_code": response.status_code}
        )
