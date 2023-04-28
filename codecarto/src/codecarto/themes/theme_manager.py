import os
import shutil
from ..utils.dirs import THEMES_DIRECTORY
from ..utils.utils import get_date_time_file_format
from ..errors import ThemeNotFoundError
from ..json.json_utils import save_json_data, load_json_data


class ThemeManager:
    """A class to manage the graph plot themes."""

    def __init__(self):
        """Initialize a theme handler."""
        self._theme_app_dir = THEMES_DIRECTORY["appdata"]
        self._theme_pack_dir = THEMES_DIRECTORY["package"]
        self._alphas = [round(0.1 * i, ndigits=1) for i in range(11)]
        self._sizes = [(100 * i) for i in range(1, 11)]
        self._theme = {
            "colors": {},
            "shapes": {},
            "labels": {},
            "alphas": {},
            "sizes": {},
            "bases": {},
        }
        self.load()

    def save(self):
        """Save the current theme to the theme json file."""
        # create dictionary with current theme data
        theme_data = {
            "bases": self.bases,
            "labels": self.labels,
            "alphas": self.alphas,
            "sizes": self.sizes,
            "shapes": self.shapes,
            "colors": self.colors,
        }
        # write theme data to file
        save_json_data(self._theme_app_dir["path"], theme_data)

    def load(self):
        """Load the themes from the theme json file."""
        # load theme data from file
        theme_data: dict = {}
        try:
            theme_data = load_json_data(self._theme_app_dir["path"])
            # check if theme data is none
            if theme_data is None:
                # load the default theme
                theme_data = load_json_data(self._theme_pack_dir["path"])
            if theme_data is None:
                raise ThemeNotFoundError(
                    "No theme data found. Package may be corrupted."
                )
            # check if theme data was loaded
            if len(theme_data.keys()) > 0:
                # load theme data
                self.bases: dict = theme_data["bases"]
                self.labels: dict = theme_data["labels"]
                self.shapes: dict = theme_data["shapes"]
                self.sizes: dict = theme_data["sizes"]
                self.colors: dict = theme_data["colors"]
                self.alphas: dict = theme_data["alphas"]
        except FileNotFoundError:
            raise ThemeNotFoundError("No theme data found. Package may be corrupted.")

    def import_theme(self, file_path: str):
        """Import a theme file from the specified file path.

        Parameters:
        -----------
        file_path : str
            The path to the theme file to import.
        """
        # check if import file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Theme file not found: {file_path}")
        # check if import file is a json file
        if not file_path.endswith(".json"):
            raise TypeError(f"Theme file must be a json file: {file_path}")
        # check if import file is a theme file
        if not os.path.basename(file_path) == self._theme_app_dir["name"]:
            raise TypeError(f"Theme file must be named 'themes.json': {file_path}")
        # overwrite theme file in appdata directory
        shutil.copy(file_path, self._theme_app_dir["path"])
        # load theme file
        self.load()

    def export_theme(self, export_path: str):
        """Export the current theme file to the specified directory.

        Parameters:
        -----------
        export_path : str
            The path to the directory to which to export the theme file.

        Returns:
        --------
        str
            The path to the exported theme file path.
        """
        # check if directory exists
        if not os.path.exists(export_path):
            raise FileNotFoundError(f"Directory not found: {export_path}")
        # check if directory is a directory
        if not os.path.isdir(export_path):
            raise TypeError(f"Path must be a directory: {export_path}")
        # check if theme file exists and is not empty
        theme_file = self._theme_app_dir["path"]
        if not os.path.exists(theme_file) or os.path.getsize(theme_file) == 0:
            theme_file = self._theme_pack_dir["path"]
            if not os.path.exists(theme_file) or os.path.getsize(theme_file) == 0:
                raise ThemeNotFoundError(
                    "No theme file found. Package may be corrupted."
                )
        # create export file
        export_date = get_date_time_file_format()
        export_name = os.path.basename(theme_file).split(".")[0]
        export_name = f"{export_name}_{export_date}.json"
        export_file = os.path.join(export_path, export_name)
        shutil.copy(theme_file, export_file)
        # check if export file exists
        if not os.path.exists(export_file):
            raise FileNotFoundError(f"Export failed.")
        # return export file path
        return export_file

    def create_new_theme(
        self,
        node_type: str,
        base: str,
        label: str,
        shape: str,
        size: float,
        color: str,
        alpha: float,
    ) -> str:
        """Create a new theme with the specified parameters.

        Parameters:
        -----------
        node_type : str
            The type of node for which to create a new theme.
        label : str
            The label of the nodes in the new theme.
        shape : str
            The shape of the nodes in the new theme.
        size : float
            The size of the nodes in the new theme.
        color : str
            The color of the nodes in the new theme.
        alpha : float
            The alpha (transparency) value of the nodes in the new theme.

        Returns:
        --------
        str
            The name of the new theme.
        """
        # check if node type already exists
        if node_type in self.bases.keys():
            # ask user if they want to overwrite
            node = self.get_node_style(node_type)
            overwrite = input(
                f"{node_type} already exists. \n {node} \n Overwrite? Y/N "
            )
            if overwrite.upper() == "N":
                return None

        # create new node type
        self.bases[node_type] = base
        self.labels[base] = label
        self.shapes[base] = shape
        self.sizes[base] = size
        self.colors[base] = color
        self.alphas[base] = alpha

        # save themes to file
        self.save()
        return node_type

    def get_node_style(self, node_type: str) -> dict:
        """Get the style for a node type.

        Parameters:
        -----------
        node_type : str
            The type of node for which to get the style.

        Returns:
        --------
        dict
            A dictionary containing the style information for the node type.
        """
        base = self.bases[node_type]
        return {
            "node_type": node_type,
            "base": self.bases[node_type],
            "size": self.sizes[base],
            "alpha": self.alphas[base],
            "color": self.colors[base],
            "shape": self.shapes[base],
            "label": self.labels[base],
        }

    def get_node_styles(self) -> dict:
        """Get the styles for all node types.

        Returns:
        --------
        dict[str, dict]
            A dictionary containing the styles for all node types.
        """
        return {
            node_type: self.get_node_style(node_type) for node_type in self.bases.keys()
        }

    def get_bases(self):
        """Get the bases of the current theme.

        Returns:
        --------
        dict
            A dictionary containing the bases of the current theme.
        """
        return self.bases

    def get_node_types(self):
        """Get the node types of the current theme.

        Returns:
        --------
        list
            A list containing the node types of the current theme.
        """
        return list(self.bases.keys())

    def get_theme_data(self) -> dict:
        """Get the data of the current theme.

        Returns:
        --------
        dict
            A dictionary containing the data of the current theme.
        """
        return {
            "bases": self.bases,
            "labels": self.labels,
            "alphas": self.alphas,
            "sizes": self.sizes,
            "shapes": self.shapes,
            "colors": self.colors,
        }
