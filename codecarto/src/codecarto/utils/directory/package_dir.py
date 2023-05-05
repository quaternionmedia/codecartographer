import os
from importlib_metadata import version

CODE_CARTO_PACKAGE_NAME = "codecarto"
CODE_CARTO_PACKAGE_VERSION = version(CODE_CARTO_PACKAGE_NAME)


def get_package_dir() -> str:
    """Return the directory of the codecarto package."""
    # this file is in the directory
    # codecarto\src\codecarto\utils\directory <--- this directory level
    # so we need to go up 3 directories to get to the codecarto package directory
    # codecarto\src\codecarto <--- this directory level
    package_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if os.path.basename(package_dir) == CODE_CARTO_PACKAGE_NAME:
        return package_dir
    else:
        return None
