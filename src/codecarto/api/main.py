from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# from .depends import get_redis_conn

from .routers.palette_router import PaletteRoute
from .routers.plotter_router import PlotterRoute

# from .routers.parser_router import ParserRoute
# from .routers.polygraph_router import PolyGraphRoute
# from .routers.processor_router import ProcessorRoute

# The API is used on the server hosted version of CodeCarto
# It is not used in the local version of CodeCarto
# So, anything that returns a python object should not be used here
app = FastAPI()

# Serve the static files
app.mount("/static", StaticFiles(directory="src/codecarto/api/static"), name="static")
templates = Jinja2Templates(directory="src/codecarto/api/static/templates")
# redis_conn = get_redis_conn()


# Root page
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


# @app.middleware("http")
# async def log_duration(request: Request, call_next):
#     from datetime import datetime
#     start_time = datetime.now()
#     response = await call_next(request)
#     end_time = datetime.now()
#     duration = (end_time - start_time).total_seconds()
#     path = request.url.path
#     return response


app.include_router(PaletteRoute, prefix="/palette", tags=["palette"])
# app.include_router(ParserRoute, prefix="/parser", tags=["parser"])
app.include_router(PlotterRoute, prefix="/plotter", tags=["plotter"])
# app.include_router(PolyGraphRoute, prefix="/polygraph", tags=["polygraph"])
# app.include_router(ProcessorRoute, prefix="/processor", tags=["processor"])
