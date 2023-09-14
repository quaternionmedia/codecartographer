import os
from importlib_metadata import version

CODE_CARTO_PACKAGE_NAME = "codecarto"
CODE_CARTO_PACKAGE_VERSION = version(CODE_CARTO_PACKAGE_NAME)


def get_package_dir() -> str:
    """Return the directory of the codecarto package."""
    # this file is in the directory
    # codecarto\src\codecarto\config\directory\ <--- this directory level
    # so we need to go up 2 directories to get to the codecarto package directory
    # codecarto\src\codecarto <--- this directory level

    # abspath, dirname, dirname, dirname
    # filename, directory, config, codecarto
    package_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if os.path.basename(package_dir) == CODE_CARTO_PACKAGE_NAME:
        return package_dir
    else:
        return None


PACKAGE_DIRECTORY = get_package_dir()


def get_processor_path() -> str:
    """Get the real path to the main file.

    Returns:
    --------
    str
        The real path to the main file.
    """
    main_file_path = os.path.realpath(os.path.join(get_package_dir(), "processor.py"))
    if not os.path.exists(main_file_path):
        raise RuntimeError("Main package file not found. Package may be corrupted.")
    return main_file_path


PROCESSOR_FILE_PATH = get_processor_path()
