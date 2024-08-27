from fastapi import APIRouter
from models.plot_data import DefaultPalette, PlotOptions, FileGraphData
from util.exceptions import proc_exception
from util.utilities import Log, generate_return

PlotterRouter = APIRouter()


@PlotterRouter.post("/raw")
async def plot_from_raw(data: FileGraphData) -> dict:
    # TODO: raw is a placeholder for now
    # really this should parse from parser service
    # save it to the database and return an id
    # and then plot from plotter service using that id
    import networkx as nx
    from notebooks.notebook import run_notebook
    from services.palette_service import apply_styles
    from models.source_data import SourceData, File
    from services.ASTs.python_ast import PythonAST
    from services.parser_service import ParserService

    try:
        # parse the raw data
        file = File(name=data.name, size=data.size, raw=data.raw)
        source = SourceData(name=data.name, size=data.size, source=[file])
        parser = ParserService(PythonAST())
        graph = parser.parse(source)

        # Run the notebook on the graph
        results = await run_notebook(
            graph_name=data.name,
            graph=apply_styles(graph),
            title=data.layout,
            type="d3",
        )
        return generate_return(message="plot_from_file - Success", results=results)
    except Exception as e:
        return proc_exception(
            "plot_from_file",
            "Error generating plot",
            {"file": data.name},
            e,
        )


@PlotterRouter.post("/url")
async def plot_from_url(url: str, options: PlotOptions) -> dict:
    # TODO: Url is a placeholder for now
    # really this should parse from parser service
    # save it to the database and return an id
    # and then plot from plotter service using that id
    from database.database import DatabaseContext
    from models.source_data import File, SourceData
    from models.graph_data import GraphBase
    from services.ASTs.python_ast import PythonAST
    from services.parser_service import ParserService
    from services.plotter_service import PlotterService
    from services.github_service import get_raw_data_from_github_url
    from notebooks.notebook import run_notebook
    from services.palette_service import apply_styles

    try:
        raw = await get_raw_data_from_github_url(url)
        file = File(name="raw", size=0, raw=raw)
        source = SourceData(name=file.name, size=file.size, source=[file])
        parser = ParserService(PythonAST())
        graph = parser.parse(source)

        # TODO: TEMPORARY Run the notebook on the graph
        results = await run_notebook(
            graph_name=file.name,
            graph=apply_styles(graph),
            title=options.layout,
            type=options.type,
        )
        # graphbase = GraphBase(graph)
        # palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        # results = PlotterService.plot_graph(
        #     graph=graphbase, palette=palette, options=options
        # )
        return generate_return(message="plot_from_url - Success", results=results)
    except Exception as e:
        return proc_exception(
            "plot_from_url",
            "Error generating plot",
            {"url": url},
            e,
        )


@PlotterRouter.post("/json")
async def plot_from_json(json_graph: dict, options: PlotOptions) -> dict:
    from services.polygraph_service import PolygraphService
    from database.database import DatabaseContext
    from services.plotter_service import PlotterService

    try:
        graph = await PolygraphService.json_to_graph(json_graph)
        palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        results = PlotterService.plot_graph(
            graph=graph, palette=palette, options=options
        )
        return generate_return(message="plot_from_json - Success", results=results)
    except Exception as e:
        return proc_exception(
            "plot_from_json",
            "Error generating plot",
            {"json_graph": json_graph},
            e,
        )


@PlotterRouter.post("/db")
async def plot_from_db(graph_id: str, options: PlotOptions) -> dict:
    from database.database import DatabaseContext
    from services.plotter_service import PlotterService

    try:
        graph = await DatabaseContext.fetch_graph_by_id(graph_id)
        palette = await DatabaseContext.fetch_palette_by_id(options.palette_id)
        results = PlotterService.plot_graph(
            graph=graph, palette=palette, options=options
        )
        return generate_return(message="plot_from_db - Success", results=results)
    except Exception as e:
        return proc_exception(
            "plot_from_db",
            "Error generating plot",
            {"graph_id": graph_id},
            e,
        )


@PlotterRouter.post("/demo")
async def plot_from_demo(options: PlotOptions) -> dict:
    from models.demo_data import DemoGraph
    from services.plotter_service import PlotterService

    try:
        graph = DemoGraph
        palette = DefaultPalette
        results = PlotterService.plot_graph(
            graph=graph, palette=palette, options=options
        )
        return generate_return(message="plot_from_demo - Success", results=results)
    except Exception as e:
        return proc_exception(
            "plot_from_db",
            "Error generating plot",
            {"": ""},
            e,
        )
