import httpx
from fastapi import APIRouter, HTTPException

from api.util import generate_return, proc_exception

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
    try:
        client = httpx.AsyncClient()
        logger.info(
            f"  Started     Proc.handle_github_url(): github_url - {github_url}"
        )
        # check that the url is a github url
        if "github.com" not in github_url:
            proc_exception(
                "handle_github_url",
                "URL is not a valid GitHub URL",
                {"github_url": github_url},
                status=404,
            )

        # Extract owner and repo from the URL
        # Assuming the URL is like: https://github.com/owner/repo
        parts = github_url.split("/")
        if len(parts) < 5 or parts[2] != "github.com":
            proc_exception(
                "read_github_file",
                "Invalid GitHub URL format",
                {"github_url": github_url},
            )
        owner, repo = parts[3], parts[4]

        # get content from url
        url_content: list[dict] = await read_github_content(github_url, owner, repo)
        if not url_content:
            proc_exception(
                "handle_github_url",
                "Empty file content received from GitHub",
                {"github_url": github_url},
            )

        # url_content = await fetch_directory(github_url)
        repo_contents = {
            "package_owner": owner,
            "package_name": repo,
            "contents": {},
        }
        logger.info(f"  Started     Proc.parse_github_content(): {owner}/{repo}")
        repo_contents["contents"]: dict = await parse_github_content(
            url_content, owner, repo
        )
        logger.info(f"  Finished    Proc.parse_github_content()")
        if repo_contents:
            return generate_return(
                "success", "Proc.handle_github_url() - Success", repo_contents
            )
        else:
            proc_exception(
                "handle_github_url",
                "Could not parse file content",
                {"github_url": github_url},
            )
    except HTTPException as exc:
        # Handle network errors
        proc_exception(
            "handle_github_url",
            "An error occurred while requesting",
            {"github_url": github_url},
            exc,
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


async def read_github_content(
    url: str, owner: str, repo: str, path: str = ""
) -> list[dict]:
    try:
        import os
        from dotenv import load_dotenv

        client = httpx.AsyncClient()
        logger.info(f"Started Proc.read_github_content(): {url}")

        # Construct the API URL
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        load_dotenv()
        git_api_key = os.getenv("GIT_API_KEY")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            # Uncomment and set your token if you have one
            "Authorization": git_api_key,
        }

        response = await client.get(api_url, headers=headers, follow_redirects=False)

        if response.status_code == 200:
            json_data = response.json()
            if not json_data:
                proc_exception(
                    "read_github_content",
                    "No data returned from GitHub API for UR",
                    {"url": url, "api_url": api_url},
                )

            # Remove unnecessary data from the response
            # this will leave us with {name, path, size, html_url, download_url, type}
            # html url is the url to view the file in the browser
            # download url is the url to see just the raw file contents
            for item in json_data:
                item.pop("sha", None)
                item.pop("url", None)
                item.pop("git_url", None)
                item.pop("_links", None)

            logger.info(f"    json_data: {json_data}")
            return json_data
        else:
            if response.status_code == 404:
                proc_exception(
                    "read_github_content",
                    "GitHub API returned 404",
                    {"url": url, "api_url": api_url},
                    HTTPException,
                    404,
                )
            else:
                proc_exception(
                    "read_github_content",
                    "Error with client response",
                    {"url": url, "status_code": response.status_code},
                )
    except httpx.RequestError as exc:
        proc_exception(
            "read_github_content",
            "Error while attempting to set up request url & headers",
            {"url": url},
            exc,
        )
    finally:
        logger.info(f"Finished Proc.read_github_content(): {url}")


async def parse_github_content(file_content, owner, repo) -> dict:
    try:
        # Check that the file content is a list
        if not file_content or not isinstance(file_content, list):
            proc_exception(
                "parse_github_content",
                "Invalid file content format",
                {"file_content": file_content},
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
            {"raw_data": raw_data},
            exc,
        )
    finally:
        logger.info(f"  Finished    Proc.text_to_json()")
