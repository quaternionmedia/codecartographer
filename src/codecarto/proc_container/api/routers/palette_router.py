from fastapi import APIRouter, Request

PaletteRoute: APIRouter = APIRouter()


@PaletteRoute.get(
    "/palette",
)
async def get_palette(request: Request):
    from ...processor.plotter.palette import Palette

    pal: Palette = Palette()
    return pal.get_palette_data()
