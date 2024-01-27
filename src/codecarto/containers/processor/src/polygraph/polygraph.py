import networkx as nx
from src.database.graph_data import GraphData


class PolyGraphError(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, source, params, message):
        self.source = source
        self.params = params
        self.message = message


def graph_to_json_file(graph: nx.DiGraph, json_path: str) -> dict:
    """Converts a networkx graph to a JSON object.

    Parameters:
    -----------
        graph (GraphData): The graph to convert.
        json_path (str): The path to save the JSON file to.

    Returns:
    --------
        dict: The JSON object.
    """
    # Validate inputs
    if graph is None:
        raise ValueError("No graph provided.")
    if json_path is None or json_path == "":
        raise ValueError("No json_path provided.")

    # Convert the graph to a JSON object and save it to a file
    json_data = graph_to_json_data(graph)
    return json_data


def json_file_to_graph(json_file: str) -> nx.DiGraph:
    """Converts a JSON object to a networkx graph.

    Parameters:
    -----------
        json_file (str): The path to the JSON file to load.

    Returns:
    --------
        nx.DiGraph: The networkx graph.
    """
    import os
    import json

    # Validate inputs
    if json_file is None or json_file == "":
        raise ValueError("No json_file provided.")

    # Check if file exists
    if not os.path.exists(json_file):
        print(f"File {json_file} not found.")
        raise FileNotFoundError(f"File not found: {json_file}")

    # Load the JSON file and convert it to a graph
    try:
        with open(json_file, "r") as f:
            graph_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Failed to load data from {json_file}.")
        raise e

    return json_data_to_graph(graph_data)


def graph_to_json_data(nx_graph: nx.DiGraph) -> dict:
    """Converts a networkx graph to a JSON object.

    Parameters:
    -----------
        graph (nx.DiGraph): The graph to convert.

    Returns:
    --------
        dict: The JSON object.
    """
    from src.plotter.palette import Palette

    # Validate inputs
    if nx_graph is None:
        raise ValueError("No graph provided.")
    if not isinstance(nx_graph, nx.DiGraph):
        try:
            graph: nx.DiGraph = graphdata_to_nx(nx_graph)
        except:
            raise ValueError("'graph' must be formatted as a GraphData object.")

    # Create the JSON object
    graph_data: dict[str, dict[str, dict[str, list]]] = {"nodes": {}, "edges": {}}

    # Create all node objects
    node_styles = Palette().get_node_styles()
    for node_id, data in nx_graph.nodes.data(True):
        node_type = data.get("type", "Unknown")
        if node_type not in node_styles.keys():
            node_type = "Unknown"

        node_obj = {
            "id": node_id,
            "type": node_type,
            "label": data.get("label", node_id),
            "base": data.get("base", "unknown"),
            "parent": data.get("parent"),
            "children": [],
            "edges": [],
        }
        graph_data["nodes"][node_id] = node_obj

    # Link parent and child nodes together
    for node_id, node_obj in graph_data["nodes"].items():
        parent_id = node_obj["parent"]
        if parent_id and parent_id in graph_data["nodes"]:
            graph_data["nodes"][parent_id]["children"].append(node_obj)

    # Create edge objects and link them to their source nodes
    for edge_id, (source, target) in enumerate(nx_graph.edges()):
        if source not in graph_data["nodes"] or target not in graph_data["nodes"]:
            continue
        source_node: dict[str, list] = graph_data["nodes"][source]
        target_node: dict[str, list] = graph_data["nodes"][target]

        edge_obj = {
            "id": str(edge_id),  # Convert edge_id to a string
            "type": "edge",
            "source": source_node["id"],
            "target": target_node["id"],
        }
        graph_data["edges"][str(edge_id)] = edge_obj  # Convert edge_id to a string
        source_node["edges"].append(edge_obj)

    # # Clean out any graph_data["nodes"] that have parents
    # for node_id, node_obj in list(graph_data["nodes"].items()):
    #     if node_obj["parent"]:
    #         del graph_data["nodes"][node_id]

    return graph_data


