import time
from fastapi import APIRouter

from models.plot_data import PlotOptions
from models.source_data import File, Folder, Directory, RepoInfo
from util.exceptions import proc_error, proc_exception
from util.utilities import Log, generate_return

PlotterRouter = APIRouter()


@PlotterRouter.post("/whole_repo")
async def plot_whole_repo(directory: Directory, options: PlotOptions):
    from services.parsers.directory_parser import DirectoryParser

    try:
        Log.info(f"PlotterRouter.plot_whole_repo(")
        Log.info(f"directory.size: {directory.size}, options: {options})")
        start_time = time.time()

        dir_parser = DirectoryParser()
        graph = dir_parser.parse(directory)

        return await plot(directory.info.name, graph, options)
    except Exception as exc:
        proc_exception(
            "plot_whole_repo",
            "Error when plotting GitHub repo",
            {"directory": directory},
            exc,
        )
    finally:
        end_time = time.time()
        total_time = time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))
        Log.info(f"Total time to parse whole repo: {total_time}")


@PlotterRouter.post("/file")
async def plot_raw(file: File, options: PlotOptions) -> dict:
    try:
        Log.info(f"PlotterRouter.plot_raw(file: {file}, options: {options})")

        file = File(name=file.name, size=file.size, raw=file.raw)

        return await get_plot(file, options)
    except Exception as e:
        return proc_exception(
            "plot_file",
            "Error generating plot",
            {"file": file.name},
            e,
        )


@PlotterRouter.post("/url")
async def plot_url(url: str, options: PlotOptions) -> dict:
    from services.github_service import get_raw_from_url

    try:
        Log.info(f"PlotterRouter.plot_url(url: {url})")

        filename = url.split("/")[-1]
        raw = await get_raw_from_url(url)
        file = File(name=filename, size=0, raw=raw)

        return await get_plot(file, options)
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
    from services.plotter_service import PlotterService
    from services.polygraph_service import PolygraphService

    try:
        graph = await PolygraphService.json_to_graph(json_graph)
        palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        results = PlotterService.plot_graph(
            graph=graph, palette=palette, options=options
        )
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
    from services.plotter_service import PlotterService

    try:
        graph = await DatabaseContext.fetch_graph_by_id(graph_id)
        palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        results = PlotterService.plot_graph(
            graph=graph, palette=palette, options=options
        )
        return generate_return(results=results)
    except Exception as e:
        return proc_exception(
            "plot_db",
            "Error generating plot",
            {"graph_id": graph_id},
            e,
        )


async def get_plot(file: File, options: PlotOptions) -> dict:
    # TODO: placeholder for now
    # really this should parse from parser service
    # save it to the database and return an id
    # and then plot from plotter service using that id
    from services.parsers.ASTs.python_custom_ast import PythonCustomAST

    info = RepoInfo(owner="local", name=file.name, url="NA")
    folder = Folder(name="root", size=0, files=[file], folders=[])
    source = Directory(info=info, size=file.size, root=folder)

    parser2 = PythonCustomAST()
    graph = parser2.parse(folder)

    # graphbase = GraphBase(graph)
    # palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
    # results = PlotterService.plot_graph(
    #     graph=graphbase, palette=palette, options=options
    # )

    return await plot(file.name, graph, options)


async def plot(graph_name: str, graph, options: PlotOptions) -> dict:
    from notebooks.notebook import run_notebook
    from services.palette_service import apply_styles

    # TODO: TEMPORARY Run the notebook on the graph
    # Run the notebook on the graph
    if graph:
        Log.pprint("######################  GRAPH  ######################")
        Log.pprint(graph.nodes(data=True))

        results = await run_notebook(
            graph_name=graph_name,
            graph=apply_styles(graph),
            title=options.layout,
            type=options.type,
        )
        return generate_return(results=results)

    # Return error if graph is empty
    return proc_error("plot", "Could not parse source code")
