from pprint import pprint
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, params
import networkx as nx
import matplotlib.pyplot as plt
import mpld3
import matplotlib.lines as mlines


from api.util import generate_return, proc_exception, proc_error

PlotterRoute: APIRouter = APIRouter()

# DEBUG
import logging

logger = logging.getLogger(__name__)


@PlotterRoute.get("/plot") 
async def plot(
    request: Request,
    url: str = None,
    graph_data: dict = None,
    db_graph: bool = False,
    demo: bool = False,
    demo_file: str = None,
    layout: str = "Spring",
    grid: bool = False,
    labels: bool = False,
    ntx: bool = True,
    custom: bool = True,
    palette: dict = None,
):
    """Plot a graph.

    Parameters:
    -----------
    request : Request
        The request object.
    url : str
        The url to parse and plot.
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

    Returns:
    --------
    dict
        The results of the plot. {index: plot html}
    """
    # TODO: need to implement labels, ntx, custom, palette as options at some point
    # TODO: need to use code in src, not here in api
    # TODO: DEBUG - This is a demo file
    params = request.query_params

    try:
        results: str = ""
        filename: str = ""
        graph: nx.DiGraph = None

        # Use demo graph
        if demo: 
            graph:nx.DiGraph = demo_graph()
            filename = "Demo Graph"

        # Get graph from demo_file
        elif demo_file:
            import os
            from src.parser.parser import Parser
 
            if not os.path.exists(demo_file):
                return {"error": "File not found."}
            parser: Parser = Parser(source_files=[demo_file])
            graph = parser.graph
            filename = os.path.basename(demo_file)

        # Get graph from database
        elif db_graph and url: 
            graph: nx.DiGraph = await get_graph_from_database(url)
            filename = url

        # Get graph from json data
        elif graph_data and graph_data != {}:
            # TODO: at some point user may be able to provide json data
            # TODO: will need to verify json data represents valid graph

            # Make sure graph has more than just 'name' key
            if len(graph_data.keys()) == 1:
                return {"error": "Graph data must be a valid json graph."}
            
            graph = nx.DiGraph(graph_data)
            filename = "Graph Data"

        # Get graph from url
        elif url: 
            from src.parser.parser import Parser
            from .polygraph_router import read_raw_data_from_url

            filename = url.split("/")[-1]
            raw_data = await read_raw_data_from_url(url) 
            parser: Parser = Parser(
                source_dict={"raw": raw_data, "filename": filename}
            )
            graph = parser.graph
            db_results = await insert_graph_into_database(filename, graph)

        # Plot the graph
        if layout.lower() == "all":
            results = grid_plot(graph)
        else:
            results = single_plot(graph=graph, title=layout, file_name=filename)

        # Return the results
        return generate_return(200, "Proc - Plot generated successfully", results)
    except Exception as e:
        proc_exception(
            "plot",
            "Could not generate plot",
            params,
            e,
        )


def single_plot(graph: nx.DiGraph, title: str = "Sprial", file_name: str = "Fib Demo") -> str:
    """Plot a graph.

    Parameters:
    -----------
    graph : nx.Graph
        The graph to plot.
    title : str
        The name of the layout to plot.
            Used to plot a single layout.
    file_name : str
        The name of the file to plot.

    Returns:
    --------
    dict
        The results of the plot. {index: plot html}
    """
    # create a simple plot
    fig, ax = plt.subplots(figsize=(15, 10))
    ax.set_title(f"{title} Layout for '{file_name}'")
    ax.set_axis_off()

    # positions
    pos = get_node_positions(graph, f"{title.lower()}_layout")

    # nodes
    nx.drawing.draw_networkx_nodes(
        graph,
        pos,
        nodelist=graph.nodes,
        ax=ax,
    )

    # labels
    nx.drawing.draw_networkx_labels(
        graph,
        pos,
        labels=nx.get_node_attributes(graph, "label"),
        font_size=12,
        font_color="black",
        ax=ax,
    )

    # edges
    nx.drawing.draw_networkx_edges(
        graph,
        pos,
        edgelist=graph.edges,
        width=2,
        alpha=0.5,
        edge_color="black",
        ax=ax,
    )

    # convert to html
    plt.tight_layout()
    plot_html = mpld3.fig_to_html(
        fig,
        template_type="simple",
        figid="pltfig",
        d3_url=None,
        no_extras=False,
        use_http=False,
        include_libraries=True,
    )
    return plot_html