def json_data_to_graph(json_data: dict[str, dict]) -> nx.DiGraph:
    """Converts a JSON object to a networkx graph.

    Parameters:
    -----------
        json_data (dict): The JSON object to convert.

    Returns:
    --------
        networkx.classes.graph.DiGraph: The graph.
    """

    # Validate inputs
    if json_data is None:
        raise ValueError("No json provided.")

    # Create the graph
    graph = nx.DiGraph()

    def add_node_and_children(node_id, node_obj):
        # Recursively add children
        graph.add_node(
            node_id,
            type=node_obj["type"],
            label=node_obj["label"],
            base=node_obj["base"],
            parent=node_obj["parent"],
        )
        for child_obj in node_obj["children"]:
            child_id = child_obj["id"]
            add_node_and_children(child_id, child_obj)

    # Add nodes and their children to the graph
    for node_id, node_obj in json_data["nodes"].items():
        add_node_and_children(node_id, node_obj)

    # Add edges to the graph
    for edge_id, edge_obj in json_data["edges"].items():
        graph.add_edge(edge_obj["source"], edge_obj["target"])

    return graph


def graphdata_to_nx(graph_data: GraphData) -> nx.DiGraph:
    """Converts a GraphData object to a networkx graph.

    Parameters:
    -----------
        graph_data (GraphData): The GraphData object to convert.

    Returns:
    --------
        networkx.classes.graph.Graph: The graph.
    """

    # Validate inputs
    if graph_data is None:
        raise ValueError("No graph provided.")

    # Create the graph
    try:
        G = nx.DiGraph()

        # Add nodes to the graph
        for node_id, node in graph_data.nodes.items():
            G.add_node(node_id, label=node.label, type=node.type, base=node.base)

        # Add edges to the graph
        for edge_id, edge in graph_data.edges.items():
            G.add_edge(edge.source, edge.target, id=edge_id, type=edge.type)

        return G
    except:
        raise ValueError("'graph' must be formatted as a GraphData object.")


def digraph_to_graphbase(digraph: nx.DiGraph) -> dict:
    """Converts a networkx DiGraph to a GraphBase compatible graph.

    Parameters:
    -----------
        digraph (nx.DiGraph): The graph to convert.

    Returns:
    --------
        dict: object compatible with graphbase database.
    """
    from src.plotter.palette import Palette

    # Validate inputs
    if digraph is None:
        raise ValueError("No graph provided.")
    if not isinstance(digraph, nx.DiGraph):
        raise ValueError("'graph' must be formatted as a GraphData object.")

    # Create the GraphData object
    graph_data: dict[str, list] = {"nodes": [], "links": []}

    # Create all node objects
    node_styles = Palette().get_node_styles()
    for node_id, data in digraph.nodes.data(True):
        node_type = data.get("type", "Unknown")
        if node_type not in node_styles.keys():
            node_type = "Unknown"

        node_obj = {
            "id": node_id,
            "type": node_type,
            "label": data.get("label", node_id),
            "base": data.get("base", "unknown"),
            "parent": data.get("parent"),
            "children": [],
            "edges": [],
        }
        graph_data["nodes"].append(node_obj)

    # Link parent and child nodes together
    for node_obj in graph_data["nodes"]:
        parent_id = node_obj["parent"]
        if parent_id and parent_id in graph_data["nodes"]:
            parent_obj: dict = graph_data["nodes"][parent_id]
            parents_children: list = parent_obj["children"]
            if node_obj not in parents_children:
                parents_children.append(node_obj)

    # Create edge objects and link them to their source nodes
    for edge_id, (source, target) in enumerate(digraph.edges()):
        if source not in graph_data["nodes"] or target not in graph_data["nodes"]:
            continue
        source_node: dict[str, list] = graph_data["nodes"][source]
        target_node: dict[str, list] = graph_data["nodes"][target]

        edge_obj = {
            "id": edge_id,
            "type": "edge",
            "source": source_node["id"],
            "target": target_node["id"],
        }
        graph_data["links"].append(edge_obj)
        source_node["links"].append(edge_obj)  # TODO: why was i doing this?

    # # Clean out any graph_data["nodes"] that have parents
    # for node_id, node_obj in list(graph_data["nodes"].items()):
    #     if node_obj["parent"]:
    #         del graph_data["nodes"][node_id]

    return graph_data


def gJGF_to_nxGraph(graph_name: str, graph_data: dict) -> tuple:
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
    graph: nx.DiGraph = nx.node_link_graph(graph_data, directed=True, multigraph=False)

    # Check if graph found
    if not graph:
        raise PolyGraphError(
            "gJGF_to_nxGraph",
            "Graph not provided",
            {"graph_name": graph_name, "graph": graph},
        )
    elif graph.number_of_nodes() == 0:
        raise PolyGraphError(
            "gJGF_to_nxGraph",
            {"graph_name": graph_name, "graph": graph},
            "Graph has no nodes",
        )

    # Return the graph
    return graph, graph_name
