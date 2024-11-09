import httpx
from models.source_data import Directory, File, Folder, RepoInfo
from util.exceptions import (
    GithubError,
    Github404Error,
    GithubNoDataError,
    GithubSizeError,
    GithubAPIError,
    ImportSourceUrlError,
)


async def get_raw_from_url(url: str) -> str:
    """Fetch raw content from a specific URL."""
    if not url.endswith(".py"):
        raise ImportSourceUrlError("Not a valid Python file URL", {"url": url})

    client = httpx.AsyncClient()
    response = await client.get(url)

    if response.status_code == 200:
        return response.text

    raise handle_status_code(response, url)


async def get_raw_from_repo(url: str) -> Directory:
    """Read raw data from a repo URL"""
    # Fetch the repo content and reduce the structure
    owner, repo_name = get_owner_repo_from_url(url)
    content = await get_repo_content(url, owner, repo_name, isFirst=True)
    tree = await build_content_tree(content, owner, repo_name)
    root = await reduce_repo_structure(tree)
    root.name = f"{owner}/{repo_name}"

    # Calculate the total size of the repo files
    size = sum(file.size for file in root.files)

    # Add the repo folder sizes
    size += sum(folder.size for folder in root.folders)

    return Directory(
        info=RepoInfo(owner=owner, name=repo_name, url=url),
        size=size,
        root=root,
    )


async def get_repo_content(
    url: str, owner: str, repo: str, path: str = "", isFirst: bool = False
) -> dict:
    """Fetches content of a GitHub repo (files and directories)."""
    headers = create_headers(url)

    # Check repo size only for the first call
    if isFirst:
        await check_repo_size(owner, repo, url, headers)

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


async def check_repo_size(owner: str, repo: str, url: str, headers: dict):
    """Check the size of the GitHub repo."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    client = httpx.AsyncClient()
    response = await client.get(api_url, headers=headers)

    if response.status_code == 200:
        json_data = response.json()
        size = json_data.get("size", 0)
        if size > 1000000:
            raise GithubSizeError(
                f"Repo is too large: {size} bytes", {"github_url": url}
            )
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


async def reduce_repo_structure(repo_data: dict) -> Folder:
    """Go through the repo structure and reduce it to just needed content"""
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
                    file_type = (
                        "python" if file["download_url"].endswith(".py") else "other"
                    )

                    if file_type == "python":
                        raw = await get_raw_from_url(file["download_url"])
                    else:
                        raw = file["download_url"]

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
            sub_dir = await reduce_repo_structure(value)

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


def get_owner_repo_from_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL."""
    if not url.startswith("https://github.com"):
        raise GithubError("Invalid GitHub URL", {"url": url})

    parts = url.split("/")
    if len(parts) < 5:
        raise GithubError("Invalid GitHub repo URL", {"url": url})

    return parts[3], parts[4]


def create_headers(url: str) -> dict:
    """Create headers for GitHub API request with authorization token."""
    with open("/run/secrets/github_token", "r") as file:
        GIT_API_KEY = file.read().strip()

    if not GIT_API_KEY:
        raise GithubAPIError("Missing GitHub token", {"github_url": url})

    return {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GIT_API_KEY}",
    }


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
