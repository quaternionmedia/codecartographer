from pprint import pprint
from fastapi import APIRouter, Request
import networkx as nx
from networkx import DiGraph

from api.util import generate_return, proc_exception, proc_error
from src.parser.get_graph import get_graph
from src.notebooks.notebook import run_notebook

PlotterRoute: APIRouter = APIRouter()

# DEBUG
import logging

logger = logging.getLogger(__name__)


@PlotterRoute.post("/plot")
async def plot(request: Request, file_data: dict | str = None):
    """Plot a graph from a file.

    Parameters:
    -----------
    request : Request
        The request object.
    file_data : dict | str
        The file name and graph to parse and plot.

    Returns:
    --------
    dict
        The results of the plot. {index: plot html}
    """

    pprint("############## PLOTTER CALLED ##############")

    if isinstance(file_data, str):
        # if string, is raw data, need to parse to graph
        file_data = {"filename": "raw_data", "graph": file_data}
        logger.info(f"File data string: {file_data}")
    else:
        # if dict, is file data, will have name and graph
        logger.info(f"File data dict: {file_data}")

    data = {"filename": file_data["name"], "data": file_data["graph"]}

    pprint("############## CALLING PLOTTER ##############")

    return await plot(
        request=request,
        # file_data=data,
        graph_data=file_data["graph"],
        layout="Spectral",
        gv=True,
    )


@PlotterRoute.get("/plot")
async def plot(
    request: Request,
    url: str = None,
    is_repo: bool = False,
    graph_data: dict = None,
    db_graph: bool = False,
    demo: bool = False,
    demo_file: str = None,
    layout: str = "Spring",
    gv: bool = False,
    nb: bool = False,
    type: str = "d3",
    grid: bool = False,
    labels: bool = False,
    ntx: bool = True,
    custom: bool = True,
    palette: dict = None,
    file_data: dict | str = None,
):
    """Plot a graph.

    Parameters:
    -----------
    request : Request
        The request object.
    url : str
        The url to parse and plot.
    is_repo : bool
        Whether the url is a repo.
    graph_data : dict
        The graph data. JSON format.
    db_graph: bool
        Whether to plot a graph from the database.
    demo: bool
        Whether to plot the demo graph.
    demo_file : str
        The demo_file to parse and plot.
    layout : str
        The name of the layout to plot.
            Used to plot a single layout.
    gv : bool
        Whether to plot the graph using gravis.
    nb : bool
        Whether to plot the graph using a notebook.
    type : str
        The type of plot to use.
            all: all types
            d3: d3.js
            vis: vis.js
            three: gravis
    grid : bool
        Whether to plot all plot layouts in a grid.
    labels : bool
        Whether to plot the graph with labels.
    ntx : bool
        Whether to use the networkx layouts.
    custom : bool
        Whether to use the custom layouts.
    palette: dict
        The palette to use for plotting.
    file_data: dict | str
        The file data to parse and plot.

    Returns:
    --------
    dict
        The results of the plot. {index: plot html}
    """
    from src.plotter.plotter import Plotter

    # TODO: need to implement labels, ntx, custom, palette as options at some point
    # TODO: need to use code in src, not here in api
    # TODO: DEBUG - This is a demo file
    params = request.query_params

    try:
        pprint("0 ############## GET GRAPH ##############")
        results: str = ""
        graph: nx.DiGraph = None
        filename: str = None
        graph, filename = await get_graph(
            demo,
            demo_file,
            db_graph,
            url,
            graph_data,
            is_repo,
            gv,
            file_data,
        )
        # Log the graph data for debugging
        pprint(
            f"graph num nodes: {graph.number_of_nodes()} num edges: {graph.number_of_edges()}"
        )
        pprint("1 ############## RECEIVED GRAPH ##############")

        # Plot the graph
        if not graph:
            return proc_error(
                "plot",
                "No graph found",
                params,
            )
        else:
            pprint("2 ############## PLOTTING STARTING ##############")
            plotter = Plotter(
                graph=graph,
                labels=labels,
                grid=grid,
                ntx_layouts=ntx,
                custom_layouts=custom,
                palette_dict=palette,
            )
            if nb:
                pprint("Running notebook")
                results = await run_notebook(
                    graph_name=filename, graph=graph, title=layout.lower(), type=type
                )
            elif db_graph or is_repo or gv:
                if layout.lower() == "all":
                    pprint("Running cc grid plot on db")
                    results = plotter.grid_plot(graph)
                elif gv:
                    pprint("Running notebook on db")
                    results = await run_notebook(
                        graph_name=filename,
                        graph=graph,
                        title=layout.lower(),
                        type=type,
                    )
                else:
                    # TODO: will probably just be gv_single_plot in the end
                    pprint("Running cc single plot on db")
                    results = plotter.single_plot(
                        graph=graph, title=layout, file_name=filename
                    )
            else:
                if layout.lower() == "all":
                    pprint("Running cc grid plot")
                    results = plotter.grid_plot(graph)
                else:
                    pprint("Running cc single plot")
                    results = plotter.single_plot(
                        graph=graph, title=layout, file_name=filename
                    )

        pprint("3 ############## GENERATING RESPONSE ##############")

        # Return the results
        return generate_return(200, "Proc - Plot generated successfully", results)
    except Exception as e:
        proc_exception(
            "plot",
            "Could not generate plot",
            params,
            e,
        )
    finally:
        pprint("4 ############## PLOTTING FINISHED ##############")


@PlotterRoute.post("/plot_nb")
async def plot_notebook(
    graph_data: dict, filename: str = "", layout: str = "Spring", type: str = "d3"
):
    pprint("Running notebook")
    graph: nx.DiGraph = None
    filename: str = None
    graph, filename = await get_graph(
        False,
        "",
        False,
        "",
        graph_data,
        False,
        True,
        "",
    )

    pprint(
        f"graph num nodes: {graph.number_of_nodes()} num edges: {graph.number_of_edges()}"
    )
    pprint(f"graph nodes: {graph.nodes( data=True)}")
    results = await run_notebook(
        graph_name=filename, graph=graph, title=layout.lower(), type=type
    )
    return generate_return(200, "Proc - Plot generated successfully", results)
