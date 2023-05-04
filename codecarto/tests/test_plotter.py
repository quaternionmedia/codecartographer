import os
import shutil
import tempfile
import itertools

import networkx as nx
import matplotlib.pyplot as plt

from codecarto.src.codecarto.plotter import GraphPlot


def create_sample_graph():
    # Nodes:
    # node(id(node), type="Unknown", label="", base="basic.uknown", parent=id(node.parent))
    # Edges:
    # edge(id(edge.source), id(edge.target))
    # TODO: make bulkier graph, also make sure graph will work with all layouts to ensure test coverage
    G = nx.DiGraph(name="root")
    G.add_node(1, type="Unknown", label="A1", base="basic.uknown", parent=0)
    G.add_node(2, type="Unknown", label="B1", base="basic.uknown", parent=1)
    G.add_node(3, type="Unknown", label="C1", base="basic.uknown", parent=1)
    G.add_edge(1, 2)
    G.add_edge(1, 3)
    return G


def test_plotter():
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    # Set up test directories
    test_dirs = {
        "graph_code_dir": os.path.join(temp_dir, "graph_code"),
        "graph_json_dir": os.path.join(temp_dir, "graph_json"),
    }

    # Create the required directories
    os.makedirs(test_dirs["graph_code_dir"])
    os.makedirs(test_dirs["graph_json_dir"])

    try:
        for json, labels, grid, show in itertools.product([False, True], repeat=4):
            # Create a sample graph
            _graph = create_sample_graph()

            # Test GraphPlot object with different options
            graph_plot = GraphPlot(
                _dirs=test_dirs, do_labels=labels, do_grid=grid, do_show=show
            )

            # Pass graph to GraphPlot object and plot
            plt.ioff()  # Turn off interactive mode so plt.show() doesn't block the test
            graph_plot.plot(_graph, _json=False)
            if json:
                graph_plot.plot(_graph, _json=True)
            plt.ion()  # Turn interactive mode back on so the test can continue

            # Check if output files exist
            dir_suffixes = [("graph_code_dir", True), ("graph_json_dir", json)]
            for dir_suffix, _json in dir_suffixes:
                plot_files = [
                    f for f in os.listdir(test_dirs[dir_suffix]) if f.endswith(".png")
                ]

                if _json:
                    if grid:
                        assert len(plot_files) == 1
                    else:
                        assert len(plot_files) > 1  # should get at least 2
                else:
                    assert len(plot_files) == 0

    except Exception as e:
        # Raise exception
        raise e
    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir)
