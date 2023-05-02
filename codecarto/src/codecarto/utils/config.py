import os


class Config:
    def __init__(self):
        """Initialize the config object to write to JSON file."""
        from .directory.config_dir import get_config_path

        self.config_data = {}
        self.config_path = get_config_path()
        if not os.path.exists(self.config_path):
            self.create_config_file()
        else:
            self.load_config_data()

    def create_config_file(self):
        """Create the config file if it doesn't exist."""
        from .directory.package_dir import CODE_CARTO_PACKAGE_VERSION
        from .directory.output_dir import get_default_output_dir

        self.config_data["config_path"] = self.config_path
        self.config_data["version"] = CODE_CARTO_PACKAGE_VERSION
        self.config_data["output_dir"] = get_default_output_dir()
        self.save_config_data()

    def save_config_data(self):
        from ..json.json_utils import save_json_data

        """Save the class' config_data to the config file."""
        save_json_data(self.config_path, self.config_data)

    def load_config_data(self):
        from ..json.json_utils import load_json_data

        """Load the config data, to the class' config_data, from the config file."""
        self.config_data = load_json_data(self.config_path)
