import os
import traceback
from json import load
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.plotter.palette import Theme
from api.util import generate_return, proc_exception

PaletteRoute: APIRouter = APIRouter()
default_palette_path: str = "src/plotter/default_palette.json"
temp_palette_path: str = "src/plotter/palette.json"

# TODO: This is a temporary solution,
# it should be coming from src.plotter.palette.get_palette_data()
# or actually, since data is actually in the database, we'll need to load database data and pass
debug: bool = True


@PaletteRoute.get(
    "/get_palette",
)
async def get_palette(user_id: int = -1) -> dict:
    try:
        # TODO: DEBUG - temporary solution
        if debug == True:
            file_path = temp_palette_path
            # check if file exists
            if not os.path.exists(file_path):
                file_path = default_palette_path

            # Open the palette file
            with open(file_path, "r") as f:
                pal_data = load(f)

        return generate_return("success", "Proc - Success", pal_data)
    except Exception as e:
        proc_exception(
            "get_palette",
            "Could not fetch palette data",
            {"user_id": user_id},
            e,
        )


@PaletteRoute.get("/set_palette")
async def set_palette(user_id: int = -1, new_pal_data: dict = {}) -> dict:
    try:
        if new_pal_data != {}:
            # If user, look up user palette id
            if user_id != -1:
                # get_user_from_database(user_id)
                pass

            # save_palette_to_database(user_id, new_pal_data)

            # TODO: DEBUG - temporary solution
            if debug == True:
                file_path = temp_palette_path
                # check if file exists
                if not os.path.exists(file_path):
                    # create the file from the default palette
                    with open(default_palette_path, "r") as f:
                        pal_data = load(f)

                    with open(file_path, "w") as f:
                        f.write(pal_data)

                # Save the new palette data
                with open(file_path, "w") as f:
                    f.write(new_pal_data)
                pal_data = new_pal_data

            return pal_data
        else:
            proc_exception(
                "set_palette",
                "No new palette data provided",
                {"user_id": user_id, "new_pal_data": new_pal_data},
            )
    except Exception as e:
        proc_exception(
            "set_palette",
            "Could not set palette data",
            {"user_id": user_id, "new_pal_data": new_pal_data},
            e,
        )


@PaletteRoute.get("/reset_palette")
async def update_palette(user_id: int = -1, new_type: Theme = {}) -> dict:
    try:
        # If user, look up user palette id
        if user_id != -1:
            # get_user_from_database(user_id)
            pass

        # load_palette_from_database(user_id)

        # TODO: DEBUG - temporary solution
        if debug == True:
            file_path = temp_palette_path
            # check if file exists
            if not os.path.exists(file_path):
                file_path = default_palette_path

            # Open the palette file
            with open(file_path, "r") as f:
                pal_data = load(f)

            # Check if new_type is in pal_data
            if new_type in pal_data:
                # Set the new type to existing type
                pal_data[new_type.base] = new_type

            # Save the new palette data
            with open(file_path, "w") as f:
                f.write(pal_data)

        return pal_data
    except Exception as e:
        proc_exception(
            "update_palette",
            "Could not add new palette type",
            {"user_id": user_id, "new_type": new_type},
            e,
        )
