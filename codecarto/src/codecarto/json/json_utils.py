import os
import json


def load_json_data(file_path) -> dict:
    """Load data from a json file.

    Parameters:
    -----------
    file_path : str
        The path to the file to load.

    Returns:
    --------
    dict
        The data loaded from the file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "r") as f:
        # check if file is empty
        if len(f.read()) > 0:
            # reset file pointer to beginning of file
            f.seek(0)
            return json.load(f)
        else:
            # file is empty
            file_name = os.path.basename(file_path)
            raise ValueError(f"JSON File Empty: {file_name}")


def save_json_data(file_path, data):
    """Save data to a json file.

    Parameters:
    -----------
    file_path : str
        The path to the file to save.
    data : dict
        The data to save to the file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
