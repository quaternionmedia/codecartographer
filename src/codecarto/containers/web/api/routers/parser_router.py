import httpx
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from api.util import generate_return, web_exception

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
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(
                PROC_API_GITHUB_URL,
                params={
                    "github_url": github_url,
                },
            )
            response.raise_for_status()
            if not response.status_code == 200:
                web_exception(
                    "handle_github_url",
                    "Could not fetch github contents from processor",
                    {"github_url": github_url},
                )
            return response.json()
        except Exception as exc:
            error_message = exc.response.json().get("detail", str(exc))
            web_exception(
                "handle_github_url",
                "Error from processor",
                {"github_url": github_url},
                exc,
                proc_error=error_message,
            )
