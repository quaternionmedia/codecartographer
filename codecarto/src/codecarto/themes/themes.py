import os
import shutil
from ..utils.utils import (
    get_appdata_dir,
    get_package_dir,
    CODE_CARTO_PACKAGE_NAME,
)
from ..errors import ThemeNotFoundError
from ..json.json_utils import save_json_data, load_json_data

DEFAULT_THEMES_FILE = "themes\default_themes.json"


class Theme:
    """A class representing a theme."""

    def __init__(self):
        """Initialize a Theme object."""
        self.theme_file_name = "themes.json"
        self.package_dir = get_package_dir()
        print("package_dir: "+self.package_dir)
        self.package_themes_dir = self.package_dir+"\\"+"themes"
        print("package_themes_dir: "+self.package_themes_dir)
        self.theme_package_file_path = os.path.join(self.package_themes_dir, self.theme_file_name)
        print("package_themes_file_path: "+self.theme_package_file_path)
        self.appdata_dir = get_appdata_dir()
        print("appdata_dir: "+self.appdata_dir)
        self.theme_appdata_file_path = self.get_file_path()
        print("appdata_path: "+self.theme_appdata_file_path)
        self.theme_file_base_name = os.path.basename(self.theme_appdata_file_path)
        print("base_name: "+self.theme_file_base_name) 
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

    def get_file_path(self):
        """Get the path to the APPDATA themes file.

        Returns:
        --------
        str
            The path to the themes file.
        """ 
        # check if appdata_dir and package_dir are not None
        if self.appdata_dir is None or self.package_dir is None:
            raise RuntimeError(
                "Unsupported operating system or package directory not found."
            )
        # create themes directory if it doesn't exist
        themes_dir = os.path.join(self.appdata_dir, CODE_CARTO_PACKAGE_NAME)
        os.makedirs(themes_dir, exist_ok=True) 
        # check if themes file exists
        themes_file_path = os.path.join(themes_dir, "themes.json")
        if not os.path.exists(themes_file_path):
            # copy default themes file
            shutil.copy2(
                os.path.join(self.package_dir, DEFAULT_THEMES_FILE), themes_file_path
            )
        # return path to themes file
        return themes_file_path
    
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
        save_json_data(self.theme_appdata_file_path, theme_data)

    def load(self):
        """Load the themes from the theme json file."""
        # load theme data from file
        theme_data: dict = {}
        try:
            theme_data = load_json_data(self.theme_appdata_file_path)
            # check if theme data is none
            if theme_data is None:
                # raise ThemeNotFoundError(
                #     f"\n\nTheme not found: {self.theme_appdata_file_path} \nCreate new themes using 'codecarto new ...' \nOr import themes with 'codecarto import FILE_PATH'.\n"
                # )
                theme_data = load_json_data(self.theme_package_file_path)
            if theme_data is None:
                raise ThemeNotFoundError(
                    f"\n\nTheme not found: {self.theme_package_file_path} \nCreate new themes using 'codecarto new ...' \nOr import themes with 'codecarto import FILE_PATH'.\n"
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
            raise ThemeNotFoundError(
                f"Theme not found: {self.theme_appdata_file_path} \n Create new themes using 'codecarto new ...' \nOr import themes with 'codecarto import FILE_PATH'."
            )

    def import_theme_file(self, file_path: str):
        """Import a theme file from the specified file path.

        Parameters:
        -----------
        file_path : str
            The path to the theme file to import.
        """
        # check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Theme file not found: {file_path}")
        # check if file is a json file
        if not file_path.endswith(".json"):
            raise TypeError(f"Theme file must be a json file: {file_path}")
        # check if file is a theme file
        if not os.path.basename(file_path) == self.theme_file_name:
            raise TypeError(f"Theme file must be named 'themes.json': {file_path}")
        # copy theme file to themes directory
        shutil.copy(file_path, self.theme_appdata_file_path)
        # load theme file
        self.load()

    def export_theme_file(self, dir_path: str):
        """Export the current theme file to the specified directory.

        Parameters:
        -----------
        dir_path : str
            The path to the directory to export the theme file to.
        """
        # check if directory exists
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Directory not found: {dir_path}")
        # check if directory is a directory
        if not os.path.isdir(dir_path):
            raise TypeError(f"Path must be a directory: {dir_path}")
        # copy theme file to themes directory
        shutil.copy(self.theme_appdata_file_path, dir_path)
        # return path to exported theme file
        return os.path.join(dir_path, self.theme_file_base_name)

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
