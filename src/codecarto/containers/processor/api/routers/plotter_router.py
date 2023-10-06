from fastapi import APIRouter, Request
import networkx as nx
import matplotlib.pyplot as plt
import mpld3
import matplotlib.lines as mlines

from api.util import generate_return, proc_exception, proc_error

import logging

logger = logging.getLogger(__name__)

PlotterRoute: APIRouter = APIRouter()


@PlotterRoute.get(
    "/plot",
)
async def plot(
    request: Request,
    graph_data: dict = None,
    file: str = None,
    url: str = None,
    layout: str = "Spring",
    grid: bool = False,
    labels: bool = False,
    ntx: bool = True,
    custom: bool = True,
    palette: dict = None,
    parse_type: str = "multiple",
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
    url : str
        The url to parse and plot.
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
    parse_type: str
        Plotting option for multiple nodes of same data type or single node.
    debug: bool
        Whether to run long process vs short process.

    Returns:
    --------
    dict
        The results of the plot. {index: plot html}
    """

    # TODO: DEBUG - This is a placeholder for the actual plotter
    try:
        results: dict = {}
        filename: str = ""
        if debug:  # using created demo graph
            graph = demo_graph()
        else:
            # Convert the graph data to a networkx graph
            graph: nx.DiGraph = None
            if not graph_data:  # if no graph, run demo
                if url:  # using a url from github
                    from .polygraph_router import read_raw_data_from_url

                    filename = url.split("/")[-1]
                    raw_data: str = await read_raw_data_from_url(url)

                    # get the file extension
                    file_ext = filename.split(".")[-1]
                    logger.info(f"\n\nfile_ext: {file_ext}")
                    logger.info(f"\n\nparse_type: {parse_type}")
                    logger.info(f"\n\nraw_data: {raw_data}")

                    if file_ext == "json":
                        # string to dict
                        import json

                        raw_data_dict = json.loads(raw_data)

                        if isinstance(raw_data_dict, list):
                            raw_data_dict = {"root": raw_data_dict}
                        logger.info(f"\n\nraw_data_dict: {raw_data_dict}")
                        if not raw_data_dict:
                            logger.error(f"\n\nparse_type: {parse_type}")
                            return proc_error(
                                "plot",
                                "Could not load raw data",
                                "JSON data is empty",
                            )

                        if parse_type == "working":
                            graph = json_working_plot(raw_data_dict)
                        elif parse_type == "single_1":
                            graph = json_parse_single_node_1(raw_data_dict)
                        elif parse_type == "single_2":
                            graph = json_parse_single_node_2(raw_data_dict)
                        elif parse_type == "multiple":
                            graph = json_parse_mutiple_node(raw_data_dict)

                        logger.info(f"\n\ngraph: {graph}")
                        if not graph:
                            logger.error(f"\n\nparse_type: {parse_type}")
                            return proc_error(
                                "plot",
                                "Could not parse json data",
                                "JSON data is empty",
                            )

                        results = json_graph_to_html(graph, layout.lower(), parse_type)
                        return generate_return(
                            200, "Proc - Plot generated successfully", results
                        )
                        # else:
                        # from src.parser.parsers.json_parser import JsonParser

                        # parser: JsonParser = JsonParser(
                        #     source=raw_data, parse_type=parse_type
                        # )
                        # graph = parser.graph
                    elif file_ext == "py":
                        from src.parser.parsers.py_parser import PyParser

                        parser: PyParser = PyParser(
                            source_dict={"raw": raw_data, "filename": filename}
                        )
                        graph = parser.graph
                elif file:  # using one of the demo files
                    import os
                    from src.parser.parser import Parser

                    py_file_path = file
                    if not os.path.exists(py_file_path):
                        return {"error": "File not found."}
                    filename = os.path.basename(py_file_path)
                    parser: Parser = Parser(source_files=[py_file_path])
                    graph = parser.graph
            else:  # passed from front end
                filename = "Demo Graph"
                graph = nx.DiGraph(graph_data)

        # Check if we need to plot a grid of all layouts or a single layout
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
            {
                "graph_data": graph_data,
                "file": file,
                "layout": layout,
            },
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


def demo_graph() -> nx.Graph:
    """Returns a fib demo graph.

    Returns:
    --------
        nx.Graph: The demo graph.
    """
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
    return graph


def json_graph_to_html(graph, layout, parse_type):
    import matplotlib.pyplot as plt

    # Draw the graph
    fig, ax = plt.subplots(figsize=(20, 20))
    ax.set_axis_off()

    pos = None
    if layout == "spiral":
        pos = nx.spiral_layout(graph)
    elif layout == "spring":
        pos = nx.spring_layout(graph)
    elif layout == "shell":
        pos = nx.shell_layout(graph)
    elif layout == "spectral":
        pos = nx.spectral_layout(graph)
    elif layout == "circular":
        pos = nx.circular_layout(graph)
    elif layout == "kamada":
        pos = nx.kamada_kawai_layout(graph)
    elif layout == "random":
        pos = nx.random_layout(graph)

    if not pos:
        raise Exception("Invalid layout")

    if parse_type == "multiple":

        def extract_node_labels(graph: nx.DiGraph) -> dict[int, str]:
            return {
                node: data["data"].label if "data" in data and data["data"] else ""
                for node, data in graph.nodes(data=True)
            }

        node_labels = extract_node_labels(graph)
        nx.draw(graph, pos, labels=node_labels, with_labels=True, font_weight="bold")
    else:
        nx.draw(graph, pos, with_labels=True, font_weight="bold", ax=ax)
    edge_labels = nx.get_edge_attributes(graph, "weight")
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, ax=ax)

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
    return plot_html


def json_working_plot(json_data):
    def add_edges(graph, parent, obj):
        if isinstance(obj, list):
            for index, item in enumerate(obj):
                item_key = f"{parent}_{index}"
                if isinstance(item, dict):
                    graph.add_edge(parent, item_key)  # edge between parent and dict
                    add_edges(graph, item_key, item)
                elif isinstance(value, list):
                    graph.add_edge(parent, key)  # edge between parent and list
                    for index, item in enumerate(value):
                        item_key = f"{key}_{index}"
                        # check if item_key is already in the graph
                        if graph.nodes.get(item_key) is not None:
                            item_key = f"{key}_{index}_{index}"
                        if isinstance(item, dict):
                            graph.add_edge(
                                key, item_key
                            )  # edge between list and dict in list
                            add_edges(
                                graph, item_key, item
                            )  # edge between dict in list and its children
                        else:
                            graph.add_edge(
                                key, item_key
                            )  # edge between list and item in list
                else:
                    graph.add_edge(
                        parent, key, weight=value
                    )  # edge between parent and child
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, dict):
                    graph.add_edge(parent, key)  # edge between parent and dict
                    add_edges(graph, key, value)
                elif isinstance(value, list):
                    graph.add_edge(parent, key)  # edge between parent and list
                    for index, item in enumerate(value):
                        item_key = f"{key}_{index}"
                        # check if item_key is already in the graph
                        if graph.nodes.get(item_key) is not None:
                            item_key = f"{key}_{index}_{index}"
                        if isinstance(item, dict):
                            graph.add_edge(
                                key, item_key
                            )  # edge between list and dict in list
                            add_edges(
                                graph, item_key, item
                            )  # edge between dict in list and its children
                        else:
                            graph.add_edge(
                                key, item_key
                            )  # edge between list and item in list
            else:
                graph.add_edge(
                    parent, key, weight=value
                )  # edge between parent and child

    def json_to_graph(json_obj):
        graph = nx.DiGraph()
        add_edges(graph, "ROOT", json_obj)
        return graph

    # Convert JSON to graph
    return json_to_graph(json_data)


def json_parse_single_node_1(json_data):
    def add_edges(graph, parent, obj):
        logger.info(f"\n\njson_data to graph 3: {obj}")
        logger.info(f"\n\njson_data to graph type: {type(obj)}")
        logger.info(f"\n\ngraph to fill 2: {graph}")
        for key, value in obj.items():
            if isinstance(value, dict):
                graph.add_edge(parent, key, weight=1)
                add_edges(graph, key, value)
            elif isinstance(value, list):
                graph.add_edge(parent, key, weight=1)
                for index, item in enumerate(value):
                    item_key = f"{key}_{index}"
                    if isinstance(item, dict):
                        graph.add_edge(key, item_key, weight=1)
                        add_edges(graph, item_key, item)
                    else:
                        graph.add_edge(key, item_key, weight=1)
            else:
                graph.add_edge(
                    parent, key, weight=value if isinstance(value, (int, float)) else 1
                )

    def json_to_graph(json_obj):
        graph = nx.DiGraph()
        logger.info(f"\n\njson_data to graph 2: {json_obj}")
        logger.info(f"\n\ngraph to fill: {graph}")
        add_edges(graph, "root", json_obj)
        return graph

    # Convert JSON to graph
    logger.info(f"\n\njson_data to graph: {json_data}")
    return json_to_graph(json_data)


def json_parse_single_node_2(json_data):
    def add_edges(graph, parent, obj):
        if isinstance(obj, list):
            for index, item in enumerate(obj):
                item_key = f"{parent}_{index}"
                if isinstance(item, dict):
                    graph.add_edge(parent, item_key)  # edge between parent and dict
                    add_edges(graph, item_key, item)
                elif isinstance(value, list):
                    graph.add_edge(parent, key)  # edge between parent and list
                    for index, item in enumerate(value):
                        item_key = f"{key}_{index}"
                        # check if item_key is already in the graph
                        if graph.nodes.get(item_key) is not None:
                            item_key = f"{key}_{index}_{index}"
                        if isinstance(item, dict):
                            graph.add_edge(
                                key, item_key
                            )  # edge between list and dict in list
                            add_edges(
                                graph, item_key, item
                            )  # edge between dict in list and its children
                        else:
                            graph.add_edge(
                                key, item_key
                            )  # edge between list and item in list
                else:
                    graph.add_edge(
                        parent, key, weight=value
                    )  # edge between parent and child
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, dict):
                    graph.add_edge(parent, key)  # edge between parent and dict
                    add_edges(graph, key, value)
                elif isinstance(value, list):
                    graph.add_edge(parent, key)  # edge between parent and list
                    for index, item in enumerate(value):
                        item_key = f"{key}_{index}"
                        # check if item_key is already in the graph
                        if graph.nodes.get(item_key) is not None:
                            item_key = f"{key}_{index}_{index}"
                        if isinstance(item, dict):
                            graph.add_edge(
                                key, item_key
                            )  # edge between list and dict in list
                            add_edges(
                                graph, item_key, item
                            )  # edge between dict in list and its children
                        else:
                            graph.add_edge(
                                key, item_key
                            )  # edge between list and item in list
                else:
                    graph.add_edge(
                        parent, key, weight=value
                    )  # edge between parent and child

    def json_to_graph(json_obj):
        graph = nx.DiGraph()
        add_edges(graph, "ROOT", json_obj)
        return graph

    return json_to_graph(json_data)


node_id_counter = 0
edge_id_counter = 0
nodes_dict = {}
edges_dict = {}


def json_parse_mutiple_node(json_data):
    from src.models.graph_data import Node, Edge, PlotGraph
    from typing import Any

    # Implement the specific structure
    def create_graph_from_object(
        obj: Any,
        parent_id: int = -1,
        label: str = "",
        base_type: str = "",
    ):
        global node_id_counter, edge_id_counter
        node_id = node_id_counter
        node_id_counter += 1
        child_ids = []

        if isinstance(obj, dict):
            node_type = "ObjectType"
            base = "object"
            for key, value in obj.items():
                # The key becomes a node
                key_node_id = create_graph_from_object(
                    "None",
                    parent_id=node_id,
                    label=key,
                    base_type=node_type,
                )
                child_ids.append(key_node_id)
                edge = Edge(
                    id=edge_id_counter,
                    type="link",
                    source=node_id,
                    target=key_node_id,
                )
                edges_dict[edge_id_counter] = edge
                edge_id_counter += 1

                # The value becomes a child of the key node
                if isinstance(value, list):
                    # If the value is a list, we need to create a separate node for each list item
                    # find the parent node in the nodes_dict and format as f"{parentNodeLabel}Object"
                    parent_node = nodes_dict[key_node_id]
                    parent_node_label = parent_node.label
                    list_lable = f"{parent_node_label}Object"
                    for idx, item in enumerate(value):
                        list_item_id = create_graph_from_object(
                            item,
                            parent_id=key_node_id,
                            label=list_lable,
                            base_type="ObjectType",
                        )
                        child_ids.append(list_item_id)
                        edge = Edge(
                            id=edge_id_counter,
                            type="link",
                            source=key_node_id,
                            target=list_item_id,
                        )
                        edges_dict[edge_id_counter] = edge
                        edge_id_counter += 1
                elif isinstance(value, dict):
                    # If the value is a dict, we need to create a separate node for each dict item
                    # find the parent node in the nodes_dict and format as f"{parentNodeLabel}Object"
                    parent_node = nodes_dict[key_node_id]
                    parent_node_label = parent_node.label
                    dict_lable = f"{parent_node_label}Object"
                    dict_item_id = create_graph_from_object(
                        value,
                        parent_id=key_node_id,
                        label=dict_lable,
                        base_type="ObjectType",
                    )
                    child_ids.append(dict_item_id)
                    edge = Edge(
                        id=edge_id_counter,
                        type="link",
                        source=key_node_id,
                        target=dict_item_id,
                    )
                    edges_dict[edge_id_counter] = edge
                    edge_id_counter += 1
                else:
                    value_node_id = create_graph_from_object(
                        value,
                        parent_id=key_node_id,
                        label=str(value),
                        base_type=node_type,
                    )
                    edge = Edge(
                        id=edge_id_counter,
                        type="link",
                        source=key_node_id,
                        target=value_node_id,
                    )
                    edges_dict[edge_id_counter] = edge
                    edge_id_counter += 1
        elif isinstance(obj, list):
            node_type = "ArrayType"
            base = "list"
            for idx, value in enumerate(obj):
                # Each list item becomes a child of the list node
                # find the parent node in the nodes_dict and format as f"{parentNodeLabel}Object"
                if parent_id < 0:
                    parent_node_label = "Root"
                else:
                    parent_node = nodes_dict[parent_id]
                    parent_node_label = parent_node.label
                list_lable = f"{parent_node_label}Object"
                list_item_id = create_graph_from_object(
                    value, parent_id=node_id, label=list_lable, base_type="ObjectType"
                )
                child_ids.append(list_item_id)
                edge = Edge(
                    id=edge_id_counter, type="link", source=node_id, target=list_item_id
                )
                edges_dict[edge_id_counter] = edge
                edge_id_counter += 1
        elif isinstance(obj, str):
            node_type = "StringType"
            base = "string"
        elif isinstance(obj, int):
            node_type = "NumberType"
            base = "number"
        elif isinstance(obj, float):
            node_type = "NumberType"
            base = "number"
        elif isinstance(obj, bool):
            node_type = "BooleanType"
            base = "boolean"
        elif obj is None:
            node_type = "NullType"
            base = "null"
        else:
            node_type = "UnknownType"
            base = "unknown"

        logger.error(
            f"\n\nnode_id: {node_id}, \nnode_type: {node_type}, \nlabel: {label}, \nbase: {base}, \nparent: {parent_id}, \nchild_ids: {child_ids}"
        )
        node = Node(
            id=node_id,
            type=node_type,
            label=label,
            base=base,
            parent=parent_id,
            child_ids=child_ids,
        )
        nodes_dict[node_id] = node
        return node_id

    create_graph_from_object(json_data, label="Root", base_type="object")

    # Convert the dictionaries to PlotGraph model
    plot_graph = PlotGraph(nodes=nodes_dict, edges=edges_dict)

    # pprint(nodes_dict)
    # pprint(edges_dict)

    ############### Convert PlotGraph to Graph ###############
    def convert_to_digraph(plot_graph: PlotGraph) -> nx.DiGraph:
        G = nx.DiGraph()

        # First, add all nodes to the graph
        for node_id, node in plot_graph.nodes.items():
            G.add_node(node_id, data=node)

        # Then, add edges to the graph
        for edge_id, edge in plot_graph.edges.items():
            G.add_edge(edge.source, edge.target, data=edge)

        return G

    # Convert final PlotGraph to NetworkX DiGraph
    return convert_to_digraph(plot_graph)


########################################################## notebook data


# import json
# import networkx as nx
# from typing import Any
# from pydantic import BaseModel, Field
# import matplotlib.pyplot as plt
# from typing import List, Dict, Union
# from pprint import pprint
# import random


# doPaletteObject = False


# ############### parse JSON ###############
# def parse_json(json_str: str) -> Union[Dict, List]:
#     return json.loads(json_str)
#  #parsed_data = parse_json(json_str)
# # pprint(parsed_data)

# # {'age': 30,
# #  'children': [{'age': 5, 'name': 'Alice'}, {'age': 7, 'name': 'Bob'}],
# #  'city': 'New York',
# #  'name': 'John'}


# ############### Pydantic models ###############
# class Edge(BaseModel):
#     id: int = None
#     type: str = ""
#     source: int = None
#     target: int = None

# class Node(BaseModel):
#     id: int = None
#     type: str = ""
#     label: str = ""
#     base: str = ""
#     parent: int = None
#     child_ids: List[int] = []  # New field for child IDs
#     children: List['Node'] = []
#     edges: List[Edge] = []

# Node.update_forward_refs()

# class PlotGraph(BaseModel):
#     nodes: Dict[str, Node] = Field(..., alias="nodes")
#     edges: Dict[str, Edge] = Field(..., alias="edges")


# ############### Create PlotGraph ################
# # Reset global counters and dictionaries for a fresh start
# node_id_counter = 0
# edge_id_counter = 0
# nodes_dict = {}
# edges_dict = {}

# # Implement the specific structure
# def create_graph_from_object(obj: Any, parent_id: int = None, label: str = "", base_type: str = ""):
#     global node_id_counter, edge_id_counter
#     node_id = node_id_counter
#     node_id_counter += 1
#     child_ids = []

#     if isinstance(obj, dict):
#         node_type = "ObjectType"
#         base = "object"
#         for key, value in obj.items():
#             # The key becomes a node
#             key_node_id = create_graph_from_object(None, parent_id=node_id, label=key, base_type=node_type)
#             child_ids.append(key_node_id)
#             edge = Edge(id=edge_id_counter, type="link", source=node_id, target=key_node_id)
#             edges_dict[edge_id_counter] = edge
#             edge_id_counter += 1

#             # The value becomes a child of the key node
#             if isinstance(value, list):
#                 # If the value is a list, we need to create a separate node for each list item
#                 # find the parent node in the nodes_dict and format as f"{parentNodeLabel}Object"
#                 parent_node = nodes_dict[key_node_id]
#                 parent_node_label = parent_node.label
#                 list_lable = f"{parent_node_label}Object"
#                 for idx, item in enumerate(value):
#                     list_item_id = create_graph_from_object(item, parent_id=key_node_id, label=list_lable, base_type="ObjectType")
#                     child_ids.append(list_item_id)
#                     edge = Edge(id=edge_id_counter, type="link", source=key_node_id, target=list_item_id)
#                     edges_dict[edge_id_counter] = edge
#                     edge_id_counter += 1
#             elif isinstance(value, dict):
#                 # If the value is a dict, we need to create a separate node for each dict item
#                 # find the parent node in the nodes_dict and format as f"{parentNodeLabel}Object"
#                 parent_node = nodes_dict[key_node_id]
#                 parent_node_label = parent_node.label
#                 dict_lable = f"{parent_node_label}Object"
#                 dict_item_id = create_graph_from_object(value, parent_id=key_node_id, label=dict_lable, base_type="ObjectType")
#                 child_ids.append(dict_item_id)
#                 edge = Edge(id=edge_id_counter, type="link", source=key_node_id, target=dict_item_id)
#                 edges_dict[edge_id_counter] = edge
#                 edge_id_counter += 1
#             else:
#                 value_node_id = create_graph_from_object(value, parent_id=key_node_id, label=str(value), base_type=node_type)
#                 edge = Edge(id=edge_id_counter, type="link", source=key_node_id, target=value_node_id)
#                 edges_dict[edge_id_counter] = edge
#                 edge_id_counter += 1
#     elif isinstance(obj, list):
#         node_type = "ArrayType"
#         base = "list"
#         for idx, value in enumerate(obj):
#             # Each list item becomes a child of the list node
#             # find the parent node in the nodes_dict and format as f"{parentNodeLabel}Object"
#             if parent_id is None:
#                 parent_node_label = "Root"
#             else:
#                 parent_node = nodes_dict[parent_id]
#                 parent_node_label = parent_node.label
#             list_lable = f"{parent_node_label}Object"
#             list_item_id = create_graph_from_object(value, parent_id=node_id, label=list_lable, base_type="ObjectType")
#             child_ids.append(list_item_id)
#             edge = Edge(id=edge_id_counter, type="link", source=node_id, target=list_item_id)
#             edges_dict[edge_id_counter] = edge
#             edge_id_counter += 1
#     elif isinstance(obj, str):
#         node_type = "StringType"
#         base = "string"
#     elif isinstance(obj, int):
#         node_type = "NumberType"
#         base = "number"
#     elif isinstance(obj, float):
#         node_type = "NumberType"
#         base = "number"
#     elif isinstance(obj, bool):
#         node_type = "BooleanType"
#         base = "boolean"
#     elif obj is None:
#         node_type = "NullType"
#         base = "null"
#     else:
#         node_type = "UnknownType"
#         base = "unknown"

#     node = Node(id=node_id, type=node_type, label=label, base=base, parent=parent_id, child_ids=child_ids)
#     nodes_dict[node_id] = node
#     return node_id

# # Create the graph from parsed data
# if not doPaletteObject:
#     create_graph_from_object(json_str, label="Root", base_type="list")
# else:
#     create_graph_from_object(json_data, label="Root", base_type="object")

# # Convert the dictionaries to PlotGraph model
# plot_graph = PlotGraph(nodes=nodes_dict, edges=edges_dict)

# # pprint(nodes_dict)
# # pprint(edges_dict)


# ############### Convert PlotGraph to Graph ###############
# def convert_to_digraph(plot_graph: PlotGraph) -> nx.DiGraph:
#     G = nx.DiGraph()

#     # First, add all nodes to the graph
#     for node_id, node in plot_graph.nodes.items():
#         G.add_node(str(node_id), data=node)  # Convert node_id to str for consistency with the rest of the code

#     # Then, add edges to the graph
#     for edge_id, edge in plot_graph.edges.items():
#         # Convert node IDs to str for consistency
#         G.add_edge(str(edge.source), str(edge.target), data=edge)

#     return G

# # Convert final PlotGraph to NetworkX DiGraph
# G = convert_to_digraph(plot_graph)

# # Function to extract node labels from the NetworkX graph
# def extract_node_labels(G: nx.DiGraph) -> Dict[int, str]:
#     return {node: data['data'].label if 'data' in data and data['data'] else '' for node, data in G.nodes(data=True)}

# ############### Plot Graph ###############
# #node_labels = {node: data['data'].label for node, data in G.nodes(data=True)}
# node_labels = extract_node_labels(G)

# # Draw the adjusted graph v2
# if not doPaletteObject:
#     plt.figure(figsize=(20, 20))
#     # create a random seed between 1 - 10000000
#     random_seed = random.randint(1, 100)
#     #pprint(random_seed) #56 looks good
#     # pos = nx.spring_layout(G, seed=56) # good when a good seed can be found, but this is specific to json data
#     # pos = nx.spectral_layout(G)
#     # pos = nx.shell_layout(G) # guaranteed to space nodes out
#     pos = nx.kamada_kawai_layout(G) # this one looks good
# else:
#     plt.figure(figsize=(20, 20))
#     #pos = nx.spiral_layout(G) # use with json_data
#     #pos = nx.spectral_layout(G)
#     #pos = nx.shell_layout(G) # guaranteed to space nodes out
#     pos = nx.kamada_kawai_layout(G) # this one looks good

# nx.draw(G, pos, labels=node_labels, with_labels=True, font_weight="bold")
# plt.show()


########################################################## notebook data 2


# def add_edges(graph, parent, obj):
#   if isinstance(obj, list):
#     for index, item in enumerate(obj):
#       item_key = f"{parent}_{index}"
#       if isinstance(item, dict):
#         graph.add_edge(parent, item_key) # edge between parent and dict
#         add_edges(graph, item_key, item)
#       elif isinstance(value, list):
#         graph.add_edge(parent, key) # edge between parent and list
#         for index, item in enumerate(value):
#           item_key = f"{key}_{index}"
#           # check if item_key is already in the graph
#           if graph.nodes.get(item_key) is not None:
#             item_key = f"{key}_{index}_{index}"
#           if isinstance(item, dict):
#             graph.add_edge(key, item_key) # edge between list and dict in list
#             add_edges(graph, item_key, item) # edge between dict in list and its children
#           else:
#             graph.add_edge(key, item_key) # edge between list and item in list
#       else:
#         graph.add_edge(parent, key, weight=value) # edge between parent and child
#   elif isinstance(obj, dict):
#     for key, value in obj.items():
#       if isinstance(value, dict):
#         graph.add_edge(parent, key) # edge between parent and dict
#         add_edges(graph, key, value)
#       elif isinstance(value, list):
#         graph.add_edge(parent, key) # edge between parent and list
#         for index, item in enumerate(value):
#           item_key = f"{key}_{index}"
#           # check if item_key is already in the graph
#           if graph.nodes.get(item_key) is not None:
#             item_key = f"{key}_{index}_{index}"
#           if isinstance(item, dict):
#             graph.add_edge(key, item_key) # edge between list and dict in list
#             add_edges(graph, item_key, item) # edge between dict in list and its children
#           else:
#             graph.add_edge(key, item_key) # edge between list and item in list
#       else:
#         graph.add_edge(parent, key, weight=value) # edge between parent and child

# def json_to_graph(json_obj):
#   graph = nx.DiGraph()
#   add_edges(graph, "ROOT", json_obj)
#   return graph

# # Convert JSON to graph
# graph = json_to_graph(json_data_3)

# # Print the graph
# print(graph.nodes)
# print(graph.edges)

# import matplotlib.pyplot as plt

# # Draw the graph
# plt.figure(figsize=(20, 20))
# # pos = nx.spiral_layout(graph)
# # pos = nx.spectral_layout(graph)
# pos = nx.shell_layout(graph)
# # pos = nx.spring_layout(graph)
# nx.draw(graph, pos, with_labels=True, font_weight="bold")
# edge_labels = nx.get_edge_attributes(graph, "weight")
# nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)
# plt.show()
