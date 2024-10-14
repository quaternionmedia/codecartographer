from fastapi import APIRouter
from models.source_data import Directory, File, RepoInfo
from util.exceptions import CodeCartoException, proc_exception
from util.utilities import Log, generate_return

ParserRouter = APIRouter()


@ParserRouter.get("/repo")
async def read_github_repo(url: str) -> dict:
    from services.github_service import get_raw_from_repo
    from services.parser_service import ParserService
    from services.ASTs.python_ast import PythonAST

    try:
        # Initialize the parser and parse the entire repository
        data = await get_raw_from_repo(url)
        parser = ParserService(PythonAST())
        graph = parser.parse(data)
        return generate_return(200, "Repository parsed successfully", {"graph": graph})
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc)
    except Exception as exc:
        return proc_exception(
            "read_github_repo",
            "Error when reading GitHub URL",
            {"github_url": url},
            exc,
        )


@ParserRouter.get("/url")
async def read_github_url(url: str) -> dict:
    from services.github_service import get_raw_from_repo

    try:
        # Get the raw data from the GitHub URL
        Log.info(f"Reading GitHub URL: {url}")
        data = await get_raw_from_repo(url)
        return generate_return(200, "read_github_url - Success", data.dict())
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc)
    except Exception as exc:
        return proc_exception(
            "read_github_url",
            "Error when reading GitHub URL",
            {"github_url": url},
            exc,
        )


@ParserRouter.post("/raw")
async def parse_raw(raw: str) -> dict:
    file = File(name="raw", size=len(raw), raw=raw)
    info = RepoInfo(owner="local", name="raw", url="NA")
    data = Directory(info=info, size=len(raw), root={"files": file})
    return parse(data)


@ParserRouter.post("/file")
async def parse_file(file: File) -> dict:
    info = RepoInfo(owner="local", name=file.name, url="NA")
    data = Directory(info=info, size=file.size, root={"files": file})
    return parse(data)


@ParserRouter.post("/directory")
async def parse_source(data: Directory) -> dict:
    return parse(data)


def parse(data: Directory) -> dict:
    from services.ASTs.python_ast import PythonAST
    from services.parser_service import ParserService
    from services.polygraph_service import graph_to_json_data

    try:
        parser_service = ParserService(visitor=PythonAST())
        graph = parser_service.parse(data)
        result = graph_to_json_data(graph)

        return generate_return(200, "parse - Success", {"contents": result})
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc)
    except Exception as exc:
        return proc_exception(
            "parse",
            "Error when parsing data",
            {"data": data.dict()},
            exc,
        )
