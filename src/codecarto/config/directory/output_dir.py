import os

JSON_GRAPH_FILE = "graph_data.json"


def get_run_version() -> str:
    """Get the version number of the run.

    Returns:
    --------
    str
        The version number of the run.
    """
    from codecarto import Utility as Util

    return Util.get_date_time_file_format()


RUN_TIME = get_run_version()


def get_output_package_dir() -> str:
    """Get the default output directory.

    Returns:
    --------
    str
        The default output directory.
    """
    from .main_dir import get_main_dir

    # create the default output dir
    upper_codecarto_dir = os.path.dirname(os.path.dirname(get_main_dir()))
    default_output_dir = os.path.join(upper_codecarto_dir, "output")
    if not os.path.exists(default_output_dir):
        os.makedirs(default_output_dir, exist_ok=True)
    return default_output_dir


def set_output_dir(new_dir: str, ask_user: bool = True, makedir: bool = False) -> str:
    """Set the output directory to a new directory.

    If new directory does not exist:
        If running from CLI, user asked if they'd like to make the new directory.\n
        If running from library, makes the new directory.

    Parameters:
    -----------
    new_dir : str
        The new output directory.
    ask_user : bool
        Whether or not to ask the user if they'd like to make the new directory.
    makedir : bool
        Whether or not to make the new directory.

    Returns:
    --------
    str
        The new output directory.
    """
    from ...config.config import Config

    # check if the new dir exists
    if not os.path.exists(new_dir):
        if ask_user and not makedir:
            # ask user if they'd like to make it
            make_dir = input(
                f"The new output directory does not exist. Would you like to make it? (y/n) "
            )
            if make_dir.lower() == "y":
                os.makedirs(new_dir, exist_ok=True)
            else:
                import sys

                print("Exiting...\n")
                sys.exit(0)
        elif makedir:
            # make the dir, used in library and testing
            os.makedirs(new_dir, exist_ok=True)
        else:
            raise ValueError("The new output directory does not exist.")

    # Save to the config file
    config = Config()
    config.set_config_property("output_dir", new_dir)
    return config.config_data["output_dir"]


def reset_output_dir() -> str:
    """Reset the output directory to the default output directory.

    Returns:
    --------
    str
        The default output directory.
    """
    return set_output_dir(get_output_package_dir(), ask_user=False)


def get_output_dir(ask_user: bool = False) -> str:
    """Get the path to the output directory.

    If output directory does not exist:
        If running from CLI, user prompted to reset output directory.\n
        If running from library, output directory is reset to default.
            Default: codecarto\output

    Parameters:
    -----------
    ask_user : bool
        Whether or not to ask the user if they'd like to reset the output directory.

    Returns:
    --------
    str
        The path to the output directory.
    """
    from ...config.config import Config

    # get the output dir
    config = Config()
    output_dir = config.config_data["output_dir"]
    if (not output_dir) or (not os.path.exists(output_dir)):
        if ask_user:  # cli
            # ask user if they'd like to make it
            make_dir = input(
                f"The output directory does not exist. Would you like to reset it to default output location? (y/n) "
            )
            if make_dir.lower() == "y":
                output_dir = reset_output_dir()
            else:
                # raise error
                raise ValueError("The output directory does not exist.")
        else:  # library
            # reset the output dir
            output_dir = reset_output_dir()

    return output_dir


def get_output_version_dir(make_dir: bool = False) -> str:
    """Get the path to the output\RUN_TIME directory.

    Returns:
    --------
    str
        The path to the output\RUN_TIME directory.
    """
    if make_dir:
        version_output_dir = os.path.join(get_output_dir(), f"{RUN_TIME}")
        if not os.path.exists(version_output_dir):
            os.makedirs(version_output_dir, exist_ok=True)
    else:
        version_output_dir = os.path.join(get_output_dir(), f"RUN_TIME")
    return version_output_dir


def get_output_json_dir(make_dir: bool = False) -> str:
    """Get the path to the output/json directory.

    Returns:
    --------
    str
        The path to the output/json directory.
    """
    output_json_dir = os.path.join(get_output_version_dir(make_dir), "json")
    if make_dir and not os.path.exists(output_json_dir):
        os.makedirs(output_json_dir, exist_ok=True)
    return output_json_dir


def get_output_graph_dir(make_dir: bool = False) -> str:
    """Get the path to the output/graph directory.

    Returns:
    --------
    str
        The path to the output/graph directory.
    """
    output_graph_dir = os.path.join(get_output_version_dir(make_dir), "graph")
    if make_dir and not os.path.exists(output_graph_dir):
        os.makedirs(output_graph_dir, exist_ok=True)
    return output_graph_dir


def get_output_graph_from_code_dir(make_dir: bool = False) -> str:
    """Get the path to the output/graph/from_code directory.

    Returns:
    --------
    str
        The path to the output/graph/from_code directory.
    """
    output_graph_fromcode_dir = os.path.join(
        get_output_graph_dir(make_dir), "from_code"
    )
    if make_dir and not os.path.exists(output_graph_fromcode_dir):
        os.makedirs(output_graph_fromcode_dir, exist_ok=True)
    return output_graph_fromcode_dir


def get_output_graph_from_json_dir(make_dir: bool = False) -> str:
    """Get the path to the output/graph/from_json directory.

    Returns:
    --------
    str
        The path to the output/graph/from_json directory.
    """
    output_graph_from_json_dir = os.path.join(
        get_output_graph_dir(make_dir), "from_json"
    )
    if make_dir and not os.path.exists(output_graph_from_json_dir):
        os.makedirs(output_graph_from_json_dir, exist_ok=True)
    return output_graph_from_json_dir


def get_json_graph_file_path(make_dir: bool = False) -> str:
    """Get the path to the output/json/graph_data.json file.

    Returns:
    --------
    str
        The path to the output/json/graph_data.json file.
    """
    return os.path.join(get_output_json_dir(make_dir), JSON_GRAPH_FILE)


def new_output_directory(make_dir: bool = False) -> dict:
    """Setup the output directory.

    Parameters:
    -----------
    make_dir : bool
        Whether or not to make the output directory. If False, the output directory is set to 'RUN_TIME' filler string.

    Returns:
    --------
    dict
        A dictionary of the output directories.
    """
    _version = ""
    if make_dir:
        _version = RUN_TIME
    else:
        _version = "RUN_TIME"
    return {
        "version": _version,
        "output_dir": get_output_dir(),
        "version_dir": get_output_version_dir(make_dir),
        "graph_dir": get_output_graph_dir(make_dir),
        "graph_code_dir": get_output_graph_from_code_dir(make_dir),
        "graph_json_dir": get_output_graph_from_json_dir(make_dir),
        "json_dir": get_output_json_dir(make_dir),
        "json_graph_file_path": get_json_graph_file_path(make_dir),
    } 

OUTPUT_DIRECTORY = get_output_dir()

def get_last_dated_dir():
    """Get the last dated directory in the output directory.

    Returns:
    --------
    str
        The path to the last dated directory in the output directory.
    """
    dated_dirs = [
        d for d in os.listdir(get_output_dir()) if os.path.isdir(os.path.join(get_output_dir(), d))
    ]
    dated_dirs.sort(reverse=True)
    return os.path.join(get_output_dir(), dated_dirs[0])

