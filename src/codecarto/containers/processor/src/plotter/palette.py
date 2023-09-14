from pydantic import BaseModel

# this is the default palette in the package
# when containerized, we'll be looking in the container's /app directory
# can see DockerFile for more info
default_palette_path: str = "src/plotter/default_palette.json"


class Theme(BaseModel):
    node_type: str
    base: str
    label: str
    shape: str
    color: str
    size: str
    alpha: str


class Palette:
    """A class to manage the plotter palette."""

    def __init__(self, palette: dict = None):
        """Initialize a palette.

        Parameters:
        -----------
        palette : dict (optional) (default=None)
            A dictionary containing the data of the palette to initialize.
        """
        if palette and isinstance(palette, dict) and palette != {}:
            self.palette: dict[str, dict] = palette
        else:
            from json import load

            # load the default palette from package
            with open(default_palette_path, "r") as f:
                self.palette: dict[str, dict] = load(f)

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

    def get_node_styles(self, type: str = None) -> dict:
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
