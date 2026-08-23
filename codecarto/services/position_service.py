import networkx as nx
from typing import Callable

from codecarto.models.plot_data import LayoutType


########################   OLD CODE   ########################
def layout_key(name: str) -> str:
    """A layout name as the registry spells it.

    **A DISPLAY NAME AND A REGISTRY KEY ARE TWO THINGS.** Callers build the key
    as `layout.lower() + "_layout"`, so `Kamada Kawai` -- the obvious way to
    write it in a menu -- became `kamada kawai_layout` and failed several
    frames deep with a message naming a layout nobody typed. Spaces and hyphens
    normalise to underscores, and an already-suffixed name is left alone, so
    every spelling of one layout reaches the same entry.
    """
    cleaned = str(name or "").strip().lower().replace(" ", "_").replace("-", "_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    if not cleaned:
        return ""
    return cleaned if cleaned.endswith("_layout") else f"{cleaned}_layout"


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
        from codecarto.models.custom_layouts.sorted_square_layout import sorted_square_layout
        from codecarto.models.custom_layouts.compound_layout import compound_layout

        self.add_layout("sorted_square_layout", sorted_square_layout, ["graph"])
        self.add_layout("compound_layout", compound_layout, ["graph"])

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
        wanted = layout_key(name)
        for layout in self._layouts:
            if layout["name"] == name or layout["name"] == wanted:
                return layout["params"]

        # If here the layout really is not registered. Name what does exist:
        # the old message gave only the mangled string, which sent readers
        # looking for a layout nobody had asked for.
        known = ", ".join(sorted(str(l["name"]) for l in self._layouts))
        raise ValueError(
            f"Layout {name!r} does not exist (looked for {wanted!r}). "
            f"Registered: {known}")

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

        # Same tolerance as `get_layout_params`, and the same reason: a display
        # name is not a registry key. **AND AN UNKNOWN LAYOUT RAISES HERE.**
        # Before this, no match left `layout_func` and `layout_params` unbound
        # and the next line failed with `UnboundLocalError` -- a message about
        # a local variable, for a caller who chose a layout that is not
        # registered.
        wanted = layout_key(name)
        layout_func = None
        layout_params = []
        for layout in self._layouts:
            if layout["name"] == name or layout["name"] == wanted:
                layout_func = layout["func"]
                layout_params = layout["params"]
                break
        if layout_func is None:
            known = ", ".join(sorted(str(l["name"]) for l in self._layouts))
            raise ValueError(
                f"Layout {name!r} does not exist (looked for {wanted!r}). "
                f"Registered: {known}")
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
            elif param != "G":
                # TODO: Handle other parameters here
                pass

        # Compute layout positions
        pos: dict = self.get_positions(layout_name, **layout_kwargs)
        return pos
