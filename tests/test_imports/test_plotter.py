import os
import tempfile
import itertools
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

from codecarto.plotter import GraphPlot


def create_sample_graph():
    """Create a sample graph for testing that looks similar to SourceParser graph."""
    # Create Graph
    G: nx.DiGraph = nx.DiGraph(name="root")
    # Create Nodes
    G.add_node(1, type="Unknown", label="A1", base="basic.unknown", parent=0)
    G.add_node(2, type="Unknown", label="B1", base="basic.unknown", parent=1)
    G.add_node(3, type="Unknown", label="C1", base="basic.unknown", parent=1)
    G.add_node(4, type="Unknown", label="D1", base="basic.unknown", parent=2)
    G.add_node(5, type="Unknown", label="E1", base="basic.unknown", parent=2)
    G.add_node(6, type="Unknown", label="F1", base="basic.unknown", parent=3)
    G.add_node(7, type="Unknown", label="G1", base="basic.unknown", parent=3)
    G.add_node(8, type="Unknown", label="H1", base="basic.unknown", parent=4)
    G.add_node(9, type="Unknown", label="I1", base="basic.unknown", parent=4)
    # Create Edges
    G.add_edge(1, 2)
    G.add_edge(1, 3)
    G.add_edge(2, 4)
    G.add_edge(2, 5)
    G.add_edge(3, 6)
    G.add_edge(3, 7)
    G.add_edge(4, 8)
    G.add_edge(4, 9)
    return G


def test_plotter():
    """Test GraphPlot class functions and that outputs exist."""
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Set up test directories
            test_dirs: dict = {
                "graph_code_dir": temp_dir_path / "graph_code",
                "graph_json_dir": temp_dir_path / "graph_json",
            }

            # Create the required directories
            test_dirs["graph_code_dir"].mkdir()
            test_dirs["graph_json_dir"].mkdir()

            for json, labels, grid, show in itertools.product([False, True], repeat=4):
                # Create a sample graph
                _graph: nx.DiGraph = create_sample_graph()

                # Test GraphPlot object with different options
                graph_plot = GraphPlot(
                    _dirs=test_dirs, do_labels=labels, do_grid=grid, do_show=show
                )

                # Pass graph to GraphPlot object and plot
                plt.ioff()  # Turn off interactive mode so plt.show() doesn't block the test
                graph_plot.plot(_graph, _json=False)
                if json == True:
                    graph_plot.plot(_graph, _json=True)
                plt.ion()  # Turn interactive mode back on so the test can continue

                # Check if output files exist
                dir_suffixes: list[tuple] = [
                    ("graph_code_dir", True),
                    ("graph_json_dir", json),
                ]
                for dir_suffix, cond in dir_suffixes:
                    plot_files: list = [
                        f
                        for f in os.listdir(test_dirs[dir_suffix])
                        if f.endswith(".png")
                    ]

                    if cond == True:
                        if grid == True:
                            assert len(plot_files) == 1
                        else:
                            assert len(plot_files) > 1  # should get at least 2
                    else:
                        assert len(plot_files) == 0
    except Exception as e:
        # Raise exception
        raise e
