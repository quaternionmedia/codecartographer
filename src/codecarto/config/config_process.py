# The saving of new config data or paths is not done by API,
# sense those are all server directories.
# So those only apply for the local pacakge use case.

import os
from ..utils.utils import load_json, save_json


CONFIG_FILE = "config.json"
DEFAULT_CONFIG_FILE = "default_config.json"

# dir is a folder. Example: C:\Users\user\AppData\Roaming\codecarto
# path is a file. Example: C:\Users\user\AppData\Roaming\codecarto\config.json
# filename is a file name. Example: config.json

def initiate_package():
    """Initiate the CodeCartographer package.

    Returns:
    --------
    dict
        The user's config data.
    """
    from .directory.appdata_dir import CODECARTO_APPDATA_DIRECTORY, APPDATA_DIRECTORY
    from ..plotter.palette_dir import get_package_palette_path, NEW_PALETTE_FILENAME, DEFAULT_PALETTE_FILENAME

    # Check if the appdata directory exists
    # This should exist, it's the system's appdata directory
    if os.path.exists(APPDATA_DIRECTORY):
        codecarto_folder_exists: bool = os.path.exists(CODECARTO_APPDATA_DIRECTORY)
        if not codecarto_folder_exists:
            # Create the codecarto appdata directory
            print("Initiate package...")
            print("Making CodeCartographr in environment folder...")
            os.makedirs(CODECARTO_APPDATA_DIRECTORY, exist_ok=True)
        
        # Check if we need to make any files
        default_palette_path:str = os.path.join(CODECARTO_APPDATA_DIRECTORY, DEFAULT_PALETTE_FILENAME)
        new_palette_path:str = os.path.join(CODECARTO_APPDATA_DIRECTORY, NEW_PALETTE_FILENAME)
        default_config_path: str = os.path.join(CODECARTO_APPDATA_DIRECTORY, DEFAULT_CONFIG_FILE)
        user_config_file: str = os.path.join(CODECARTO_APPDATA_DIRECTORY, CONFIG_FILE) 
        if not (os.path.exists(CODECARTO_APPDATA_DIRECTORY) 
                or os.path.exists(default_palette_path)
                or os.path.exists(new_palette_path)
                or os.path.exists(default_config_path)
                or os.path.exists(user_config_file)): 
            if codecarto_folder_exists:
                # If the codecarto folder exists, but the files don't,
                # print the initiate message
                print("Initiate package...")
            
            # Check we have the default palette file
            package_palette_path: str = get_package_palette_path()
            print("Loading package default palette...")
            print(f"Package default palette path {package_palette_path}")
            if not os.path.exists(package_palette_path):
                raise FileNotFoundError(
                    f"Package Missing Files: Default palette file not found at {package_palette_path}"
                )
            
            # Check if the default palette file exists in the appdata directory
            print("Creating default app data files...")
            print(f"Default palette: {default_palette_path}")
            if not os.path.exists(default_palette_path):
                # Create the default palette file in the appdata directory. 
                # This is so we have a backup of the default palette file.
                default_palette_data: dict = load_json(package_palette_path)
                save_json(default_palette_path, default_palette_data)
            
            # Check if the new palette file exists in the appdata directory
            # Shouldn't be the case that default does exist and this doesn't, but lets check. 
            print(f"User's palette: {new_palette_path}")
            if not os.path.exists(new_palette_path):
                # Create the default palette file in the appdata directory. 
                # This is so users can create their own palette file.
                default_palette_data: dict = load_json(package_palette_path)
                save_json(new_palette_path, default_palette_data)

            # Create the default/user config files
            print("Creating config files...")
            create_config_file()

            # Double check that all appdata folder and four files exist
            print(f"Default config file: {default_config_path}")
            print(f"User config file: {user_config_file}")
            if not (os.path.exists(CODECARTO_APPDATA_DIRECTORY) 
                    or os.path.exists(default_palette_path)
                    or os.path.exists(new_palette_path)
                    or os.path.exists(default_config_path)
                    or os.path.exists(user_config_file)):
                raise FileNotFoundError(
                    f"CRITICAL ERROR: Package was unable to create all necessary files and folders. Please contact the package maintainer."
                )
            
            print("Package initiated successfully!")
            



