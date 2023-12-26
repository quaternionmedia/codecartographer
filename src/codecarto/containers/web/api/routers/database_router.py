# from fastapi import APIRouter, Request, Depends, HTTPException
# from pydantic import BaseModel


# from api.util import generate_return, web_exception, proc_error
# from db.document import doc_insert, doc_select
# from db.connection import get_db_col


# import logging

# logger = logging.getLogger(__name__)


# class GraphModel(BaseModel):
#     nodes: list[dict]
#     edges: list[dict]


# DatabaseRoute: APIRouter = APIRouter()


# @DatabaseRoute.post("/write_to_db")
# async def write_to_db(table_name: str, document: list[GraphModel] | GraphModel):
#     # TODO: setting up some stuff to use as httpx client call later
#     # async with httpx.AsyncClient() as client:
#     try:
#         # TODO: Not sure this will be needed. Leaving it here for now.
#         # DB_API_URL = "http://database:2020"
#         # DB_API_WRITE = f"{DB_API_URL}/write_to_db"
#         # response = await client.get(DB_API_WRITE)
#         # data = response.json() # currently returns a list of ids
#         # # check if the response is an error
#         # if status_code != 200:
#         #     # error_message = data.get("message", "No error message")
#         #     error_message = "Error from db"
#         #     results = proc_error(
#         #         "write_to_db",
#         #         "Error from db",
#         #         {"table_name": table_name, "data": data},
#         #         status=status_code,
#         #         proc_error=error_message,
#         #     )
#         # else:
#         #     results = data
#         ids = await doc_insert(table_name=table_name, data=document)
#         return generate_return(200, "Data written to db", ids)
#     except Exception as exc:
#         web_exception(
#             "write_to_db",
#             "Error with request to db",
#             {},
#             exc,
#         )


# @DatabaseRoute.get("/read_from_db")
# async def read_from_db(table_name: str, doc_id: str, filter: dict = None):
#     try:
#         filter = {"_id": doc_id}
#         data = await doc_select(table_name=table_name, filter=filter)
#         return generate_return(200, "Data written to db", data)
#     except Exception as exc:
#         web_exception(
#             "write_to_db",
#             "Error with request to db",
#             {},
#             exc,
#         )
