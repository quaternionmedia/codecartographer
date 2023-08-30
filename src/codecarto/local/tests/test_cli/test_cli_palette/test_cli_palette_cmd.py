import os
import json
import subprocess
import tempfile
from cli_palette_helper import get_palette_data


# # print themes by base
# for base, node_types in base_themes.items():
#     max_width = max(len(prop) for prop in palette_data.keys()) + 1
#     print(f"{'Base     ':{max_width}}: {base}")
#     for prop in palette_data.keys():
#         if prop != "bases":
#             print(f"  {prop:{max_width}}: {palette_data[prop][base]}")
#     print()
# print(
#     f"\nBase themes and properties can be found in 'palette.json': {palette._palette_user_path}\n"
# )


def test_palette():
    """Test the palette command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result = subprocess.run(
            ["codecarto", "palette"], capture_output=True, text=True
        )

        # define the expected strings
        palette_path = get_palette_data("path")
        expected_strings = [
            f"Base themes and properties can be found in 'palette.json': {palette_path}"
        ]

        # check if the expected strings are in the output
        for string in expected_strings:
            assert string in result.stdout

        # Load palette data
        palette_data = get_palette_data("bases")

        # Group the themes by base
        base_themes: dict[str, list] = {}
        for node_type in palette_data["bases"].keys():
            base = palette_data["bases"][node_type]
            if base not in base_themes:
                base_themes[base] = []
            base_themes[base].append(node_type)

        # print themes by base
        for base, node_types in base_themes.items():
            max_width = max(len(prop) for prop in palette_data.keys()) + 1
            assert f"{'Base     ':{max_width}}: {base}" in result.stdout
            for prop in palette_data.keys():
                if prop != "bases":
                    assert (
                        f"  {prop:{max_width}}: {palette_data[prop][base]}"
                        in result.stdout
                    )
            assert "\n" in result.stdout
        assert "\n" in result.stdout

        # check the config file to make sure it didn't change during printing
        # get the config file in the \src\codecarto\ directory
        config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "src\\codecarto\\config.json",
        )
        with open(config_file, "r") as f:
            config = json.load(f)
        # check if the output directory is the same as the one in the config file
        assert config["palette_path"] == palette_path

        # # check if the base style string is in the output
        # assert data in result.stdout
