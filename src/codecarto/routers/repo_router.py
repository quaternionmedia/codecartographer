from fastapi import APIRouter
from services.github_service import get_raw_from_repo
from util.exceptions import CodeCartoException, proc_exception
from util.utilities import Log, generate_return

RepoReaderRouter = APIRouter()


@RepoReaderRouter.get("/tree")
async def get_repo_directory_tree(url: str) -> dict:
    # Get the GitHub repo directory tree
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
