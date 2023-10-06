import networkx as nx
import json

import logging

logger = logging.getLogger(__name__)


# Reset global counters and dictionaries for a fresh start
node_id_counter = 0
edge_id_counter = 0


class JsonParser:
    """A parser for JSON files."""

    def __init__(
        self,
        source: str or list or dict = None,
        parse_type: str = "multiple",
    ):
        """Initializes the parser.

        Parameters:
        -----------
            source (str or list or dict):
                json data to parse.
            parse_type (str):
                the type of parsing for the json data.
        """
        # The graph to populate
        self.source: list or dict = source
        self.parse_type: str = parse_type
        self.graph: nx.DiGraph = nx.DiGraph()

        # To track current elements
        self.current_node: nx.DiGraph = None  # current node for code element
        self.current_type: str = None  # type of code element
        self.current_parent: nx.DiGraph = None  # parent of current node
        self.data_list: list = []

        # If data is string, load it as json
        if isinstance(source, str):
            try:
                source = json.loads(source)
            except ValueError as e:
                raise ValueError("Parser.__init__: source string is not valid json")

        # If data is list, convert it to dict
        if isinstance(source, list):
            source = {"ROOT": source}

        # Parse the source code
        if isinstance(source, dict):
            self.parse_code(source)
        elif not source:
            raise ValueError("Parser.__init__: source is None")
        else:
            logger.info(f"\n\nsource type: {type(source)} \nsource: {source}")
            raise ValueError("Parser.__init__: source is an invalid json object")

    def parse_code(self, source) -> nx.DiGraph:
        """Parse the code in the specified file path.

        Parameters:
        -----------
        source : dict
            The source code to parse.
        """
        # TODO: will fill out the visit functions later
        # for now use the json_parse functions

        # Check the parse type
        if self.parse_type == "single_1":
            self.graph = json_parse_single_node_1(source)
        elif self.parse_type == "single_2":
            self.graph = json_parse_single_node_2(source)
        elif self.parse_type == "multiple":
            self.graph = json_parse_mutiple_node(source)
        else:
            raise ValueError("Parser.parse_code: invalid parse type")

    def create_new_node(
        self,
        node_id: int,
        node_type: str,
        node_label: str,
        node_parent_id: int,
    ) -> nx.DiGraph:
        """Create new node.

        Parameters:
        -----------
        node_id : int
            The id of the new node.
        node_type : str
            The type of the new node.
        node_label : str
            The label of the new node.
        node_parent_id : int
            The id of the parent new node.

        Returns:
        --------
        nx.DiGraph
            The new node.
        """
        # If no node_label, use node_type
        if not node_label:
            node_label = f"{node_type} (u)"

        # Create the new node
        _node = self.graph.add_node(
            node_id,
            type=node_type,
            label=node_label,
            parent=node_parent_id,
        )

        # Add edge between parent and child
        if node_parent_id is not None:
            self.graph.add_edge(node_parent_id, node_id)

        # Set current node
        self.current_node = _node

        # Return the new node
        return _node

    def visit_tree(self, json_data: dict) -> nx.DiGraph:
        """
        Convert a JSON object to a networkx graph.

        Parameters:
        -----------
            json_data (dict): The JSON object to convert.

        Returns:
        --------
            networkx.classes.graph.DiGraph: The graph.
        """
        for key, value in json_data.items():
            if isinstance(value, dict):
                # object type
                # if value is a json object, it won't necessarily have a parent
                # so we need to create a new node
                # create_new_node(value, key, "object", None)
                pass
            elif isinstance(value, list):
                # array type
                # if value is a json array, it won't necessarily have a parent
                # so we need to create a new node
                # create_new_node(value, key, "array", None)
                pass
            elif isinstance(value, str):
                # string type
                # if value is a json string, it's parent will be the key
                # create_new_node(value, key, "string", key)
                pass
            elif isinstance(value, (int, float)):
                # number type
                # if value is a json number, it's parent will be the key
                # create_new_node(value, key, "number", key)
                pass
            elif isinstance(value, bool):
                # boolean type
                # if value is a json boolean, it's parent will be the key
                # create_new_node(value, key, "boolean", key)
                pass
            elif value is None:
                # null type
                # if value is a json null, it's parent will be the key
                # create_new_node(value, key, "null", key)
                pass
            else:
                # unknown type (shouldn't happen)
                # give it a parent of key
                # create_new_node(value, key, "unknown", key)
                pass

    # def visit_object()
    # def visit_array()
    # def visit_string()
    # def visit_number()
    # def visit_boolean()
    # def visit_null()
    # def visit_unknown()


def json_parse_single_node_1(json_data):
    import json

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

    # Load JSON from string
    # TODO: refactor for a list object, this is a janky fix
    # where we're putting the list in an top level object (dict)
    if json_data[0] != "{":
        json_data = '{"key": ' + json_data + "}"
    json_obj = json.loads(json_data)

    # Convert JSON to graph
    return json_to_graph(json_obj)


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

    # Convert JSON to graph
    json_obj = json_data
    return json_to_graph(json_obj)


def json_parse_mutiple_node(json_data):
    from src.models.graph_data import Node, Edge, PlotGraph
    from typing import Any

    ############### Create PlotGraph ################
    nodes_dict = {}
    edges_dict = {}

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
                    None, parent_id=node_id, label=key, base_type=node_type
                )
                child_ids.append(key_node_id)
                edge = Edge(
                    id=edge_id_counter, type="link", source=node_id, target=key_node_id
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

        logger.info(
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

    # Create the graph from parsed data
    if isinstance(json_data, list):
        create_graph_from_object(json_data, label="Root", base_type="list")
    else:
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
    G = convert_to_digraph(plot_graph)
    return G


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
