import httpx
from fastapi import APIRouter

from src.util.exceptions import GithubError
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
    """Handles a GitHub URL and returns a dictionary of directories and files

    Parameters:
        github_url {str} -- GitHub URL to handle

    Returns:
        dict -- Dictionary of directories and files
    """
    import time
    from src.parser.import_source_url import (
        ImportSourceUrlError,
        get_github_repo_content,
        get_repo_tree,
    )

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
        url_content: list[dict] | dict = await get_github_repo_content(
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
        logger.info(f"\tStarted\tProc.get_repo_tree(): {owner}/{repo}")
        contents: dict = await get_repo_tree(url_content, owner, repo)
        logger.info(f"\tFinished\tProc.get_repo_tree()")

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
    except GithubError as exc:
        proc_exception(
            exc.source,
            exc.message,
            exc.params,
            exc,
        )
    except ImportSourceUrlError as exc:
        proc_exception(
            exc.source,
            exc.message,
            exc.params,
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
        # calculate total time taken
        end_time = time.time()
        total_time = time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))
        logger.info(f"  Total time taken: {total_time}")
        # TODO: Log this in database later
