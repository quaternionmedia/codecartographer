import os

JSON_GRAPH_FILE = "graph_data.json"


def get_run_version() -> str:
    """Get the version number of the run.

    Returns:
    --------
    str
        The version number of the run.
    """
    from ...utils.utils import get_date_time_file_format

    return get_date_time_file_format()


def get_output_dir(default: bool = False, ask_user: bool = False) -> str:
    """Get the path to the output directory.

    Parameters:
    -----------
    default: bool
        Whether to return the default output directory.
    ask_user: bool
        Whether or not to ask the user if they'd like to reset the output directory.

    Returns:
    --------
    str
        The path to the output directory.
    """
    from ..config_process import get_config_data
    from ...utils.utils import load_json

    # Get the config file
    default_config_data: str = get_config_data(True)
    config_data: dict = load_json(default_config_data["user_config_path"])

    # Get the output directory
    output_dir: str = ""
    if default:
        output_dir = default_config_data["default_output_dir"]
    else:
        output_dir = config_data["output_dir"]

    # Check if the output dir exists, shouldn't hit from API
    if (not output_dir) or (not os.path.exists(output_dir)):
        if ask_user:  # from cli
            # Ask user if they'd like to make it
            make_dir = input(
                f"The output directory does not exist. Would you like to reset it to default output location? (y/n) "
            )
            if make_dir.lower() == "y":
                output_dir = reset_output_dir()
            else:
                raise ValueError("The output directory does not exist.")
        else:  # from lib
            # Create the output dir
            os.makedirs(output_dir, exist_ok=True)

    # Return the output dir
    return output_dir


