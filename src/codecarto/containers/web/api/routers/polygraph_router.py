import httpx

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

PolyGraphRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "parse/parse.html"

PROC_API_URL = "http://processor:2020/polygraph/get_graph_desc"


# Root page
@PolyGraphRoute.get("/")
async def root(request: Request):
    return pages.TemplateResponse(html_page, {"request": request})


@PolyGraphRoute.get("/graph_description")
async def get_graph_desc(request: Request) -> dict[str, str]:
    async with httpx.AsyncClient() as client:
        # returns a dict[str:str] of graph description
        response = await client.get(PROC_API_URL)
        if not response.status_code == 200:
            return {"error": "Could not fetch graph description from process container"}

    return pages.TemplateResponse(
        html_page, {"request": request, "graph_desc": response}
    )
