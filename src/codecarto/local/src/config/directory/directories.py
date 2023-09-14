# TODO: import all directory files here to make it easier to import them from other files
# TODO: rework all directory files, i feel like there is a lot of duplicated code
import os


def get_all_directories() -> dict:
    """Get all the directories.

    Returns:
    --------
    dict
        All the directories.
    """
    from .appdata_dir import CODECARTO_APPDATA_DIRECTORY, APPDATA_DIRECTORY
    from .package_dir import PACKAGE_DIRECTORY, PROCESSOR_FILE_PATH
    from ...plotter.palette_dir import PALETTE_DIRECTORY
    from .output_dir import OUTPUT_DIRECTORY, OUTPUT_GROUPING
    from ...config.config_process import CONFIG_DIRECTORY

    return {
        "appdata_dir": APPDATA_DIRECTORY,
        "codecarto_appdata_dir": CODECARTO_APPDATA_DIRECTORY,
        "package_dir": PACKAGE_DIRECTORY,
        "processor_file": PROCESSOR_FILE_PATH,
        "config_dirs": CONFIG_DIRECTORY,
        "palette_dirs": PALETTE_DIRECTORY,
        "output_dirs": OUTPUT_DIRECTORY,
        "output_grouping": OUTPUT_GROUPING,
    }


def print_all_directories(directory: dict = None, indent: str = "") -> dict:
    """Print all the directories.

    Parameters:
    -----------
    directory: dict
        The directory to print.
    indent: str
        The indent to use.

    Returns:
    --------
    dict
        The directories.
    """
    if directory is None:
        directory = get_all_directories()

    # get directories and the max width of the keys
    max_width = max([len(key) for key in directory.keys()]) + 1

    # print the directories
    if indent == "":
        print()
    for key, value in directory.items():
        if isinstance(value, dict) and value != {}:
            # print the key then recursively call the function
            print(f"{indent}{key}:")
            print_all_directories(value, f"{indent}\t")
        else:
            print(f"{indent}{key:<{max_width}}: {value}")
    if indent == "":
        print()

    return directory


def get_users_documents_dir() -> str:
    """Get the path to the user's documents directory.

    Returns:
    --------
    str
        The path to the user's documents directory.
    """
    return os.path.expanduser("~\\Documents")
