import os


def get_date_time_file_format():
    """Get the current date and time in a file format.

    Returns:
    --------
    str
        The current date and time in a file format.
        Format: MM-DD-YY_HH-MM-SS
    """
    from datetime import datetime

    return datetime.now().strftime("%m-%d-%y_%H-%M-%S")


def check_file_path(file_path):
    """Check if a file path is valid.

    Parameters:
    -----------
    file_path : str
        The path to the file to check.

    Raises:
    -------
    ValueError
        If the file path is invalid.
    """
    # check if path exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    # check if file is a file
    if not os.path.isfile(file_path):
        raise ValueError(f"Invalid file path: {file_path}")
    return True
