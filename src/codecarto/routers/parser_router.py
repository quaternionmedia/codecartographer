from re import L
from fastapi import APIRouter
from models.source_data import File, Source
from util.exceptions import proc_exception, proc_error
from util.utilities import Log, generate_return

ParserRouter = APIRouter()


@ParserRouter.get("/repo")
async def read_github_repo(url: str):
    import time
    from services.github_service import (
        ImportSourceUrlError,
        GithubError,
        get_raw_data_from_github_repo,
        get_github_repo_source,
        get_repo_tree,
    )
    from services.parser_service import ParserService
    from services.ASTs.python_ast import PythonAST
    from models.graph_data import Repo
    from pprint import pprint

    try:
        # get current time to calculate total time taken
        start_time = time.time()

        # Get the repo content and structure
        repo_data = await get_raw_data_from_github_repo(url)
        if not repo_data:
            return proc_error("read_github_repo", "Could not read GitHub repo")

        data = get_github_repo_source(repo_data)

        source_data = Source(
            name=f"{data.owner}/{data.repo}",
            size=data.size,
            source=data.raw,
        )

        # Initialize the parser and parse the entire repository
        parser = ParserService(PythonAST())
        graph = parser.parse_repository(source_data)

        pprint("#################################################################")
        pprint(graph.nodes(data=True))

        return generate_return(200, "Repository parsed successfully", {"graph": graph})
    except Exception as exc:
        proc_exception(
            "read_github_url",
            "Error when reading GitHub URL",
            {"github_url": url},
            exc,
        )
    finally:
        # calculate total time taken
        end_time = time.time()
        total_time = time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))
        # TODO: Log this in database later
        Log.info(f"  Total time taken: {total_time}")


@ParserRouter.get("/url")
async def read_github_url(url: str):
    import time
    from services.github_service import (
        ImportSourceUrlError,
        GithubError,
        get_github_repo_content,
        get_repo_tree,
    )

    try:
        # get current time to calculate total time taken
        start_time = time.time()

        # Extract owner and repo from the URL: https://github.com/owner/repo
        parts = url.split("/")
        if len(parts) < 5 or parts[2] != "github.com":
            return proc_error("read_github_url", "Invalid GitHub URL format")

        owner, repo = parts[3], parts[4]
        url_content = await get_github_repo_content(url, owner, repo, "", True)

        # check if url_content is empty or an Error response
        if not url_content or len(url_content) == 0:
            if "status" in url_content:
                Log.error(f"Error response from GitHub: {url_content}")
            return proc_error("read_github_url", "Empty contents received from GitHub")

        repo_contents = {"package_owner": owner, "package_name": repo, "contents": {}}
        contents: dict = await get_repo_tree(url_content, owner, repo)

        # check if contents is empty or an Error response
        if not contents or len(contents) == 0:
            if "status" in contents:
                Log.error(f"Error response from GitHub: {contents}")
            return proc_error("read_github_url", "Could not parse file content")

        repo_contents["contents"] = contents
        return generate_return(200, "read_github_url - Success", repo_contents)
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
            "read_github_url",
            "Error when reading GitHub URL",
            {"github_url": url},
            exc,
        )
    finally:
        # calculate total time taken
        end_time = time.time()
        total_time = time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))
        # TODO: Log this in database later
        Log.info(f"  Total time taken: {total_time}")


@ParserRouter.post("/source")
async def parse_source(source: Source) -> dict:
    return parse(source)


@ParserRouter.post("/file")
async def parse_file(file: File) -> dict:
    source = Source(name=file.name, size=file.size, source=[file])
    return parse(source)


@ParserRouter.post("/raw")
async def parse_raw(raw: str) -> dict:
    file = File(name="raw", size=len(raw), raw=raw)
    source = Source(name="raw", size=len(raw), source=[file])
    return parse(source)


def parse(source: Source) -> dict:
    from services.ASTs.python_ast import PythonAST
    from services.parser_service import ParserService
    from services.polygraph_service import graph_to_json_data

    try:
        parser_service = ParserService(visitor=PythonAST())
        graph = parser_service.parse(source)
        result = graph_to_json_data(graph)
        return generate_return(200, "parse - Success", {"contents": result})
    except Exception as e:
        return proc_exception(
            "parse",
            "error parsing data",
            {"source": source},
            e,
        )
