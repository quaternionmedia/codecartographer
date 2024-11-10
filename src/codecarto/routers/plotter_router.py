from fastapi import APIRouter

from models.plot_data import PlotOptions
from models.source_data import Directory, Folder, File
from services.parser_service import ParserService
from services.plotter_service import PlotterService
from util.exceptions import proc_exception
from util.utilities import Log, generate_return

PlotterRouter = APIRouter()


@PlotterRouter.post("/whole_repo")
async def plot_whole_repo(directory: Directory, options: PlotOptions):
    try:
        graph_name = directory.info.name
        graph = await ParserService.parse_directory(directory)
        results = await PlotterService.plot_nx_graph(graph_name, graph, options)
        return generate_return(results=results)
    except Exception as exc:
        proc_exception(
            "plot_whole_repo",
            "Error when plotting GitHub repo",
            {"directory": directory},
            exc,
        )


@PlotterRouter.post("/folder")
async def plot_folder(folder: Folder, options: PlotOptions) -> dict:
    try:
        graph = await ParserService.parse_code(folder)
        results = await PlotterService.plot_nx_graph(folder.name, graph, options)
        return generate_return(results=results)
    except Exception as e:
        return proc_exception(
            "plot_file",
            "Error generating plot",
            {"folder": folder.name},
            e,
        )


@PlotterRouter.post("/file")
async def plot_file(file: File, options: PlotOptions) -> dict:
    try:
        folder = Folder(name="root", size=0, files=[file], folders=[])
        graph = await ParserService.parse_code(folder)
        results = await PlotterService.plot_nx_graph(file.name, graph, options)
        return generate_return(results=results)
    except Exception as e:
        return proc_exception(
            "plot_file",
            "Error generating plot",
            {"file": file.name},
            e,
        )


@PlotterRouter.post("/url")
async def plot_url(url: str, options: PlotOptions) -> dict:
    try:
        graph = await ParserService.parse_raw(url)
        results = await PlotterService.plot_nx_graph(graph.name, graph, options)
        return generate_return(results=results)
    except Exception as e:
        return proc_exception(
            "plot_url",
            "Error generating plot",
            {"url": url},
            e,
        )


# NOTE: UNUSED
@PlotterRouter.post("/json")
async def plot_json(json_graph: dict, options: PlotOptions) -> dict:
    from database.database import DatabaseContext
    from services.polygraph_service import PolygraphService

    try:
        graph = await PolygraphService.json_to_graph(json_graph)
        palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        results = PlotterService.plot_graphbase(graph, palette, options)
        return generate_return(results=results)
    except Exception as e:
        return proc_exception(
            "plot_json",
            "Error generating plot",
            {"json_graph": json_graph},
            e,
        )


# NOTE: UNUSED
@PlotterRouter.post("/db")
async def plot_db(graph_id: str, options: PlotOptions) -> dict:
    from database.database import DatabaseContext

    try:
        graph = await DatabaseContext.fetch_graph_by_id(graph_id)
        palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        results = PlotterService.plot_graphbase(graph, palette, options)
        return generate_return(results=results)
    except Exception as e:
        return proc_exception(
            "plot_db",
            "Error generating plot",
            {"graph_id": graph_id},
            e,
        )
