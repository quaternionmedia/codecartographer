import os

# from .appdata_dir import get_codecarto_appdata_dir
from .package_dir import get_package_dir


def get_config_path() -> str:
    """Return the path of the codecarto config file in appdata."""
    # _path = os.path.join(get_codecarto_appdata_dir(), "config.json")
    _path = os.path.join(get_package_dir(), "config.json")
    return _path
