import os
import shutil
import tempfile

from codecarto.src.codecarto.palette.palette import Palette
from codecarto.src.codecarto.errors import ThemeNotFoundError


def test_palette():
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Initialize a new Palette object
        palette = Palette()

        # Test save, load, and get_palette_data methods
        palette.save()
        palette.load()
        palette_data = palette.get_palette_data()
        assert palette_data is not None

        # Test create_new_theme method
        new_node_type = "custom_node"
        new_theme = palette.create_new_theme(
            node_type=new_node_type,
            base="basic",
            label="Custom Label",
            shape="o",
            size=5,
            color="white",
            alpha=5,
        )
        assert new_theme == new_node_type

        # Test get_node_style method
        node_style = palette.get_node_style(new_node_type)
        assert node_style is not None

        # Test get_node_styles method
        node_styles = palette.get_node_styles()
        assert node_styles is not None
        assert new_node_type in node_styles

        # Test get_node_types method
        node_types = palette.get_node_types()
        assert new_node_type in node_types

        # Test get_bases method
        bases = palette.get_bases()
        assert new_node_type in bases

        # Test reset_palette method
        palette.reset_palette()
        reset_palette_data = palette.get_palette_data()
        assert reset_palette_data is not None
        assert new_node_type not in reset_palette_data["bases"]

        # Test import_palette and export_palette methods
        palette_file = os.path.join(temp_dir, "palette.json")
        shutil.copy(palette._palette_pack_dir["path"], palette_file)
        palette.import_palette(palette_file)
        exported_file = palette.export_palette(temp_dir)
        assert os.path.exists(exported_file)

        # Check if the exported file is the same as palette._palette_pack_dir["path"]
        with open(palette_file, "r") as f:
            palette_file_data = f.read()
        with open(exported_file, "r") as f:
            exported_file_data = f.read()
        assert palette_file_data == exported_file_data

        # Test ThemeNotFoundError
        try:
            palette.get_node_style("nonexistent_node_type")
        except ThemeNotFoundError:
            pass
        else:
            raise Exception("ThemeNotFoundError not raised")
    except Exception as e:
        raise e
    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir)
