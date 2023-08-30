from fastapi import FastAPI

from .routers.palette_router import PaletteRoute
from .routers.plotter_router import PlotterRoute
from .routers.parser_router import ParserRoute
from .routers.polygraph_router import PolyGraphRoute

app = FastAPI()
app.include_router(PaletteRoute, prefix="/palette", tags=["palette"])
app.include_router(PlotterRoute, prefix="/plotter", tags=["plotter"])
app.include_router(ParserRoute, prefix="/parser", tags=["parser"])
app.include_router(PolyGraphRoute, prefix="/polygraph", tags=["polygraph"])
