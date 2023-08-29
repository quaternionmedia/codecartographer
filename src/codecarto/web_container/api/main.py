from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routers.palette_router import PaletteRoute
from .routers.plotter_router import PlotterRoute

# Create the app
app = FastAPI()

# Serve the static files
app.mount("/templates", StaticFiles(directory="src/templates"), name="templates")
app.mount("/temp_files", StaticFiles(directory="src/temp_files"), name="temp_files")
templates = Jinja2Templates(directory="src/templates")


# Root page
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


# Add the routers
app.include_router(PaletteRoute, prefix="/palette", tags=["palette"])
app.include_router(PlotterRoute, prefix="/plotter", tags=["plotter"])
