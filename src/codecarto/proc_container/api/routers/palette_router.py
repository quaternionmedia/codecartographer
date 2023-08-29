from fastapi import APIRouter
from fastapi.responses import JSONResponse
import traceback

PaletteRoute: APIRouter = APIRouter()


@PaletteRoute.get(
    "/get_palette",
)
async def get_palette() -> dict:
    try:
        from json import load

        # TODO: This is a temporary solution,
        # it should be coming from src.plotter.palette.get_palette_data()

        file_path = "api/temp_files/default_palette.json"
        with open(file_path, "r") as f:
            pal_data = load(f)

        return pal_data
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": str(e)})
