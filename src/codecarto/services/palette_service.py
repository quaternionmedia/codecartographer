import networkx as nx

from models.plot_data import DefaultPalette

########################   OLD CODE   ########################

# this is the default palette in the package
# when containerized, we'll be looking in the container's /app directory
# can see DockerFile for more info


class Palette:
    """A class to manage the plotter palette."""

    def __init__(self, palette: dict = {}):
        """Initialize a palette.

        Parameters:
        -----------
        palette : dict (optional) (default=None)
            A dictionary containing the data of the palette to initialize.
        """
        if palette and isinstance(palette, dict) and palette != {}:
            self.palette: dict[str, dict] = palette
        else:
            self.palette: dict[str, dict] = DefaultPalette.dict()

    def create_new_theme(
        self,
        node_type: str,
        base: str,
        label: str,
        shape: str,
        color: str,
        size: float,
        alpha: float,
    ) -> dict:
        """Create a new theme with the specified parameters.

        Parameters:
        -----------
        node_type : str
            The type of node for which to create a new theme.
        label : str
            The label of the nodes in the new theme.
        shape : str
            The shape of the nodes in the new theme.
        color : str
            The color of the nodes in the new theme.
        size : float
            The size of the nodes in the new theme.
        alpha : float
            The alpha (transparency) value of the nodes in the new theme.

        Returns:
        --------
        dict
            The palette.
        """
        _base: str = base

        # check if node type already exists
        if node_type in self.palette["bases"].keys():
            # update existing base for the node type
            _base = self.palette["bases"][node_type]
        else:
            # add new node type to palette
            self.palette["bases"][node_type] = _base

        # save base attrs to palette file
        self.palette["labels"][_base] = label
        self.palette["shapes"][_base] = shape
        self.palette["colors"][_base] = color
        self.palette["sizes"][_base] = size
        self.palette["alphas"][_base] = alpha

        # return the palette
        return self.palette

    def get_node_styles(self, type: str = "") -> dict:
        """Get the styles for all node types.

        Parameters:
        -----------
        type : str (optional) (default=None)
            If specified, only the style for the specified node type will be returned.

        Returns:
        --------
        dict[node_type(str), styles(dict)]
            A dictionary containing the styles for all node types, or a specfied type.
        """
        if type:
            _base = self.palette["bases"][type]
            return {
                type: {
                    "base": _base,
                    "label": self.palette["labels"][_base],
                    "shape": self.palette["shapes"][_base],
                    "color": self.palette["colors"][_base],
                    "size": self.palette["sizes"][_base],
                    "alpha": self.palette["alphas"][_base],
                }
            }
        else:
            styles = {}
            for node_type in self.palette["bases"].keys():
                _base = self.palette["bases"][node_type]
                styles[node_type] = {
                    "base": _base,
                    "label": self.palette["labels"][_base],
                    "shape": self.palette["shapes"][_base],
                    "color": self.palette["colors"][_base],
                    "size": self.palette["sizes"][_base],
                    "alpha": self.palette["alphas"][_base],
                }
            return styles

    def get_palette_data(self) -> dict[str, dict]:
        """Get the data of the current palette.

        Returns:
        --------
        dict
            A dictionary containing the data of the current palette.
        """
        return {
            "bases": self.palette["bases"],
            "labels": self.palette["labels"],
            "shapes": self.palette["shapes"],
            "colors": self.palette["colors"],
            "sizes": self.palette["sizes"],
            "alphas": self.palette["alphas"],
        }


