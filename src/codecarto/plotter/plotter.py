import os
import math
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx
import random
import inspect


class Plotter:
    def __init__(
        self,
        dirs: dict[str, str] = None,
        file_path: str = "",
        labels: bool = False,
        grid: bool = False,
        json: bool = False,
        show_plot: bool = False,
        single_file: bool = False,
        ntx_layouts: bool = True,
        custom_layouts: bool = True,
    ):
        """Plots a graph using matplotlib and outputs the plots to the output directory.

        Parameters:
        -----------
            dirs (dict[str, str]) Default = None:
               The directories to use.
            file_path (str) Default = "":
               The path to the file to plot.
            labels (bool) Default = False:
                Whether or not to show the labels.
            grid (bool) Default = False:
                Whether or not to plot all layouts in a grid.
            json (bool) Default = False:
                Whether or not to return the json data.
            show_plot (bool) Default = False:
                Whether or not to show the plots.
            single_file (bool) Default = False:
                Whether or not to plot all layouts in a single file.
            ntx_layouts (bool) Default = True:
                Whether or not to include networkx layouts.
            custom_layouts (bool) Default = True:
               Whether or not to include custom layouts.
        """
        from .positions import Positions

        self.api: bool = False
        self.seed: dict[str, int] = {}
        self.dirs: dict[str, str] = dirs
        self.file_path: str = file_path
        self.labels: bool = labels
        self.grid: bool = grid
        self.json: bool = json
        self.show_plot: bool = show_plot
        self.single_file: bool = single_file
        self.ntx_layouts: bool = ntx_layouts
        self.custom_layouts: bool = custom_layouts
        self.layouts: tuple(str, function, list) = Positions(
            self.ntx_layouts, custom_layouts
        ).get_layouts()

    def set_plotter_attrs(
        self,
        dirs: dict[str, str] = None,
        file_path: str = "",
        labels: bool = False,
        grid: bool = False,
        json: bool = False,
        show_plot: bool = False,
        single_file: bool = False,
        ntx_layouts: bool = True,
        custom_layouts: bool = True,
    ):
        """Sets the plotter attributes.

        Parameters:
        -----------
            dirs (dict):
                The directories to use for the plotter.
            file_path (str):
                The file path to use for the plotter.
            labels (bool):
                Whether or not to show the labels.
            grid (bool):
                Whether or not to show the grid.
            json (bool):
                Whether or not to save the json file.
            show_plot (bool):
                Whether or not to show the plot.
            single_file (bool):
                Whether or not to save the plot to a single file.
            ntx_layouts (bool):
                Whether or not to save the plot to a networkx file.
            custom_layouts (bool):
                Whether or not to save the plot to a custom file.
        """
        self.dirs = dirs if dirs is not None else self.dirs
        self.file_path = file_path if file_path is not None else self.file_path
        self.labels = labels
        self.grid = grid
        self.json = json
        self.show_plot = show_plot
        self.single_file = single_file
        self.ntx_layouts = ntx_layouts
        self.custom_layouts = custom_layouts

    def plot(self, _graph: nx.DiGraph, specific_layout: str = ""):
        """Plots a graph using matplotlib.

        Parameters:
        -----------
            _graph (networkx.classes.graph.Graph):
                The graph to plot.
            _layout (str) Default = "":
                The layout to use.
        """
        # Check if graph provided
        if not _graph or not isinstance(_graph, nx.Graph):
            raise ValueError("No graph provided.")
        # Plot based on args
        if specific_layout != "":
            print(f"Plotting {specific_layout} layout...")
            self.plot_layout(_graph, specific_layout, self.json)
        elif self.grid:
            self.plot_all_in_grid(_graph, self.json)
        else:
            self.plot_all_separate(_graph, self.json)

    def plot_layout(self, _graph: nx.DiGraph, _layout: str, _json: bool = False):
        pass

    def plotting_progress(self):
        pass

    def plot_all_separate(self, _graph, _json: bool = False):
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
            from ..plotter.palette import Palette
            from ..cli.progressbar import ProgressBar

            # check if json
            if _json == False:
                graph_dir = self.dirs["graph_code_dir"]
            else:
                graph_dir = self.dirs["graph_json_dir"]

            # Create the overall progress bar
            overall_total: int = (
                len(self.layouts.items()) + 1
            )  # plus 1 for when the overall bar finishes
            progress_overall: ProgressBar = ProgressBar(
                overall_total, "  Plotting:", "Complete", extra_msg="Plotting..."
            )
            overall_line = (
                progress_overall.get_current_cursor_position()[1]
            ) - 1  # move back one line
            line_number: int = (
                overall_line + 2
            )  # plus 2 for where we want the children to start
            progress_overall.has_children = True
            progress_overall.current_line = (
                overall_line + 1
            )  # plus 1 to combat the -1 in first call of increment()
            max_layout_name_length: int = max(
                [len(layout_name) for layout_name in self.layouts.keys()]
            )
            # TODO: after creating sub progress bars set the line number - number of layouts for overall progress bar
            # TODO: May need to print blank lines equal to number of layouts to get the cursor to the correct position
            # TODO: Create the sub progress bars for each layout in dict, set line number for each layout

            # Loop through all layouts
            for layout_name, layout_info in self.layouts.items():
                # Unpack layout info
                layout, layout_params = layout_info
                progress_overall.increment()

                # Calculate ProgressBar total
                node_styles = Palette().get_node_styles()
                node_data: dict[str, list] = {
                    node_type: [] for node_type in node_styles.keys()
                }
                len_node_data: int = len(node_data.items())
                num_of_nodes: int = _graph.number_of_nodes()
                unique_node_types = set()
                for _, node_type in _graph.nodes(data="type"):
                    if node_type is not None:
                        unique_node_types.add(node_type)
                len_unigue_node_types: int = len(unique_node_types)
                len_layout_param: int = len(layout_params)
                param_len: int = 0
                for param in layout_params:
                    if param == "seed":
                        param_len += 1
                    elif param == "nshells" and layout_name == "shell_layout":
                        param_len += num_of_nodes + 1
                    elif param == "root" and layout_name == "cluster_layout":
                        param_len += num_of_nodes
                    elif param != "G":
                        param_len += 1
                progress_total: int = 8  # the number of .increment()s outside of loops
                progress_total += (
                    num_of_nodes
                    + len_layout_param
                    + param_len
                    + len_node_data
                    + len_unigue_node_types
                )  # various lengths of expected loops

                # Create progress bar extra messages
                extra_msg: dict[str, str] = {
                    "Start": "Starting Plot",
                    "Init": "Initializing Plot Figure",
                    "Nodes": "Collecting Graph Nodes",
                    "Layout": "Getting Layout Params",
                    "Position": "Computing Node Positions",
                    "GError": "Error: G is not planar",
                    "Loop": "Looping Node Shapes",
                    "Shapes": "Drawing Node Shapes",
                    "Edges": "Drawing Edges and Labels",
                    "Legend": "Drawing Legend",
                    "Filename": "Making Filename",
                    "Save": "Saving Plot File",
                    "Final": "Finished",
                }
                max_extra_msg_len: int = max([len(msg) for msg in extra_msg.values()])

                # create ProgressBar
                progress_plot: ProgressBar = ProgressBar(
                    progress_total,
                    f"    {layout_name:{max_layout_name_length}}:",
                    "Complete",
                    line_number=line_number,
                )
                progress_plot.increment(
                    extra_msg=f"{extra_msg['Start']:<{max_extra_msg_len}}"
                )

                # Initialize figure, axes (w, h), title, and position on monitor
                fig, ax = plt.subplots(figsize=(15, 15))
                fig.canvas.manager.window.wm_geometry("+0+0")
                _title: str = (
                    f"{str(layout_name).replace('_layout', '').capitalize()} Layout"
                )
                if self.single_file:
                    _file_name: str = os.path.basename(self.file_path)
                    _title = f"{_title} for '{_file_name}'"
                ax.set_title(_title)
                ax.axis("off")
                progress_plot.increment(
                    extra_msg=f"{extra_msg['Init']:<{max_extra_msg_len}}"
                )

                # Collect nodes and their attributes
                for n, a in _graph.nodes(data=True):
                    node_type = a.get("type", "Unknown")
                    if node_type not in node_styles.keys():
                        node_type = "Unknown"
                    node_data[node_type].append(n)
                    progress_plot.increment(
                        extra_msg=f"{extra_msg['Nodes']:<{max_extra_msg_len}}"
                    )

                # Get layout parameters
                seed = -1
                layout_kwargs = {"G": _graph}
                for param in layout_params:
                    if param == "seed":
                        if _json:
                            # Use the same seed for the same layout
                            seed = self.seed[layout_name]
                        else:
                            seed = random.randint(0, 1000)
                            self.seed[layout_name] = seed
                        layout_kwargs["seed"] = seed
                        progress_plot.increment(
                            extra_msg=f"{extra_msg['Layout']:<{max_extra_msg_len}}"
                        )
                    elif param == "nshells" and layout_name == "shell_layout":
                        # Group nodes by parent
                        grouped_nodes: dict[str, list] = {}
                        for node, data in _graph.nodes(data=True):
                            parent = data.get("parent", "Unknown")
                            if parent not in grouped_nodes:
                                grouped_nodes[parent] = []
                            grouped_nodes[parent].append(node)
                            progress_plot.increment(
                                extra_msg=f"{extra_msg['Layout']:<{max_extra_msg_len}}"
                            )
                        # Create the list of lists (shells)
                        shells = list(grouped_nodes.values())
                        layout_kwargs["nshells"] = shells
                        progress_plot.increment(
                            extra_msg=f"{extra_msg['Layout']:<{max_extra_msg_len}}"
                        )
                    elif param == "root" and layout_name == "cluster_layout":
                        # get the node at the very top
                        root = None
                        for node, data in _graph.nodes(data=True):
                            if data.get("label", "") == "root":
                                root = node
                                break
                            progress_plot.increment(
                                extra_msg=f"{extra_msg['Layout']:<{max_extra_msg_len}}"
                            )
                        layout_kwargs["root"] = root
                        progress_plot.increment(
                            extra_msg=f"{extra_msg['Layout']:<{max_extra_msg_len}}"
                        )
                    elif param != "G":
                        # TODO: Handle other parameters here
                        progress_plot.increment(
                            extra_msg=f"{extra_msg['Layout']:<{max_extra_msg_len}}"
                        )
                    progress_plot.increment(
                        extra_msg=f"{extra_msg['Layout']:<{max_extra_msg_len}}"
                    )

                # Compute layout positions
                progress_plot.increment(
                    extra_msg=f"{extra_msg['Position']:<{max_extra_msg_len}}"
                )
                try:
                    from .positions import Positions

                    layout_pos = Positions(
                        include_networkx=self.ntx_layouts,
                        include_custom=self.custom_layouts,
                    )
                    pos = layout_pos.get_positions(layout_name, **layout_kwargs)
                except Exception as e:
                    progress_plot.increment(
                        extra_msg=f"{extra_msg['GError']:<{max_extra_msg_len}}"
                    )
                    print()  # needs an extra line
                    continue

                # Draw nodes with different shapes
                progress_plot.increment(
                    extra_msg=f"{extra_msg['Loop']:<{max_extra_msg_len}}"
                )
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
                    progress_plot.increment(
                        extra_msg=f"{extra_msg['Shapes']:<{max_extra_msg_len}}"
                    )

                # Draw edges and labels
                progress_plot.increment(
                    extra_msg=f"{extra_msg['Edges']:<{max_extra_msg_len}}"
                )
                nx.drawing.draw_networkx_edges(_graph, pos, alpha=0.2)
                if self.labels:
                    nx.drawing.draw_networkx_labels(
                        _graph,
                        pos,
                        labels=nx.classes.get_node_attributes(_graph, "label"),
                        font_size=10,
                        font_family="sans-serif",
                    )

                # Draw legend
                _colors: dict = {}
                _shapes: dict = {}
                for node_type in unique_node_types:
                    _colors[node_type] = node_styles[node_type]["color"]
                    _shapes[node_type] = node_styles[node_type]["shape"]
                    progress_plot.increment(
                        extra_msg=f"{extra_msg['Legend']:<{max_extra_msg_len}}"
                    )
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
                progress_plot.increment(
                    extra_msg=f"{extra_msg['Filename']:<{max_extra_msg_len}}"
                )
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

                progress_plot.increment(
                    extra_msg=f"{extra_msg['Save']:<{max_extra_msg_len}}"
                )
                plt.tight_layout()
                plt.savefig(file_path)

                # Show the plot
                if self.show_plot:
                    if self.api:
                        import mpld3

                        mpld3.show()
                    else:
                        plt.show()
                        # Close the plot
                        plt.close()

                progress_plot.increment(
                    extra_msg=f"{extra_msg['Final']:<{max_extra_msg_len}}"
                )
                line_number += 1
                # TODO: loop through layout progress bars and decrement the start_line, call their 'increment' method after each loop with 'Final' message
            progress_overall.increment(extra_msg="Finished     ")

    def plot_all_in_grid(self, _graph, _json: bool = False):
        """
        Plots the given graph in a grid of subplots, one subplot for each layout.
        """

        # check if graph
        if _graph and isinstance(_graph, nx.classes.graph.Graph):
            from .palette import Palette

            # check if json
            if _json == False:
                graph_dir = self.dirs["graph_code_dir"]
            else:
                graph_dir = self.dirs["graph_json_dir"]

            print("Plotting grid...")

            # compute grid
            num_layouts = len(self.layouts)
            grid_size = math.ceil(math.sqrt(num_layouts))

            # Set the figure size
            figsize = (5, 5)
            fig, axes = plt.subplots(
                grid_size,
                grid_size,
                figsize=(figsize[0] * grid_size, figsize[1] * grid_size),
            )
            fig.set_size_inches(18.5, 9.5)

            # Set the figure position to the top-left corner of the screen plus the margin
            mng = plt.get_current_fig_manager()
            mng.window.wm_geometry("+0+0")

            # Loop through all layouts
            empty_axes_indices = []
            for layout_name, layout_info in self.layouts.items():
                layout, layout_params = layout_info

                # Set up ax
                ax = axes[idx // grid_size, idx % grid_size] if grid_size > 1 else axes
                ax.set_title(f"{layout_name}")
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

                # Get layout parameters
                seed = -1
                layout_kwargs = {"G": _graph}
                for param in layout_params:
                    if param == "seed":
                        if _json:
                            # Use the same seed for the same layout
                            seed = self.seed[layout_name]
                        else:
                            seed = random.randint(0, 1000)
                            self.seed[layout_name] = seed
                        layout_kwargs["seed"] = seed
                    elif param == "nshells" and layout_name == "shell_layout":
                        # Group nodes by parent
                        grouped_nodes: dict[str, list] = {}
                        for node, data in _graph.nodes(data=True):
                            parent = data.get("parent", "Unknown")
                            if parent not in grouped_nodes:
                                grouped_nodes[parent] = []
                            grouped_nodes[parent].append(node)

                        # Create the list of lists (shells)
                        shells = list(grouped_nodes.values())
                        layout_kwargs["nshells"] = shells
                    elif param != "G":
                        # TODO: Handle other parameters here
                        pass

                # Compute Layout
                try:
                    from .positions import Positions

                    layout_pos = Positions(
                        include_networkx=self.ntx_layouts,
                        include_custom=self.custom_layouts,
                    )
                    pos = layout_pos.get_positions(layout_name, **layout_kwargs)
                except Exception as e:
                    print(f"Skipping {layout_name} due to an error: {e}")
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
                if self.labels:
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

            if not self.api:
                # Save the file to the interations folder
                if _json:
                    file_path = os.path.join(graph_dir, "JSON_grid.png")
                else:
                    file_path = os.path.join(graph_dir, "CODE_grid.png")

                plt.savefig(file_path)

                # Show plot
                if self.show_plot:
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
