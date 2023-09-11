import httpx
from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates


# Create a router
ParserRoute: APIRouter = APIRouter()
pages = Jinja2Templates(directory="src/pages")
html_page = "/parse/parse.html"

PROC_PARSE_API_URL = "http://processor:2020/parser/parse"
PROC_GITHUB_API_URL = "http://processor:2020/parser/handle_github_url"


# Root page
@ParserRoute.get("/")
async def root(request: Request):
    return pages.TemplateResponse(html_page, {"request": request})


@ParserRoute.get("/handle_github_url/")
async def handle_github_url(github_url: str) -> dict:
    # Call the processor container

    # TODO: call the proc api to start it, will get a job id
    # TODO: check the database every X secs on job id for results
    # TODO: Temp work around to see if working
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(
                PROC_GITHUB_API_URL,
                params={
                    "github_url": github_url,
                },
            )
            response.raise_for_status()
            if not response.status_code == 200:
                detail: dict = response.json()
                detail["web_err_msg"] = "Could not fetch github contents from processor"
                raise HTTPException(
                    status_code=response.status_code, detail=response.json()
                )
            return response.json()
        except httpx.RequestError as exc:
            # Handle network errors
            raise HTTPException(
                status_code=500,
                detail={
                    "web_err_msg": "An error occurred while requesting",
                    "github_url": github_url,
                },
            ) from exc
        except httpx.HTTPStatusError as exc:
            # Handle non-2xx responses
            # Extract the actual error message from the response content
            error_message = exc.response.json().get("detail", str(exc))
            raise HTTPException(
                status_code=exc.response.status_code,
                detail={
                    "web_err_msg": f"Error response from processor: {error_message}",
                    "github_url": github_url,
                },
            ) from exc
        except KeyError as exc:
            # Handle missing 'results' key in response
            raise HTTPException(
                status_code=500,
                detail={
                    "web_err_msg": "Key 'results' not found in response",
                    "github_url": github_url,
                },
            ) from exc
        finally:
            await client.aclose()


@ParserRoute.get(
    "/parse",
    response_class=JSONResponse,
    responses={200: {"content": {"application/json": {}}}},
)
async def parse(
    source_files: list[UploadFile] = File(...), language: str = "Python"
) -> dict[str, str]:
    # check that it's a .py file
    # pass the files to the processor api
    pass
