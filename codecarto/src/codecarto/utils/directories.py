import os
import shutil


# region AppData/Package
############  APPDATA/PACKAGE DIRECTORIES  ############
CODE_CARTO_PACKAGE_NAME = "codecarto"


def get_appdata_dir() -> str:
    """Return the application data directory."""
    if os.name == "nt":
        # On Windows, use %APPDATA% environment variable
        return os.getenv("APPDATA")
    elif os.name == "posix":
        # On Linux/Unix/Mac, use ~/.local/share directory
        return os.path.expanduser("~/.local/share")
    else:
        # Unsupported operating system
        raise RuntimeError("Unsupported operating system.")


def get_codecarto_appdata_dir() -> str:
    """Return the APPDATA\Roaming\CodeCartographer directory."""
    codecarto_appdata_dir = os.path.join(get_appdata_dir(), "CodeCartographer")
    if not os.path.exists(codecarto_appdata_dir):
        os.makedirs(codecarto_appdata_dir, exist_ok=True)
    return codecarto_appdata_dir


def get_package_dir() -> str:
    """Return the directory of the codecarto package."""
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.basename(package_dir) == CODE_CARTO_PACKAGE_NAME:
        return package_dir
    else:
        return None


# endregion


# region Main
############  CodeCartographer's __main__ DIRECTORIES ############
CODE_CARTO_MAIN_FILE = "processor.py"


def get_main_path() -> str:
    """Get the real path to the main file.

    Returns:
    --------
    str
        The real path to the main file.
    """
    main_file_path = os.path.realpath(
        os.path.join(get_package_dir(), CODE_CARTO_MAIN_FILE)
    )
    if not os.path.exists(main_file_path):
        raise RuntimeError("Main package file not found. Package may be corrupted.")
    return main_file_path


def get_main_dir() -> str:
    """Get the path to the main directory.

    Returns:
    --------
    str
        The path to the main directory.
    """
    main_module_file: str = get_main_path()
    return os.path.dirname(main_module_file)


def get_main_file_base_name() -> str:
    """Get the base name of the main file.

    Returns:
    --------
    str
        The base name of the main file.
    """
    main_module_file: str = get_main_path()
    return os.path.basename(main_module_file)


def get_main_file_dirs_dict() -> dict:
    """Get a dictionary of the main file's directories.

    Returns:
    --------
    dict
        A dictionary of the main file's directories.
    """
    return {
        "dir": get_main_dir(),
        "path": get_main_path(),
        "base_name": get_main_file_base_name(),
    }


MAIN_DIRECTORIES = get_main_file_dirs_dict()
# endregion


# region Output
############  CodeCartographer's OUTPUT DIRECTORIES ############
JSON_GRAPH_FILE = "graph_data.json"


def get_run_version() -> str:
    """Get the version number of the run.

    Returns:
    --------
    str
        The version number of the run.
    """
    from .utils import get_date_time_file_format

    return get_date_time_file_format()


RUN_TIME = get_run_version()


def get_output_dir() -> str:
    """Get the path to the output directory.

    Returns:
    --------
    str
        The path to the output directory.
    """
    # TODO: Make this configurable by the user through the GUI or CLI
    output_dir = os.path.join(get_main_dir(), f"output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    return output_dir


def get_output_version_dir() -> str:
    """Get the path to the output\RUN_TIME directory.

    Returns:
    --------
    str
        The path to the output\RUN_TIME directory.
    """
    version_output_dir = os.path.join(get_output_dir(), f"{RUN_TIME}")
    if not os.path.exists(version_output_dir):
        os.makedirs(version_output_dir, exist_ok=True)
    return version_output_dir


def get_output_json_dir() -> str:
    """Get the path to the output/json directory.

    Returns:
    --------
    str
        The path to the output/json directory.
    """
    output_json_dir = os.path.join(get_output_version_dir(), "json")
    if not os.path.exists(output_json_dir):
        os.makedirs(output_json_dir, exist_ok=True)
    return output_json_dir


def get_json_graph_file_path() -> str:
    """Get the path to the output/json/graph_data.json file.

    Returns:
    --------
    str
        The path to the output/json/graph_data.json file.
    """
    return os.path.join(get_output_json_dir(), JSON_GRAPH_FILE)


def get_output_graph_dir() -> str:
    """Get the path to the output/graph directory.

    Returns:
    --------
    str
        The path to the output/graph directory.
    """
    output_graph_dir = os.path.join(get_output_version_dir(), "graph")
    if not os.path.exists(output_graph_dir):
        os.makedirs(output_graph_dir, exist_ok=True)
    return output_graph_dir


def get_output_graph_from_code_dir() -> str:
    """Get the path to the output/graph/from_code directory.

    Returns:
    --------
    str
        The path to the output/graph/from_code directory.
    """
    output_graph_fromcode_dir = os.path.join(get_output_graph_dir(), "from_code")
    if not os.path.exists(output_graph_fromcode_dir):
        os.makedirs(output_graph_fromcode_dir, exist_ok=True)
    return output_graph_fromcode_dir


def get_output_graph_from_json_dir() -> str:
    """Get the path to the output/graph/from_json directory.

    Returns:
    --------
    str
        The path to the output/graph/from_json directory.
    """
    output_graph_from_json_dir = os.path.join(get_output_graph_dir(), "from_json")
    if not os.path.exists(output_graph_from_json_dir):
        os.makedirs(output_graph_from_json_dir, exist_ok=True)
    return output_graph_from_json_dir


def setup_output_directory() -> dict:
    """Setup the output directory.

    Returns:
    --------
    dict
        A dictionary of the output directories.
    """
    return {
        "version": RUN_TIME,
        "output_dir": get_output_dir(),
        "version_dir": get_output_version_dir(),
        "graph_dir": get_output_graph_dir(),
        "graph_code_dir": get_output_graph_from_code_dir(),
        "graph_json_dir": get_output_graph_from_json_dir(),
        "json_dir": get_output_json_dir(),
        "json_graph_file_path": get_json_graph_file_path(),
    }


OUTPUT_DIRECTORY = setup_output_directory()
# endregion


# region palette
############  CodeCartographer's PALETTE ############
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

    # update function will be interesting if the user is updating from a really old version.
    # do we make a merge file that keeps track of the changes made to the default palette file?
    # then we get the version of user's package and then canonically go through update functions
    # to update the user's palette file to the latest version? Seems like it could be a big file.
    # Maybe it would be better to go through user's palette and change names and add new palette as needed.

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
# endregion


def get_all_directories() -> dict:
    """Get all the directories.

    Returns:
    --------
    dict
        All the directories.
    """
    return {
        "appdata_dir": get_appdata_dir(),
        "codecarto_appdata_dir": get_codecarto_appdata_dir(),
        "package_dir": get_package_dir(),
        "main_dirs": MAIN_DIRECTORIES,
        "palette_dirs": PALETTE_DIRECTORY,
        "output_dirs": OUTPUT_DIRECTORY,
    }


def print_all_directories(
    directory: dict = get_all_directories(), indent: str = ""
) -> None:
    """Print all the directories."""
    # get directories and the max width of the keys
    max_width = max([len(key) for key in directory.keys()]) + 1
    # print the directories
    if indent == "":
        print()
    for key, value in directory.items():
        if isinstance(value, dict):
            # print the key then recursively call the function
            print(f"{indent}{key}:")
            print_all_directories(value, f"{indent}\t")
        else:
            print(f"{indent}{key:<{max_width}}: {value}")
    if indent == "":
        print()
