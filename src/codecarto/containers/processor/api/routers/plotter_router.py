from pprint import pprint
from fastapi import APIRouter, HTTPException, Request
import networkx as nx
import matplotlib.pyplot as plt
import mpld3


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
    gv: bool = False,
    nb: bool = False,
    type: str = "d3",
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
        graph, filename = await get_graph(demo, demo_file, db_graph, url, graph_data)

        # Plot the graph
        if not graph:
            return proc_error(
                "plot",
                "No graph found",
                params,
            )
        else:
            if nb: 
                pprint("Running notebook")
                results = await run_notebook(graph_name=filename,
                                             graph=graph,
                                             title=layout.lower(), 
                                             type=type)
            elif db_graph:
                if layout.lower() == "all":
                    pprint("Running cc grid plot on db")
                    results = grid_plot(graph)
                elif gv:
                    pprint("Running notebook on db")
                    results = await run_notebook(graph_name=filename,
                                                 graph=graph,
                                                 title=layout.lower(), 
                                                 type=type)
                else:
                    # TODO: will probably just be gv_single_plot in the end
                    pprint("Running cc single plot on db")
                    results = single_plot(graph=graph, title=layout, file_name=filename)
            else:
                if layout.lower() == "all":
                    pprint("Running cc grid plot")
                    results = grid_plot(graph)
                else:
                    pprint("Running cc single plot")
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


################## PLOT ##################
def grav_single_plot(graph: nx.DiGraph, title: str = "Sprial", file_name: str = "Fib Demo") -> str:
    """Plot a graph.

    Parameters:
    -----------
    graph : nx.DiGraph
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
    import gravis as gv

    # get the positions
    pos = get_node_positions(graph, f"{title.lower()}_layout")

    # add the positions to the graph
    for name, (x,y) in pos.items():
        node = graph.nodes[name]
        node['x'] = float(x)*100
        node['y'] = float(y)*100

    # create the figure
    fig = gv.d3(graph, zoom_factor=2, graph_height=550,
                show_menu = True, show_details_toggle_button=False,
                node_label_data_source='label', edge_label_data_source='label',
                node_hover_neighborhood=True)
    
    # convert to html
    results = fig.to_html_partial()
    return results
 

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
        "spring",
        "shell",
        "spectral",
        # "sorted_Square",
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


################## GRAPHS ##################
async def get_graph(demo:bool, file_path:str, db_graph:bool, url:str, graph_data:dict) -> tuple:
    """Get a graph.

    Parameters:
    -----------
        demo (bool):
            Whether to use the demo graph.
        file_path (str):
            The path to the file.
        db_graph (bool):
            Whether to use a graph from the database.
        url (str):
            The url to the file.
        graph_data (dict):
            The graph data.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    graph: nx.DiGraph = None
    filename: str = ""

    # Use demo graph
    if demo:
        pprint("demo")
        graph, filename = demo_graph()

    # Get graph from demo_file
    elif file_path and file_path != "":
        pprint("file_path")
        graph, filename = file_graph(file_path)

    # Get graph from database
    elif db_graph and url:
        pprint("db_graph")
        graph_data, filename = await get_gJGF_from_database(url)
        graph_data["name"] = filename
        #graph_data = format_gJGF(graph_data)
        graph, filename = gJGF_to_nxGraph(url, graph_data)

    # Get graph from url
    elif url:
        pprint("url")
        graph, filename = await url_graph(url)

    # Get graph from json data
    elif graph_data and graph_data != {}:
        pprint("graph_data")
        # TODO: at some point user may be able to provide json data
        # TODO: will need to verify json data represents valid graph
        graph, filename = given_data_graph(graph_data)

    return graph, filename


def demo_graph() -> tuple:
    """Create a demo graph.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
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
    return graph, "Fib Demo"


def file_graph(file_path) -> tuple:
    """Create a graph from a file path.

    Parameters:
    -----------
        file_path (str):
            The path to the file.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    import os
    from src.parser.parser import Parser

    if not os.path.exists(file_path):
        return {"error": "File not found."}
    parser: Parser = Parser(source_files=[file_path])
    filename = os.path.basename(file_path)

    return parser.graph, filename


def given_data_graph(data: dict) -> tuple:
    """Create a graph from given data.

    Parameters:
    -----------
        data (dict):
            The data to create the graph from.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    # Make sure graph has more than just 'name' key
    if len(data.keys()) == 1:
        return {"error": "Graph data must be a valid json graph."}
    
    # Create the graph
    graph = nx.DiGraph(data)

    # Return the graph and filename
    return graph, "Graph Data"


async def url_graph(url: str) -> tuple:
    """Create a graph from a url.

    Parameters:
    -----------
        url (str):
            The url to the file.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    from src.parser.parser import Parser
    from .polygraph_router import read_raw_data_from_url

    filename = url.split("/")[-1]
    raw_data = await read_raw_data_from_url(url) 
    parser: Parser = Parser(
        source_dict={"raw": raw_data, "filename": filename}
    )
    graph = parser.graph
    
    #TODO: need to have the 'insert into database' code in somewhere else
    # Not when the user click Single Plot on Plotter page.
    db_results = await insert_graph_into_database(filename, graph)

    return graph, filename


