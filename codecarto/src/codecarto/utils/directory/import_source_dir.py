import os


def find_starting_file(source_files: list):
    # Prioritize user-specified starting file
    user_specified_file = os.environ.get("STARTING_FILE")
    if user_specified_file:
        for source_file in source_files:
            source_file_name = os.path.basename(source_file)
            if source_file_name == user_specified_file:
                if os.path.exists(source_file):
                    return source_file

    # Heuristics to guess the starting file
    possible_starting_files = [
        "main.py",
        "app.py",
        "__init__.py",
        "run.py",
        "cli.py",
        "application.py",
    ]
    for possible_starting_file in possible_starting_files:
        for source_file in source_files:
            source_file_name = os.path.basename(source_file)
            if source_file_name == possible_starting_file:
                if os.path.exists(source_file):
                    return source_file

    # If no Python files found, return None
    return None


def find_top_level_directory(file_path):
    current_dir = os.path.dirname(file_path)
    last_dir_with_init = None

    while os.path.exists(os.path.join(current_dir, "__init__.py")):
        last_dir_with_init = current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir

    return last_dir_with_init or current_dir


def get_all_source_files(starting_file_path) -> list:
    top_level_directory = find_top_level_directory(starting_file_path)
    source_files: list = []
    for root, _, files in os.walk(top_level_directory):
        for file in files:
            if file.endswith(".py"):
                source_files.append(os.path.join(root, file))
    return source_files


def get_file_source_directory(file_path) -> dict:
    # source_files = get_all_source_files(file_path)
    # top_level_directory = find_top_level_directory(file_path)
    # starting_file = find_starting_file(top_level_directory)

    # return {
    #     "start_file": starting_file,
    #     "top_level_directory": top_level_directory,
    #     "source_files": source_files,
    # }
    pass
