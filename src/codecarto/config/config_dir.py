import os

CONFIG_FILE = "config.json"


def create_config_file() -> dict:
    """Create the config file with default values.

    Returns:
    --------
    dict
        The config data.
    """
    from ..utils.directory.package_dir import get_package_dir
    from ..utils.directory.palette_dir import PALETTE_FILE, get_palette_appdata_dir
    from ..polygraph.json_utils import save_json_file

    # create the default output dir
    upper_codecarto_dir: str = os.path.dirname(os.path.dirname(get_package_dir()))
    default_output_dir: str = os.path.join(upper_codecarto_dir, "output")
    if not os.path.exists(default_output_dir):
        os.makedirs(default_output_dir, exist_ok=True)

    # create the config path
    config_path: str = get_config_path()

    # create the config data
    config_data: dict = {
        "version": "0.0.0",
        "default_config_path": config_path,
        "default_palette_path": get_palette_appdata_dir(),
        "default_output_dir": default_output_dir,
        "config_path": config_path,
        "palette_dir": get_palette_appdata_dir,
        "output_dir": default_output_dir,
        "palette_file_name": PALETTE_FILE,
    }
    save_json_file(config_path, config_data)
    return config_data


def reset_config_data() -> dict:
    """Recreate the config data.

    Returns:
    --------
    dict
        The config data.
    """
    # if it exists, delete the current config file
    if os.path.exists(get_config_path()):
        os.remove(get_config_path())

    return create_config_file()


def get_config_path() -> str:
    """Return the path of the codecarto config file.

    Returns:
    --------
    str
        The path of the codecarto config file.
    """
    from ..utils.directory.appdata_dir import get_codecarto_appdata_dir

    return os.path.join(get_codecarto_appdata_dir(), "config.json")


CONFIG_APPDATA_DIRECTORY = {
    "name": CONFIG_FILE,
    "dir": os.path.dirname(get_config_path()),
    "path": get_config_path(),
}

CONFIG_DIRECTORY = {
    "appdata": CONFIG_APPDATA_DIRECTORY,
    "default": CONFIG_APPDATA_DIRECTORY,
}