def grid_plot(graph: nx.DiGraph) -> str: 
    import math

    layouts: list[str] = [
        "circular",
        "spiral",
        # "spring",
        "shell",
        # "spectral",
        "sorted_Square",
    ]

    # create a grid plot
    num_layouts = len(layouts)
    grid_size = math.ceil(math.sqrt(num_layouts))

    fig, axs = plt.subplots(
        grid_size,
        grid_size,
        figsize=(grid_size * 15, grid_size * 10),
    )
    fig.set_size_inches(18.5, 9.5)  # TODO: try to size in css

    idx: int = 0
    for layout_name in layouts:
        # ax
        ax = axs[idx // grid_size, idx % grid_size] if grid_size > 1 else axs
        ax.set_title(f"{str(layout_name).capitalize()} Layout")

        # positions
        pos = get_node_positions(graph, f"{layout_name.lower()}_layout")

        # nodes
        nx.drawing.draw_networkx_nodes(
            graph,
            pos,
            nodelist=graph.nodes,
            ax=ax,
        )

        idx += 1

        # labels
        nx.drawing.draw_networkx_labels(
            graph,
            pos,
            labels=nx.get_node_attributes(graph, "label"),
            font_size=12,
            font_color="black",
            ax=ax,
        )

        # edges
        nx.drawing.draw_networkx_edges(
            graph,
            pos,
            edgelist=graph.edges,
            width=2,
            alpha=0.5,
            edge_color="black",
            ax=ax,
        )

    # convert to html
    plt.tight_layout()
    plot_html = mpld3.fig_to_html(
        fig,
        template_type="simple",
        figid="pltfig",
        d3_url=None,
        no_extras=False,
        use_http=False,
        include_libraries=True,
    )
    return plot_html 


def get_node_positions(graph: nx.DiGraph, layout_name: str) -> dict:
    """Gets the node positions for a given layout.

    Parameters:
    -----------
        layout_name (str):
            The name of the layout.

    Returns:
    --------
        positions (dict):
            The positions of nodes for layout.
    """
    from src.plotter.positions import Positions

    position = Positions(True, True)
    seed = -1
    layout_params = position.get_layout_params(layout_name)
    layout_kwargs: dict = {"G": graph}
    for param in layout_params:
        if param == "seed":
            import random

            seed = random.randint(0, 1000)
            layout_kwargs["seed"] = seed
        elif param == "nshells" and layout_name == "shell_layout":
            # Group nodes by parent
            grouped_nodes: dict[str, list] = {}
            for node, data in graph.nodes(data=True):
                parent = data.get("parent", "Unknown")
                if parent not in grouped_nodes:
                    grouped_nodes[parent] = []
                grouped_nodes[parent].append(node)
            # Create the list of lists (shells)
            shells = list(grouped_nodes.values())
            layout_kwargs["nshells"] = shells
        elif param == "root" and layout_name == "cluster_layout":
            # get the node at the very top
            root = None
            for node, data in graph.nodes(data=True):
                if data.get("label", "") == "root":
                    root = node
                    break
            layout_kwargs["root"] = root
        elif param != "G":
            # TODO: Handle other parameters here
            pass

    # Compute layout positions
    pos: dict = position.get_positions(layout_name, **layout_kwargs)
    return pos


def demo_graph() -> nx.DiGraph:
    """Create a demo graph.

    Returns:
    --------
        graph (nx.DiGraph):
            The demo graph.
    """
    graph = nx.DiGraph()
    graph.add_nodes_from(
        [
            (1, {"type": "file", "label": "1"}),
            (2, {"type": "file", "label": "2"}),
            (3, {"type": "file", "label": "3"}),
            (4, {"type": "file", "label": "4"}),
            (5, {"type": "file", "label": "5"}),
            (6, {"type": "file", "label": "6"}),
            (7, {"type": "file", "label": "7"}),
            (8, {"type": "file", "label": "8"}),
        ]
    )
    graph.add_edges_from(
        [
            (1, 2),
            (1, 3),
            (2, 3),
            (2, 4),
            (3, 4),
            (5, 6),
            (5, 7),
            (6, 7),
            (6, 8),
            (7, 8),
        ]
    )
    return graph


################## DATABASE ##################

async def get_graph_from_database(graph_name: str) -> nx.DiGraph: 
    """Get a graph from the database.

    Parameters:
    -----------
        graph_name (str):
            The name of the graph.

    Returns:
    --------
        graph (nx.DiGraph):
            The graph.
    """
    from graphbase.src.main import read_graph

    # Check if graph name provided
    if not graph_name or graph_name == "":
        return proc_error(
            "get_graph_from_database",
            "No graph name provided",
            {"graph_name": graph_name}
        )
    
    # Get the graph from database
    graph_data: nx.DiGraph = await read_graph(graph_name)

    # Check if graph data found
    if not graph_data or graph_data == {}:
        return proc_error(
            "get_graph_from_database",
            "Graph data not found in database",
            {"graph_name": graph_name,"graph_data": graph_data}
        )
    

    # TODO: node_link_data creates an undirected multiDiGraph by default
    #       1.need to decide if we want to use MultiDiGraph or DiGraph in graphBase
    #       2.or if we need to set directed=True by default in GraphBase node_link_data
    #       3.or, we convert to what is needed when we get the graph

    # GraphBase uses node_link_data, which has directed=False by default
    # Set directed=True to get arrows working correctly
    graph_data["directed"] = True
    graph: nx.DiGraph = nx.node_link_graph(graph_data)
    

    # Check if graph found
    if not graph:
        return proc_error(
            "get_graph_from_database",
            "Graph not found in database",
            {"graph_name": graph_name,"graph": graph}
        )
    elif graph.number_of_nodes() == 0:
        return proc_error(
            "get_graph_from_database",
            "Graph has no nodes",
            {"graph_name": graph_name,"graph": graph}
        )
    
    # Return the graph
    return graph


async def insert_graph_into_database(graph_name: str, graph: nx.DiGraph) -> dict:
    """Insert a graph into the database.

    Parameters:
    -----------
        graph_name (str):
            The name of the graph.
        graph (nx.DiGraph):
            The graph.

    Returns:
    --------
        results (dict):
            The results of the insert.
    """
    try:
        from graphbase.src.main import insert_serialized_graph, serialize_graph 
        json_data = serialize_graph(graph_name, graph)
        # pprint(json_data)
        result:dict = await insert_serialized_graph(graph_name, json_data)
        return result
    except HTTPException as e:
        logger.error(e)
        # If graph already exists (409), ignore error
        if e.status_code != 409:
            raise e