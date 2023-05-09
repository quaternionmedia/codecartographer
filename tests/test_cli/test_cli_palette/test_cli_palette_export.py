import os
import json 
import subprocess
import tempfile
from cli_palette_helper import get_palette_data


def test_palette_export():
    """Test the palette export command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # create a temporary file
        temp_file = os.path.join(temp_dir, "test_palette_export.json")

        # define commands
        commands = [
            ["codecarto", "palette", "-e", temp_file],
            ["codecarto", "palette", "--export", temp_file],
        ]

        # run commands
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True)
            assert "Palette exported to " in result.stdout

        # get the default palette
        palette_path = get_palette_data("path", False)

        # check if the palette file is the same as the default palette
        with open(palette_path, "r") as f:
            default_palette = json.load(f)
        with open(temp_file, "r") as f:
            exported_palette = json.load(f)
        assert default_palette == exported_palette
