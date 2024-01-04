import httpx
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from api.util import generate_return, web_exception, proc_error

# Create a router
PlotterRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/plot/plot.html"

# Set the processor api url
PROC_API_URL = "http://processor:2020/plotter"
PROC_API_PLOT = f"{PROC_API_URL}/plot"

# Root page
@PlotterRoute.get("/")
async def root(request: Request, file_url: str = None, db_graph: bool = False):
    if file_url and file_url != "":
        return pages.TemplateResponse(
            html_page, {"request": request, "file_url": file_url, "db_graph": db_graph}
        )
    else:
        return pages.TemplateResponse(html_page, {"request": request})


@PlotterRoute.get("/plot")
async def plot(
    request: Request,
    url:str = None,
    graph_data: dict = None,
    db_graph: bool = False,
    demo: bool = False,
    demo_file: str = None,
    layout: str = "Spring",
    gv: bool = False,
    nb: bool = False,
    type: str = "d3",
    grid: bool = False,
    labels: bool = False,
    ntx: bool = True,
    custom: bool = True,
    palette: dict = None,
) -> dict:
    """Plot a graph.

    Parameters:
    -----------
    request : Request
        The request object.
    url : str
        The url to parse and plot.
    graph_data : dict
        The graph data. JSON format.
    db_graph: bool
        Whether to plot a graph from the database.
    demo: bool
        Whether to plot the demo graph.
    demo_file : str
        The demo_file to parse and plot.
    layout : str
        The name of the layout to plot.
            Used to plot a single layout.
    gv : bool
        Whether to plot with gravis.
    nb : bool
        Whether to show ipython notebooks.
    type : str
        The type of plot to use.
            all: all types
            d3: d3.js
            vis: vis.js
            three: gravis
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
        params = request.query_params

        try:
            response = await client.get(PROC_API_PLOT, params=params)

            # returning a json response from the processor
            # even in the case of an error in the processor
            data: dict = response.json()
            status_code = data.get("status", 500)

            # check if the response is an error
            if status_code != 200:
                error_message = data.get("message", "No error message")
                results = proc_error(
                    "plot",
                    "Error from processor",
                    params,
                    status=status_code,
                    proc_error=error_message,
                )
            else:
                results = data

            return results
        except Exception as exc:
            # should only get here if there
            # is an error with web container
            web_exception(
                "plot",
                "Error with request to processor",
                params,
                exc,
            )
 