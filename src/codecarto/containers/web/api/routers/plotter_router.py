import httpx

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

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
        # returns a string of HTML representing plot
        response = await client.get(
            PROC_API_URL,
            params={
                "graph_data": graph_data,
                "file": file,
                "layout": layout,
                "grid": grid,
                "labels": labels,
                "ntx": ntx,
                "custom": custom,
                "palette": palette,
                "debug": debug,
            },
        )
        if not response.status_code == 200:
            return {"error": "Could not fetch plot from processor."}

        try:
            plot_html = response.json()["plotted"]
        except KeyError:
            print("Received JSON:", response.json())  # Debugging line
            return {"error": "Key 'plotted' not found in response"}

    return {
        "plot_html": plot_html,
        "layout": layout,
        "file": file,
        "status": "completed",
    }