def create_user_config_file(
    config_path: str = "", palette_path: str = "", output_dir: str = ""
) -> dict:
    """Create the user config file with default values.

    Parameters:
    -----------
    config_path: str
        The path of the config file to create.
    palette_path: str
        The path of the palette file to create.
    output_dir: str
        The path of the output directory to create.

    Returns:
    --------
    dict
        The user's config data.
    """
    from .directory.appdata_dir import CODECARTO_APPDATA_DIRECTORY
    from .directory.package_dir import CODE_CARTO_PACKAGE_VERSION
    from .directory.directories import get_users_documents_dir
    from ..plotter.palette_dir import DEFAULT_PALETTE_FILENAME

    ########## CONFIG PATH ##########
    if config_path == "":
        config_path = os.path.join(CODECARTO_APPDATA_DIRECTORY, CONFIG_FILE)
    elif not os.path.exists(config_path):
        # create it if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    ########## PALETTE PATH ##########
    if palette_path == "":
        palette_name: str = DEFAULT_PALETTE_FILENAME.replace("default_", "")
        palette_path = os.path.join(CODECARTO_APPDATA_DIRECTORY, palette_name)
    elif not os.path.exists(palette_path):
        # create it if it doesn't exist and save the default palette to it
        os.makedirs(os.path.dirname(palette_path), exist_ok=True)
        default_palette_data: dict = load_json(
            os.path.join(CODECARTO_APPDATA_DIRECTORY, DEFAULT_CONFIG_FILE)
        )
        save_json(palette_path, default_palette_data["default_palette_path"])

    ########## OUTPUT DIR ##########
    if output_dir == "":
        output_dir = os.path.join(
            get_users_documents_dir(), "CodeCartographer", "output"
        )
    elif not os.path.exists(output_dir):
        # create it if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    # Create the user config file
    user_config_data: dict = {
        "version": CODE_CARTO_PACKAGE_VERSION,
        "config_path": config_path,
        "palette_path": palette_path,
        "output_dir": output_dir,
    }
    save_json(user_config_data["config_path"], user_config_data)

    return user_config_data


def create_config_file(user_config_path: str = "") -> dict:
    """Create the config file with default values.

    Parameters:
    -----------
    user_config_path: str
        The path of the config file to create.

    Returns:
    --------
    dict
        The config data.
    """
    from .directory.appdata_dir import CODECARTO_APPDATA_DIRECTORY
    from .directory.package_dir import CODE_CARTO_PACKAGE_VERSION
    from .directory.directories import get_users_documents_dir
    from ..plotter.palette_dir import DEFAULT_PALETTE_FILENAME

    # !!!! DO NOT USE CONFIG.JSON FILE FOR DEFAULTS !!!!
    #   If we're creating it, we don't want to try
    #   and get anything from the config.json file
    #   so need to create the default values
    # !!!! DO NOT USE CONFIG.JSON FILE FOR DEFAULTS !!!!

    # get the app data and package directories
    version: str = CODE_CARTO_PACKAGE_VERSION
    appdata_codecarto: str = CODECARTO_APPDATA_DIRECTORY
    default_palette_name: str = DEFAULT_PALETTE_FILENAME

    # create the default config file 
    default_config_path: str = os.path.join(appdata_codecarto, DEFAULT_CONFIG_FILE)
    default_palette_path: str = os.path.join(appdata_codecarto, default_palette_name)
    default_output_dir: str = os.path.join(
        get_users_documents_dir(), "CodeCartographer", "output"
    )
    if not os.path.exists(default_output_dir):
        os.makedirs(default_output_dir, exist_ok=True)

    # check if the user config path is valid, exists and is a json file
    if (
        user_config_path != ""
        and os.path.isfile(user_config_path)
        and user_config_path.endswith(".json")
    ):
        if os.path.exists(user_config_path):
            config_path: str = user_config_path
        else:
            # make the file if it doesn't exist
            with open(user_config_path, "w") as f:
                f.write("")
            config_path: str = user_config_path
    else:
        print(
            "Invalid user config path, using default config path.\n%APPDATA%/Roaming/CodeCartographer/config.json\n"
        )
        config_path: str = os.path.join(appdata_codecarto, CONFIG_FILE)

    default_config_data: dict = {
        "version": version,
        "default_config_path": default_config_path,
        "default_palette_path": default_palette_path,
        "default_output_dir": default_output_dir,
        "user_config_path": config_path,
    }
    save_json(default_config_path, default_config_data)

    user_config_data = create_user_config_file(config_path)

    return user_config_data


