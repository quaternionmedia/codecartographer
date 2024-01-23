import httpx
from src.util.exceptions import (
    GithubAPIError,
    GithubSizeError,
    GithubNoDataError,
    Github404Error,
    GithubError,
)


class ImportSourceUrlError(Exception):
    """Import Source Url error"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "Import Source Url error",
        status_code: int = 500,
        exc: Exception = None,
    ):
        self.source = source
        self.message = message
        self.status_code = status_code
        self.params = params
        self.exc = exc


class ImportSourceUrlHttpError(httpx.RequestError):
    """Import Source Url Httpx error"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "Import Source Url Httpx error",
        status_code: int = 500,
        exc: Exception = None,
    ):
        super().__init__(source, params, message, status_code, exc)


# DEBUG
import logging

logger = logging.getLogger(__name__)


async def read_github_content(
    url: str,
    owner: str,
    repo: str,
    path: str = "",
    first: bool = False,
) -> list[dict] | dict:
    """Reads GitHub content from a URL

    Parameters:
        url {str} -- URL to read from
        owner {str} -- Owner of the GitHub repo
        repo {str} -- Name of the GitHub repo
        path {str} -- Path to the file or directory to read from
        first {bool} -- Whether this is the first call to this function

    Returns:
        list[dict] | dict -- List of dictionaries containing GitHub file content
    """
    try:
        client = httpx.AsyncClient()

        # Construct the API URL
        with open("/run/secrets/github_token", "r") as file:
            GIT_API_KEY = file.read().strip()
        if not GIT_API_KEY or GIT_API_KEY == "":
            raise GithubAPIError(
                "read_github_content", {"github_url": url, "api_url": "nothing"}
            )

        headers = {
            "Accept": "application/vnd.github.v3+json",
            # Uncomment and set your token if you have one
            "Authorization": f"token {GIT_API_KEY}",
        }

        # get the size of the whole repo
        if first:
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = await client.get(
                api_url, headers=headers, follow_redirects=False
            )
            if response.status_code == 200:
                json_data = response.json()
                if json_data["size"]:
                    size = json_data["size"]
                    logger.info(f"  Repo Size: {size} bytes")
                    if size > 1000000:
                        raise GithubSizeError(
                            "read_github_content",
                            {"github_url": url, "api_url": api_url},
                        )

        # get the actual contents of the repo
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        response = await client.get(api_url, headers=headers, follow_redirects=False)

        # Check the response
        if response.status_code == 200:
            json_data = response.json()
            if not json_data:
                raise GithubNoDataError(
                    "read_github_content",
                    {"github_url": url, "api_url": api_url},
                )
            else:
                # Remove unnecessary data from the response
                # this will leave us with {name, path, size, html_url, download_url, type}
                # html url is the url to view the file in the browser
                # download url is the url to see just the raw file contents
                for item in json_data:
                    item.pop("sha", None)
                    item.pop("url", None)
                    item.pop("git_url", None)
                    item.pop("_links", None)

                return json_data
        else:
            if response.status_code == 404:
                raise GithubNoDataError(
                    "read_github_content",
                    {"github_url": url, "api_url": api_url},
                )
            if response.status_code == 403:
                error_message = f"GitHub API returned 403: {response.text}"
                if "rate_limit" in response.text:
                    error_message = f"GitHub API rate limit exceeded: {response.text}"
                raise Github404Error(
                    "read_github_content",
                    {"github_url": url, "api_url": api_url},
                    error_message,
                )
            else:
                raise GithubError(
                    "read_github_content",
                    {"url": url, "status_code": response.status_code},
                    "Error with client response",
                )
    except httpx.RequestError as exc:
        raise ImportSourceUrlHttpError(
            "read_github_content",
            {"url": url},
            "Error while attempting to set up request url & headers",
            500,
            exc,
        )
    except Exception as exc:
        raise ImportSourceUrlError(
            "read_github_content",
            {"url": url},
            "Error when reading GitHub content",
            500,
            exc,
        )


async def parse_github_content(file_content, owner, repo) -> dict:
    """Parses GitHub content and returns a dictionary of directories and files

    Parameters:
        file_content {list} -- List of dictionaries containing GitHub file content
        owner {str} -- Owner of the GitHub repo
        repo {str} -- Name of the GitHub repo

    Returns:
        dict -- Dictionary of directories and files
    """
    try:
        # Check that the file content is a list
        if not file_content or not isinstance(file_content, list):
            raise ImportSourceUrlError(
                "parse_github_content",
                {},
                "Invalid file content format",
                404,
                exc,
            )

        # Process directories
        results = {}
        directories: list = [item for item in file_content if item["type"] == "dir"]
        files: list = [item for item in file_content if item["type"] == "file"]

        for dir in directories:
            dir_content = await read_github_content("", owner, repo, dir["path"])
            parsed_dir_content = await parse_github_content(dir_content, owner, repo)
            dir_name = dir["name"]
            results[dir_name] = parsed_dir_content

        # Process files
        top_files = []
        for file in files:
            top_files.append(file)
        if top_files and len(top_files) > 0:
            results["files"] = top_files

        return results
    except Exception as exc:
        raise ImportSourceUrlError(
            "parse_github_content",
            {"owner": owner, "repo": repo},
            "Error when parsing GitHub content",
            exc,
        )


async def read_data_from_url(url: str) -> str | dict:
    """Read raw data from a URL.

    Parameters:
        url (str): URL to read from

    Returns:
        str | dict: Raw data from URL
    """
    try:
        logger.info(f"  Started   Proc.read_raw_data_from_url(): url - {url}")
        if not url.endswith(".py"):
            raise ImportSourceUrlError(
                "read_raw_data_from_url",
                {"url": url},
                "URL is not a valid Python file",
                404,
            )
        client = httpx.AsyncClient()
        response = await client.get(url)
        if response.status_code == 200:
            return response.text
        else:
            raise ImportSourceUrlError(
                "read_raw_data_from_url",
                {"url": url},
                "Could not read raw data from URL",
                404,
            )
    except Exception as exc:
        raise ImportSourceUrlError(
            "read_raw_data_from_url",
            {"url": url},
            "Error when reading raw data from URL",
            500,
            exc,
        )
    finally:
        if client:
            await client.aclose()
        logger.info(f"  Finished    Proc.read_raw_data_from_url()")
