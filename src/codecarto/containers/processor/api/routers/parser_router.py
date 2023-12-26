import re 
import httpx
from fastapi import APIRouter, HTTPException

from api.util import generate_return, proc_exception, proc_error

# DEBUG
import logging

logger = logging.getLogger(__name__)

# Create a router
ParserRoute = APIRouter()


@ParserRoute.get("/parse")
async def parse():
    pass


@ParserRoute.get("/handle_github_url")
async def handle_github_url(github_url: str) -> dict:
    import time
    # get current time to calculate total time taken
    start_time = time.time()
    try: 
        client = httpx.AsyncClient()
        logger.info(
            f"  Started     Proc.handle_github_url(): github_url - {github_url}"
        )

        # check that the url is a github url
        if "github.com" not in github_url:
            return proc_error(
                "handle_github_url",
                "Invalid GitHub URL",
                {"github_url": github_url},
                404,
            )

        # Extract owner and repo from the URL
        # Assuming the URL is like: https://github.com/owner/repo
        parts = github_url.split("/")
        if len(parts) < 5 or parts[2] != "github.com":
            return proc_error(
                "handle_github_url",
                "Invalid GitHub URL format",
                {"github_url": github_url},
                404,
            )
        owner, repo = parts[3], parts[4]

        # get content from url
        url_content: list[dict] | dict = await read_github_content(
            github_url, owner, repo, "", True
        )
        if not url_content:
            return proc_error(
                "handle_github_url",
                "Empty file content received from GitHub",
                {"github_url": github_url},
                500,
            )
        else:
            # check if url_content is an error
            if "status" in url_content:
                return url_content

        # parse the content
        repo_contents = {
            "package_owner": owner,
            "package_name": repo,
            "contents": {},
        }
        logger.info(f"\tStarted\tProc.parse_github_content(): {owner}/{repo}")
        contents: dict = await parse_github_content(url_content, owner, repo)
        logger.info(f"\tFinished\tProc.parse_github_content()")

        # check contents
        if contents:
            # check if contents dict has status key
            # if it does, then it is an error
            # logger.info(f"\n\n\tContents: {contents}\n\n")
            if "status" in contents:
                return contents
            else:
                # otherwise good to return
                repo_contents["contents"] = contents
                return generate_return(
                    200, "Proc.handle_github_url() - Success", repo_contents
                )
        else:
            # contents is empty
            return proc_error(
                "handle_github_url",
                "Could not parse file content",
                {"github_url": github_url},
                500,
            )
    except Exception as exc:
        proc_exception(
            "handle_github_url",
            "Error when handling GitHub URL",
            {"github_url": github_url},
            exc,
        )

    finally:
        await client.aclose()
        logger.info(f"  Finished    Proc.handle_github_url()")
        # calculate total time taken
        end_time = time.time()
        total_time = time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))
        logger.info(f"  Total time taken: {total_time}")
        # TODO: Log this in database later
        


async def read_github_content(
    url: str,
    owner: str,
    repo: str,
    path: str = "",
    first: bool = False,
) -> list[dict] | dict:
    try:
        client = httpx.AsyncClient()

        # Construct the API URL
        with open("/run/secrets/github_token", "r") as file:
            GIT_API_KEY = file.read().strip() 
        if not GIT_API_KEY or GIT_API_KEY == "":
            return proc_error(
                "read_github_content",
                "No GitHub API key found",
                {"url": url, "api_url": "nothing"},
                403,
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
                        return proc_error(
                            "read_github_content",
                            "GitHub repo is too large",
                            {"url": url, "api_url": api_url},
                            500,
                        )

        # get the actual contents of the repo
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        response = await client.get(api_url, headers=headers, follow_redirects=False)

        # Check the response
        if response.status_code == 200:
            json_data = response.json()
            if not json_data:
                return proc_error(
                    "read_github_content",
                    "No data returned from GitHub API for URL",
                    {"url": url, "api_url": api_url},
                    404,
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
                return proc_error(
                    "read_github_content",
                    "GitHub API returned 404",
                    {"url": url, "api_url": api_url},
                    404,
                )
            if response.status_code == 403:
                error_message = f"GitHub API returned 403: {response.text}"
                if "rate_limit" in response.text:
                    error_message = f"GitHub API rate limit exceeded: {response.text}"
                return proc_error(
                    "read_github_content",
                    error_message,
                    {"url": url, "api_url": api_url},
                    403,
                )
            else:
                return proc_error(
                    "read_github_content",
                    "Error with client response",
                    {"url": url, "status_code": response.status_code},
                    500,
                )
    except httpx.RequestError as exc:
        proc_exception(
            "read_github_content",
            "Error while attempting to set up request url & headers",
            {"url": url},
            exc,
        )
    except Exception as exc:
        proc_exception(
            "read_github_content",
            "Error when reading GitHub content",
            {"url": url},
            exc,
        ) 
        


async def parse_github_content(file_content, owner, repo) -> dict:
    try:
        # Check that the file content is a list
        if not file_content or not isinstance(file_content, list):
            return proc_error(
                "parse_github_content",
                "Invalid file content format",
                {},
                404,
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
        proc_exception(
            "parse_github_content",
            "Error when parsing GitHub content",
            {"owner": owner, "repo": repo},
            exc,
        ) 
        


def raw_to_graph(raw_data: str, filename: str):
    try:
        logger.info(f"  Started     Proc.text_to_json()")
        from src.parser.parser import Parser

        parser = Parser(None, {"raw": raw_data, "filename": filename})
        graph = parser.graph
        return graph
    except Exception as exc:
        proc_exception(
            "text_to_json",
            "Error when transforming raw data to JSON",
            {},
            exc,
        )
    finally:
        logger.info(f"  Finished    Proc.text_to_json()")
        
