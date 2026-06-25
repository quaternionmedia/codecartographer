from typing import Dict, Any
import networkx as nx
import gravis as gv

from codecarto.models.plot_data import PlotOptions
from codecarto.services.position_service import Positions


class GraphSerializer:
    """Service for serializing NetworkX graphs to JSON format for client-side rendering."""

    @staticmethod
    def serialize_to_gjgf(
        graph: nx.DiGraph, options: PlotOptions, isDependencyPlot: bool = False
    ) -> Dict[str, Any]:
        """Convert NetworkX graph to Graph JSON Format (gJGF) with layout positions.

        Parameters
        ----------
        graph : nx.DiGraph
            The NetworkX directed graph to serialize
        options : PlotOptions
            Plot options containing layout, type, and palette info
        isDependencyPlot : bool
            Whether this is a dependency plot (affects node coloring)

        Returns
        -------
        Dict[str, Any]
            The graph in gJGF format with positions and styling
        """
        # Ensure we have a DiGraph
        ntxGraph = nx.DiGraph(graph)

        # Apply layout algorithm to get node positions
        layout_name = f"{options.layout.lower()}_layout"
        positions = Positions().get_node_positions(graph=ntxGraph, layout_name=layout_name)

        # Scale positions based on layout type
        spread = 100
        if options.layout == "Spectral":
            spread = 500
        elif layout_name == "kamada_kawai_layout":
            spread = 500

        # Add scaled positions to graph nodes
        for node_id, (x, y) in positions.items():
            node = ntxGraph.nodes[node_id]
            node["x"] = float(x) * spread
            node["y"] = float(y) * spread

        # Scale nodes based on depth (unified schema) and edge count
        for node, data in ntxGraph.nodes(data=True):
            # Calculate the number of edges
            out_edges_count = len(ntxGraph.out_edges(node)) * 10
            in_edges_count = len(ntxGraph.in_edges(node)) * 10

            # Depth-based base size (unified schema: 0=dir, 1=file, 2=symbol, 3=sub)
            node_depth = data.get("depth")
            if node_depth is not None:
                depth_base = {0: 40, 1: 20, 2: 10, 3: 6}.get(int(node_depth), 10)
                data["size"] = depth_base + out_edges_count + in_edges_count
            else:
                # Legacy nodes without depth: use edge-count heuristic
                data["size"] = 1 + out_edges_count + in_edges_count

            # Set color based on type for dependency plot
            if isDependencyPlot:
                if data.get("type") == "external":
                    data["color"] = "red"  # External dependencies
                else:
                    data["color"] = "blue"  # Internal project files

        # Convert to gJGF using gravis
        # gravis returns {graph: {...}}, we only need the inner graph object
        gjgf = gv.convert.any_to_gjgf(ntxGraph)
        return gjgf["graph"]  # Extract the inner graph object

    @staticmethod
    def create_metadata(graph: nx.DiGraph, options: PlotOptions) -> Dict[str, Any]:
        """Generate metadata about the graph.

        Parameters
        ----------
        graph : nx.DiGraph
            The NetworkX graph
        options : PlotOptions
            Plot options

        Returns
        -------
        Dict[str, Any]
            Metadata dictionary with graph statistics and options
        """
        return {
            "layout": options.layout,
            "type": options.type,
            "nodeCount": graph.number_of_nodes(),
            "edgeCount": graph.number_of_edges(),
            "palette_id": options.palette_id,
        }
