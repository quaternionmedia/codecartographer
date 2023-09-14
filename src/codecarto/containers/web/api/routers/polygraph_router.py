import httpx
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from api.util import generate_return, web_exception

# Create a router
PolyGraphRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/parse/parse.html"

# Set the processor api url
PROC_API_URL = "http://processor:2020/polygraph"
PROC_API_GRAPH_DESC = f"{PROC_API_URL}/get_graph_desc"
PROC_API_RAW_TO_JSON = f"{PROC_API_URL}/raw_to_json"


@PolyGraphRoute.get("/get_graph_desc")
async def get_graph_desc() -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(PROC_API_GRAPH_DESC)
            response.raise_for_status()
            if not response.status_code == 200:
                web_exception(
                    "get_graph_desc",
                    "Could not fetch graph description from processor",
                )
            return response.json()
        except Exception as exc:
            error_message = exc.response.json().get("detail", str(exc))
            web_exception(
                "get_graph_desc",
                "Error from processor",
                {},
                exc,
                proc_error=error_message,
            )


@PolyGraphRoute.get("/raw_to_json")
async def raw_to_json(file_url: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(
                PROC_API_RAW_TO_JSON,
                params={
                    "file_url": file_url,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            error_message = exc.response.json().get("detail", str(exc))
            web_exception(
                "raw_to_json",
                "Error from processor",
                {},
                exc,
                proc_error=error_message,
            )
