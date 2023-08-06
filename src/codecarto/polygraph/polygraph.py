import networkx as nx
from codecarto import GraphData, Json, ErrorHandler


class PolyGraph: 
    """A class used to convert data types to a networkx graph and vice versa."""

    def graph_to_json_file(self, graph: GraphData, json_path:str) -> str:
        """Converts a networkx graph to a JSON object. 

        Parameters: 
        -----------
            graph (GraphData): The graph to convert. 
            json_path (str): The path to save the JSON file to.
            
        Returns: 
        --------
            str: The JSON object. 
        """
        # Validate inputs
        if graph is None:
            ErrorHandler.raise_error("No graph provided.")
        if json_path is None or json_path == "":
            ErrorHandler.raise_error("No json_path provided.")

        # Convert the graph to a JSON object and save it to a file
        json_data = self.graph_to_json_data(graph)
        return Json.save_json(json_path, json_data)
    
    def json_file_to_graph(self, json_file: str) -> nx.DiGraph:
        """Converts a JSON object to a networkx graph.

        Parameters:
        -----------
            json_file (str): The path to the JSON file to load.

        Returns:
        --------
            nx.DiGraph: The networkx graph.
        """
        # Validate inputs
        if json_file is None or json_file == "":
            ErrorHandler.raise_error("No json_file provided.")

        # Load the JSON file and convert it to a graph
        graph_data = Json.load_json(json_file)
        return self.json_data_to_graph(graph_data)

    def graph_to_json_data(self, graph:GraphData) -> dict:
        """Converts a networkx graph to a JSON object. 

        Parameters: 
        -----------
            graph (GraphData): The graph to convert. 
            
        Returns: 
        --------
            dict: The JSON object. 
        """ 
        from codecarto import Palette

        # Validate inputs
        if graph is None:
            ErrorHandler.raise_error("No graph provided.") 
        if not isinstance(graph, nx.DiGraph):
            try:
                graph:nx.DiGraph = self.graphdata_to_nx(graph)
            except:
                ErrorHandler.raise_error("'graph' must be formatted as a GraphData object.") 

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

    def json_data_to_graph(self, json_data: dict[str, dict]) -> nx.DiGraph:
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
            ErrorHandler.raise_error("No json provided.")
        
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
            ErrorHandler.raise_error("No graph provided.")

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
            ErrorHandler.raise_error("'graph' must be formatted as a GraphData object.")
