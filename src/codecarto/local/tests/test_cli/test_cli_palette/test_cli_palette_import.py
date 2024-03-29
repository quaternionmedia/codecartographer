import os
import json
import shutil
import subprocess
import tempfile
from cli_palette_helper import get_palette_data


def test_palette_import():
    """Test the palette import command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # create a temporary file
        temp_file = os.path.join(temp_dir, "test_palette_import.json")

        # get the default palette
        palette_path = get_palette_data("path", False)

        # copy the default palette to the temporary directory
        shutil.copy(palette_path, temp_file)

        # define commands
        commands = [
            ["codecarto", "palette", "-i", temp_file],
            ["codecarto", "palette", "--import", temp_file],
        ]

        # run commands
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True)
            assert "Palette imported from " in result.stdout

        # check if the palette file is the same as the default palette
        with open(palette_path, "r") as f:
            default_palette = json.load(f)
        with open(temp_file, "r") as f:
            imported_palette = json.load(f)
        assert default_palette == imported_palette
