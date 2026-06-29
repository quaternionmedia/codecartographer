from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from codecarto.routers.c_parser_router import CParserRouter
from codecarto.routers.palette_router import PaletteRouter
from codecarto.routers.plotter_router import PlotterRouter
from codecarto.routers.repo_router import RepoReaderRouter
from codecarto.routers.pam_router import PamRouter
from codecarto.routers.unified_parser_router import UnifiedParserRouter
from codecarto.routers.lexicon_router import LexiconRouter


# Debug
import logging

logging.basicConfig(level=logging.INFO)

# Create the app
app = FastAPI()


# TODO: this is here to test moe calling the api
origins = [
    "http://localhost:1234",  # web
    "http://localhost:1235",  # web (vite default)
    "http://localhost:5000",  # moe
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Catch all exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


# Add the routers
app.include_router(PaletteRouter, prefix="/palette", tags=["palette"])
app.include_router(PlotterRouter, prefix="/plotter", tags=["plotter"])
app.include_router(RepoReaderRouter, prefix="/repo", tags=["repo"])
app.include_router(CParserRouter, prefix="/c-parser", tags=["c-parser"])
app.include_router(PamRouter, prefix="/pam", tags=["pam"])
app.include_router(UnifiedParserRouter, prefix="/parse", tags=["parse"])
app.include_router(LexiconRouter, prefix="/lexicon", tags=["lexicon"])

# Optional: Graphbase MongoDB router — activated when MONGODB_URI env var is set
import os as _os
if _os.getenv("MONGODB_URI"):
    try:
        from graphbase.src.main import graphdb as GraphBaseRouter
        app.include_router(GraphBaseRouter, prefix="/db", tags=["db"])
    except Exception as _e:
        import logging as _logging
        _logging.warning(f"Graphbase router could not be loaded: {_e}")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.on_event("startup")
async def startup():
    from codecarto.routers.pam_router import on_pam_startup
    await on_pam_startup()
