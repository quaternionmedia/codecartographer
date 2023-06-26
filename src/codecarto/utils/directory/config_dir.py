import os


DEFAULT_CONFIG_FILE = "default_config.json"
CONFIG_FILE = "config.json"


def reset_config_data() -> dict:
    """Initialize the config data.

    Returns:
    --------
    dict
        The config data.
    """
    from pkg_resources import get_distribution
    from .palette_dir import get_palette_package_file_path
    from .palette_dir import PALETTE_FILE, get_palette_appdata_dir
    from ...json.json_utils import save_json_file
    from .main_dir import get_main_dir

    # create the default output dir
    upper_codecarto_dir: str = os.path.dirname(os.path.dirname(get_main_dir()))
    default_output_dir: str = os.path.join(upper_codecarto_dir, "output")
    if not os.path.exists(default_output_dir):
        os.makedirs(default_output_dir, exist_ok=True)

    # create the config path
    config_path: str = get_default_config_path()

    # create the config data
    config_data: dict = {
        "version": get_distribution("codecarto").version,
        "default_config_path": config_path,
        "default_palette_path": get_palette_package_file_path(),
        "default_output_dir": default_output_dir,
        "config_path": config_path,
        "palette_file_name": PALETTE_FILE,
        "palette_dir": get_palette_appdata_dir(),
        "output_dir": default_output_dir,
    }
    save_json_file(config_path, config_data)
    return config_data


def get_default_config_path() -> str:
    """Return the path of the default config file path.

    Returns:
    --------
    str
        The path of the default config file path.
    """
    from .package_dir import get_package_dir

    config_dir = os.path.join(get_package_dir(), "config\\default_config.json")
    if not os.path.exists(config_dir):
        raise RuntimeError("Config directory not found. Package may be corrupted.")
    return config_dir


def get_config_path(package: bool = True) -> str:
    """Return the path of the codecarto config file.

    Parameters:
    -----------
    package: bool
        If True, return the path of the config file in the package directory.
        If False, return the path of the config file in the appdata directory.

    Returns:
    --------
    str
        The path of the codecarto config file.
    """
    from .appdata_dir import get_codecarto_appdata_dir
    from .package_dir import get_package_dir

    _path: str = ""
    if package:
        _path = os.path.join(get_package_dir(), "config.json")
    else:
        _path = os.path.join(get_codecarto_appdata_dir(), "config.json")
    return _path


CONFIG_APPDATA_DIRECTORY = {
    "name": CONFIG_FILE,
    "dir": os.path.dirname(get_config_path(False)),
    "path": get_config_path(False),
}
CONFIG_PACKAGE_DIRECTORY = {
    "name": CONFIG_FILE,
    "dir": os.path.dirname(get_config_path()),
    "path": get_config_path(),
}
CONFIG_DEFAULT_DIRECTORY = {
    "name": DEFAULT_CONFIG_FILE,
    "dir": os.path.dirname(get_default_config_path()),
    "path": get_default_config_path(),
}
CONFIG_DIRECTORY = {
    "appdata": CONFIG_APPDATA_DIRECTORY,
    "package": CONFIG_PACKAGE_DIRECTORY,
    "default": CONFIG_DEFAULT_DIRECTORY,
}
