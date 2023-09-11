import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates

from api.util import generate_return, web_exception

PlotterRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/plot/plot.html"

PROC_API_URL = "http://processor:2020/plotter/plot"


# Root page
@PlotterRoute.get("/")
async def root(request: Request):
    return pages.TemplateResponse(html_page, {"request": request})


@PlotterRoute.get("/plot")
async def plot(
    request: Request,
    graph_data: dict = None,
    file: str = None,
    layout: str = "spring",
    grid: bool = False,
    labels: bool = False,
    ntx: bool = True,
    custom: bool = True,
    palette: dict = None,
    debug: bool = False,
) -> dict:
    """Plot a graph.

    Parameters:
    -----------
    request : Request
        The request object.
    graph_data : dict
        The graph data. JSON format.
    file : str
        The file to parse and plot.
    layout : str
        The name of the layout to plot.
            Used to plot a single layout.
    grid : bool
        Whether to plot all plot layouts in a grid.
    labels : bool
        Whether to plot the graph with labels.
    ntx : bool
        Whether to use the networkx layouts.
    custom : bool
        Whether to use the custom layouts.
    palette: dict
        The palette to use for plotting.

    Returns:
    --------
    dict
        The results of the plot. {index: plot html}
    """
    # Call the processor container
    async with httpx.AsyncClient(timeout=60.0) as client:
        params: dict = {
            "graph_data": graph_data,
            "file": file,
            "layout": layout,
            "grid": grid,
            "labels": labels,
            "ntx": ntx,
            "custom": custom,
            "palette": palette,
            "debug": debug,
        }
        try:
            response = await client.get(PROC_API_URL, params=params)
            response.raise_for_status()
            if not response.status_code == 200:
                web_exception(
                    "plot",
                    "Could not fetch plot from processor",
                    params,
                )
            return response.json()
        except httpx.RequestError as exc:
            # Handle network errors
            web_exception(
                "plot",
                "An error occurred while requesting",
                params,
                exc,
            )
        except httpx.HTTPStatusError as exc:
            # Handle non-2xx responses
            web_exception(
                "plot",
                "Error response from processor",
                params,
                exc,
            )
        except KeyError as exc:
            web_exception(
                "plot",
                "Key 'results' not found in response",
                params,
                exc,
            )
