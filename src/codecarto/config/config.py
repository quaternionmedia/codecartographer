import os
from ..polygraph.json_utils import load_json_file, save_json_file
from .config_dir import (
    create_config_file,
    reset_config_data,
    get_config_path,
)


class Config:
    def __init__(self):
        """Initialize the config object to write to JSON file."""
        self.config_data = {}
        self.config_path = self.get_config_path()  # appdata config file path
        if not os.path.exists(self.config_path):
            self.create_config_file()  # create the config file
        self.load_config_data()  # load the config data from the config file

    def create_config_file(self) -> dict:
        """Create the config file.

        Returns:
        --------
        dict
            The config data.
        """
        self.config_data = create_config_file()
        self.save_config_data()
        return self.config_data

    def reset_config_data(self) -> dict:
        """Recreate the config data.

        Returns:
        --------
        dict
            The config data.
        """
        self.config_data = reset_config_data()
        self.save_config_data()
        return self.config_data

    def load_config_data(self) -> dict:
        """Load the config data from the config file.

        Returns:
        --------
        dict
            The config data.
        """
        self.config_data = load_json_file(self.config_path)
        return self.config_data

    # TODO: likely unused as the 'set_config_property' method saves the config data
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
                config_path = self.config_path
            # try to set the value of the property in the appdata config file
            save_json_file(config_path, self.config_data)
        except Exception as e:
            # if it fails, likely due to save permissions
            # send exception to the console
            print(e)
        finally:
            return self.config_data

    # unlikely to be used much, as the config class has a config_path attribute
    def get_config_path(self) -> str:
        """Return the path of the codecarto config file.

        Returns:
        --------
        str
            The path of the codecarto config file.
        """
        return get_config_path()

    def set_config_property(self, property_name: str, property_value: str):
        """Set the value of a property in the config file.

        Parameters:
        -----------
        property_name: str
            The name of the property to set.
        property_value: str
            The value of the property to set.

        Returns:
        --------
        Any
            The value of the property that was set.
        """
        try:
            # set the value of the property in the package config file
            config_path: str = self.get_config_path()
            self.config_data[property_name] = property_value
            # try to set the value of the property in the appdata config file
            save_json_file(config_path, self.config_data)
        except Exception as e:
            # if it fails, likely due to save permissions
            # send exception to the console
            print(e)
        finally:
            return self.config_data[property_name]
