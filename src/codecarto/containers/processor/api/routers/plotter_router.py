from fastapi import APIRouter, Request
import networkx as nx
import matplotlib.pyplot as plt
import mpld3
import matplotlib.lines as mlines


PlotterRoute: APIRouter = APIRouter()


@PlotterRoute.get(
    "/plot",
)
async def plot(
    request: Request,
    graph_data: dict = None,
    file: str = None,
    layout: str = "Spring",
    grid: bool = False,
    labels: bool = False,
    ntx: bool = True,
    custom: bool = True,
    palette: dict = None,
    debug: bool = False,
):
    """Plot a graph.

    Parameters:
    -----------
    request : Request
        The request object.
    graph_data : dict
        The graph data. JSON format.
    file : str
        The file to parse and plot.
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
    debug: bool
        Whether to run long process vs short process.

    Returns:
    --------
    dict
        The results of the plot. {index: plot html}
    """

    # TODO: DEBUG - This is a demo file
    try:
        if not debug:
            # from src.plotter.plotter import Plotter
            # from src.polygraph.polygraph import PolyGraph
            from src.parser.parser import Parser

            # Convert the graph data to a networkx graph
            graph: nx.DiGraph = None
            if not graph_data:  # if no graph, run demo
                import os

                py_file_path = file
                if not os.path.exists(py_file_path):
                    return {"error": "File not found."}

                parse: Parser = Parser([py_file_path])
                # poly: PolyGraph = PolyGraph()
                # graph = poly.json_file_to_graph(json_file_path)
                graph = parse.graph

            # plots: list[str] = []
            # plotter: Plotter = Plotter(graph, labels, grid, ntx, custom, palette)
            # plots = plotter.plot(layout_name=layout)  # a list of html strings

            # # get the last plot
            # plot_html: str = plots[-1]

            # return {"plotted": plot_html}
            return simple_plot(graph=graph, title=layout, file_name="processor.py")
        else:
            graph = nx.Graph()
            # add nodes with a type and label attribute
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

            return simple_plot(graph=graph, title=layout, file_name="Demo Graph")
    except Exception as e:
        import traceback

        tb_str = traceback.format_exception(type(e), e, e.__traceback__)
        tb_str = "".join(tb_str)
        return {
            "error": f"Could not generate plot in processor: {e.__str__()}",
            "traceback": f"{tb_str}",
        }


def simple_plot(graph: nx.Graph, title: str = "Sprial", file_name: str = "Fib Demo"):
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
    pos = get_node_positions(graph, f"{title.lower()}_layout")

    # nodes
    nx.drawing.draw_networkx_nodes(
        graph,
        pos,
        nodelist=graph.nodes,
    )

    # labels
    nx.drawing.draw_networkx_labels(
        graph,
        pos,
        labels=nx.get_node_attributes(graph, "label"),
        font_size=12,
        font_color="black",
    )

    # edges
    nx.drawing.draw_networkx_edges(
        graph,
        pos,
        edgelist=graph.edges,
        width=2,
        alpha=0.5,
        edge_color="black",
    )

    # convert to html
    plot_html = mpld3.fig_to_html(
        fig,
        template_type="simple",
        figid="pltfig",
        d3_url=None,
        no_extras=False,
        use_http=False,
        include_libraries=True,
    )
    return {"plotted": plot_html}


def get_node_positions(graph: nx.Graph, layout_name: str) -> dict:
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
    layout_kwargs = {"G": graph}
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
    pos: dict = {}
    try:
        pos = position.get_positions(layout_name, **layout_kwargs)
    except Exception as e:
        # TODO: log an error in the database to be displayed to the user
        raise e

    return pos