def reset_config_data(
    reset_user: bool = False, reset_output: bool = False, reset_palette: bool = False
) -> dict:
    """Remove the old config file and recreate the config file with defaults.

    Parameters:
    -----------
    reset_user: bool
        If True, reset the user config file path.
    reset_output: bool
        If True, reset the output directory.
    reset_palette: bool
        If True, reset the palette file.

    Returns:
    --------
    dict
        The reset config data.
    """
    ########## GET PREVIOUS CONFIG DATA ##########
    prev_user_config_data: dict[str:str] = get_config_data()
    prev_user_config_path = prev_user_config_data["config_path"]
    prev_user_palette_path = prev_user_config_data["palette_path"]
    prev_user_output_dir = prev_user_config_data["output_dir"]
    if os.path.exists(prev_user_config_path):
        # remove the old config file if it exists
        os.remove(prev_user_config_path)

    ########## LOAD DEFAULT CONFIG DATA ##########
    config_data: dict[str:str] = {}
    default_config_data: dict[str:str] = get_config_data(True)
    default_config_path: str = default_config_data["default_config_path"]
    default_palette_path: str = default_config_data["default_palette_path"]
    default_output_dir: str = default_config_data["default_output_dir"]
    if not os.path.exists(default_config_path):
        # create the default config file if it doesn't exist
        config_data = create_config_file()

    ########## USER CONFIG PATH ##########
    if reset_user:
        # reset the user's config file path
        default_config_data["user_config_path"] = default_config_path.replace(
            "default_", ""
        )
        user_config_path: str = default_config_data["user_config_path"]
    else:
        # keep the user's config file path
        # update the default config file with the users config path
        default_config_data["user_config_path"] = prev_user_config_path
        user_config_path: str = default_config_data["user_config_path"]
    save_json(default_config_path, default_config_data)

    ########## PALETTE PATH ##########
    if reset_palette:
        # reset the palette path
        palette_path: str = default_palette_path.replace("default_", "")
    else:
        # create the user config file
        palette_path: str = prev_user_palette_path

    ########## OUTPUT DIRECTORY ##########
    if reset_output:
        # reset the output directory
        output_dir: str = default_output_dir
    else:
        # keep the output directory
        output_dir: str = prev_user_output_dir

    # create the user config data
    user_config_data: dict = {
        "version": default_config_data["version"],
        "config_path": user_config_path,
        "palette_path": palette_path,
        "output_dir": output_dir,
    }
    save_json(user_config_data["config_path"], user_config_data)

    return config_data


def reset_config_CLI() -> dict:
    """Validate information and asks the user if they want to reset the various config properties.

    Returns:
    --------
    dict
        The reset config data.
    """
    # Check if the user is sure they want to reset config file
    user_resp: str = input(
        "\nAre you sure you want to reset the config file to default values? (y/n) : "
    )
    if user_resp.lower() == "y":
        ########## GET PREVIOUS CONFIG DATA ##########
        reset_user: bool = False
        reset_output: bool = False
        reset_palette: bool = False
        prev_user_config_data: dict[str:str] = get_config_data()
        prev_user_config_path: str = prev_user_config_data["config_path"]
        prev_user_palette_path: str = prev_user_config_data["palette_path"]
        prev_user_output_dir: str = prev_user_config_data["output_dir"]
        exists: bool = True
        pre_msg: str = "\nDo you want to KEEP your current"

        ########## USER CONFIG PATH ##########
        exists = os.path.exists(prev_user_config_path)
        msg = f"{pre_msg} config path?\nCurrent config path: {prev_user_config_path}\n"
        if not exists:
            msg += "\nWARNING: The current config file was not found! It will be created.\n"
        msg += "\nKeep the current config file path (y/n) : "
        if input(msg).lower() == "n":
            reset_user = True
        elif not exists:
            # create the config file if it doesn't exist
            create_config_file()

        ########## USER PALETTE PATH ##########
        exists = os.path.exists(prev_user_palette_path)
        msg = (
            f"{pre_msg} palette file?\nCurrent palette path: {prev_user_palette_path}\n"
        )
        if not exists:
            msg += "\nWARNING: The current palette file was not found! It will be created with default values.\n"
        msg += "\nKeep the current palette file path (y/n) : "
        if input(msg).lower() == "n":
            reset_palette = True
        elif not exists:
            # create the palette file if it doesn't exist
            os.makedirs(prev_user_palette_path, exist_ok=True)
            # copy the default palette file to the user's palette file
            default_palette_data: dict = load_json(
                get_config_data(True)["default_palette_data"]
            )
            save_json(prev_user_palette_path, default_palette_data)

        ########## USER OUTPUT DIRECTORY ##########
        exists = os.path.exists(prev_user_output_dir)
        msg = f"{pre_msg} output directory?\nCurrent output directory: {prev_user_output_dir}\n"
        if not exists:
            msg += "\nWARNING: The current output directory was not found! It will be created.\n"
        msg += "\nKeep the current output direcotry (y/n) : "
        if input(msg).lower() == "n":
            reset_output = True
        elif not exists:
            # create the output file if it doesn't exist
            os.makedirs(prev_user_output_dir, exist_ok=True)

        ########## RESET THE CONFIG DATA ##########
        return reset_config_data(
            reset_user=reset_user,
            reset_output=reset_output,
            reset_palette=reset_palette,
        )
    else:
        import sys

        print("Exiting ... \n")
        sys.exit(0)


