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
CODE_CARTO_MAIN_FILE = "code_cartographer.py"


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


# region Theme
############  CodeCartographer's THEME ############
DEFAULT_THEMES_FILE = "default_themes.json"
THEMES_FILE = "themes.json"


# the package default theme will be in src/themes/default_themes.json
# but when packaged, themes.json will be in appdata/CodeCartographer/themes.json
# when users edit their own themes, they will be edited on the appdata/Roaming/CodeCartographer/themes.json file
# when the package loads the themes, it checks if appdata/Roaming/CodeCartographer/themes.json exists
# if it does, it will load file from there
# if it doesn't, it will copy/load default themes file to
# appdata/Roaming/CodeCartographer/themes.json


def get_theme_package_dir() -> str:
    """Get the path to the package\\themes directory.

    Returns:
    --------
    str
        The path to the package\\themes directory.
    """
    # the package themes will actually be default themes file in the src/codecarto/themes directory.
    # when packaged, the default themes file will be copied to appdata/CodeCartographer/themes.json
    # this is so that users can edit their own themes and not overwrite the default themes file

    # TODO:
    # when package is updated and the default themes file is updated,
    # the user's themes file will not be overwritten. If the user needs to update their themes file,
    # we can make a function to attempt to merge the default themes file with the user's themes file.

    # update function will be interesting if the user is updating from a really old version.
    # do we make a merge file that keeps track of the changes made to the default themes file?
    # then we get the version of user's package and then canonically go through update functions
    # to update the user's themes file to the latest version? Seems like it could be a big file.
    # Maybe it would be better to go through user's themes and change names and add new themes as needed.

    themes_dir = os.path.join(get_package_dir(), "themes")
    if not os.path.exists(themes_dir):
        raise RuntimeError("Themes directory not found. Package may be corrupted.")
    return os.path.join(get_package_dir(), "themes")


def get_theme_package_file_path() -> str | None:
    """Get the path to the package\\themes\\default_themes.json file.

    Returns:
    --------
    str
        The path to the package\\themes\\default_themes.json file.
    """
    default_theme_file = os.path.join(get_theme_package_dir(), DEFAULT_THEMES_FILE)
    if not os.path.exists(default_theme_file):
        raise RuntimeError("Default themes file not found. Package may be corrupted.")
    return default_theme_file


def get_theme_appdata_dir() -> str:
    """Get the path to the APPDATA\Roaming\CodeCartographer directory.

    Returns:
    --------
    str
        The path to the APPDATA\Roaming\CodeCartographer directory.
    """
    return get_codecarto_appdata_dir()


def get_theme_appdata_file_path() -> str:
    """Get the path to the APPDATA\Roaming\CodeCartographer\\themes.json file.

    Returns:
    --------
    str
        The path to the APPDATA\Roaming\CodeCartographer\\themes.json file.
    """
    themes_file_path = os.path.join(get_theme_appdata_dir(), THEMES_FILE)
    if not os.path.exists(themes_file_path):
        # copy the default themes file to the appdata directory
        default_themes_file = get_theme_package_file_path()
        shutil.copy2(default_themes_file, themes_file_path)
        # check if the file was copied successfully
        if not os.path.exists(themes_file_path):
            raise RuntimeError(
                "Unable to copy default themes. Package may be corrupted."
            )
    return themes_file_path


THEMES_APPDATA_DIRECTORY = {
    "name": THEMES_FILE,
    "dir": get_theme_appdata_dir(),
    "path": get_theme_appdata_file_path(),
}
THEMES_PACKAGE_DIRECTORY = {
    "name": DEFAULT_THEMES_FILE,
    "dir": get_theme_package_dir(),
    "path": get_theme_package_file_path(),
}


def setup_theme_directory() -> dict:
    """Setup the theme directories.

    Returns:
    --------
    dict
        The theme directories.
    """
    return {
        "appdata": THEMES_APPDATA_DIRECTORY,
        "package": THEMES_PACKAGE_DIRECTORY,
    }


THEMES_DIRECTORY = setup_theme_directory()
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
        "theme_dirs": THEMES_DIRECTORY,
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
