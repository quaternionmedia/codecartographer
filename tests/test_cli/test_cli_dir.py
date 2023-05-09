import subprocess
import tempfile


def test_dir():
    """Test the dir command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        command = ["codecarto", "dir"]
        result = subprocess.run(command, capture_output=True, text=True)

        # Check if certain strings are in the directory section
        expected_strings = [
            "appdata_dir",
            "codecarto_appdata_dir",
            "package_dir",
            "config_dirs",
            "main_dirs",
            "palette_dirs",
            "output_dirs",
            "version",
            "output_dir",
            "version_dir",
            "graph_dir",
            "graph_code_dir",
            "graph_json_dir",
            "json_dir",
            "json_graph_file_path",
            "Package Source Python Files:",
        ]
        for string in expected_strings:
            assert string in result.stdout

        # Check if key files are in the package source files section
        key_files = [
            "errors.py",
            "parser.py",
            "plotter.py",
            "processor.py",
            "palette.py",
            "json_graph.py",
            "json_utils.py",
            "cli.py",
            "config.py",
            "directories.py",
            "utils.py",
            "appdata_dir.py",
            "config_dir.py",
            "import_source_dir.py",
            "main_dir.py",
            "output_dir.py",
            "package_dir.py",
            "palette_dir.py",
        ]
        for string in key_files:
            assert string in result.stdout
