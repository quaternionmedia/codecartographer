import os
from .package_dir import get_package_dir

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


MAIN_DIRECTORY = get_main_file_dirs_dict()
