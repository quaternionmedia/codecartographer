from fastapi import FastAPI, Request
from datetime import datetime
from .routers import (
    palette_router,
    parser_router,
    plotter_router,
    polygraph_router,
    processor_router,
)


# The API is used on the server hosted version of CodeCarto
# It is not used in the local version of CodeCarto
# So, anything that returns a python object should not be used here

app = FastAPI()


@app.middleware("http")
async def log_duration(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    path = request.url.path
    return response


app.include_router(palette_router, prefix="/palette", tags=["palette"])
app.include_router(parser_router, prefix="/parser", tags=["parser"])
app.include_router(plotter_router, prefix="/plotter", tags=["plotter"])
app.include_router(polygraph_router, prefix="/polygraph", tags=["polygraph"])
app.include_router(processor_router, prefix="/processor", tags=["processor"])
