import json
import tempfile
import networkx as nx
from pathlib import Path

from codecarto.json.json_graph import JsonGraph


def test_json_graph():
    """Test that json graph can be created and then converted back to a graph."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # create some digraph with decent size using networkx
            G = nx.DiGraph()
            G.add_nodes_from(
                [
                    (
                        i,
                        {
                            "type": f"Type_{i}",
                            "label": f"Node_{i}",
                            "parent": i - 1 if i > 0 else None,
                        },
                    )
                    for i in range(5)
                ]
            )
            G.add_edges_from([(i, i + 1) for i in range(4)])

            # use graph_to_json to pass graph
            json_file_path = tmpdir_path / "test_graph.json"
            json_graph_obj = JsonGraph(str(json_file_path), G)

            # check that the json file created an object that represents the graph created
            with open(json_file_path, "r") as f:
                json_data = json.load(f)

            # check that the json file has the same number of nodes and edges as the graph
            assert len(json_data["nodes"]) == len(G.nodes)
            assert len(json_data["edges"]) == len(G.edges)

            # Check if the JSON data's nodes have the same attributes as the test graph's nodes
            for node in json_data["nodes"]:
                node_id = node["id"]
                assert G.nodes[node_id]["type"] == node["type"]
                assert G.nodes[node_id]["label"] == node["label"]
                assert G.nodes[node_id]["parent"] == node["parent"]

            # Check if the JSON data's edges match the test graph's edges
            json_edges = [
                (edge["source"], edge["target"]) for edge in json_data["edges"]
            ]
            for edge in G.edges:
                assert edge in json_edges

            # pass json file into json_to_graph
            new_G = json_graph_obj.json_to_graph(json_data)

            # check that graph was created
            assert new_G is not None

            # check that graph matches orig graph
            assert nx.is_isomorphic(
                G, new_G, node_match=lambda n1, n2: n1["label"] == n2["label"]
            )

    except Exception as e:
        # Raise exception
        raise e
