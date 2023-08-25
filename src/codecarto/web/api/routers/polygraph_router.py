from fastapi import APIRouter
from ....processor.models.graph_data import get_graph_description

PolyGraphRoute = APIRouter()


@PolyGraphRoute.get("/description")
async def get_graph_desc() -> dict:
    return get_graph_description()
