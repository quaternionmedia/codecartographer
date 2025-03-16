import networkx as nx
from typing import Callable

from models.plot_data import LayoutType


########################   OLD CODE   ########################
class Positions:
    def __init__(self, include_networkx: bool = True, include_custom: bool = True):
        """Constructor for Layouts

        Parameters
        ----------
        layouts : tuple(str,function,list)
            A tuple of layout_names, the layout_function, and their attributes
        """
        self._layouts: list[LayoutType] = []
        if include_networkx:
            self.add_networkx_layouts()
        if include_custom:
            self.add_custom_layouts()

    def add_layout(self, name: str, layout: Callable, attr: list) -> None:
        """Add a layout to the list of available layouts

        Parameters
        ----------
        name : str
            The name of the layout
        layout : function
            The layout function
        attr : list
            The attributes of the layout
        """
        layoutType: LayoutType = LayoutType()
        layoutType["name"] = name
        layoutType["func"] = layout
        layoutType["params"] = attr
        self._layouts.append(layoutType)

    def add_networkx_layouts(self) -> None:
        """Add all networkx layouts to the list of available layouts"""
        self.add_layout(
            "spring_layout",
            nx.layout.spring_layout,
            ["graph", "seed"],
        )
        self.add_layout("spiral_layout", nx.layout.spiral_layout, ["graph"])
        self.add_layout("circular_layout", nx.layout.circular_layout, ["graph"])
        self.add_layout("random_layout", nx.layout.random_layout, ["graph", "seed"])
        self.add_layout("spectral_layout", nx.layout.spectral_layout, ["graph"])
        self.add_layout("shell_layout", nx.layout.shell_layout, ["graph", "nshells"])
        self.add_layout("kamada_kawai_layout", nx.layout.kamada_kawai_layout, ["graph"])
        # self.add_layout("planar_layout", nx.layout.planar_layout, ["graph"])

    def add_custom_layouts(self) -> None:
        """Add all custom layouts to the list of available layouts"""
        from models.custom_layouts.sorted_square_layout import sorted_square_layout

        self.add_layout("sorted_square_layout", sorted_square_layout, ["graph"])

        # from .custom_layouts.cluster_layout import cluster_layout
        # self.add_layout("cluster_layout", cluster_layout, ["graph", "root"])

    def get_layout_names(self) -> list:
        """Get all layout names from the list of available layouts

        Returns
        -------
        list
            The name of available layouts
        """
        return [layout["name"] for layout in self._layouts]

    def get_layouts(self) -> list:
        """Get all layouts with their attributes from the list of available layouts

        Returns
        -------
        list[LayoutType]:
            The layouts with their attributes
        """
        return self._layouts

    def get_layout(self, name: str) -> LayoutType:
        """Get a layout from the list of available layouts

        Parameters
        ----------
        name : str
            The name of the layout

        Returns
        -------
        dict (LayoutType):
            The layout with its attributes
        """
        # Check if the provided name in list (_layouts: list[LayoutType])
        for layout in self._layouts:
            if layout["name"] == name:
                return layout
        # if here then layout not found
        raise ValueError(f"Layout {name} does not exist")

    def get_layout_params(self, name: str) -> list:
        """Get the parameters of a layout from the list of available layouts

        Parameters
        ----------
        name : str
            The name of the layout

        Returns
        -------
        list
            The parameters of the layout
        """
        # Check if the provided name in list (_layouts: list[LayoutType])
        for layout in self._layouts:
            if layout["name"] == name:
                return layout["params"]

        # if here then layout not found
        raise ValueError(f"Layout {name} does not exist")

    def get_positions(self, name: str, seed: int = -1, **kwargs) -> dict:
        """Get a positions from the list of available layouts

        Parameters
        ----------
        name : str
            The name of the layout
        seed : int (optional, default=-1)
            The seed to use for the layout
        **kwargs : dict
            The attributes of the layout

        Returns
        -------
        dict
            The positions of the layout
        """
        _graph: nx.Graph = kwargs.get("G", None)
        # get the layout function
        layout_func: Callable
        layout_params: list

        for layout in self._layouts:
            if layout["name"] == name:
                layout_func = layout["func"]
                layout_params = layout["params"]
                break
        layout_kwargs: dict = {}

        for param in layout_params:
            if param == "seed" and seed != -1:
                # Set the seed if it is not -1
                layout_kwargs["seed"] = seed
            elif param == "nshells" and name == "shell_layout":
                # Group nodes by parent
                if "G" not in kwargs:
                    grouped_nodes: dict[str, list] = {}
                    for node, data in kwargs["G"].nodes(data=True):
                        parent = data.get("parent", "Unknown")
                        if parent not in grouped_nodes:
                            grouped_nodes[parent] = []
                        grouped_nodes[parent].append(node)
                    # Create the list of lists (shells)
                    shells = list(grouped_nodes.values())
                    layout_kwargs["nshells"] = shells
            elif param == "root" and name == "cluster_layout":
                # Set the root node
                layout_kwargs["root"] = kwargs["root"]
            elif param != "G":
                # TODO Handle other parameters here
                pass

        return layout_func(G=_graph, **layout_kwargs)

    def get_node_positions(self, graph: nx.DiGraph, layout_name: str):
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
        seed = -1
        layout_params = self.get_layout_params(layout_name)
        layout_kwargs: dict = {"G": graph}
        for param in layout_params:
            if param == "seed":
                import random

                seed = random.randint(0, 1000)
                layout_kwargs["seed"] = seed
            elif param == "prog" and layout_name == "dot_layout":
                # Set the program to use for graphviz
                layout_kwargs["prog"] = "dot"
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
        pos: dict = self.get_positions(layout_name, **layout_kwargs)
        return pos
