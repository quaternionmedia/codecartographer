import os

CODE_CARTO_PACKAGE_NAME = "codecarto"


def _check_file_path(file_path):
    """Check if a file path is valid.

    Parameters:
    -----------
    file_path : str
        The path to the file to check.

    Raises:
    -------
    ValueError
        If the file path is invalid.
    """
    file_path: str = get_main_real_path()
    # check if path exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    # check if file is a file
    if not os.path.isfile(file_path):
        raise ValueError(f"Invalid file path: {file_path}")
    return True


############  APPDATA/PACKAGE DIRECTORIES  ############
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
        return None


def get_package_dir() -> str:
    """Return the directory of the codecarto package."""
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.basename(package_dir) == CODE_CARTO_PACKAGE_NAME:
        return package_dir
    else:
        return None


############  CodeCartographer's __main__ DIRECTORIES ############
def get_main_dir() -> str:
    """Get the path to the main directory.

    Returns:
    --------
    str
        The path to the main directory.
    """
    main_module_file: str = get_main_file_path()
    return os.path.dirname(main_module_file)


def get_main_real_path() -> str:
    """Get the real path to the main file.

    Returns:
    --------
    str
        The real path to the main file.
    """
    main_module_file: str = get_main_file_path()
    return os.path.realpath(main_module_file)


def get_main_file_base_name() -> str:
    """Get the base name of the main file.

    Returns:
    --------
    str
        The base name of the main file.
    """
    main_module_file: str = get_main_file_path()
    return os.path.basename(main_module_file)


def get_main_file_path() -> str:
    """Get the path to the main file.

    Returns:
    --------
    str
        The path to the main file.
    """
    from .. import code_cartographer as main

    return main.__file__


# TODO: need to get directories for the passed FILE_PATH to be parsed
# CodeCartographer(file_path: str) is passed this from cli.py
# @click.argument("import_name", metavar="FILE or FILE:APP")
# def run_app(import_name: str) -> None:
# will need file path, dir path, the run script path and base name
# will need to be a .py file


############  Imported Path DIRECTORIES ############
# def get_import_path(file_name: str) -> str:
# def get_import_real_path(file_name: str) -> str:
# def get_import_base_name(file_name: str) -> str:
# def get_import_dir(file_name: str) -> str:
# def get_import_real_dir(file_name: str) -> str:
# def get_import_base_name_dir(file_name: str) -> str:

############  CodeCartographer's graph_data.json DIRECTORIES ############


############  CodeCartographer's themes.json DIRECTORIES ############


def get_file_path(file_name: str) -> str:
    """Get the path to the file.

    Parameters:
    -----------
    file_name : str
        The name of the file.

    Returns:
    --------
    str
        The path to the file.
    """
    # get the path to the main directory
    main_dir: str = get_main_dir()
    # get the path to the file
    file_path: str = os.path.join(main_dir, file_name)
    return file_path


def get_json_file_path(file_name: str = "graph_data.json") -> str:
    """Get the path to the json file.

    Parameters:
    -----------
    file_name : str
        The name of the json file.

    Returns:
    --------
    str
        The path to the json file.
    """
    return get_file_path(file_name)


def set_up_directories() -> dict:
    """Create a version directory and return necessary paths.

    Returns:
        dict: A dictionary with the following keys:
            - "version": (str) The version number in the format "mm-dd-yy_HH-MM-SS".
            - "code_graph_dir": (str) The path to the code graph directory.
            - "json_graph_dir": (str) The path to the JSON graph directory.
            - "json_file_path": (str) The path to the JSON file.
    """
    import os
    from datetime import datetime

    # get the version number
    now: datetime = datetime.now()
    formatted_now: str = now.strftime("%m-%d-%y_%H-%M-%S")
    # get current path
    base_name: str = get_main_file_base_name()
    file_path: str = get_main_real_path()
    file_path: str = file_path.replace(base_name, "")
    # create paths
    version_dir: str = os.path.join(file_path, "Output", formatted_now)
    code_graph_dir: str = os.path.join(version_dir, "code_graph")
    json_graph_dir: str = os.path.join(version_dir, "json_graph")
    json_file_path: str = os.path.join(json_graph_dir, "graph_data.json")
    # create directories
    os.makedirs(version_dir, exist_ok=True)
    os.makedirs(code_graph_dir, exist_ok=True)
    os.makedirs(json_graph_dir, exist_ok=True)
    # return the paths
    return {
        "version": formatted_now,
        "code_graph_dir": code_graph_dir,
        "json_graph_dir": json_graph_dir,
        "json_file_path": json_file_path,
    }
