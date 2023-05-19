import os
import shutil
from ..utils.directory.palette_dir import PALETTE_DIRECTORY
from ..utils.utils import get_date_time_file_format
from ..errors import ThemeNotFoundError
from ..json.json_utils import save_json_data, load_json_data


class Palette:
    """A class to manage the graph plot themes."""

    def __init__(self):
        """Initialize a palette."""
        self._palette_app_dir = PALETTE_DIRECTORY["appdata"]
        self._palette_pack_dir = PALETTE_DIRECTORY["package"]
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
        self.load()

    def save(self):
        """Save the current palette to the palette json file."""
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
        save_json_data(self._palette_app_dir["path"], palette_data)

    def load(self):
        """Load the palette from the palette json file."""
        # load palette data from file
        palette_data: dict = {}
        try:
            palette_data = load_json_data(self._palette_app_dir["path"])
            # check if palette data is none
            if palette_data is None:
                # load the default palette
                palette_data = load_json_data(self._palette_pack_dir["path"])
            if palette_data is None:
                raise ThemeNotFoundError(
                    "No palette data found. Package may be corrupted."
                )
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
            raise ThemeNotFoundError("No palette data found. Package may be corrupted.")

    def reset_palette(self, ask_user: bool = False):
        """Reset the palette to the default palette."""
        if ask_user:
            # check if user wants to overwrite existing palette
            overwrite = input(
                f"\nAre you sure you want to reset the palette to the default palette?\nOverwrite? Y/N "
            )
            if overwrite.upper() == "N":
                return
        # load the default palette
        palette_data = load_json_data(self._palette_pack_dir["path"])
        # check if palette data was loaded
        if len(palette_data.keys()) > 0:
            # overwrite palette file in appdata directory
            shutil.copy(self._palette_pack_dir["path"], self._palette_app_dir["path"])
        else:
            raise ThemeNotFoundError(
                "No default palette data found. Package may be corrupted."
            )
        if ask_user:
            print(f"Palette reset to default.\n")

    def import_palette(self, import_path: str, ask_user: bool = False):
        """Import a palette file from the specified file path.

        Parameters:
        -----------
        import_path : str
            The path to the palette file to import.
        """
        # check if import file exists
        if not os.path.exists(import_path):
            raise FileNotFoundError(f"Palette file not found: {import_path}")
        # check if import file is a json file
        if not import_path.endswith(".json"):
            raise TypeError(f"Palette file must be a json file: {import_path}")
        if ask_user:
            # check if user wants to overwrite existing palette
            overwrite = input(
                f"\nAre you sure you want to import a palette file? This will overwrite the current palette.\nOverwrite? Y/N "
            )
            if overwrite.upper() == "N":
                return
        # overwrite palette file in appdata directory
        shutil.copy(import_path, self._palette_app_dir["path"])
        # load palette file
        self.load()
        if ask_user:
            print(f"Palette imported from '{import_path}'.\n")

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
        palette_file = self._palette_app_dir["path"]
        if not os.path.exists(palette_file) or os.path.getsize(palette_file) == 0:
            palette_file = self._palette_pack_dir["path"]
            if not os.path.exists(palette_file) or os.path.getsize(palette_file) == 0:
                raise ThemeNotFoundError(
                    "No palette file found. Package may be corrupted."
                )
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
                    f"\n{node_type} already exists in '{self._palette_app_dir['path']}' with parameters: \n {node} \n\nOverwrite? Y/N "
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
        self.save()
        if ask_user:
            print(f"\nNew theme added to palette: {self._palette_app_dir['path']}")
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
