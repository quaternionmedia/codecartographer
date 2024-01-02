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
 
@PlotterRoute.get("/ipynb")
async def extract_outputs(graph_name:str, nb_path:str = "src/notebooks/codecarto.ipynb"):
    """Extract the outputs from a notebook.

    Parameters:
    -----------
    graph_name : str
        The name of the graph to pass to ipynb.
    nb_path : str
        The path to the notebook.

    Returns:
    --------
    list
        The list of outputs.
    """
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor
    from graphbase.src.main import read_graph

    from pprint import pprint
    
    # Get the graph from the database
    pprint(f"start reading graph {graph_name}")

    graph_data = await read_graph(graph_name)
    graph_data = {"graph": graph_data.get("graph", None)}
    pprint(graph_data)

    if not graph_data:
        return None
    
    # Read in the notebook
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

        # Create a new code cell with the parameter
        param_cell = nbformat.v4.new_code_cell(f"g = {graph_data}")
        
        # Insert the cell at the beginning of the notebook
        nb.cells.insert(0, param_cell)

    # Execute the notebook
    ep = ExecutePreprocessor(timeout=600)
    ep.preprocess(nb, {'metadata': {'path': 'src/notebooks/'}})

    # Extract the outputs
    outputs = []
    for cell in nb.cells:
        if cell.cell_type == 'code':
            for output in cell.outputs:
                if output.output_type == 'execute_result':
                    outputs.append(output.data)

    # Return the outputs
    return outputs