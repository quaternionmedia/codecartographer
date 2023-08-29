import httpx

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

PlotterRoute: APIRouter = APIRouter()
templates = Jinja2Templates(directory="src/templates")
PROC_API_URL = "http://processor:2020/plotter/plot"


# Root page
@PlotterRoute.get("/")
async def root(request: Request):
    return templates.TemplateResponse("plot.html", {"request": request})


@PlotterRoute.get("/plot")
async def plot(request: Request, grid: bool = False) -> str:
    async with httpx.AsyncClient() as client:
        # returns a string of HTML representing plot
        response = await client.get(PROC_API_URL, params={"grid": grid})
        if not response.status_code == 200:
            return {"error": "Could not fetch plot from processor container"}

    return templates.TemplateResponse(
        "plot.html", {"request": request, "plot_html": response}
    )


# return templates.TemplateResponse(
#         "plot.html",
#         {
#             "request": request,
#             "output": output,
#             "plot_html": plot_html,
#             "status": "completed",
#         },
#     )
