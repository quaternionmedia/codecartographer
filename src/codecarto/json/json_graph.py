from .json_utils import save_json_data
from ..palette.palette import Palette

# TODO: We have a 'P' theme going on here, plotter, parser, palette, processor.
#      We should try to make this follow the same convention.
#      It should be descriptive, short, not too many syllables, and easy to type.
#      GPT suggested PolyGrapher, if we changed this to take in any data type,
#      not just JSON, then this could work.


class JsonGraph:
    """Converts a networkx graph to a JSON object and vice versa."""

    def __init__(self, _path, _graph, _convert_back: bool = False):
        """Constructor.\n
        Args:\n
            graph (networkx.classes.graph.Graph): The graph to convert.\n
            json_file_path (str): The path to the JSON file to save.\n
        """
        self.json_file_path = _path
	if not _graph.has_children():
		_json_data = load_json_data(_path)
        	save_json_data(self.json_file_path, self.json_data)
		self.json_graph = self.json_to_graph(self.json_data)
	else:
        	self.json_data = self.graph_to_json(_graph)
        	save_json_data(self.json_file_path, self.json_data)
        	if _convert_back:
            		self.json_graph = self.json_to_graph(self.json_data)
        	else:
            		self.json_graph = None

    def graph_to_json(self, graph):
        """Converts a networkx graph to a JSON object.\n
        Args:\n
            G (networkx.classes.graph.Graph): The graph to convert.\n
        Returns:\n
            dict: The JSON object.\n
        """
        # Check if the graph is a networkx graph
        import networkx as nx

        if not isinstance(graph, nx.Graph):
            raise TypeError("'graph' must be a networkx graph")

        # Create the JSON object
        graph_data: dict[str, dict[str, dict[str, list]]] = {"nodes": {}, "edges": {}}

        # Create all node objects
        node_styles = Palette().get_node_styles()
        for node_id, data in graph.nodes.data(True):
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
        for edge_id, (source, target) in enumerate(graph.edges()):
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
            graph_data["edges"][edge_id] = edge_obj
            source_node["edges"].append(edge_obj)

        # # Clean out any graph_data["nodes"] that have parents
        # for node_id, node_obj in list(graph_data["nodes"].items()):
        #     if node_obj["parent"]:
        #         del graph_data["nodes"][node_id]

        return graph_data

    def json_to_graph(self, json_data: dict[str, dict]):
        """Converts a JSON object to a networkx graph.\n
        Args:\n
            json_data (dict): The JSON object to convert.\n
        Returns:\n
            networkx.classes.graph.Graph: The graph.\n
        """
        import networkx as nx

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