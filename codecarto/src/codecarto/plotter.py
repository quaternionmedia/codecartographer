import os
import math
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx
import random
import inspect
from .palette.palette import Palette

#TODO: add grid option
#TODO: add label option

class GraphPlot:
    def __init__(self, _dirs: dict[str, str] = None, do_labels: bool = False, do_grid: bool = False, do_show: bool = False):
        """Constructor.

        Parameters:
        -----------
            _dirs (dict[str, str]) Default = None:
                The directories to use.
        """
        self.seed: dict[str, int] = {}
        self.dirs: dict[str, str] = _dirs
        self.show_label: bool = do_labels
        self.do_grid: bool = do_grid
        self.do_show: bool = do_show

    def plot(self, _graph, _json: bool = False):
        """Plots a graph using matplotlib.

        Parameters:
        -----------
            _graph (networkx.classes.graph.Graph):
                The graph to plot.
            _json (bool) Default = True:
                Whether the graph is in JSON format.
        """
        # check if graph
        if _graph and isinstance(_graph, nx.classes.graph.Graph):
            # check if json
            if _json == False:
                graph_dir = self.dirs["graph_code_dir"]
            else:
                graph_dir = self.dirs["graph_json_dir"]

            # get all layout functions
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

            # compute grid
            num_layouts = len(layouts)
            grid_size = math.ceil(math.sqrt(num_layouts)) 

            # setup for grids
            if self.do_grid:
                print("Plotting grid...") 

                # Set the figure size
                figsize = (5, 5)
                fig, axes = plt.subplots(grid_size, grid_size, figsize=(figsize[0]*grid_size, figsize[1]*grid_size))
                fig.set_size_inches(18.5, 9.5)

                # Set the figure position to the top-left corner of the screen plus the margin
                mng = plt.get_current_fig_manager()
                mng.window.wm_geometry("+0+0") 
            
            # Loop through all layouts 
            empty_axes_indices = []
            for idx, layout in enumerate(layouts):
                if self.do_grid:
                    # Set up ax
                    ax = (
                        axes[idx // grid_size, idx % grid_size]
                        if grid_size > 1
                        else axes
                    )
                    ax.set_title(f"{layout.__name__}")
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
                            if _json:
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
                        print(f"Skipping {layout.__name__} due to an error: {e}") 
                        empty_axes_indices.append(idx) 
                        
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
                            ax=ax,
                        ) 

                    # Draw edges and labels
                    nx.drawing.draw_networkx_edges(_graph, pos, alpha=0.2, ax=ax)
                    if self.show_label:
                        nx.drawing.draw_networkx_labels(
                            _graph,
                            pos,
                            labels=nx.classes.get_node_attributes(_graph, "label"),
                            font_size=10,
                            ax=ax,
                            font_family="sans-serif",
                        ) 

                    # Create legend
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

                elif not self.do_grid:
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
                            if _json:
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
                    if self.show_label:
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
                        if _json:
                            plot_name = f"JSON_{layout.__name__}.png"
                        else:
                            plot_name = f"CODE_{layout.__name__}.png"
                    else:
                        if _json:
                            plot_name = f"JSON_{seed}_{layout.__name__}.png"
                        else:
                            plot_name = f"CODE_{seed}_{layout.__name__}.png"

                    file_path = os.path.join(graph_dir, plot_name)

                    plt.tight_layout()
                    plt.savefig(file_path)
                    if self.do_show:
                        plt.show()
                    plt.close()

            if self.do_grid: 

                # Remove extra subplots if the grid is not fully filled
                for idx in reversed(empty_axes_indices):
                    fig.delaxes(fig.axes[idx])
        

                # TODO: attempting to recreate the figure with the correct grid size, but not working out yet
                # import copy 
                # # Remove titles of empty plots
                # for ax in fig.axes:
                #     if ax not in empty_axes_indices:
                #         ax.set_title("")
                        
                # # Get new grid size
                # new_grid_size = (math.ceil(num_layouts / math.floor(math.sqrt(num_layouts - len(empty_axes_indices)))), math.floor(math.sqrt(num_layouts - len(empty_axes_indices))))

                # # Get new figure size
                # new_figsize = (new_grid_size[0] * 5, new_grid_size[1] * 5)

                # # Create a new figure and axes with the correct size and shape
                # new_fig, new_axes = plt.subplots(new_grid_size[0], new_grid_size[1], figsize=(new_figsize[0], new_figsize[1]))

                # # Loop through the non-empty axes of the old figure and recreate the contents of each non-empty axis in the corresponding axis in the new figure
                # old_ax_index = 0
                # for new_ax_index in range(new_grid_size[0] * new_grid_size[1]):
                #     if new_ax_index in empty_axes_indices:
                #         # This axis is empty, skip it
                #         continue
 
                #     # Copy the contents of the old axis to the new axis
                #     old_ax = fig.axes[old_ax_index]
                #     old_ax_title = old_ax.get_title()
                #     old_ax_lines = old_ax.lines
                #     old_ax_patches = old_ax.patches
                #     old_ax_images = old_ax.images
                #     old_ax_collections = old_ax.collections
                #     old_ax_tables = old_ax.tables
                #     old_ax_legends = old_ax.legend()
                #     old_ax_texts = old_ax.texts

                #     new_ax = new_axes.flatten()[new_ax_index]
                #     new_ax.set_title(old_ax_title)
                #     for line in old_ax_lines:
                #         new_ax.add_line(line)
                #     for patch in old_ax_patches:
                #         new_patch = type(patch)(**patch.properties())
                #         new_patch.set_transform(new_ax.transData)
                #         new_ax.add_patch(new_patch)
                #     for image in old_ax_images:
                #         new_ax.add_image(image)
                #     for collection in old_ax_collections:
                #         new_ax.add_collection(collection)
                #     for table in old_ax_tables:
                #         new_ax.add_table(table)
                #     for legend in old_ax_legends:
                #         new_ax.add_artist(legend)
                #     for text in old_ax_texts:
                #         new_ax.add_artist(text)

                #     # Move to the next non-empty axis in the old figure
                #     old_ax_index += 1


                # Save the file to the interations folder 
                if _json: 
                    file_path = os.path.join(graph_dir, "JSON_grid.png") 
                else: 
                    file_path = os.path.join(graph_dir, "CODE_grid.png")  
                plt.savefig(file_path) 
                if self.do_show:
                    plt.show()
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
