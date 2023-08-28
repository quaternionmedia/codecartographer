from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

# Create a router and add the limiter to it
ParserRoute: APIRouter = APIRouter()


@ParserRoute.get(
    "/parse",
    response_class=JSONResponse,
    responses={200: {"content": {"application/json": {}}}},
)
async def parse(
    source_files: list[UploadFile] = File(...), language: str = "Python"
) -> dict[str, str]:
    pass
