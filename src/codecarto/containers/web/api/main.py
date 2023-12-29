from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .routers.palette_router import PaletteRoute
from .routers.plotter_router import PlotterRoute
from .routers.parser_router import ParserRoute
from .routers.polygraph_router import PolyGraphRoute
from .routers.graphs_router import GraphsRoute
from graphbase.src.main import graphdb as GraphBaseRouter
# TODO: if we expose the graphbase package, we can import the router directly
# like this 'from graphbase import GraphBaseRouter'

# Debug
import logging

logging.basicConfig(level=logging.INFO)

# Create the app
app = FastAPI()

# Serve the static files
app.mount("/pages", StaticFiles(directory="src/pages"), name="pages")
pages = Jinja2Templates(directory="src/pages")


# Catch all exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


# Root page
@app.get("/")
async def root(request: Request):
    return pages.TemplateResponse("/home/home.html", {"request": request})


# TODO: this is here to test moe calling the api
origins = [
    "http://localhost:5000",  # moe
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add the routers
app.include_router(PaletteRoute, prefix="/palette", tags=["palette"])
app.include_router(PlotterRoute, prefix="/plotter", tags=["plotter"])
app.include_router(ParserRoute, prefix="/parser", tags=["parser"])
app.include_router(PolyGraphRoute, prefix="/polygraph", tags=["polygraph"])
app.include_router(GraphsRoute, prefix="/graphs", tags=["graphs"])
app.include_router(GraphBaseRouter, prefix="/db", tags=["db"])
