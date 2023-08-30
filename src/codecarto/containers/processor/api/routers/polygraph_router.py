from fastapi import APIRouter

PolyGraphRoute = APIRouter()


@PolyGraphRoute.get("/graph_description")
async def get_graph_desc() -> dict:
    from src.models.graph_data import get_graph_description

    return get_graph_description()
