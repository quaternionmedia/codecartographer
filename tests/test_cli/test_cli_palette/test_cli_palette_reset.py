import json
import subprocess
import tempfile
from cli_palette_helper import get_palette_data


def test_palette_reset():
    """Test the palette reset command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # define commands
        commands = [
            ["codecarto", "palette", "-r"],
            ["codecarto", "palette", "--reset"],
        ]

        # run commands
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True)
            assert "Palette reset to default." in result.stdout

        # get the default palette
        default_palette_path = get_palette_data("path", False)

        # get the appdata palette
        appdata_palette_path = get_palette_data("path")

        # check if the palette file is the same as the default palette
        with open(default_palette_path, "r") as f:
            default_palette = json.load(f)
        with open(appdata_palette_path, "r") as f:
            appdata_palette = json.load(f)
        assert default_palette == appdata_palette
