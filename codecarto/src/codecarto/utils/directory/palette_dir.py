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


def get_palette_package_dir() -> str:
    """Get the path to the package\\palette directory.

    Returns:
    --------
    str
        The path to the package\\palette directory.
    """
    # the package palette will actually be default palette file in the src/codecarto/palette directory.
    # when packaged, the default palette file will be copied to appdata/CodeCartographer/palette.json
    # this is so that users can edit their own palette and not overwrite the default palette file

    # TODO:
    # when package is updated and the default palette file is updated,
    # the user's palette file will not be overwritten. If the user needs to update their palette file,
    # we can make a function to attempt to merge the default palette file with the user's palette file.
    #     update function will be interesting if the user is updating from a really old version.
    # do we make a merge file that keeps track of the changes made to the default palette file?
    # then we get the version of user's package and then canonically go through update functions
    # to update the user's palette file to the latest version? Seems like it could be a big file.
    #     Maybe it would be better to go through user's palette and change names and add new palette as needed.

    palette_dir = os.path.join(get_package_dir(), "palette")
    if not os.path.exists(palette_dir):
        raise RuntimeError("Palette directory not found. Package may be corrupted.")
    return os.path.join(get_package_dir(), "palette")


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


def get_palette_appdata_dir() -> str:
    """Get the path to the APPDATA\Roaming\CodeCartographer directory.

    Returns:
    --------
    str
        The path to the APPDATA\Roaming\CodeCartographer directory.
    """
    return get_codecarto_appdata_dir()


def get_palette_appdata_file_path() -> str:
    """Get the path to the APPDATA\Roaming\CodeCartographer\\palette.json file.

    Returns:
    --------
    str
        The path to the APPDATA\Roaming\CodeCartographer\\palette.json file.
    """
    palette_file_path = os.path.join(get_palette_appdata_dir(), PALETTE_FILE)
    if not os.path.exists(palette_file_path):
        # copy the default palette file to the appdata directory
        default_palette_file = get_palette_package_file_path()
        shutil.copy2(default_palette_file, palette_file_path)
        # check if the file was copied successfully
        if not os.path.exists(palette_file_path):
            raise RuntimeError(
                "Unable to copy default palette. Package may be corrupted."
            )
    return palette_file_path


PALETTE_APPDATA_DIRECTORY = {
    "name": PALETTE_FILE,
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
