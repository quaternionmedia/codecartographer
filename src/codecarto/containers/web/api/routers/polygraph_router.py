import httpx
from fastapi import APIRouter
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
                return generate_return(
                    "error",
                    "Web - Could not fetch graph description from processor.",
                    response.content,
                )
            return response.json()
        except httpx.RequestError as exc:
            # Handle network errors
            return web_exception(
                "error", "Web - An error occurred while requesting", exc
            )
        except httpx.HTTPStatusError as exc:
            # Handle non-2xx responses
            return web_exception(
                "error", "Web - Error response from processor", exc.response.content
            )
        except KeyError:
            return web_exception(
                "error", "Web - Key 'results' not found in response", response.json()
            )
