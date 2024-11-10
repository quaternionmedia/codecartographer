from fastapi import APIRouter
from models.source_data import Directory, Folder, File, RepoInfo
from util.exceptions import CodeCartoException, proc_exception
from util.utilities import Log, generate_return

ParserRouter = APIRouter()

# NOTE: CURRENTLY UNUSED


@ParserRouter.post("/directory")
async def parse_source(data: Directory) -> dict:
    return parse(data)


@ParserRouter.post("/folder")
async def parse_folder(folder: Folder) -> dict:
    info = RepoInfo(owner="local", name=folder.name, url="NA")
    data = Directory(info=info, size=folder.size, root=folder)
    return parse(data)


@ParserRouter.post("/file")
async def parse_file(file: File) -> dict:
    info = RepoInfo(owner="local", name=file.name, url="NA")
    folder = Folder(name="raw", files=[file])
    data = Directory(info=info, size=file.size, root=folder)
    return parse(data)


@ParserRouter.post("/raw")
async def parse_raw(raw: str) -> dict:
    file = File(name="raw", size=len(raw), raw=raw)
    info = RepoInfo(owner="local", name="raw", url="NA")
    folder = Folder(name="raw", files=[file])
    data = Directory(info=info, size=len(raw), root=folder)
    return parse(data)


def parse(data: Directory) -> dict:
    from services.parsers.ASTs.python_list_ast import PythonListAST
    from services.parser_service import ParserService
    from services.polygraph_service import graph_to_json_data

    try:
        parser_service = ParserService(visitor=PythonListAST())
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
