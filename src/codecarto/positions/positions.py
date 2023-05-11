import networkx as nx
from typing import Callable


class LayoutPositions:
    def __init__(self, include_networkx: bool = True, include_custom: bool = True):
        """Constructor for Layouts

        Parameters
        ----------
        layouts : tuple(str,function,list)
            A tuple of layout_names, the layout_function, and their attributes
        """
        self._layouts: tuple(str, function, list) = {}
        if include_networkx:
            self.add_networkx_layouts()
        if include_custom:
            self.add_custom_layouts()

    def add_layout(self, name: str, layout: Callable, attr: list):
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
        self._layouts[name] = (layout, attr)

    def add_networkx_layouts(self):
        """Add all networkx layouts to the list of available layouts"""
        self.add_layout(
            "spring_layout",
            nx.layout.spring_layout,
            ["graph", "seed"],
        )
        self.add_layout("spiral_layout", nx.layout.spiral_layout, ["graph"])
        self.add_layout("circular_layout", nx.layout.circular_layout, ["graph"])
        self.add_layout("random_layout", nx.layout.random_layout, ["graph", "seed"])
        # self.add_layout(
        #     "kamada_kawai_layout",
        #     nx.layout.kamada_kawai_layout,
        #     ["graph", "iterations"],
        # )
        self.add_layout("shell_layout", nx.layout.shell_layout, ["graph", "nshells"])
        self.add_layout("spectral_layout", nx.layout.spectral_layout, ["graph"])
        self.add_layout("planar_layout", nx.layout.planar_layout, ["graph"])

    def add_custom_layouts(self):
        """Add all custom layouts to the list of available layouts"""
        from .custom_layouts import grid_layout

        self.add_layout("grid_layout", grid_layout, ["graph"])

    def get_layout_names(self):
        """Get all layout names from the list of available layouts

        Returns
        -------
        list
            The name of available layouts
        """
        return self._layouts.keys()

    def get_layouts(self):
        """Get all layouts with their attributes from the list of available layouts

        Returns
        -------
        list[tuple(name,function,attributes)]
            The layouts with their attributes
        """
        return self._layouts

    def get_layout(self, name: str):
        """Get a layout from the list of available layouts

        Parameters
        ----------
        name : str
            The name of the layout

        Returns
        -------
        tuple(str,function,list)
            The layout with its attributes
        """
        return self._layouts[name]

    # def get_positions(self, name: str, graph: nx.Graph, **kwargs):
    #     """Get a positions from the list of available layouts

    #     Parameters
    #     ----------
    #     name : str
    #         The name of the layout
    #     graph : nx.Graph
    #         The graph to apply the layout to
    #     **kwargs : dict
    #         The attributes of the layout

    #     Returns
    #     -------
    #     dict
    #         The positions of the layout
    #     """
    #     return self._layouts[name][0](graph, **kwargs)

    def get_positions(self, name: str, seed: int = -1, **kwargs):
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
        layout, layout_params = self._layouts[name]
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
            elif param != "G":
                # TODO Handle other parameters here
                pass
        return layout(G=_graph, **layout_kwargs)
