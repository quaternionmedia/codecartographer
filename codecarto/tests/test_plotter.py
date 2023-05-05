import os 
import tempfile
import itertools
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt

from ..src.codecarto.plotter import GraphPlot
from ..src.codecarto.utils.directory.output_dir import set_output_dir


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
    """Test GraphPlot class functions and that outputs exist."""
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Set up test directories
            test_dirs = {
                "graph_code_dir": temp_dir_path / "graph_code",
                "graph_json_dir": temp_dir_path / "graph_json",
            }

            # Create the required directories
            test_dirs["graph_code_dir"].mkdir()
            test_dirs["graph_json_dir"].mkdir()

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