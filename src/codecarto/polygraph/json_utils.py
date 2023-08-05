import os
import json


def load_json_file(file_path) -> dict:
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
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON data in file '{file_path}': {str(e)}") from e
    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid JSON data in file '{file_path}': expected dictionary"
        )
    return data


def save_json_file(file_path, data):
    """Save data to a json file.

    Parameters:
    -----------
    file_path : str
        The path to the file to save.
    data : dict
        The data to save to the file.
    """
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
