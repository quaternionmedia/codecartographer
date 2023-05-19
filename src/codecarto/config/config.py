import os

from ..json.json_utils import load_json_data, save_json_data

#TODO: Need to be setting up default_config and config files when the package is installed.

class Config:
    def __init__(self):
        """Initialize the config object to write to JSON file."""
        self.config_data = {}
        self.config_path = self.get_config_path()
        if not os.path.exists(self.config_path):
            self.reset_config_data()
        else:
            self.load_config_data()

    def reset_config_data(self):
        """Initialize the config data."""
        from ..utils.directory.config_dir import reset_config_data

        self.config_data = reset_config_data()
        self.save_config_data()

    def save_config_data(self, config_path: str = None):
        """Save the class' config_data to the config file.

        Parameters:
        -----------
        config_path: str
            The path of the config file to save the config data to.
            Default uses the package config file path.
        """
        if config_path is None:
            config_path = self.config_path

        save_json_data(config_path, self.config_data)

    def load_config_data(self):
        """Load the config data, to the class' config_data, from the config file."""
        self.config_data = load_json_data(self.config_path)

    def get_config_path(self, package_dir: bool = True) -> str:
        """Return the path of the codecarto config file.

        Parameters:
        -----------
        package_dir: bool
            If True, return the path of the config file in the package directory.
            If False, return the path of the config file in the appdata directory.

        Returns:
        --------
        str
            The path of the codecarto config file.
        """
        from ..utils.directory.config_dir import get_config_path

        return get_config_path(package_dir)

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
        # set the value of the property in the package config file
        config_path: str = self.get_config_path(package_dir = True)
        self.config_data[property_name] = property_value
        save_json_data(config_path, self.config_data)

        try:
            # try to set the value of the property in the appdata config file
            config_path: str = self.get_config_path(False)
            save_json_data(config_path, self.config_data)
        except:
            pass

        return self.config_data[property_name]
