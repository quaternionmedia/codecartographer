__package__ = "app" 

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates 

# from .depends import get_redis_conn

# from .routers.palette_router import PaletteRoute
# from .routers.plotter_router import PlotterRoute

# from .routers.parser_router import ParserRoute
# from .routers.polygraph_router import PolyGraphRoute
# from .routers.processor_router import ProcessorRoute

# The API is used on the server hosted version of CodeCarto
# It is not used in the local version of CodeCarto
# So, anything that returns a python object should not be used here
app = FastAPI()

# Serve the static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static/templates")
# redis_conn = get_redis_conn()


# Root page
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
 

# app.include_router(PaletteRoute, prefix="/palette", tags=["palette"])
# app.include_router(PlotterRoute, prefix="/plotter", tags=["plotter"])
# app.include_router(ParserRoute, prefix="/parser", tags=["parser"])
# app.include_router(PolyGraphRoute, prefix="/polygraph", tags=["polygraph"])
# app.include_router(ProcessorRoute, prefix="/processor", tags=["processor"])
