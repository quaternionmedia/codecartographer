import os
import shutil

NEW_PALETTE_FILENAME = "palette.json"
DEFAULT_PALETTE_FILENAME = "default_palette.json"

# the package default palette will be in src/plotter/default_palette.json
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


def get_palette_dir(default: bool = False) -> str:
    """Get the palette directory.

    Parameters:
    -----------
    default: bool (default: False)
        If True, return the package's default palette dir.

    Returns:
    --------
    str:
        The palette directory.
    """
    from ..config.config_process import get_config_data

    if default:
        return os.path.dirname(get_config_data(True)["default_palette_path"])
    else:
        return os.path.dirname(get_config_data()["palette_path"])


def get_palette_name(default: bool = False) -> str:
    """Get the name of the palette file.

    Parameters:
    -----------
    default: bool (default: False)
        If True, return the default palette file name.

    Returns:
    --------
    str
        The name of the palette file.
    """
    from ..config.config_process import get_config_data

    if default:
        file_name: str = get_config_data(True)["default_palette_path"].split("/")[-1]
        return file_name
    else:
        file_name: str = get_config_data()["palette_path"].split("/")[-1]
        return file_name


def get_palette_path(default: bool = False) -> str:
    """Get the path to the palette file.

    Parameters:
    -----------
    default: bool (default: False)
        If True, return the path to the default palette file.

    Returns:
    --------
    str
        The path to the palette file.
    """
    palette_path: str = os.path.join(
        get_palette_dir(default), get_palette_name(default)
    )
    # Check if the user's palette file exists
    if not default and not os.path.exists(palette_path):
        # copy the package's default palette file to the palette path
        shutil.copy(
            os.path.join(get_palette_dir(True), get_palette_name(True)), palette_path
        )

    return palette_path

def get_package_palette_path() -> str:
    """Get the path to the package's default palette file.

    Returns:
    --------
    str
        The path to the package's default palette file.
    """
    from ..config.directory.package_dir import get_package_dir

    return os.path.join(get_package_dir(), "plotter", DEFAULT_PALETTE_FILENAME)

PALETTE_DIRECTORY = {"default": get_package_palette_path(), "user": get_palette_path()}
