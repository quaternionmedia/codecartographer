from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pprint import pprint

from api.util import generate_return, web_exception, proc_error
from graphbase.src.main import list_graphs

# Create a router
GraphsRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/db/db.html"

# Set the processor api url
PROC_API_URL = "http://processor:2020/graphs" 


# Root page
@GraphsRoute.get("/")
async def root(request: Request):
    return pages.TemplateResponse(html_page, {"request": request})

# Get all graphs
@GraphsRoute.get("/list")
async def get_graphs():
    try:
        # Get the graphs
        graphs = await list_graphs() 
        pprint(graphs)

        # Return the graphs
        return generate_return(
            200, "Web.get_graphs() - Success", graphs
        ) 
    except Exception as exc:
        web_exception(
            "get_graphs",
            "Error with request to processor",
            {},
            exc,
        )

