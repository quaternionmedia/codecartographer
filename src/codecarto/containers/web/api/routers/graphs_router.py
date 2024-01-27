from os import read
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pprint import pprint

from httpx import delete

from api.util import generate_return, web_exception, proc_error
from graphbase.src.main import list_graphs, delete_graph, read_graph

# Create a router
GraphsRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/saved_graphs/saved_graphs.html"

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
        return generate_return(200, "Web.get_graphs() - Success", graphs)
    except Exception as exc:
        web_exception(
            "get_graphs",
            "Error with request to processor",
            {},
            exc,
        )


# Delete a graph
@GraphsRoute.get("/delete")
async def delete_graphs(name: str):
    try:
        print(f"Delete graph: {name}")
        # Get the name of the url
        if name is None:
            return generate_return(400, "Web.delete_graph() - No name provided", {})

        # Check the graph name is in the database
        read_results = await read_graph(name)
        if read_results is None:
            return generate_return(
                400,
                "Web.delete_graph() - Graph not in database",
                {"name": name},
            )

        # Delete the graph
        delete_results = await delete_graph(name)
        if delete_results is None:
            return generate_return(
                400,
                "Web.delete_graph() - Graph not deleted",
                {"name": name},
            )

        # Return the graphs
        return generate_return(200, "Web.delete_graph() - Success", delete_results)
    except Exception as exc:
        web_exception(
            "delete_graph",
            "Error with request to processor",
            {"name": name},
            exc,
        )


# Delete all graphs
@GraphsRoute.get("/delete_all")
async def delete_all_graphs():
    try:
        print(f"Delete all graphs")
        # Get the graphs
        graphs = await list_graphs()
        pprint(graphs)

        # Delete the graphs
        for graph in graphs:
            delete_results = await delete_graph(graph)
            if delete_results is None:
                return generate_return(
                    400,
                    "Web.delete_graph() - Graph not deleted",
                    {},
                )

        # Return the graphs
        return generate_return(200, "Web.delete_graph() - Success", graphs)
    except Exception as exc:
        web_exception(
            "delete_graph",
            "Error with request to processor",
            {},
            exc,
        )
