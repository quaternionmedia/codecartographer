import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates

from api.util import generate_return, web_exception

PolyGraphRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/parse/parse.html"

PROC_API_URL = "http://processor:2020/polygraph/get_graph_desc"


@PolyGraphRoute.get("/get_graph_desc")
async def get_graph_desc() -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(PROC_API_URL)
            response.raise_for_status()
            if not response.status_code == 200:
                web_exception(
                    "get_graph_desc",
                    "Could not fetch graph description from processor",
                )
            return response.json()
        except httpx.RequestError as exc:
            # Handle network errors
            web_exception(
                "get_graph_desc",
                "An error occurred while requesting",
                {},
                exc,
            )
        except httpx.HTTPStatusError as exc:
            # Handle non-2xx responses
            web_exception(
                "get_graph_desc",
                "Error response from processor",
                {},
                exc,
            )
        except KeyError:
            web_exception(
                "get_graph_desc",
                "Key 'results' not found in response",
                {},
                exc,
            )
