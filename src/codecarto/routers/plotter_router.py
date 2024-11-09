import time
from fastapi import APIRouter
from pprint import pprint
from database.database import DatabaseContext

# from models.demo_data import DemoGraph
from models.plot_data import DefaultPalette, PlotOptions
from models.source_data import File, Folder, Directory, RepoInfo
from notebooks.notebook import run_notebook
from services.ASTs.python_ast import PythonAST
from services.github_service import get_raw_from_repo, get_raw_from_url
from services.palette_service import apply_styles
from services.parser_service import ParserService
from services.plotter_service import PlotterService
from services.polygraph_service import PolygraphService
from util.exceptions import proc_error, proc_exception
from util.utilities import Log, generate_return


PlotterRouter = APIRouter()


@PlotterRouter.post("/repo")
async def plot_whole_repo(url: str, options: PlotOptions):

    Log.info(f"plotter_router.plot_whole_repo(url: {url}, options: {options})")
    try:
        # get current time to calculate total time taken
        start_time = time.time()

        # Get the repo content and structure
        repo = await get_raw_from_repo(url)
        if not repo:
            return proc_error("read_github_repo", "Could not read GitHub repo")

        # Initialize the parser and parse the entire repository
        from services.ASTs.python_ast_again import PythonAST as PythonAST2

        parser = ParserService(PythonAST())
        parser2 = PythonAST2()
        graph = parser2.parse(repo.root)

        Log.pprint("######################  GRAPH  ######################")
        Log.pprint(graph.nodes(data=True))

        results = await run_notebook(
            graph_name=repo.info.name,
            graph=apply_styles(graph),
            title=options.layout,
            type="d3",
        )

        return generate_return(message="plot_whole_repo - Success", results=results)
    except Exception as exc:
        proc_exception(
            "plot_whole_repo",
            "Error when plotting GitHub repo",
            {"url": url},
            exc,
        )
    finally:
        # calculate total time taken
        end_time = time.time()
        total_time = time.strftime("%H:%M:%S", time.gmtime(end_time - start_time))
        # TODO: Log this in database later
        Log.info(f"  Total time taken: {total_time}")


@PlotterRouter.post("/file")
async def plot_raw(file: File, options: PlotOptions) -> dict:
    # TODO: raw is a placeholder for now
    # really this should parse from parser service
    # save it to the database and return an id
    # and then plot from plotter service using that id

    Log.info(f"plotter_router.plot_raw(file: {file}, options: {options})")
    try:
        # parse the raw data
        file = File(name=file.name, size=file.size, raw=file.raw)
        info = RepoInfo(owner="local", name=file.name, url="NA")
        folder = Folder(name="root", size=0, files=[file], folders=[])
        source = Directory(info=info, size=file.size, root=folder)
        parser = ParserService(PythonAST())
        graph = parser.parse(source)

        # Run the notebook on the graph
        results = await run_notebook(
            graph_name=file.name,
            graph=apply_styles(graph),
            title=options.layout,
            type="d3",
        )
        return generate_return(message="plot_file - Success", results=results)
    except Exception as e:
        return proc_exception(
            "plot_file",
            "Error generating plot",
            {"file": file.name},
            e,
        )


@PlotterRouter.post("/url")
async def plot_url(url: str, options: PlotOptions) -> dict:
    # really this should parse from parser service
    # save it to the database and return an id
    # and then plot from plotter service using that id

    Log.info(f"plotter_router.plot_url(url: {url})")
    try:
        raw = await get_raw_from_url(url)
        filename = url.split("/")[-1]
        file = File(name=filename, size=0, raw=raw)
        info = RepoInfo(owner="local", name=file.name, url="NA")
        folder = Folder(name="root", size=0, files=[file], folders=[])
        source = Directory(info=info, size=file.size, root=folder)
        from services.ASTs.python_ast_again import PythonAST as PythonAST2

        parser = ParserService(PythonAST())
        parser2 = PythonAST2()
        graph = parser2.parse(folder)

        Log.pprint("######################  GRAPH  ######################")
        datass = graph.nodes(data=True)
        pprint(datass)

        # TODO: TEMPORARY Run the notebook on the graph
        if graph:
            results = await run_notebook(
                graph_name=file.name,
                graph=apply_styles(graph),
                title=options.layout,
                type=options.type,
            )
            return generate_return(message="plot_url - Success", results=results)

        # graphbase = GraphBase(graph)
        # palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        # results = PlotterService.plot_graph(
        #     graph=graphbase, palette=palette, options=options
        # )

        return proc_error("plot_url", "Could not parse URL")
    except Exception as e:
        return proc_exception(
            "plot_url",
            "Error generating plot",
            {"url": url},
            e,
        )


@PlotterRouter.post("/json")
async def plot_json(json_graph: dict, options: PlotOptions) -> dict:

    try:
        graph = await PolygraphService.json_to_graph(json_graph)
        palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        results = PlotterService.plot_graph(
            graph=graph, palette=palette, options=options
        )
        return generate_return(message="plot_json - Success", results=results)
    except Exception as e:
        return proc_exception(
            "plot_json",
            "Error generating plot",
            {"json_graph": json_graph},
            e,
        )


@PlotterRouter.post("/db")
async def plot_db(graph_id: str, options: PlotOptions) -> dict:

    try:
        graph = await DatabaseContext.fetch_graph_by_id(graph_id)
        palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        results = PlotterService.plot_graph(
            graph=graph, palette=palette, options=options
        )
        return generate_return(message="plot_db - Success", results=results)
    except Exception as e:
        return proc_exception(
            "plot_db",
            "Error generating plot",
            {"graph_id": graph_id},
            e,
        )


# @PlotterRouter.post("/demo")
# async def plot_demo(options: PlotOptions) -> dict:

#     try:
#         graph = DemoGraph
#         palette = DefaultPalette
#         results = PlotterService.plot_graph(
#             graph=graph, palette=palette, options=options
#         )
#         return generate_return(message="plot_demo - Success", results=results)
#     except Exception as e:
#         return proc_exception(
#             "plot_db",
#             "Error generating plot",
#             {"": ""},
#             e,
#         )
