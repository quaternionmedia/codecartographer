import httpx

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

PolyGraphRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "parse/parse.html"

PROC_API_URL = "http://processor:2020/polygraph/get_graph_desc"


@PolyGraphRoute.get("/get_graph_desc")
async def get_graph_desc() -> dict:
    async with httpx.AsyncClient() as client:
        # returns a dict[str:str] of graph description
        response = await client.get(PROC_API_URL)

        if not response.status_code == 200:
            return {
                "error": "Could not fetch graph description from process container",
                "status": "failed",
                "response_error": response["error"],
            }

        try:
            graph_desc = response.json()
        except KeyError:
            print("Received JSON:", response.json())  # Debugging line
            return {
                "error": "Key 'graph_desc' not found in response",
                "status": "failed",
            }

    return {
        "graph_desc": graph_desc,
        "status": "completed",
    }