def get_config_path(default: bool = False) -> str:
    """Return the path of the codecarto config file.

    Parameters:
    -----------
    default: bool
        Whether to return the default config file path.

    Returns:
    --------
    str
        The path of the codecarto config file.
    """
    from .directory.appdata_dir import CODECARTO_APPDATA_DIRECTORY

    # get the default config file path
    default_config_path: str = os.path.join(
        CODECARTO_APPDATA_DIRECTORY, DEFAULT_CONFIG_FILE
    )
    if not os.path.exists(default_config_path):
        create_config_file()
    default_config_data: dict = load_json(default_config_path)

    # return the config file path
    if not default:
        # returns the user's config file path
        return default_config_data["user_config_path"]
    else:
        return default_config_data["default_config_path"]


def set_config_property(property_name: str, property_value: str) -> dict:
    """Set the value of a property in the config file.

    Parameters:
    -----------
    property_name: str
        The name of the property to set.
    property_value: str
        The value of the property to set.

    Returns:
    --------
    dict
        The updated config data.
    """
    config_data: dict = {}
    try:
        # get the user's config file path from the default config file
        default_config_path: str = get_config_path(True)
        default_config_data: dict = load_json(default_config_path)
        user_config_path: str = default_config_data["user_config_path"]
        user_config_data: dict = load_json(user_config_path)

        # check if this is changing the user's config path
        new_config_path: str = ""
        if property_name == "config_path":
            new_config_path = property_value
            # if the new config path is the same as the current config path
            # then don't do anything
            if new_config_path == user_config_path:
                return user_config_data

            # check if the new config path exists
            if not os.path.exists(new_config_path):
                raise Exception(f"Provided path does not exist: {new_config_path}")
            # check if the new config path is a file
            if not os.path.isfile(new_config_path):
                raise Exception(f"Provided path is not a file: {new_config_path}")
            # check if the new config path is a JSON file
            if not new_config_path.endswith(".json"):
                raise Exception(f"Provided path is not a JSON file: {new_config_path}")

            # save the new config file
            if save_user_config_path(new_config_path, user_config_data):
                config_data = user_config_data
            else:
                raise Exception(f"Failed to save config file: {new_config_path}")
        else:
            # save the new property value in the user's config data
            user_config_data[property_name] = property_value
            save_json(user_config_path, user_config_data)
            config_data = user_config_data
    except Exception as e:
        # if it fails, likely due to save permissions
        # send exception to the console
        print(e)

    return config_data


def save_user_config_path(user_config_path: str, user_config_data: dict) -> bool:
    """Save the user's config data to the provided location.

    Parameters:
    -----------
    user_config_path: str
        The path of the user config file.

    Returns:
    --------
    bool
        If save was successful.
    """
    # Check if the user config path has been set in data dict
    if user_config_data["config_path"] != user_config_path:
        user_config_data["config_path"] = user_config_path

    # Update the default config file with the new user config path
    default_config_path = get_config_path(True)
    default_config_data = load_json(default_config_path)
    old_config_path = default_config_data["user_config_path"]
    default_config_data["user_config_path"] = user_config_path
    save_json(default_config_path, default_config_data)

    # Save the new config file
    save_json(user_config_path, user_config_data)

    # Remove the old config file
    if os.path.exists(old_config_path):
        os.remove(old_config_path)

    # Check if save was successful
    if os.path.exists(user_config_path):
        return True
    else:
        return False


def get_config_data(default: bool = False) -> dict:
    """Return the codecarto config data.

    Parameters:
    -----------
    default: bool
        Whether to return the default config data.

    Returns:
    --------
    dict
        The codecarto config data.
    """
    # get the default config file path
    default_config_path: str = get_config_path(True)
    if not os.path.exists(default_config_path):
        create_config_file()
    default_config_data: dict = load_json(default_config_path)

    # return the config data
    if not default:
        # returns the user's config file path
        return load_json(default_config_data["user_config_path"])
    else:
        return default_config_data


CONFIG_DIRECTORY = {
    "default": get_config_path(True),
    "user": get_config_path(),
}
