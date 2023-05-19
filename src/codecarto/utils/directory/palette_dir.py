import os
import shutil
from .package_dir import get_package_dir
from .appdata_dir import get_codecarto_appdata_dir

DEFAULT_PALETTE_FILE = "default_palette.json"
PALETTE_FILE = "palette.json"


# the package default palette will be in src/palette/default_palette.json
# but when packaged, palette.json will be in appdata/CodeCartographer/palette.json
# when users edit their own palette, they will be edited on the appdata/Roaming/CodeCartographer/palette.json file
# when the package loads the palette, it checks if appdata/Roaming/CodeCartographer/palette.json exists
# if it does, it will load file from there
# if it doesn't, it will copy/load default palette file to
# appdata/Roaming/CodeCartographer/palette.json

# TODO: figure out how to update palette file
# when package is updated, the default palette file will be updated
# but the user's palette file will not be overwritten
# the user will be asked if they want to attempt to merge the default palette file with their palette file
# if they say yes, we can make a function to attempt to merge the default palette file with the user's palette file
#         Update function will be interesting if the user is updating from a really old version
#         Do we make a merge file that keeps track of the changes made to the default palette file?
#       Then we get the version of user's package and then canonically go through update functions
#       to update the user's palette file to the latest version? Seems like it could be a big file
#         Maybe it would be better to go through user's palette and change names and add new palette as needed
# if they say no, notify them that they'll have to manually update their palette file


def get_palette_package_dir() -> str:
    """Get the path to the package\\palette directory.

    Returns:
    --------
    str
        The path to the package\\palette directory.
    """
    palette_dir = os.path.join(get_package_dir(), "palette")
    if not os.path.exists(palette_dir):
        raise RuntimeError("Palette directory not found. Package may be corrupted.")
    return palette_dir


def get_palette_package_file_path() -> str | None:
    """Get the path to the package\\palette\\default_palette.json file.

    Returns:
    --------
    str
        The path to the package\\palette\\default_palette.json file.
    """
    default_palette_file = os.path.join(get_palette_package_dir(), DEFAULT_PALETTE_FILE)
    if not os.path.exists(default_palette_file):
        raise RuntimeError("Default palette file not found. Package may be corrupted.")
    return default_palette_file


def get_palette_appdata_file_name() -> str:
    """Get the name of the palette file in the appdata directory.

    Returns:
    --------
    str
        The name of the palette file in the appdata directory.
    """
    from ...config.config import Config

    config: Config = Config()
    if "palette_file_name" not in config.config_data:
        # add the palette file name to the config file
        config.set_config_property("palette_file_name", PALETTE_FILE)

    return config.config_data["palette_file_name"]


def get_palette_appdata_dir() -> str:
    """Get the appdata dir from config.json.

    Returns:
    --------
    str
        The appdata dir from config.json.
    """
    from ...config.config import Config

    config: Config = Config() 
    if "palette_dir" not in config.config_data:
        # add the palette dir to the config file
        config.set_config_property("palette_dir", get_codecarto_appdata_dir())
    return config.config_data["palette_dir"]


def get_palette_appdata_file_path() -> str:
    """Get the appdata path from config.json.

    Returns:
    --------
    str
        The appdata path from config.json.
    """
    return os.path.join(get_palette_appdata_dir(), get_palette_appdata_file_name())


PALETTE_APPDATA_DIRECTORY = {
    "name": get_palette_appdata_file_name(),
    "dir": get_palette_appdata_dir(),
    "path": get_palette_appdata_file_path(),
}
PALETTE_PACKAGE_DIRECTORY = {
    "name": DEFAULT_PALETTE_FILE,
    "dir": get_palette_package_dir(),
    "path": get_palette_package_file_path(),
}


def setup_palette_directory() -> dict:
    """Setup the palette directories.

    Returns:
    --------
    dict
        The palette directories.
    """
    return {
        "appdata": PALETTE_APPDATA_DIRECTORY,
        "package": PALETTE_PACKAGE_DIRECTORY,
    }


PALETTE_DIRECTORY = setup_palette_directory()
