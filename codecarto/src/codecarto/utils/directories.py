def get_all_directories() -> dict:
    """Get all the directories.

    Returns:
    --------
    dict
        All the directories.
    """
    from .directory.appdata_dir import get_codecarto_appdata_dir, get_appdata_dir
    from .directory.package_dir import get_package_dir
    from .directory.config_dir import get_config_path
    from .directory.palette_dir import PALETTE_DIRECTORY
    from .directory.output_dir import OUTPUT_DIRECTORY
    from .directory.main_dir import MAIN_DIRECTORY

    return {
        "appdata_dir": get_appdata_dir(),
        "codecarto_appdata_dir": get_codecarto_appdata_dir(),
        "package_dir": get_package_dir(),
        "config_path": get_config_path(),
        "main_dirs": MAIN_DIRECTORY,
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
