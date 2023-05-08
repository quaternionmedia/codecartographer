import subprocess
import tempfile
from palette_helper import get_palette_data


def test_palette_types():
    with tempfile.TemporaryDirectory() as temp_dir:
        # define commands
        commands = [
            ["codecarto", "palette", "-t"],
            ["codecarto", "palette", "--types"],
        ]

        # define expected strings
        expected_strings = [
            "Node types and properties:",
            "Information:",
            "For a list of valid types      : https://docs.python.org/3/library/ast.html#abstract-grammar",
            "for a list of valid colors     : https://matplotlib.org/stable/gallery/color/named_colors.html",
            "for a list of valid shapes     : https://matplotlib.org/stable/api/markers_api.html",
        ]

        # run commands
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True)
            for string in expected_strings:
                assert string in result.stdout

            # Check that the bases are in the output
            palette_data = get_palette_data("bases")

            # Print node types
            data: str = ""
            for node_type in sorted(palette_data["bases"].keys()):
                base = palette_data["bases"][node_type]
                max_width = max(len(prop) for prop in palette_data.keys()) + 1
                data += f"{'Node_Type':{max_width}}  : {node_type}\n"
                data += f"    {'base':{max_width}}: {base}\n"
                for prop in palette_data.keys():
                    if prop != "bases":
                        data += f"    {prop:{max_width}}: {palette_data[prop][base]}\n"

            # check if the base style string is in the output
            assert data in result.stdout
