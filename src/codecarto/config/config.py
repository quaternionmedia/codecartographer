from .config_process import (
    load_json,
    save_json,
    get_config_path,
    create_config_file,
    reset_config_data,
)


class Config:
    def __init__(self):
        """Initialize the config object to write to JSON file."""
        default_config_path = get_config_path(True)
        default_config_data = load_json(default_config_path)
        user_config_path = default_config_data["user_config_path"]
        self.config_data = load_json(user_config_path)

    def create_config_file(self) -> dict:
        """Create the config file.

        Returns:
        --------
        dict
            The config data.
        """
        self.config_data = create_config_file()
        return self.config_data

    def reset_config_data(self) -> dict:
        """Recreate the config data to default.

        Returns:
        --------
        dict
            The config data.
        """
        self.config_data = reset_config_data()
        return self.config_data

    def reload_config_data(self) -> dict:
        """Reload the config data from the config file.

        Returns:
        --------
        dict
            The config data.
        """
        default_config_path: str = get_config_path(True)
        default_config_data: dict = load_json(default_config_path)
        self.config_data = load_json(default_config_data["user_config_path"])
        return self.config_data

    def save_config_data(self, config_path: str = None) -> dict:
        """Save the config data to the config file.

        Parameters:
        -----------
        config_path: str
            The path of the config file to save the config data to.

        Returns:
        --------
        dict
            The config data.
        """
        try:
            if config_path is None:
                config_path = self.config_data["config_path"]
            # try to set the value of the property in the appdata config file
            save_json(config_path, self.config_data)
        except Exception as e:
            # if it fails, likely due to save permissions
            # send exception to the console
            print(e)
        finally:
            return self.config_data

    def set_config_property(self, property_name: str, property_value: str) -> dict:
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
        try:
            # set the value of the property in the package config file
            config_path: str = self.config_data["config_path"]
            self.config_data[property_name] = property_value
            # try to set the value of the property in the appdata config file
            save_json(config_path, self.config_data)
        except Exception as e:
            # if it fails, likely due to save permissions
            # send exception to the console
            print(e)
        finally:
            return self.config_data
