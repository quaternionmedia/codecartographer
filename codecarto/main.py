from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from codecarto.routers.c_parser_router import CParserRouter
from codecarto.routers.topology_router import TopologyRouter
from codecarto.routers.capability_router import CapabilityRouter
from codecarto.routers.app_router import AppRouter, DIST, build_present
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


origins = [
    "http://localhost:1234",  # web
    "http://localhost:1235",  # web (vite default)
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
# The harness's topology, drawn here. `codecarto` is qmcp's front end on
# the web; the terminal one is `dossier`, and both read the same document.
app.include_router(TopologyRouter, prefix="/topology", tags=["topology"])
# What each named thing this estate can do has reached. The vocabulary is the
# corpus's and `dossier` is the other window onto the same registry.
app.include_router(CapabilityRouter, prefix="/capabilities",
                   tags=["capabilities"])

# The built web application, on the same origin as the API it talks to. Mounted
# after the routers so a route always wins over a static file of the same name.
app.include_router(AppRouter)
if build_present():
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=str(DIST / "assets")),
              name="assets")
    logging.getLogger(__name__).info(
        "Web application served at /app (built assets in %s)", DIST)
else:
    logging.getLogger(__name__).info(
        "No web build found in %s; /app explains how to make one", DIST)

# Optional: Graphbase MongoDB router — activated when MONGODB_URI env var is set.
# Surfaced explicitly at startup so a missing variable in the wrong shell
# (e.g. a git-bash session that doesn't inherit Windows user-scope env vars)
# is immediately visible in the log rather than silently absent.
import os as _os
import logging as _log
if _os.getenv("MONGODB_URI"):
    try:
        from graphbase import graphdb as GraphBaseRouter
        app.include_router(GraphBaseRouter, prefix="/db", tags=["db"])
        _log.info("Graphbase router mounted at /db (MONGODB_URI=%s)",
                  _os.getenv("MONGODB_URI"))
    except Exception as _e:
        _log.error("Graphbase router failed to load — /db/* will be unavailable: %s", _e)
else:
    _log.info("Graphbase disabled — set MONGODB_URI to enable /db/* routes "
              "(note: git-bash does not inherit Windows user-scope env vars "
              "set via PowerShell or the registry; use 'export MONGODB_URI=...' "
              "in the same shell that starts the server)")


@app.get("/", include_in_schema=False)
async def root():
    """The application when there is one, the API docs when there is not.

    Redirecting to `/docs` unconditionally is what made "the web front end is
    up" mean "here is a schema". A person opening this port wants the thing
    they were told was running.
    """
    return RedirectResponse(url="/app" if build_present() else "/docs")


@app.get("/auth/github", tags=["auth"])
async def github_auth_status_endpoint():
    """Report the active GitHub credential source and whether a token is present.

    Useful for diagnosing the env-var / gh-CLI keyring precedence issue:
    a stale GITHUB_TOKEN silently shadows a valid gh keyring token unless
    CC_GITHUB_TOKEN is set or GITHUB_TOKEN/GH_TOKEN are cleared.
    """
    from codecarto.services.github_service import github_auth_status
    return github_auth_status()


@app.on_event("startup")
async def startup():
    from codecarto.routers.pam_router import on_pam_startup
    from codecarto.services.github_service import get_github_token
    get_github_token()  # resolve and log the auth source at startup
    await on_pam_startup()
