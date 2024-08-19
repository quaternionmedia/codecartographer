import math
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import mpld3
import networkx as nx
import random


class Plotter:
    def __init__(
        self,
        graph: nx.DiGraph = None,
        labels: bool = False,
        grid: bool = False,
        ntx_layouts: bool = True,
        custom_layouts: bool = True,
        palette_dict: dict = None,
    ):
        """Plots a graph using matplotlib and outputs the plots to the output directory.

        Parameters:
        -----------
            graph (networkx.DiGraph) Default = None:
                The graph to plot.
            labels (bool) Default = False:
                Whether or not to show the labels.
            grid (bool) Default = False:
                Whether or not to plot all layouts in a grid.
            ntx_layouts (bool) Default = True:
                Whether or not to include networkx layouts.
            custom_layouts (bool) Default = True:
                Whether or not to include custom layouts.
            palette_dict (dict) Default = None:
                The palette to use.
        """
        from .palette import Palette
        from .positions import Positions

        if not graph:
            raise ValueError("No graph provided.")
        self.graph: nx.DiGraph = graph
        self.labels: bool = labels
        self.grid: bool = grid
        self.seed: dict[str, int] = {}  # layout_name: seed
        self.ntx_layouts: bool = ntx_layouts
        self.custom_layouts: bool = custom_layouts
        self.layouts: list[dict] = Positions(
            self.ntx_layouts, self.custom_layouts
        ).get_layouts()
        self.palette_dict: dict = palette_dict
        # if palette_dict is None uses default in Palette
        self.palette: Palette = Palette(palette_dict)
        self.node_styles: dict = self.palette.get_node_styles()
        self.unique_node_types: set = set()
        self.node_data: dict[str, list] = self.set_node_data()

    def set_plotter_attrs(
        self,
        graph: nx.DiGraph = None,
        labels: bool = False,
        grid: bool = False,
        ntx_layouts: bool = True,
        custom_layouts: bool = True,
        palette_dict: dict = None,
    ):
        """Change the attributes of an already initiated Plotter object.

        Parameters:
        -----------
            graph (networkx.DiGraph):
                The graph to plot.
            labels (bool):
                Whether or not to show the labels.
            grid (bool):
                Whether or not to show the grid.
            ntx_layouts (bool):
                Whether or not to save the plot to a networkx file.
            custom_layouts (bool):
                Whether or not to save the plot to a custom file.
            palette_dict (dict):
                The palette to use.
        """
        from .palette import Palette
        from .positions import Positions, Layout

        # Graph
        if not graph and not self.graph:
            raise ValueError("No graph provided.")
        self.graph: nx.DiGraph = graph if graph is not None else self.graph

        # Bools
        self.labels: bool = labels if labels is not None else self.labels
        self.grid: bool = grid if grid is not None else self.grid

        # Layouts
        self.seed: dict[str, int] = {}  # layout_name: seed
        self.ntx_layouts: bool = (
            ntx_layouts if ntx_layouts is not None else self.ntx_layouts
        )
        self.custom_layouts: bool = (
            custom_layouts if custom_layouts is not None else self.custom_layouts
        )
        self.layouts: list[dict] = Positions(
            self.ntx_layouts, self.custom_layouts
        ).get_layouts()

        # Palette
        self.palette_dict: dict = (
            palette_dict if palette_dict is not None else self.palette_dict
        )
        self.palette: Palette = Palette(palette_dict)
        self.node_styles: dict = self.palette.get_node_styles()
        self.unique_node_types: set = set()
        self.node_data: dict[str, list] = self.set_node_data()

    def plot(
        self,
        graph: nx.DiGraph = None,
        layout_name: str = "",
        grid: bool = False,
    ) -> list[str]:
        """Plots a graph using matplotlib.

        Parameters:
        -----------
            graph (networkx.DiGraph) Default = None:
                The graph to plot.
                    Can use this to overwrite the Plotter object's graph attribute.
            layout_name (str) Default = "":
                The name of the layout to use. Will return only the specified layout.
                    Leave blank to return all layouts.
            grid (bool) Default = False:
                Whether or not to plot all layouts in a grid. Will return only the grid plot with all layouts.
                    Can use this to overwrite the Plotter object's grid attribute.

        Returns:
        --------
            plots (list[str]):
                The plots as html strings.
        """
        # Check graph
        if graph and isinstance(graph, nx.DiGraph):
            self.graph = graph
        elif not self.graph or not isinstance(self.graph, nx.DiGraph):
            raise ValueError("No graph provided or is not valid.")

        # Check layout
        if layout_name != "":
            try:
                from .positions import Positions, LayoutType

                # set self.layouts to the specified layout
                # will make it so we only plot the specified layout
                position: Positions = Positions()
                _layout: LayoutType = position.get_layout(layout_name)
                self.layouts = [_layout]
            except:
                raise ValueError("Layout does not exist.")

        # Start the plotting
        # If grid, setup the figure and axes before loop
        self.grid = grid
        if self.grid:
            num_layouts = len(self.layouts)
            grid_size = math.ceil(math.sqrt(num_layouts))
            figwh = (5, 5)
            figs = (figwh[0] * grid_size, figwh[1] * grid_size)

            fig, axs = plt.subplots(
                grid_size,
                grid_size,
                figsize=figs,
            )
            fig.set_size_inches(18.5, 9.5)  # TODO: try to size in css

        idx: int = 0
        ax: plt.Axes = None
        plots: list[str] = []
        # loop through self.layouts list of dictionaries
        for layout in self.layouts:
            layout_name = layout["name"]
            # Set up the ax for the figure
            if self.grid:
                # Figure has been created already
                # Get the ax for the subplot in the figure
                ax = axs[idx // grid_size, idx % grid_size] if grid_size > 1 else axs
                idx += 1
            else:
                # Only one plot per figure
                fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(5, 5))
            ax.axis("off")
            ax.set_title(
                f"{str(layout_name).replace('_layout', '').capitalize()} Layout"
            )

            # Get node positions for layout
            pos: dict = self.get_node_positions(layout_name)

            # Draw the plot
            self.draw_plot(ax, pos)

            # If not a grid, append the plot to the list
            if not self.grid:
                plt.tight_layout()
                plot_html: str = mpld3.fig_to_html(fig)
                plots.append(plot_html)
                plt.close()

        # If grid, append the one plot to the list
        if self.grid:
            plt.tight_layout()
            plot_html = mpld3.fig_to_html(
                fig,
                template_type="simple",
                figid="figid",
                d3_url=None,
                no_extras=False,
                use_http=False,
                include_libraries=True,
            )
            plots.append(plot_html)
            plt.close()

        return plots

    def plotting_progress(self) -> float:
        """Calculates the progress of the current plotting.

        Returns:
        --------
            progress (float):
                The progress of the current plotting.
        """
        # TODO: could be used to return the percentage of the plotting progress
        # would need to track position during plot and compare against a total
        # these would need to be established before plotting

        # progress_total = self.calculate_progress_total()
        pass

    def calculate_progress_total(self) -> float:
        """Calculates the total number of steps needed to plot the graph.

        Returns:
        --------
            total (float):
                The total number of steps.
        """
        # TODO: calc total based on number of layouts and number of nodes
        # and the type of layouts, some layous need to loop graph a second time
        # also if labels are involved, if edges are involved, legend, etc.
        pass

    def set_node_data(self) -> dict:
        """Sets the node data for the Plotter object."""
        # Collect the node data and unique node types
        self.node_data = {node_type: [] for node_type in self.node_styles.keys()}
        self.unique_node_types = set()  # clear the set

        for n, a in self.graph.nodes(data=True):
            node_type = a.get("type", "Unknown")  # if no type, set to Unknown
            if node_type and (node_type not in self.unique_node_types):
                # could be duplicates in self.node_styles
                self.unique_node_types.add(node_type)
            if node_type not in self.node_styles.keys():
                node_type = "Unknown"
            self.node_data[node_type].append(n)

    def draw_plot(self, ax: plt.Axes, pos: dict):
        """Draws the nodes, edges, labels and legend.

        Parameters:
        -----------
            ax (plt.Axes):
                The axes to draw on.
            pos (dict):
                The positions of the nodes.
        """
        # Draw nodes with different attrs
        for node_type, nodes in self.node_data.items():
            nx.drawing.draw_networkx_nodes(
                self.graph,
                pos,
                nodelist=nodes,
                node_color=self.node_styles[node_type]["color"],
                node_shape=self.node_styles[node_type]["shape"],
                node_size=self.node_styles[node_type]["size"],
                alpha=self.node_styles[node_type]["alpha"],
                ax=ax,
            )

        # Draw edges and labels
        nx.drawing.draw_networkx_edges(self.graph, pos, alpha=0.2, ax=ax)
        if self.labels:
            nx.drawing.draw_networkx_labels(
                self.graph,
                pos,
                labels=nx.classes.get_node_attributes(self.graph, "label"),
                font_size=10,
                font_family="sans-serif",
                ax=ax,
            )

        # Create legend
        _colors: dict = {}
        _shapes: dict = {}
        for node_type in self.unique_node_types:
            _colors[node_type] = self.node_styles[node_type]["color"]
            _shapes[node_type] = self.node_styles[node_type]["shape"]
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
            for theme, color, shape in zip(_colors, _colors.values(), _shapes.values())
        ]
        ax.legend(handles=legend_elements, loc="upper right", fontsize=10)

    ################## PLOT ##################
    def grav_single_plot(
        self,
        graph: nx.DiGraph,
        title: str = "Sprial",
        file_name: str = "Fib Demo",
    ) -> str:
        """Plot a graph.

        Parameters:
        -----------
        graph : nx.DiGraph
            The graph to plot.
        title : str
            The name of the layout to plot.
                Used to plot a single layout.
        file_name : str
            The name of the file to plot.

        Returns:
        --------
        dict
            The results of the plot. {index: plot html}
        """
        import gravis as gv

        # get the positions
        pos = self.get_node_positions(graph, f"{title.lower()}_layout")

        # add the positions to the graph
        for name, (x, y) in pos.items():
            node = graph.nodes[name]
            node["x"] = float(x) * 100
            node["y"] = float(y) * 100

        # create the figure
        fig = gv.d3(
            graph,
            zoom_factor=2,
            graph_height=550,
            show_menu=True,
            show_details_toggle_button=False,
            node_label_data_source="label",
            edge_label_data_source="label",
            node_hover_neighborhood=True,
        )

        # convert to html
        results = fig.to_html_partial()
        return results

    def single_plot(
        self,
        graph: nx.DiGraph,
        title: str = "Sprial",
        file_name: str = "Fib Demo",
    ) -> str:
        """Plot a graph.

        Parameters:
        -----------
        graph : nx.Graph
            The graph to plot.
        title : str
            The name of the layout to plot.
                Used to plot a single layout.
        file_name : str
            The name of the file to plot.

        Returns:
        --------
        dict
            The results of the plot. {index: plot html}
        """
        # create a simple plot
        fig, ax = plt.subplots(figsize=(15, 10))
        ax.set_title(f"{title} Layout for '{file_name}'")
        ax.set_axis_off()

        # positions
        pos = self.get_node_positions(graph, f"{title.lower()}_layout")

        # nodes
        nx.drawing.draw_networkx_nodes(
            graph,
            pos,
            nodelist=graph.nodes,
            ax=ax,
        )

        # labels
        nx.drawing.draw_networkx_labels(
            graph,
            pos,
            labels=nx.get_node_attributes(graph, "label"),
            font_size=12,
            font_color="black",
            ax=ax,
        )

        # edges
        nx.drawing.draw_networkx_edges(
            graph,
            pos,
            edgelist=graph.edges,
            width=2,
            alpha=0.5,
            edge_color="black",
            ax=ax,
        )

        # convert to html
        plt.tight_layout()
        plot_html = mpld3.fig_to_html(
            fig,
            template_type="simple",
            figid="pltfig",
            d3_url=None,
            no_extras=False,
            use_http=False,
            include_libraries=True,
        )
        return plot_html

    def grid_plot(self, graph: nx.DiGraph) -> str:
        import math

        layouts: list[str] = [
            "circular",
            "spiral",
            "spring",
            "shell",
            "spectral",
            # "sorted_Square",
        ]

        # create a grid plot
        num_layouts = len(layouts)
        grid_size = math.ceil(math.sqrt(num_layouts))

        fig, axs = plt.subplots(
            grid_size,
            grid_size,
            figsize=(grid_size * 15, grid_size * 10),
        )
        fig.set_size_inches(18.5, 9.5)  # TODO: try to size in css

        idx: int = 0
        for layout_name in layouts:
            # ax
            ax = axs[idx // grid_size, idx % grid_size] if grid_size > 1 else axs
            ax.set_title(f"{str(layout_name).capitalize()} Layout")

            # positions
            pos = self.get_node_positions(graph, f"{layout_name.lower()}_layout")

            # nodes
            nx.drawing.draw_networkx_nodes(
                graph,
                pos,
                nodelist=graph.nodes,
                ax=ax,
            )

            idx += 1

            # labels
            nx.drawing.draw_networkx_labels(
                graph,
                pos,
                labels=nx.get_node_attributes(graph, "label"),
                font_size=12,
                font_color="black",
                ax=ax,
            )

            # edges
            nx.drawing.draw_networkx_edges(
                graph,
                pos,
                edgelist=graph.edges,
                width=2,
                alpha=0.5,
                edge_color="black",
                ax=ax,
            )

        # convert to html
        plt.tight_layout()
        plot_html = mpld3.fig_to_html(
            fig,
            template_type="simple",
            figid="pltfig",
            d3_url=None,
            no_extras=False,
            use_http=False,
            include_libraries=True,
        )
        return plot_html

    def get_node_positions(self, graph: nx.DiGraph, layout_name: str) -> dict:
        """Gets the node positions for a given layout.

        Parameters:
        -----------
            graph (nx.DiGraph):
                The graph to plot.
            layout_name (str):
                The name of the layout.

        Returns:
        --------
            positions (dict):
                The positions of nodes for layout.
        """
        from src.plotter.positions import Positions

        position = Positions(True, True)
        seed = -1
        layout_params = position.get_layout_params(layout_name)
        layout_kwargs: dict = {"G": graph}
        for param in layout_params:
            if param == "seed":
                import random

                seed = random.randint(0, 1000)
                layout_kwargs["seed"] = seed
            elif param == "nshells" and layout_name == "shell_layout":
                # Group nodes by parent
                grouped_nodes: dict[str, list] = {}
                for node, data in graph.nodes(data=True):
                    parent = data.get("parent", "Unknown")
                    if parent not in grouped_nodes:
                        grouped_nodes[parent] = []
                    grouped_nodes[parent].append(node)
                # Create the list of lists (shells)
                shells = list(grouped_nodes.values())
                layout_kwargs["nshells"] = shells
            elif param == "root" and layout_name == "cluster_layout":
                # get the node at the very top
                root = None
                for node, data in graph.nodes(data=True):
                    if data.get("label", "") == "root":
                        root = node
                        break
                layout_kwargs["root"] = root
            elif param != "G":
                # TODO: Handle other parameters here
                pass

        # Compute layout positions
        pos: dict = position.get_positions(layout_name, **layout_kwargs)
        return pos


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
