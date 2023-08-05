from fastapi import FastAPI
from .routers import parser_router, plotter_router, palette_router

# The API is used on the server hosted version of CodeCarto
# It is not used in the local version of CodeCarto
# So, anything that returns a python object should not be used here

app = FastAPI()
app.include_router(parser_router, prefix="/parser", tags=["parser"])
app.include_router(plotter_router, prefix="/plotter", tags=["plotter"])
app.include_router(palette_router, prefix="/palette", tags=["palette"])
