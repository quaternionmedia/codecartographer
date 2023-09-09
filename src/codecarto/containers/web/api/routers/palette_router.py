import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates

from api.util import generate_return, web_exception

PaletteRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/palette/palette.html"

PROC_API_URL = "http://processor:2020/palette/get_palette"


# Root page
@PaletteRoute.get("/")
async def root(request: Request):
    return pages.TemplateResponse(html_page, {"request": request})


@PaletteRoute.get("/get_palette")
async def get_palette() -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(PROC_API_URL)
            response.raise_for_status()
            if not response.status_code == 200:
                web_exception(
                    "get_palette",
                    "Could not fetch palette from processor",
                    {},
                )
            return response.json()
        except httpx.RequestError as exc:
            # Handle network errors
            web_exception(
                "get_palette",
                "An error occurred while requesting",
                {},
            )
        except httpx.HTTPStatusError as exc:
            # Handle non-2xx responses
            web_exception(
                "get_palette",
                "Error response from processor",
                {},
                exc,
            )
        except KeyError as exc:
            web_exception(
                "get_palette",
                "Key 'results' not found in response",
                {},
                exc,
            )


# @PaletteRoute.get("/set_palette")
# async def set_palette(palette_file_path: str) -> dict[str, str]:
#     """Sets the palette to use for plots

#     Parameters:
#     -----
#         palette_file_path (str):
#             The path to the palette file.

#     Returns:
#     --------
#         dict:
#             The new palette data.
#     """
#     from ....processor.plotter.palette import Palette

#     palette: Palette = Palette()
#     palette.set_palette(palette_file_path)
#     return palette.get_palette_data()


# @PaletteRoute.get("/reset_palette")
# async def reset_palette() -> dict[str, str]:
#     """Resets the palette to the default.

#     Returns:
#     --------
#         dict:
#             The current palette data.
#     """
#     from ....processor.plotter.palette import Palette

#     palette: Palette = Palette()
#     palette.reset_palette()
#     return palette.get_palette_data()


# @PaletteRoute.get("/add_theme")
# async def add_theme(
#     node_type: str,
#     base: str,
#     label: str,
#     shape: str,
#     color: str,
#     size: str,
#     alpha: str,
# ) -> dict[str, str]:
#     """Creates a new theme.

#     Parameters:
#     -----
#         node_type (str):
#             The type of node to create a theme for.
#         base (str):
#             The base color of the theme.
#         label (str):
#             The label color of the theme.
#         shape (str):
#             The shape color of the theme.
#         color (str):
#             The color color of the theme.
#         size (str):
#             The size color of the theme.
#         alpha (str):
#             The alpha color of the theme.

#     Returns:
#     --------
#         dict:
#             The current palette data.
#     """
#     from ....processor.plotter.palette import Palette, Theme

#     theme = Theme(node_type, base, label, shape, color, size, alpha)
#     palette: Palette = Palette()
#     palette.create_new_theme(theme)
#     return palette.get_palette_data()
