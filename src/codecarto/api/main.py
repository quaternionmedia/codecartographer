from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
from ..website.site import test_site, site
from .routers.palette_router import PaletteRoute
from .routers.parser_router import ParserRoute
from .routers.plotter_router import PlotterRoute
from .routers.polygraph_router import PolyGraphRoute
from .routers.processor_router import ProcessorRoute

# The API is used on the server hosted version of CodeCarto
# It is not used in the local version of CodeCarto
# So, anything that returns a python object should not be used here

app = FastAPI()

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import mpld3

# Serve the static files
app.mount("/static", StaticFiles(directory="src/codecarto/api/static"), name="static")

templates = Jinja2Templates(directory="src/codecarto/api/static/templates")


@app.get("/")
async def mpld3_plot(request: Request):
    # Create a simple plot
    fig, ax = plt.subplots(figsize=(5, 5))
    fig.canvas.manager.window.wm_geometry("+0+0")
    _title: str = f"Spiral Layout"
    _file_name: str = "graph_data.json"
    _title = f"{_title} for '{_file_name}'"
    ax.set_title(_title)
    ax.axis("off")

    from ..polygraph.polygraph import PolyGraph
    from ..plotter.palette import Palette

    pal: Palette = Palette()
    node_styles = pal.get_node_styles()
    node_data: dict[str, list] = {node_type: [] for node_type in node_styles.keys()}
    file_path: str = "src/codecarto/api/static/parse_files/graph_data.json"
    poly: PolyGraph = PolyGraph()
    graph: nx.Graph = poly.json_file_to_graph(file_path)

    # Collect nodes and their attributes
    for n, a in graph.nodes(data=True):
        node_type = a.get("type", "Unknown")
        if node_type not in node_styles.keys():
            node_type = "Unknown"
        node_data[node_type].append(n)
    pos = nx.spiral_layout(graph)

    # Draw Nodes
    for node_type, nodes in node_data.items():
        nx.drawing.draw_networkx_nodes(
            graph,
            pos,
            nodelist=nodes,
            node_color=node_styles[node_type]["color"],
            node_shape=node_styles[node_type]["shape"],
            node_size=node_styles[node_type]["size"],
            alpha=node_styles[node_type]["alpha"],
        )

    # fig, ax = plt.subplots(figsize=(6, 4))
    # np.random.seed(0)
    # x, y = np.random.normal(size=(2, 200))
    # ax.scatter(x, y)

    # Convert the Matplotlib plot to D3.js HTML representation
    plot_html = mpld3.fig_to_html(fig)

    return templates.TemplateResponse(
        "plot.html", {"request": request, "plot_html": plot_html}
    )


# @app.get("/", response_class=HTMLResponse)
# async def read_items():
#     html_content = site()
#     return HTMLResponse(content=html_content, status_code=200)


@app.middleware("http")
async def log_duration(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    path = request.url.path
    return response


app.include_router(PaletteRoute, prefix="/palette", tags=["palette"])
app.include_router(ParserRoute, prefix="/parser", tags=["parser"])
app.include_router(PlotterRoute, prefix="/plotter", tags=["plotter"])
app.include_router(PolyGraphRoute, prefix="/polygraph", tags=["polygraph"])
app.include_router(ProcessorRoute, prefix="/processor", tags=["processor"])
