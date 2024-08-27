import httpx
from util.exceptions import (
    GithubError,
    Github404Error,
    GithubNoDataError,
    GithubSizeError,
    GithubAPIError,
    ImportSourceUrlError,
    ImportSourceUrlHttpError,
)
from util.utilities import Log
from models.graph_data import Repo


########################   OLD CODE   ########################
async def get_github_repo_content(
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
                "get_github_repo_content", {"github_url": url, "api_url": "nothing"}
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
                    Log.info(f"  Repo Size: {size} bytes")
                    if size > 1000000:
                        raise GithubSizeError(
                            "get_github_repo_content",
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
                    "get_github_repo_content",
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
                    "get_github_repo_content",
                    {"github_url": url, "api_url": api_url},
                )
            if response.status_code == 403:
                error_message = f"GitHub API returned 403: {response.text}"
                if "rate_limit" in response.text:
                    error_message = f"GitHub API rate limit exceeded: {response.text}"
                raise Github404Error(
                    "get_github_repo_content",
                    {"github_url": url, "api_url": api_url},
                    error_message,
                )
            else:
                raise GithubError(
                    "get_github_repo_content",
                    {"url": url, "status_code": response.status_code},
                    "Error with client response",
                )
    except httpx.RequestError as exc:
        raise ImportSourceUrlHttpError(
            "get_github_repo_content",
            {"url": url},
            "Error while attempting to set up request url & headers",
            500,
            exc,
        )
    except Exception as exc:
        raise ImportSourceUrlError(
            "get_github_repo_content",
            {"url": url},
            "Error when reading GitHub content",
            500,
            exc,
        )


async def get_repo_tree(file_content, owner, repo) -> dict:
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
                "get_repo_tree",
                {},
                "Invalid file content format",
                404,
            )

        # Process directories
        results = {}
        directories: list = [item for item in file_content if item["type"] == "dir"]
        files: list = [item for item in file_content if item["type"] == "file"]

        for dir in directories:
            dir_content = await get_github_repo_content("", owner, repo, dir["path"])
            parsed_dir_content = await get_repo_tree(dir_content, owner, repo)
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
            "get_repo_tree",
            {"owner": owner, "repo": repo},
            "Error when parsing GitHub content",
            500,
            exc,
        )


async def get_raw_data_from_github_url(url: str) -> str:
    """Read raw data from a URL.

    Parameters:
        url (str): URL to read from

    Returns:
        str: Raw data from URL
    """
    try:
        Log.info(f"  Started   Proc.get_raw_data_from_github_url(): url - {url}")
        if not url.endswith(".py"):
            raise ImportSourceUrlError(
                "get_raw_data_from_github_url",
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
                "get_raw_data_from_github_url",
                {"url": url},
                "Could not read raw data from URL",
                404,
            )
    except Exception as exc:
        raise ImportSourceUrlError(
            "get_raw_data_from_github_url",
            {"url": url},
            "Error when reading raw data from URL",
            500,
            exc,
        )
    finally:
        Log.info(f"  Finished    Proc.get_raw_data_from_github_url()")


async def get_raw_data_from_github_repo(url: str) -> dict:
    """Read raw data from a repo URL.

    Parameters:
        url (str): Repo URL to read from

    Returns:
        str | dict: Raw repo data from URL
    """
    from pprint import pprint

    try:
        Log.info(f"  Started    Proc.get_raw_data_from_github_repo(): url - {url}")
        if not url or url == "":
            raise ImportSourceUrlError(
                "get_raw_data_from_github_repo",
                {"url": url},
                "URL is not a valid repo URL",
                404,
            )

        # Parse the URL
        url_parts = url.split("/")
        if len(url_parts) < 5:
            raise ValueError(f"Invalid GitHub repo URL: {url}")

        # Get the owner and repo name
        # url is in the format github.com/owner/repo and possibly /repo/
        owner = url_parts[3]
        repo = url_parts[4]
        Log.info(f"Owner: {owner}, Repo: {repo}, URL: {url}")
        # Call the recursive function to create the repo structure
        repo_contents = await get_github_repo_content(url, owner, repo, "", True)
        repo_tree = await get_repo_tree(repo_contents, owner, repo)
        repo_raw_data, repo_size = await reduce_repo_structure(repo_tree)
        repo_structure = {
            "owner": owner,
            "repo": repo,
            "size": repo_size,
            "raw": repo_raw_data,
        }
        pprint(repo_structure)

        return repo_structure
    except Exception as exc:
        raise ImportSourceUrlError(
            "get_raw_data_from_github_repo",
            {"url": url},
            f"Error when reading raw data from repo URL: {exc}",
            500,
            exc,
        )
    finally:
        Log.info(f"  Finished    Proc.get_raw_data_from_github_repo()")


def get_github_repo_source(data: dict) -> Repo:
    try:
        return Repo(data["owner"], data["repo"], data["size"], data["raw"])
    except Exception as exc:
        raise ImportSourceUrlError(
            "get_github_repo_tree",
            {"data": data},
            f"Error when reading raw data from repo URL: {exc}",
            500,
            exc,
        )
    finally:
        Log.info(f"  Finished    Proc.get_github_repo_tree()")


async def reduce_repo_structure(repo_data: dict, repo_size: int = 0) -> tuple:
    """Go through the repo structure and reduce it to just needed content

    Parameters:
        repo_data {dict} -- Dictionary of directories and files
        repo_size {int} -- Size of the repo in bytes

    Returns:
        tuple -- Tuple containing the reduced repo structure and the repo size
    """
    try:
        repo_structure = {}
        # loop through the repo data
        for key, value in repo_data.items():
            # if key is files, then it's a list of files
            if key == "files":
                files = []
                # loop through the files
                for file in value:
                    # add the file size to the repo size
                    repo_size += file.get("size", 0)
                    # if the file is a python file, get the raw data
                    if file["download_url"]:
                        if file["download_url"].endswith(".py"):
                            file_raw_data = await get_raw_data_from_github_url(
                                file["download_url"]
                            )
                            file["file_type"] = "python"
                        else:  # otherwise, just get the download url
                            file_raw_data = file["download_url"]
                            file["file_type"] = "other"
                    file["raw"] = file_raw_data
                    # remove unnecessary data from the file
                    file.pop("path", None)
                    file.pop("size", None)
                    file.pop("type", None)
                    file.pop("html_url", None)
                    file.pop("download_url", None)
                    # add the file to the list of files
                    files.append(file)
                repo_structure[key] = files
            else:  # key is a directory
                # recursively call this function to reduce the sub directory
                sub_dir_structure, repo_size = await reduce_repo_structure(
                    value, repo_size
                )
                repo_structure[key] = sub_dir_structure

        # return the repo structure and the repo size
        # pprint(repo_structure)
        return (repo_structure, repo_size)
    except Exception as exc:
        raise ImportSourceUrlError(
            "reduce_repo_structure",
            {"repo_data": repo_data},
            "Error when reading raw data from repo URL",
            500,
            exc,
        )
