from fastapi import APIRouter
from util.exceptions import proc_exception
from util.utilities import Log, generate_return

PaletteRouter = APIRouter()


@PaletteRouter.get("/default")
async def get_default_palette():
    from models.plot_data import DefaultPalette

    try:
        return generate_return(
            message="get_default_palette - Success", results=DefaultPalette.dict()
        )
    except Exception as e:
        return proc_exception(
            "get_palette",
            "Error getting default palette",
            {},
            e,
        )


@PaletteRouter.get("/custom")
async def get_custom_palette(palette_id: str):
    from database.database import DatabaseContext

    try:
        palette = await DatabaseContext.fetch_palette_by_id(palette_id)
        return generate_return(
            message="get_custom_palette - Success", results=palette.dict()
        )
    except Exception as e:
        return proc_exception(
            "get_palette",
            "Error getting custom palette",
            {},
            e,
        )
