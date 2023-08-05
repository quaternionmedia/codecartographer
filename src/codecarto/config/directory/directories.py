# TODO: import all directory files here to make it easier to import them from other files
# TODO: rework all directory files, i feel like there is a lot of duplicated code


def get_all_directories() -> dict:
    """Get all the directories.

    Returns:
    --------
    dict
        All the directories.
    """
    from .appdata_dir import CODECARTO_APPDATA_DIRECTORY, APPDATA_DIRECTORY
    from .package_dir import PACKAGE_DIRECTORY
    from .palette_dir import PALETTE_DIRECTORY
    from .output_dir import OUTPUT_DIRECTORY
    from ...config.config_dir import CONFIG_DIRECTORY
    from .main_dir import MAIN_DIRECTORY

    return {
        "appdata_dir": APPDATA_DIRECTORY,
        "codecarto_appdata_dir": CODECARTO_APPDATA_DIRECTORY,
        "package_dir": PACKAGE_DIRECTORY,
        "config_dirs": CONFIG_DIRECTORY,
        "main_dirs": MAIN_DIRECTORY,
        "palette_dirs": PALETTE_DIRECTORY,
        "output_dirs": OUTPUT_DIRECTORY,
    }


def print_all_directories(
    directory: dict = get_all_directories(), indent: str = ""
) -> dict:
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

    return directory
