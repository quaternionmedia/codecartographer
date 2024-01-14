import httpx
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from api.util import web_exception, proc_error

# Create a router
PolyGraphRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/parse/parse.html"

# Set the processor api url
PROC_API_URL = "http://processor:2020/polygraph"
PROC_API_GRAPH_DESC = f"{PROC_API_URL}/get_graph_desc"
PROC_API_URL_TO_JSON = f"{PROC_API_URL}/url_to_json"


@PolyGraphRoute.get("/get_graph_desc")
async def get_graph_desc() -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(PROC_API_GRAPH_DESC)
            # returning a json response from the processor
            # even in the case of an error in the processor
            data: dict = response.json()
            status_code = data.get("status", 500)

            # check if the response is an error
            if status_code != 200:
                error_message = data.get("message", "No error message")
                results = proc_error(
                    "get_graph_desc",
                    "Error from processor",
                    {},
                    status=status_code,
                    proc_error=error_message,
                )
            else:
                results = data

            return results
        except Exception as exc:
            web_exception(
                "get_graph_desc",
                "Error with request to processor",
                {},
                exc,
            )


@PolyGraphRoute.get("/url_to_json")
async def url_data_to_json(file_url: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(
                PROC_API_URL_TO_JSON,
                params={
                    "file_url": file_url,
                },
            )
            # returning a json response from the processor
            # even in the case of an error in the processor
            data: dict = response.json()
            status_code = data.get("status", 500)

            # check if the response is an error
            if status_code != 200:
                error_message = data.get("message", "No error message")
                results = proc_error(
                    "url_data_to_json",
                    "Error from processor",
                    {},
                    status=status_code,
                    proc_error=error_message,
                )
            else:
                results = data

            return results
        except Exception as exc:
            web_exception(
                "url_data_to_json",
                "Error with request to processor",
                {},
                exc,
            )
