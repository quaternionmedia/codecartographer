import tempfile
from pathlib import Path

from codecarto import Palette, ErrorHandler, Directory as Dir 


def test_palette():
    """Test Palette class functions."""
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a new Palette object
            paletteHandler:Palette = Palette()
            palette = paletteHandler.palette

            # Test save, load, and get_palette_data methods
            palette.save_palette()
            palette.load_palette()
            palette_data = palette.get_palette_data()
            assert palette_data is not None

            # Test create_new_theme method
            new_node_type = "custom_node"
            new_theme = palette.create_new_theme(
                node_type=new_node_type,
                base="basic",
                label="Custom Label",
                shape="o",
                color="white",
                size=5,
                alpha=5,
            )
            assert new_theme == new_node_type

            # Test get_node_style method
            node_style = palette.get_node_styles(new_node_type)
            assert node_style is not None

            # Test get_node_styles method
            node_styles = palette.get_node_styles()
            assert node_styles is not None
            assert new_node_type in node_styles

            # Test reset_palette method
            palette.reset_palette()
            reset_palette_data = palette.get_palette_data()
            assert reset_palette_data is not None
            assert new_node_type not in reset_palette_data["bases"]

            # Test import_palette and export_palette methods
            with tempfile.NamedTemporaryFile(
                dir=temp_dir, suffix=".json", delete=False
            ) as temp_file:
                palette_file = Path(temp_file.name)
                with palette_file.open("w") as dest, open(
                    palette._palette_pack_dir["path"], "r"
                ) as src:
                    dest.write(src.read())
            palette.import_palette(palette_file)
            exported_file = palette.export_palette(temp_dir)
            assert exported_file.exists()

            # Check if the exported file is the same as palette._palette_pack_dir["path"]
            with palette_file.open("r") as f:
                palette_file_data = f.read()
            with exported_file.open("r") as f:
                exported_file_data = f.read()
            assert palette_file_data == exported_file_data

            # Test ThemeNotFoundError
            try:
                palette.get_node_styles("nonexistent_node_type")
            except ErrorHandler.ThemeNotFoundError:
                pass
            else:
                raise Exception("ThemeNotFoundError not raised")
    except Exception as e:
        # Raise exception
        raise e