def set_output_dir(
    new_dir: str, ask_user: bool = True, makedir: bool = False, default: bool = False
) -> str:
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
    default : bool
        Whether or not to set the output directory to the default output directory.

    Returns:
    --------
    str
        The new output directory.
    """
    from ..config_process import get_config_data
    from ...utils.utils import save_json

    # check if the new dir exists
    if not os.path.exists(new_dir):
        # check if the new dir is a folder or a file
        if os.path.isfile(new_dir):
            raise ValueError("The new output directory cannot be a file.")

        dir_type = "default" if default else "new"
        if ask_user and not makedir:
            # ask user if they'd like to make it
            make_dir = input(
                f"\nThe {dir_type} output directory does not exist. Would you like to make it? (y/n) : "
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
            raise ValueError(f"The {dir_type} output directory does not exist.")

    # Save to the config file
    config_data = get_config_data()
    config_data["output_dir"] = new_dir
    save_json(config_data["config_path"], config_data)
    return config_data["output_dir"]


def reset_output_dir() -> str:
    """Reset the output directory to the default output directory.

    Returns:
    --------
    str
        The default output directory.
    """
    from ..config_process import get_config_data

    config_data: dict = get_config_data(True)
    output_dir: str = config_data["default_output_dir"]

    return set_output_dir(output_dir, ask_user=False, default=True)


def create_output_dirs() -> dict:
    """Get the path to the output sub directories.

    Returns:
    --------
    dict
        A dictionary of the output sub directories.
    """
    # Get the output directory
    output_dir: str = get_output_dir(True)

    # Get the run version
    run_version: str = get_run_version()

    # Create the run version directory path
    run_version_dir: str = os.path.join(output_dir, run_version)

    # Check if the run version already exists
    if os.path.exists(run_version_dir):
        # If it does, add a number to the end of the run version
        i: int = 1
        while os.path.exists(run_version_dir):
            run_version_dir = f"{run_version}_{i}"
            i += 1

    # Create the other sub directories paths
    output_graph_dir: str = os.path.join(get_output_dir(), run_version, "graph")
    output_graph_from_code_dir: str = os.path.join(output_graph_dir, "from_code")
    output_graph_from_json_dir: str = os.path.join(output_graph_dir, "from_json")
    output_json_dir: str = os.path.join(get_output_dir(), run_version, "json")
    output_json_file: str = os.path.join(output_json_dir, JSON_GRAPH_FILE)

    # Create the output sub directories
    os.makedirs(run_version_dir, exist_ok=True)
    os.makedirs(output_graph_dir, exist_ok=True)
    os.makedirs(output_graph_from_code_dir, exist_ok=True)
    os.makedirs(output_graph_from_json_dir, exist_ok=True)
    os.makedirs(output_json_dir, exist_ok=True)

    # Return the output sub directories
    return {
        "version": run_version,
        "output_dir": output_dir,
        "version_dir": run_version,
        "graph_dir": output_graph_dir,
        "graph_code_dir": output_graph_from_code_dir,
        "graph_json_dir": output_graph_from_json_dir,
        "json_dir": output_json_dir,
        "json_file_path": output_json_file,
    }


def get_last_dated_output_dirs():
    """Get the paths of the last dated output sub directories.

    Returns:
    --------
    str
        The path to the last dated directory in the output directory.
    """
    # Get the output directory
    output_dir = get_output_dir()

    # Get a list of all dated directories
    dated_dirs = [
        d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))
    ]

    # Sort the dated directories
    dated_dirs.sort(reverse=True)

    # Get the last dated directory
    last_dated_dir = os.path.join(output_dir, dated_dirs[0])

    # Check if the last dated directory exists, if not, raise an error
    if not os.path.exists(last_dated_dir):
        raise ValueError(
            f"The last dated directory does not exist: {os.path.join(output_dir, dated_dirs[0])}"
        )
    else:
        # Get the run version from the tail of last dated directory
        run_version: str = os.path.basename(last_dated_dir)

        # Get the output sub directories
        output_graph_dir: str = os.path.join(last_dated_dir, "graph")
        output_graph_from_code_dir: str = os.path.join(output_graph_dir, "from_code")
        output_graph_from_json_dir: str = os.path.join(output_graph_dir, "from_json")
        output_json_dir: str = os.path.join(last_dated_dir, "json")
        output_json_file: str = os.path.join(output_json_dir, JSON_GRAPH_FILE)

        # Check that all the dirs exist, if any don't, create them
        if not os.path.exists(output_graph_dir):
            os.makedirs(output_graph_dir, exist_ok=True)
        if not os.path.exists(output_graph_from_code_dir):
            os.makedirs(output_graph_from_code_dir, exist_ok=True)
        if not os.path.exists(output_graph_from_json_dir):
            os.makedirs(output_graph_from_json_dir, exist_ok=True)
        if not os.path.exists(output_json_dir):
            os.makedirs(output_json_dir, exist_ok=True)

        # Return the output sub directories
        return {
            "version": run_version,
            "output_dir": output_dir,
            "version_dir": last_dated_dir,
            "graph_dir": output_graph_dir,
            "graph_code_dir": output_graph_from_code_dir,
            "graph_json_dir": output_graph_from_json_dir,
            "json_dir": output_json_dir,
            "json_file_path": output_json_file,
        }


def get_specific_output_dirs(run_version: str = "") -> dict:
    """Get the output directories of the specified or last run_version directory.

    Parameters:
    -----------
    run_version: str (default = "")
        The run version to use. Default returns last dated directory.

    Returns:
    --------
    dict
        A dictionary of the output sub directories.
    """
    # Get the output directory
    output_dir: str = get_output_dir()

    # Get the run version
    if run_version == "":
        run_version = get_last_dated_output_dirs()
    else:
        # Check if the run version provided exists
        if not os.path.exists(os.path.join(output_dir, run_version)):
            # If it doesn't, raise an error
            raise ValueError(
                f"The run version provided does not exist: {os.path.join(output_dir, run_version)}"
            )

    # Create the other sub directories paths
    output_graph_dir: str = os.path.join(output_dir, run_version, "graph")
    output_graph_from_code_dir: str = os.path.join(output_graph_dir, "from_code")
    output_graph_from_json_dir: str = os.path.join(output_graph_dir, "from_json")
    output_json_dir: str = os.path.join(output_dir, run_version, "json")
    output_json_file: str = os.path.join(output_json_dir, JSON_GRAPH_FILE)

    # Return the output sub directories
    return {
        "version": run_version,
        "output_dir": output_dir,
        "version_dir": run_version,
        "graph_dir": output_graph_dir,
        "graph_code_dir": output_graph_from_code_dir,
        "graph_json_dir": output_graph_from_json_dir,
        "json_dir": output_json_dir,
        "json_file_path": output_json_file,
    }


OUTPUT_DIRECTORY = {"default": get_output_dir(True), "user": get_output_dir()}

OUTPUT_GROUPING = {
    "dir": OUTPUT_DIRECTORY["user"],
    "graph_dir": OUTPUT_DIRECTORY["user"] + "\CREATED_DATE\graph",
    "graph_code_dir": OUTPUT_DIRECTORY["user"] + "\CREATED_DATE\graph\\from_code",
    "graph_json_dir": OUTPUT_DIRECTORY["user"] + "\CREATED_DATE\graph\\from_json",
    "json_dir": OUTPUT_DIRECTORY["user"] + "\CREATED_DATE\json",
    "json_file_path": OUTPUT_DIRECTORY["user"] + "\CREATED_DATE\json\graph.json",
}
