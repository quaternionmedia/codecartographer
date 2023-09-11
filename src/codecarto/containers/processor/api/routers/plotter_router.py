from fastapi import APIRouter, Request, HTTPException
import networkx as nx
import matplotlib.pyplot as plt
import mpld3
import matplotlib.lines as mlines

from api.util import generate_return, proc_exception

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
        results: dict = {}
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
            if layout.lower() == "all":
                results = grid_plot(graph)
            else:
                results = single_plot(
                    graph=graph, title=layout, file_name="processor.py"
                )
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

            if layout.lower() == "all":
                results = grid_plot(graph)
            else:
                results = single_plot(graph=graph, title=layout, file_name="Demo Graph")
        return generate_return("success", "Proc - Plot generated successfully", results)
    except Exception as e:
        proc_exception(
            "plot",
            "Could not generate plot",
            {"graph_data": graph_data, "file": file, "layout": layout},
            e,
        )


def single_plot(graph: nx.Graph, title: str = "Sprial", file_name: str = "Fib Demo"):
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


def grid_plot(graph: nx.DiGraph = None):
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
    pos: dict = position.get_positions(layout_name, **layout_kwargs)
    return pos
