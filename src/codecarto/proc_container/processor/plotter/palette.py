import os
import shutil
from pydantic import BaseModel
from ..utils.utils import (
    get_date_time_file_format,
    save_json,
    load_json,
)
from ..plotter.palette_dir import PALETTE_DIRECTORY


class Theme(BaseModel):
    node_type: str
    base: str
    label: str
    shape: str
    color: str
    size: str
    alpha: str


class Palette:
    """A class to manage the graph plot themes."""

    def __init__(self):
        """Initialize a palette."""
        self._palette_default_path = PALETTE_DIRECTORY["default"]
        self._palette_user_path = PALETTE_DIRECTORY["user"]
        self._alphas = [round(0.1 * i, ndigits=1) for i in range(11)]
        self._sizes = [(100 * i) for i in range(1, 11)]
        self._theme = {
            "bases": {},
            "labels": {},
            "shapes": {},
            "colors": {},
            "sizes": {},
            "alphas": {},
        }
        self.load_palette()

    def save_palette(self, default: bool = False):
        """Save the current palette to the palette json file.

        Args:
            default (bool, optional): Whether to save the palette to the default palette file. Defaults to False.
        """
        # create dictionary with current palette data
        palette_data = {
            "bases": self.bases,
            "labels": self.labels,
            "shapes": self.shapes,
            "colors": self.colors,
            "sizes": self.sizes,
            "alphas": self.alphas,
        }
        # write palette data to file
        if default:
            save_json(self._palette_default_path, palette_data)
        else:
            save_json(self._palette_user_path, palette_data)

    def load_palette(self, default: bool = False):
        """Load the palette from the palette json file.

        Args:
            default (bool, optional): Whether to load the palette from the default palette file. Defaults to False.
        """
        # load palette data from file
        palette_data: dict = {}
        try:
            if default:
                palette_data = load_json(self._palette_default_path)
            else:
                palette_data = load_json(self._palette_user_path)
                # check if palette data is none
                if palette_data is None:
                    # load the default palette
                    palette_data = load_json(self._palette_default_path)
            if palette_data is None:
                raise ValueError("No palette data found. Package may be corrupted.")
            # check if palette data was loaded
            if len(palette_data.keys()) > 0:
                # load palette data
                self.bases: dict = palette_data["bases"]
                self.labels: dict = palette_data["labels"]
                self.shapes: dict = palette_data["shapes"]
                self.colors: dict = palette_data["colors"]
                self.sizes: dict = palette_data["sizes"]
                self.alphas: dict = palette_data["alphas"]
                self.types: list = list(self.bases.keys())
        except FileNotFoundError:
            raise ValueError("No palette data found. Package may be corrupted.")

    def reset_palette(self, ask_user: bool = False):
        """Reset the palette to the default palette."""
        if ask_user:
            # check if user wants to overwrite existing palette
            overwrite = input(
                f"\nAre you sure you want to reset the palette to the default palette?\nOverwrite? (y/n) : "
            )
            if overwrite.lower() == "n":
                print("Exiting ... \n")  # blank line
                return
        # load the default palette
        palette_data = load_json(self._palette_default_path)
        # check if palette data was loaded
        if len(palette_data.keys()) > 0:
            # overwrite user's palette with the appdata palette
            shutil.copy(self._palette_default_path, self._palette_user_path)
        else:
            raise ValueError("No default palette data found. Package may be corrupted.")
        if ask_user:
            print(f"Palette reset to default.\n")

    def set_palette(self, file_path: str, ask_user: bool = False):
        """Set the palette to the specified palette file.

        Parameters:
        -----------
        file_path : str
            The path to the palette file to set as the current palette.
        """
        # check if user wants to overwrite existing palette
        if ask_user:
            overwrite = input(
                f"\nAre you sure you want to set the palette to the specified palette file? (y/n) : "
            )
            if overwrite.lower() == "n":
                print("Exiting ... \n")  # blank line
                return

        # check if the new config path exists
        if not os.path.exists(file_path):
            raise Exception(f"Provided path does not exist: {file_path}")
        # check if the new config path is a file
        if not os.path.isfile(file_path):
            raise Exception(f"Provided path is not a file: {file_path}")
        # check if the new config path is a JSON file
        if not file_path.endswith(".json"):
            raise Exception(f"Provided path is not a JSON file: {file_path}")

        # set the pallette path property in the config file
        from ..config.config_process import CONFIG_DIRECTORY

        config_path = CONFIG_DIRECTORY["user"]
        config_data = load_json(config_path)
        config_data["palette_path"] = file_path
        save_json(config_path, config_data)

        # load palette file
        self.load_palette()
        print(f"Now using palette file '{file_path}'\n")

    def import_palette(self, import_path: str, ask_user: bool = False):
        """Import a palette file from the specified file path.

        Parameters:
        -----------
        import_path : str
            The path to the palette file to import.
        """
        # check if the new config path exists
        if not os.path.exists(import_path):
            raise Exception(f"Provided path does not exist: {import_path}")
        # check if the new config path is a file
        if not os.path.isfile(import_path):
            raise Exception(f"Provided path is not a file: {import_path}")
        # check if the new config path is a JSON file
        if not import_path.endswith(".json"):
            raise Exception(f"Provided path is not a JSON file: {import_path}")

        # check if user wants to overwrite existing palette
        if ask_user:
            overwrite = input(
                f"\nAre you sure you want to import a palette file? This will overwrite the current palette.\nOverwrite? (y/n) : "
            )
            if overwrite.lower() == "n":
                print("Exiting ... \n")  # blank line
                return

        # overwrite palette file in appdata directory
        shutil.copy(import_path, self._palette_user_path)
        # load palette file
        self.load_palette()

        if ask_user:
            print(f"Palette imported from '{import_path}'\n")

    def export_palette(self, export_path: str):
        """Export the current palette file to the specified directory.

        Parameters:
        -----------
        export_path : str
            The path to the directory to which to export the palette file.

        Returns:
        --------
        str
            The path to the exported palette file path.
        """
        # check if directory exists
        if not os.path.exists(export_path):
            raise FileNotFoundError(f"Directory not found: {export_path}")
        # check if directory is a directory
        if not os.path.isdir(export_path):
            raise TypeError(f"Path must be a directory: {export_path}")
        # check if palette file exists and is not empty
        palette_file = self._palette_user_path
        if not os.path.exists(palette_file) or os.path.getsize(palette_file) == 0:
            palette_file = self._palette_user_path
            if not os.path.exists(palette_file) or os.path.getsize(palette_file) == 0:
                raise ValueError("No palette file found. Package may be corrupted.")
        # create export file
        export_date = get_date_time_file_format()
        export_name = str(os.path.basename(palette_file)).split(".")[0]
        export_name = f"{export_name}_{export_date}.json"
        export_file = os.path.join(export_path, export_name)
        shutil.copy(palette_file, export_file)
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
        color: str,
        size: float,
        alpha: float,
        ask_user: bool = False,
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
            Dictionary of the new theme. Keys are the values are the theme parameters.
        """
        if ask_user:
            # check if node type already exists
            if node_type in self.bases.keys():
                # ask user if they want to overwrite
                node = self.get_node_styles(node_type)
                overwrite = input(
                    f"\n{node_type} already exists in '{self._palette_user_path}' with parameters: \n {node} \n\nOverwrite? Y/N "
                )
                if overwrite.upper() == "N":
                    print(f"\nNew theme not created.\n")
                    return None
        # create new node type
        self.bases[node_type] = base
        self.labels[base] = label
        self.shapes[base] = shape
        self.colors[base] = color
        self.sizes[base] = size
        self.alphas[base] = alpha

        # save themes to palette file
        self.save_palette()
        if ask_user:
            print(f"\nNew theme added to palette: {self._palette_user_path}")
            print(
                f"New theme '{node_type}' created with parameters: base={base}, label={label}, shape={shape}, color={color}, size={size}, alpha={alpha}\n"
            )
        return self.get_node_styles(node_type)

    def get_node_styles(self, type: str = None) -> dict:
        """Get the styles for all node types.

        Parameters:
        -----------
        type : str (optional) (default=None)
            If specified, only the style for the specified node type will be returned.

        Returns:
        --------
        dict[node_type(str), styles(dict)]
            A dictionary containing the styles for all node types.
        """
        if type:
            return {
                type: {
                    "base": self.bases[type],
                    "label": self.labels[self.bases[type]],
                    "shape": self.shapes[self.bases[type]],
                    "color": self.colors[self.bases[type]],
                    "size": self.sizes[self.bases[type]],
                    "alpha": self.alphas[self.bases[type]],
                }
            }
        else:
            styles = {}
            for type in self.bases.keys():
                styles[type] = {
                    "base": self.bases[type],
                    "label": self.labels[self.bases[type]],
                    "shape": self.shapes[self.bases[type]],
                    "color": self.colors[self.bases[type]],
                    "size": self.sizes[self.bases[type]],
                    "alpha": self.alphas[self.bases[type]],
                }
            return styles

    def get_palette_data(self) -> dict:
        """Get the data of the current palette.

        Returns:
        --------
        dict
            A dictionary containing the data of the current palette.
        """
        return {
            "bases": self.bases,
            "labels": self.labels,
            "shapes": self.shapes,
            "colors": self.colors,
            "sizes": self.sizes,
            "alphas": self.alphas,
        }