# TOOD: this is temporary until we define more in palette.py
def apply_styles(graph: nx.DiGraph) -> nx.DiGraph:
    node_styles = {
        # "interactive": visitor.interactives,
        # "expression": visitor.expressions,
        "function": {"color": "#99ff99", "shape": "rectangle"},
        "asyncfunction": {"color": "#99ff99", "shape": "rectangle"},
        "class": {"color": "#ff9999", "shape": "ellipse"},
        # "return": visitor.returns,
        # "delete": visitor.deletes,
        # "assign": visitor.assigns,
        # "typealias": visitor.typealiases,
        # "augassign": visitor.augassigns,
        # "annassign": visitor.annassigns,
        # "forloop": visitor.forloops,
        # "asyncforloop": visitor.asyncforloops,
        # "whileloop": visitor.whileloops,
        # "if": visitor.ifs,
        # "with": visitor.withs,
        # "asyncwith": visitor.asyncwiths,
        # "match": visitor.matches,
        # "raise": visitor.raises,
        # "try": visitor.trys,
        # "trystar": visitor.trystars,
        # "assert": visitor.asserts,
        "import": {"color": "#9999ff", "shape": "diamond"},
        "importfrom": {"color": "#9999ff", "shape": "diamond"},
        # "global": visitor.globals,
        # "nonlocal": visitor.nonlocals,
        # "expr": visitor.exprs,
        # "pass": visitor.passes,
        # "break": visitor.breaks,
        # "continue": visitor.continues,
        # "boolop": visitor.boolops,
        # "namedexpr": visitor.namedexprs,
        # "binop": visitor.binops,
        # "unaryop": visitor.uarynops,
        # "lambda": visitor.lambdas,
        # "ifexp": visitor.ifexps,
        # "dict": visitor.dicts,
        # "set": visitor.sets,
        # "listcomp": visitor.listcomps,
        # "setcomp": visitor.setcomps,
        # "dictcomp": visitor.dictcomps,
        # "generatorexp": visitor.generatorexps,
        # "await": visitor.awaits,
        # "yield": visitor.yields,
        # "yieldfrom": visitor.yieldfroms,
        # "comparison": visitor.comparisons,
        # "call": visitor.calls,
        # "formattedvalue": visitor.formattedvalues,
        # "joinedstr": visitor.joinedstrs,
        # "constant": visitor.constats,
        # "attribute": visitor.attribuetes,
        # "subscript": visitor.subscripts,
        # "starred": visitor.starreds,
        # "name": visitor.names,
        # "list": visitor.lists,
        # "tuple": visitor.tuples,
        # "slice": visitor.slices,
        # "load": visitor.loads,
        # "store": visitor.stores,
        # "del": visitor.dels,
        # "and": visitor.ands,
        # "or": visitor.ors,
        # "add": visitor.adds,
        # "sub": visitor.subs,
        # "mult": visitor.mults,
        # "matmult": visitor.matmults,
        # "div": visitor.divs,
        # "mod": visitor.mods,
        # "pow": visitor.pows,
        # "lshift": visitor.lshifts,
        # "rshift": visitor.rshifts,
        # "bitor": visitor.bitors,
        # "bitxor": visitor.bitxors,
        # "bitand": visitor.bitands,
        # "floordiv": visitor.floordivs,
        # "invert": visitor.inverts,
        # "not": visitor.nots,
        # "uadd": visitor.uaddss,
        # "usub": visitor.usubss,
        # "eq": visitor.eqss,
        # "not_eq": visitor.not_eqss,
        # "lt": visitor.lts,
        # "lte": visitor.ltes,
        # "gt": visitor.gts,
        # "gte": visitor.gtes,
        # "is": visitor.iss,
        # "isnot": visitor.isnots,
        # "in": visitor.ins,
        # "notin": visitor.notins,
        # "excepthandler": visitor.excepthandlers,
        # "matchvalue": visitor.matchvalues,
        # "matchsingleton": visitor.matchsingleton,
        # "matchsequence": visitor.matchsequences,
        # "matchmapping": visitor.matchmappings,
        # "matchclass": visitor.matchclasses,
        # "matchstar": visitor.matchstars,
        # "matchas": visitor.matchases,
        # "machor": visitor.machors,
        # "typeignore": visitor.typeignores,
        # "typevar": visitor.typevars,
        # "paramspec": visitor.paramspecs,
        # "typevartuple": visitor.typevartuples,
        # "relation": visitor.relations,
        "variables": {"color": "#009999", "shape": "rectangle"},
        "module": {"color": "#ffff99", "shape": "rectangle"},
        "default": {"color": "#0c0c44", "shape": "circle"},
    }

    edge_styles = {
        "inheritance": {"color": "#990066", "line_style": "solid"},
        "import": {"color": "#005500", "line_style": "dashed"},
        "variable": {"color": "#000055", "line_style": "dotted"},
        "function": {"color": "#550000", "line_style": "dotted"},
        "default": {"color": "#000000", "line_style": "dotted"},
    }

    for _, data in graph.nodes(data=True):
        node_type = data.get("type", "default")
        style = node_styles.get(node_type.lower(), node_styles["default"])
        data.update(style)
        data["opacity"] = 0.5

    for _, _, data in graph.edges(data=True):
        edge_type = data.get("type", "default")
        style = edge_styles.get(edge_type, edge_styles["default"])
        data.update(style)

    return graph
