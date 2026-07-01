import asyncio
import logging
import os
import subprocess
import httpx
from pathlib import Path
from codecarto.models.source_data import Directory, File, Folder, RepoInfo
from codecarto.services.cache_service import CacheService
from codecarto.util.exceptions import (
    GithubError,
    Github403Error,
    Github404Error,
    GithubNoDataError,
    GithubRateLimitError,
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

async def _api_get(client: httpx.AsyncClient, url: str, headers: dict) -> httpx.Response:
    """GET an api.github.com URL, retrying once without auth on a bad token.

    A stale/expired GITHUB_TOKEN makes api.github.com hard-reject every call
    with 401 "Bad credentials" — even for public repos that need no auth at
    all. GitHub's archive-download endpoint (codeload.github.com, used by
    the C parser path) instead silently ignores a bad token and serves the
    repo unauthenticated. This brings api.github.com calls in line with
    that behavior so a bad token degrades to "unauthenticated rate limit"
    instead of "nothing works", matching the C path.
    """
    response = await client.get(url, headers=headers)
    if response.status_code == 401 and "Authorization" in headers:
        fallback_headers = {k: v for k, v in headers.items() if k != "Authorization"}
        response = await client.get(url, headers=fallback_headers)
    return response


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


async def _fetch_content_for_folder(folder: Folder, concurrency: int = 8) -> None:
    """Fill in ``File.raw`` for every registered-extension file under *folder*,
    fetched concurrently. Mutates the tree in place."""
    from codecarto.services.parsers.language_parser import ParserRegistry
    registered_exts = set(ParserRegistry.all_extensions())

    targets: list[File] = [
        file for _, file in folder.iter_files()
        if file.url and Path(file.name).suffix.lower() in registered_exts
    ]

    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_one(file: File) -> None:
        async with semaphore:
            try:
                file.raw = await get_raw_from_url(file.url)
            except Exception:
                file.raw = ""

    await asyncio.gather(*(fetch_one(f) for f in targets))


async def get_raw_from_repo(url: str) -> Directory:
    """Read raw data from a repo URL (cached — see CacheService.get_tree).

    For repos within the size limit, fetches the full tree with file content.
    For medium repos, structure only (no content). For huge/truncated repos,
    falls back to a shallow top-level listing marked ``is_partial=True``.
    """
    cached = CacheService.get_tree(url)
    if cached is not None:
        return Directory.model_validate(cached)

    owner, repo_name = get_owner_repo_from_url(url)
    headers = create_headers(url)

    items, _default_branch, size_kb, truncated = await fetch_tree_fast(
        owner, repo_name, headers, url
    )

    if truncated or size_kb >= _STRUCTURE_FETCH_LIMIT_KB:
        # Very large repo (≥ 50 MB, or the recursive tree call itself got
        # truncated by GitHub): return only the root-level structure
        root = await get_shallow_root(owner, repo_name, url, headers)
        root.name = f"{owner}/{repo_name}"
        directory = Directory(
            info=RepoInfo(owner=owner, name=repo_name, url=url),
            size=size_kb,
            root=root,
            is_partial=True,
        )
        CacheService.set_tree(url, directory.model_dump())
        return directory

    root = build_folder_from_tree_items(items, owner, repo_name)
    root.name = f"{owner}/{repo_name}"

    if size_kb < _CONTENT_FETCH_LIMIT_KB:
        await _fetch_content_for_folder(root)

    directory = Directory(
        info=RepoInfo(owner=owner, name=repo_name, url=url),
        size=size_kb,
        root=root,
        is_partial=False,
    )
    CacheService.set_tree(url, directory.model_dump())
    return directory


async def get_shallow_root(
    owner: str, repo: str, url: str, headers: dict
) -> Folder:
    """Fetch only the root-level listing of a repo without recursing into subdirectories.

    Directories become stub Folders with no children; files are listed without
    downloading their raw content.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
    async with httpx.AsyncClient() as client:
        response = await _api_get(client, api_url, headers)

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
        response = await _api_get(client, api_url, headers)

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


# In-process memo for fetch_tree_fast — every /parse/stream-url call hits
# api.github.com twice with zero caching today, so re-streaming the same
# repo seconds apart (re-clicking a chip, a page reload, repeated manual
# testing) burns 2 calls each time against the 60/hour unauthenticated
# budget for no reason. This is deliberately a short-TTL in-memory dict, not
# a new persistent cache — it's pure rate-limit protection against
# redundant rapid repeats, not a feature in its own right. Cleared on
# process restart, which is fine for that purpose.
_TREE_CACHE_TTL = 120  # seconds
_tree_cache: dict[str, tuple[float, list[tuple[str, str, str]], str, int, bool]] = {}


async def fetch_tree_fast(
    owner: str,
    repo: str,
    headers: dict,
    url: str,
) -> tuple[list[tuple[str, str, str]], str, int, bool]:
    """Fetch the complete repo tree in TWO GitHub API calls (memoized).

    Call 1: GET /repos/{owner}/{repo} → default branch name + repo size.
    Call 2: GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1 → full flat tree.

    Returns
    -------
    items : list of (path, type, download_url)
        type is ``"blob"`` (file) or ``"tree"`` (directory).
        download_url is the raw.githubusercontent.com URL for blobs, ``""`` for trees.
    default_branch : str
        e.g. ``"main"`` or ``"master"``
    size_kb : int
        Repo size as reported by GitHub (from call 1 — avoids a separate
        check_repo_size call).
    truncated : bool
        True if GitHub truncated the recursive tree response (repo too large
        for one call — >100k entries or >7MB) — caller should fall back to a
        shallow listing rather than trust this as the complete tree.
    """
    import time

    cache_key = f"{owner}/{repo}"
    cached = _tree_cache.get(cache_key)
    if cached and (time.monotonic() - cached[0]) < _TREE_CACHE_TTL:
        return cached[1], cached[2], cached[3], cached[4]

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Call 1: repo metadata → default branch + size
        resp = await _api_get(
            client, f"https://api.github.com/repos/{owner}/{repo}", headers
        )
    if resp.status_code != 200:
        raise handle_status_code(resp, url)

    meta = resp.json()
    default_branch = meta.get("default_branch", "main")
    size_kb = meta.get("size", 0)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Call 2: full recursive tree
        resp = await _api_get(
            client,
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
            headers,
        )
    if resp.status_code != 200:
        raise handle_status_code(resp, url)

    data = resp.json()
    truncated = bool(data.get("truncated", False))
    tree = data.get("tree", [])
    base = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/"

    items: list[tuple[str, str, str]] = []
    for item in tree:
        path = item.get("path", "")
        item_type = item.get("type", "")  # "blob" or "tree"
        dl_url = (base + path) if item_type == "blob" else ""
        items.append((path, item_type, dl_url))

    _tree_cache[cache_key] = (time.monotonic(), items, default_branch, size_kb, truncated)
    return items, default_branch, size_kb, truncated


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
        resp = await _api_get(client, api_url, headers)

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


_log = logging.getLogger(__name__)

# ── GitHub token resolution ─────────────────────────────────────────────────
# Resolved once at startup via resolve_github_token(); cached here so every
# API request reuses it without re-running the subprocess.
_github_token: str | None = None
_github_token_source: str = "none"


def resolve_github_token() -> tuple[str | None, str]:
    """Resolve the best available GitHub token and name the source.

    Resolution order (first non-empty string wins):

    1. CC_GITHUB_TOKEN — project-specific env var that can be set
       independently of the system GITHUB_TOKEN, so it never conflicts
       with a stale gh-cli GITHUB_TOKEN.

    2. gh auth token (keyring) — `gh auth token --hostname github.com`
       invoked with GITHUB_TOKEN and GH_TOKEN stripped from the subprocess
       environment so the gh CLI uses its keyring credential rather than
       the (potentially stale) env var.

    3. GITHUB_TOKEN env var — legacy / Docker Compose pass-through.

    4. GH_TOKEN env var — alternative legacy name.

    5. Docker secrets file — /run/secrets/github_token.

    6. None — unauthenticated; rate-limited to 60 req/h per IP.

    Returns (token_or_None, source_label).
    """
    # 1. Explicit project override
    if token := os.environ.get("CC_GITHUB_TOKEN", "").strip():
        return token, "CC_GITHUB_TOKEN env var"

    # 2. gh CLI keyring — strip GITHUB_TOKEN/GH_TOKEN so gh uses keyring
    try:
        env_without_token = {
            k: v for k, v in os.environ.items()
            if k not in ("GITHUB_TOKEN", "GH_TOKEN")
        }
        result = subprocess.run(
            ["gh", "auth", "token", "--hostname", "github.com"],
            capture_output=True, text=True, timeout=5, env=env_without_token,
        )
        if result.returncode == 0 and (token := result.stdout.strip()):
            return token, "gh CLI keyring"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # gh not installed or timed out

    # 3 & 4. Env vars (legacy / Docker Compose)
    if token := (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip():
        return token, "GITHUB_TOKEN/GH_TOKEN env var"

    # 5. Docker secrets
    try:
        token = Path("/run/secrets/github_token").read_text().strip()
        if token:
            return token, "Docker secret"
    except (FileNotFoundError, PermissionError):
        pass

    # 6. Unauthenticated
    return None, "none (unauthenticated)"


def get_github_token() -> str | None:
    """Return the cached GitHub token, resolving it on first call."""
    global _github_token, _github_token_source
    if _github_token is None and _github_token_source == "none":
        _github_token, _github_token_source = resolve_github_token()
        if _github_token:
            _log.info("GitHub auth: %s (token: %s…)", _github_token_source, _github_token[:8])
        else:
            _log.warning(
                "GitHub auth: unauthenticated — rate-limited to 60 req/h per IP. "
                "Set CC_GITHUB_TOKEN or run 'gh auth login'."
            )
    return _github_token


def github_auth_status() -> dict:
    """Return a dict describing the current GitHub auth state (for /auth/github)."""
    get_github_token()  # ensure resolved
    return {
        "source": _github_token_source,
        "authenticated": _github_token is not None,
        "token_prefix": _github_token[:8] + "…" if _github_token else None,
    }


def create_headers(url: str) -> dict:
    """Build GitHub API request headers using the resolved token."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def handle_status_code(
    response: httpx.Response, url: str, api_url: str = ""
) -> Exception:
    """Handle GitHub API response status codes.

    Always carries the REAL status code and response body into the
    exception/message — a previous version defaulted everything outside
    404/403 to a generic "GitHub API returned 500", which made an invalid
    GITHUB_TOKEN (401) or a genuine rate limit (429) indistinguishable from
    an actual server error. See docs/api.md's GitHub error notes.
    """
    params = {"github_url": url, "api_url": api_url, "status_code": response.status_code}
    body = response.text[:500]  # avoid dumping huge HTML error pages into logs

    retry_after = response.headers.get("retry-after")
    reset = response.headers.get("x-ratelimit-reset")
    retry_hint = f" Retry after {retry_after}s." if retry_after else (
        f" Resets at unix ts {reset}." if reset else ""
    )

    if response.status_code == 404:
        return GithubNoDataError(
            "Resource not found", params, f"GitHub API returned 404: {body}"
        )
    if response.status_code == 401:
        return GithubAPIError(
            "Invalid GitHub credentials", params,
            "GitHub API returned 401 (Unauthorized) — the GITHUB_TOKEN/GH_TOKEN "
            f"env var is set but invalid or expired. Response: {body}",
        )
    if response.status_code == 429 or (
        response.status_code == 403 and (
            "rate limit" in body.lower() or "abuse" in body.lower()
        )
    ):
        return GithubRateLimitError(
            "GitHub API rate limit", params,
            f"GitHub API rate limit exceeded (HTTP {response.status_code}).{retry_hint} {body}",
        )
    if response.status_code == 403:
        return Github403Error(
            "GitHub API access denied", params, f"GitHub API returned 403: {body}"
        )
    return GithubError(
        "GitHub API error", params,
        f"GitHub API returned {response.status_code}: {body}",
        status_code=response.status_code,
    )