################## DATABASE ##################
async def get_gJGF_from_database(graph_name: str) -> tuple: 
    """Get a gJGF from the database.

    Parameters:
    -----------
        graph_name (str):
            The name of the graph.

    Returns:
    --------
        tuple (str, str):
            The gJGF data and the filename.
    """
    from graphbase.src.main import read_graph

    # Check if graph name provided
    if not graph_name or graph_name == "":
        return proc_error(
            "get_gJGF_from_database",
            "No graph name provided",
            {"graph_name": graph_name}
        )
    
    # Get the graph from database
    graph_data: dict = await read_graph(graph_name)

    # Check if graph data found
    if not graph_data or graph_data == {}:
        return proc_error(
            "get_gJGF_from_database",
            "Graph data not found in database",
            {"graph_name": graph_name, "graph_data": graph_data}
        )
    
    # Return the graph data and filename
    return graph_data, graph_name


def gJGF_to_nxGraph(graph_name:str, graph_data: dict) -> tuple:
    """Convert a graph in gJGF format to a networkx graph.

    Parameters:
    -----------
        graph_name (str):
            The name of the graph.
        graph_data (dict):
            The graph in gJGF format.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """ 
    # Convert the graph to a networkx graph
    #graph = nx.node_link_graph(format_gJGF(graph_data), directed=True)
    graph = nx.node_link_graph(graph_data, directed=True)

    # Check if graph found
    if not graph:
        return proc_error(
            "gJGF_to_nxGraph",
            "Graph not provided",
            {"graph_name": graph_name,"graph": graph}
        )
    elif graph.number_of_nodes() == 0:
        return proc_error(
            "gJGF_to_nxGraph",
            "Graph has no nodes",
            {"graph_name": graph_name,"graph": graph}
        )
     
    # Return the graph
    return graph, graph_name


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
        from graphbase.src.main import insert_graph

        # Check if graph provided
        if not graph:
            return proc_error(
                "insert_graph_into_database",
                "No graph provided",
                {"graph_name": graph_name,"graph": graph}
            )
        
        # Convert graph to json
        nx_graph_json = nx.node_link_data(graph)

        # Insert the graph into the database
        result:dict = await insert_graph(graph_name, nx_graph_json)

        return result
    except HTTPException as e:
        logger.error(e)
        # If graph already exists (409), ignore error
        if e.status_code != 409:
            raise e


################## NOTEBOOK ##################
async def run_notebook(
        graph_name: str,
        graph: nx.DiGraph,
        title: str = "Sprial", 
        type:str = "d3") -> list:
    """Extract the outputs from a notebook.

    Parameters:
    -----------
    graph_name : str
        The name of the graph to read from database.
    graph : nx.DiGraph
        The graph to plot.
    title : str
        The name of the layout to plot.
    type : str
        The type of graph to plot in the notebook.

    Returns:
    --------
    list
        The list of outputs.
    """
    import nbformat
    import gravis as gv
    from nbconvert.preprocessors import ExecutePreprocessor
    
    # Check if graph provided
    if not graph:
        return proc_error(
            "run_notebook",
            "No graph provided",
            {"graph_name": graph_name,"graph": graph}
        )

    # Set and scale up the postiions
    pos = get_node_positions(graph, f"{title.lower()}_layout")
    for id, (x,y) in pos.items():
        node = graph.nodes[id]
        node['x'] = float(x)*100
        node['y'] = float(y)*100 

    # Convert the graph to gJGF for the notebook
    gJFG = gv.convert.any_to_gjgf(graph)

    # Read in the notebook
    nb_path = f"src/notebooks/gravis_{type}.ipynb"
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

        # Create a new code cell with the graph_data (g)
        param_cell = nbformat.v4.new_code_cell(f"g = {gJFG}")
        
        # Insert the cell at the beginning of the notebook
        nb.cells.insert(0, param_cell)

    # Execute the notebook
    ep = ExecutePreprocessor(timeout=600)
    ep.preprocess(nb, {'metadata': {'path': 'src/notebooks/'}})

    # Extract the outputs
    outputs = []
    for cell in nb.cells:
        if cell.cell_type == 'code':
            for output in cell.outputs:
                if output.output_type == 'execute_result':
                    outputs.append(output.data)

    # Return the outputs
    return outputs