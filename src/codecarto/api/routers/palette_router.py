from fastapi import APIRouter
from ...plotter.palette import Palette, Theme

PaletteRoute: APIRouter = APIRouter()

# TODO: how does each user using the API get their own palette? Is it cached on their machine? How do?


@PaletteRoute.get("/palette/get_palette")
async def get_palette() -> dict[str, str]:
    """Gets the current palette data.

    Returns:
    --------
        dict:
            The current palette data.
    """
    palette: Palette = Palette()
    return palette.get_palette_data()


@PaletteRoute.get("/palette/set_palette")
async def set_palette(palette_file_path: str) -> dict[str, str]:
    """Sets the palette to use for plots

    Parameters:
    -----
        palette_file_path (str):
            The path to the palette file.

    Returns:
    --------
        dict:
            The new palette data.
    """
    palette: Palette = Palette()
    palette.set_palette(palette_file_path)
    return palette.get_palette_data()


@PaletteRoute.get("/palette/reset_palette")
async def reset_palette() -> dict[str, str]:
    """Resets the palette to the default.

    Returns:
    --------
        dict:
            The current palette data.
    """
    palette: Palette = Palette()
    palette.reset_palette()
    return palette.get_palette_data()


@PaletteRoute.get("/palette/add_theme")
async def add_theme(
    node_type: str,
    base: str,
    label: str,
    shape: str,
    color: str,
    size: str,
    alpha: str,
) -> dict[str, str]:
    """Creates a new theme.

    Parameters:
    -----
        node_type (str):
            The type of node to create a theme for.
        base (str):
            The base color of the theme.
        label (str):
            The label color of the theme.
        shape (str):
            The shape color of the theme.
        color (str):
            The color color of the theme.
        size (str):
            The size color of the theme.
        alpha (str):
            The alpha color of the theme.

    Returns:
    --------
        dict:
            The current palette data.
    """
    theme = Theme(node_type, base, label, shape, color, size, alpha)
    palette: Palette = Palette()
    palette.create_new_theme(theme)
    return palette.get_palette_data()
