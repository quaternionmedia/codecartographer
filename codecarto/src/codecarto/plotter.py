import os
import math
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx
import random
import inspect
from .palette.palette import Palette
from .utils.directories import OUTPUT_DIRECTORY as output_dir


class GraphPlot:
    def __init__(self):
        self.seed: dict[str, int] = {}

    def plot(self, _graph, json: bool = False):
        """Plots a graph using matplotlib.

        Parameters:
        -----------
            _graph (networkx.classes.graph.Graph):
                The graph to plot.
            json (bool) Default = True:
                Whether the graph is in JSON format.
        """
        grid: bool = False
        if _graph and isinstance(_graph, nx.classes.graph.Graph):
            if json == False:
                graph_dir = output_dir["graph_code_dir"]
            else:
                graph_dir = output_dir["graph_json_dir"]

            # Get all layout functions
            layouts = [
                nx.layout.spring_layout,
                nx.layout.spiral_layout,
                nx.layout.circular_layout,
                nx.layout.random_layout,
                # nx.layout.kamada_kawai_layout,
                nx.layout.shell_layout,
                nx.layout.spectral_layout,
                nx.layout.planar_layout,
            ]

            if grid:
                num_layouts = len(layouts)
                grid_size = math.ceil(math.sqrt(num_layouts))

                fig, axes = plt.subplots(nrows=1, sharex=True, sharey=True)
                fig.set_size_inches(15, 7.5)
                mng = plt.get_current_fig_manager()
                mng.window.wm_geometry("+0+0")

            # Loop through all layouts
            for idx, layout in enumerate(layouts):
                if grid:
                    ax = (
                        axes[idx // grid_size, idx % grid_size]
                        if grid_size > 1
                        else axes
                    )
                    ax.set_title(f"{layout.__name__}")
                    ax.axis("off")
                    pos = layout(self.G)

                    node_list = []
                    node_sizes = []
                    node_alphas = []
                    node_colors = []
                    node_shapes = []
                    node_labels = {}

                    node_styles = Palette().get_node_styles()

                    for n, a in _graph.nodes(data=True):
                        node_type = a.get("type", "Unknown")
                        if node_type not in node_styles.keys():
                            node_type = "Unknown"

                        node_list.append(n)
                        node_sizes.append( node_styles[node_type]["size"])
                        node_alphas.append( node_styles[node_type]["alpha"])
                        node_colors.append( node_styles[node_type]["color"])
                        node_shapes.append( node_styles[node_type]["shape"])
                        node_labels[n] = node_styles[node_type]["label"]

                    # Draw nodes
                    for node_shape in set(node_shapes):
                        nx.draw_networkx_nodes(
                            _graph,
                            pos,
                            nodelist=[
                                n
                                for n, shape in zip(node_list, node_shapes)
                                if shape == node_shape
                            ],
                            node_size=[
                                size
                                for size, shape in zip(node_sizes, node_shapes)
                                if shape == node_shape
                            ],
                            node_color=[
                                color
                                for color, shape in zip(node_colors, node_shapes)
                                if shape == node_shape
                            ],
                            node_shape=node_shape,
                            alpha=node_alphas[
                                0
                            ],  # Assuming alpha values are same for all nodes
                            ax=ax,
                        )

                    # Draw labels
                    nx.draw_networkx_labels(
                        _graph,
                        pos,
                        font_size=10,
                        font_family="sans-serif",
                        ax=ax,
                        labels=node_labels,
                    )

                    # Draw edges
                    nx.draw_networkx_edges(_graph, pos, alpha=0.2, ax=ax)

                    unique_node_types = set(
                        node_type
                        for _, node_type in _graph.nodes(data="type")
                        if node_type is not None
                    )

                    # Create legend
                    t_colors = {
                        node_type: node_styles[node_type]["color"]
                        for node_type in unique_node_types
                    }
                    t_shapes = {
                        node_type: node_styles[node_type]["shape"]
                        for node_type in unique_node_types
                    }

                    legend_elements = [
                        mlines.Line2D(
                            [0],
                            [0],
                            color=color,
                            marker=shape,
                            linestyle="None",
                            markersize=10,
                            label=theme,
                        )
                        for theme, color, shape in zip(
                            t_colors, t_colors.values(), t_shapes.values()
                        )
                    ]
                    ax.legend(handles=legend_elements, loc="upper right", fontsize=10)

                    # Remove extra subplots if the grid is not fully filled
                    for idx in range(num_layouts, grid_size * grid_size):
                        fig.delaxes(axes[idx // grid_size, idx % grid_size])

                    file_path = os.path.join(graph_dir, "grid.png")
                    plt.tight_layout()
                    plt.savefig(file_path)
                    # plt.show()
                else:
                    # Initialize figure and axes
                    fig, ax = plt.subplots(figsize=(15, 7.5))

                    # placement of show on monitor
                    fig.canvas.manager.window.wm_geometry("+0+0")
                    ax.set_title(
                        f"{str(layout.__name__).replace('_layout', '').capitalize()} Layout"
                    )
                    ax.axis("off")

                    # Collect nodes and their attributes
                    node_styles = Palette().get_node_styles()
                    node_data: dict[str, list] = {
                        node_type: [] for node_type in node_styles.keys()
                    }
                    for n, a in _graph.nodes(data=True):
                        node_type = a.get("type", "Unknown")
                        if node_type not in node_styles.keys():
                            node_type = "Unknown"
                        node_data[node_type].append(n)

                    # Compute positions
                    seed = -1
                    try:
                        if "seed" in inspect.signature(layout).parameters:
                            if json:
                                # Use the same seed for the same layout
                                seed = self.seed[layout.__name__]
                            else:
                                seed = random.randint(0, 1000)
                                self.seed[layout.__name__] = seed
                            pos = layout(_graph, seed=seed)
                        elif layout.__name__ == "shell_layout":
                            # Group nodes by parent
                            grouped_nodes: dict[str, list] = {}
                            for node, data in _graph.nodes(data=True):
                                parent = data.get("parent", "Unknown")
                                if parent not in grouped_nodes:
                                    grouped_nodes[parent] = []
                                grouped_nodes[parent].append(node)

                            # Create the list of lists (shells)
                            shells = list(grouped_nodes.values())

                            # Apply shell layout
                            pos = nx.layout.shell_layout(_graph, nlist=shells)
                        else:
                            pos = layout(_graph)
                    except Exception as e:
                        print(e)
                        continue

                    # Draw nodes with different shapes
                    for node_type, nodes in node_data.items():
                        nx.drawing.draw_networkx_nodes(
                            _graph,
                            pos,
                            nodelist=nodes,
                            node_color=node_styles[node_type]["color"],
                            node_shape=node_styles[node_type]["shape"],
                            node_size=node_styles[node_type]["size"],
                            alpha=node_styles[node_type]["alpha"],
                        )

                    # Draw edges and labels
                    nx.drawing.draw_networkx_edges(_graph, pos, alpha=0.2)
                    nx.drawing.draw_networkx_labels(
                        _graph,
                        pos,
                        labels=nx.classes.get_node_attributes(_graph, "label"),
                        font_size=10,
                        font_family="sans-serif",
                    )

                    # Draw legend
                    unique_node_types = set(
                        node_type
                        for _, node_type in _graph.nodes(data="type")
                        if node_type is not None
                    )
                    _colors = {
                        node_type: node_styles[node_type]["color"]
                        for node_type in unique_node_types
                    }
                    _shapes = {
                        node_type: node_styles[node_type]["shape"]
                        for node_type in unique_node_types
                    }
                    legend_elements = [
                        mlines.Line2D(
                            [0],
                            [0],
                            color=color,
                            marker=shape,
                            linestyle="None",
                            markersize=10,
                            label=theme,
                        )
                        for theme, color, shape in zip(
                            _colors, _colors.values(), _shapes.values()
                        )
                    ]
                    ax.legend(handles=legend_elements, loc="upper right", fontsize=10)

                    # Save the file to the interations folder
                    plot_name = ""
                    if seed == -1:
                        plot_name = f"{layout.__name__}.png"
                    else:
                        plot_name = f"{seed}_{layout.__name__}.png"

                    file_path = os.path.join(graph_dir, plot_name)

                    if layout.__name__ == "planar_layout":
                        plt.show()

                    plt.tight_layout()
                    plt.savefig(file_path)
                    plt.close()


########## OPTIONAL ##########
# in the plot() function after creating pos, can use this to center the main and plot nodes

# Center the main and plot nodes
# import numpy as np
# x_center = (
#     max(x for x, _ in pos.values()) + min(x for x, _ in pos.values())
# ) / 2
# y_center = (
#     max(y for _, y in pos.values()) + min(y for _, y in pos.values())
# ) / 2

# if "main" in pos:
#     print("main")
#     pos["main"] = np.array([x_center, y_center + 0.2])
# if "plot" in pos:
#     print("plot")
#     pos["plot"] = np.array([x_center, y_center])
