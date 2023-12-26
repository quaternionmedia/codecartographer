# import httpx
# from fastapi import APIRouter
# from fastapi.templating import Jinja2Templates

# from api.util import generate_return, web_exception, proc_error

# # Create a router
# MoeRoute: APIRouter = APIRouter()
# pages = Jinja2Templates(directory="src/pages")
# html_page = "/parse/parse.html"

# # Set the processor api url
# MOE_API_URL = "http://processor:2020/polygraph"


# @MoeRoute.get("/open_in_moe")
# async def open_in_moe(graphJson):
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.get(MOE_API_URL)
#             # returning a json response from the processor
#             # even in the case of an error in the processor
#             data: dict = response.json()
#             status_code = data.get("status", 500)

#             # check if the response is an error
#             if status_code != 200:
#                 error_message = data.get("message", "No error message")
#                 results = proc_error(
#                     "open_in_moe",
#                     "Error calling Moe",
#                     {},
#                     status=status_code,
#                     proc_error=error_message,
#                 )
#             else:
#                 results = data

#             return results
#         except Exception as exc:
#             web_exception(
#                 "open_in_moe",
#                 "Error with request to processor",
#                 {},
#                 exc,
#             )
