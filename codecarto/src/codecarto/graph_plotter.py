import os
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx
import random
import inspect
from .themes.themes import Theme
from .utils.dirs import OUTPUT_DIRECTORY as output_dir


class GraphPlotter:
    def __init__(self):
        self.seed: dict[str, int] = {}

    def plot(self, G, json: bool = False):
        """Plots a graph using matplotlib.

        Parameters:
        -----------
            G (networkx.classes.graph.Graph):
                The graph to plot.
            json (bool) Default = True:
                Whether the graph is in JSON format.
        """
        if G:
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
                nx.layout.kamada_kawai_layout,
                nx.layout.shell_layout,
                nx.layout.spectral_layout,
                nx.layout.planar_layout,
            ]

            # Loop through all layouts
            for idx, layout in enumerate(layouts):
                # Initialize figure and axes
                fig, ax = plt.subplots(figsize=(15, 7.5))

                # placement of show on monitor
                fig.canvas.manager.window.wm_geometry("+0+0")
                ax.set_title(
                    f"{layout.__name__.replace('_layout', '').capitalize()} Layout"
                )
                ax.axis("off")

                # Collect nodes and their attributes
                node_styles = Theme().get_node_styles()
                node_data: dict(str, list) = {
                    node_type: [] for node_type in node_styles.keys()
                }
                for n, a in G.nodes(data=True):
                    node_type = a.get("node_type", "Unknown")
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
                        pos = layout(G, seed=seed)
                    elif layout.__name__ == "shell_layout":
                        # Group nodes by parent
                        grouped_nodes = {}
                        for node, data in G.nodes(data=True):
                            parent = data.get("parent", "Unknown")
                            if parent not in grouped_nodes:
                                grouped_nodes[parent] = []
                            grouped_nodes[parent].append(node)

                        # Create the list of lists (shells)
                        shells = list(grouped_nodes.values())

                        # Apply shell layout
                        pos = nx.layout.shell_layout(G, nlist=shells)
                    else:
                        pos = layout(G)
                except Exception as e:
                    print(e)
                    continue

                # Draw nodes with different shapes
                for node_type, nodes in node_data.items():
                    nx.draw_networkx_nodes(
                        G,
                        pos,
                        nodelist=nodes,
                        node_color=node_styles[node_type]["color"],
                        node_shape=node_styles[node_type]["shape"],
                        node_size=node_styles[node_type]["size"],
                        alpha=node_styles[node_type]["alpha"],
                    )

                # Draw edges and labels
                nx.draw_networkx_edges(G, pos, alpha=0.2)
                nx.draw_networkx_labels(
                    G,
                    pos,
                    labels=nx.get_node_attributes(G, "label"),
                    font_size=10,
                    font_family="sans-serif",
                )

                # Draw legend
                unique_node_types = set(
                    node_type
                    for _, node_type in G.nodes(data="node_type")
                    if node_type is not None
                )
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

                # Save the file to the interations folder
                plot_name = ""
                if seed == -1:
                    plot_name = f"{layout.__name__}.png"
                else:
                    plot_name = f"{seed}_{layout.__name__}.png"

                file_path = os.path.join(graph_dir, plot_name)
                plt.tight_layout()
                plt.savefig(file_path)

                # TODO: DEBUG, remove later
                print(f"Saved {layout.__name__}, seed: {seed}")
                # plt.show()
                # if (
                #     layout.__name__ == "spiral_layout"
                #     or layout.__name__ == "spectral_layout"
                # ):
                #     plt.show()

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
