import networkx as nx
import json

from ..parser import Parser


class JsonParser(Parser):
    """A parser for JSON files."""

    def __init__(self, source_files: list = None, source_dict: dict = None):
        """Initializes the parser.

        Parameters:
        -----------
            source_files (list): A list of file paths to parse.
            source_dict (dict): A dictionary of file names and raw file contents.
        """
        super().__init__(source_files, source_dict)

    def add_edges(graph, parent, obj):
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
        add_edges(graph, "root", json_obj)
        return graph

    def graph_to_json(graph):
        def recurse(node):
            edges = dict(graph[node])
            json_obj = {}
            for edge, attrs in edges.items():
                weight = attrs.get("weight", 1)
                if weight == 1 and edge in graph:
                    json_obj[edge] = recurse(edge)
                else:
                    json_obj[edge] = weight
            return json_obj

        return recurse("root")

    # Usage:
    # Load JSON from file
    with open("data.json", "r") as file:
        json_obj = json.load(file)

    # Convert JSON to graph
    graph = json_to_graph(json_obj)

    # Optionally, convert the graph back to JSON
    json_obj_back = graph_to_json(graph)

    # Optionally, save the JSON back to file
    with open("data_back.json", "w") as file:
        json.dump(json_obj_back, file, indent=4)


################ OLD inital thoughts ##############
# def json_data_to_generic_graph(self, json_data: dict) -> nx.DiGraph:
#     """Converts a JSON object to a networkx graph.

#     Parameters:
#     -----------
#         json_data (dict): The JSON object to convert.

#     Returns:
#     --------
#         networkx.classes.graph.DiGraph: The graph.
#     """
#     # TODO: https://www.json.org/json-en.html
#     #       outline of json objects and how we can parse them
#     # Validate inputs
#     if json_data is None:
#         raise ValueError("No json provided.")

#     # Create a func to recusively add nodes and edges from a key-value pair
#     def add_nodes_and_edges_from_list(graph: nx.DiGraph, data: list):
#         for i in data:
#             if isinstance(i, dict):
#                 add_nodes_and_edges_from_dict(graph, i)
#             elif isinstance(i, list):
#                 add_nodes_and_edges_from_list(graph, i)
#             elif (
#                 isinstance(i, str)
#                 or isinstance(i, int)
#                 or isinstance(i, float)
#                 or isinstance(i, bool)
#             ):
#                 graph.add_node(
#                     i,
#                     type="Unknown",
#                     label=str(i),
#                     base="unknown",
#                     parent=i,
#                 )

#     def add_nodes_and_edges_from_dict(graph: nx.DiGraph, data: dict):
#         for k, v in data.items():
#             if isinstance(v, dict):
#                 add_nodes_and_edges_from_dict(graph, v)
#                 graph.add_edge(k, v)
#             elif isinstance(v, list):
#                 add_nodes_and_edges_from_list(graph, i)
#             elif (
#                 isinstance(v, str)
#                 or isinstance(v, int)
#                 or isinstance(v, float)
#                 or isinstance(v, bool)
#             ):
#                 graph.add_node(
#                     k,
#                     type="Unknown",
#                     label=str(v),
#                     base="unknown",
#                     parent=k,
#                 )

#     # Add nodes and edges to the graph
#     graph = nx.DiGraph()
#     add_nodes_and_edges_from_dict(graph, json_data)

#     return graph
