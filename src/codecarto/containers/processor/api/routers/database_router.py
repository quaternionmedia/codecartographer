# from fastapi import APIRouter, Request
# import networkx as nx
# import matplotlib.pyplot as plt
# import mpld3
# import matplotlib.lines as mlines
# from pydantic import BaseModel

# from api.util import generate_return, proc_exception, proc_error
# from graphbase import get_db_col, doc_insert, doc_select


# class GraphModel(BaseModel):
#     nodes: list[dict]
#     edges: list[dict]


# DatabaseRoute: APIRouter = APIRouter()


# # @DatabaseRoute.post("/graph/save/")
# # async def save_graph(graph_data: dict, db=Depends(get_db_col)):
# #     serialized_data = graph_to_data(nx.json_graph.node_link_graph(graph_data))
# #     result = db.insert_one(serialized_data)
# #     return {"status": "success", "id": str(result.inserted_id)}


# # @DatabaseRoute.get("/graph/{graph_id}/")
# # async def get_graph(graph_id: str, db=Depends(get_db_col)):
# #     result = db.find_one({"_id": ObjectId(graph_id)})
# #     if not result:
# #         return proc_error(
# #             "get_graph",
# #             "Graph not found",
# #             {"graph_id": graph_id, "db": db},
# #             500,
# #         )
# #     return nx.json_graph.node_link_data(data_to_graph(result))


# @DatabaseRoute.post("/write_to_db")
# async def write_to_db(table_name: str, document: list[GraphModel] | GraphModel):
#     try:
#         ids = await doc_insert(table_name=table_name, data=document)
#         return generate_return(200, "Data written to db", ids)
#     except Exception as exc:
#         proc_exception(
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
#         proc_exception(
#             "read_from_db",
#             "Error with request to db",
#             {},
#             exc,
#         )
