import subprocess
import tempfile
from palette_helper import get_palette_data


def test_palette(session):
    """Test the palette command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        session.install(".")
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
        data: str = ""
        for base, node_types in base_themes.items():
            max_width = max(len(prop) for prop in palette_data.keys()) + 1
            data += f"{'Base     ':{max_width}}: {base}\n"
            for prop in palette_data.keys():
                if prop != "bases":
                    data += f"  {prop:{max_width}}: {palette_data[prop][base]}\n"

        # check if the base style string is in the output
        assert data in result.stdout
