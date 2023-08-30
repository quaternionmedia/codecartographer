from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

# Create a router and add the limiter to it
ParserRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/parse/parse.html"

PROC_API_URL = "http://processor:2020/parser/parser"


@ParserRoute.get(
    "/parse",
    response_class=JSONResponse,
    responses={200: {"content": {"application/json": {}}}},
)
async def parse(
    source_files: list[UploadFile] = File(...), language: str = "Python"
) -> dict[str, str]:
    pass
