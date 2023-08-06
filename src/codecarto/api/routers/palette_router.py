from fastapi import APIRouter
from codecarto import Palette, Theme

router: APIRouter = APIRouter()

# TODO: how does each user using the API get their own palette? Is it cached on their machine? How do?

@router.get("/palette/get_palette") 
async def get_palette() -> dict[str, str]:
    """Gets the current palette data.

    Returns:
    --------
        dict:
            The current palette data.
    """
    return Palette.get_palette()

@router.post("/palette/set_palette")
async def set_palette(palette_file_path: str):
    """Sets the palette to use for plots

    Parameters:
    -----
        palette_file_path (str):
            The path to the palette file. 
    """
    Palette.set_palette(palette_file_path)
 
@router.get("/palette/reset_palette")
async def reset_palette() -> dict[str, str]:
    """Resets the palette to the default.

    Returns:
    --------
        dict:
            The current palette data.
    """
    Palette.reset_palette()
    return Palette.get_palette()
    

@router.get("/palette/add_theme") 
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
    Palette.create_new_theme(theme)
    return Palette.get_palette()