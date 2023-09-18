import httpx
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from api.util import generate_return, web_exception, proc_error

# Debug
import logging

logger = logging.getLogger(__name__)

# Create a router
ParserRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
parse_html_page = "/parse/parse.html"

# Set the processor api url
PROC_API_URL = "http://processor:2020/parser"
PROC_API_GITHUB_URL = f"{PROC_API_URL}/handle_github_url"


# Root page
@ParserRoute.get("/")
async def root(request: Request):
    return pages.TemplateResponse(parse_html_page, {"request": request})


@ParserRoute.get("/handle_github_url/")
async def handle_github_url(github_url: str) -> dict:
    # Call the processor container

    # TODO: call the proc api to start it, will get a job id
    # TODO: check the database every X secs on job id for results
    # TODO: Temp work around to see if working
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.get(
                PROC_API_GITHUB_URL,
                params={
                    "github_url": github_url,
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
                    "handle_github_url",
                    "Error from processor",
                    {"github_url": github_url},
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
                "handle_github_url",
                "Error with request to processor",
                {"github_url": github_url},
                exc,
            )
