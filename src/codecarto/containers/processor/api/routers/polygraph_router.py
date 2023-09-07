from fastapi import APIRouter

from api.util import generate_return, proc_exception

PolyGraphRoute = APIRouter()


@PolyGraphRoute.get("/get_graph_desc")
async def get_graph_desc() -> dict:
    try:
        from src.models.graph_data import get_graph_description

        graph_desc: dict = get_graph_description()

        return generate_return(
            "success",
            "Graph description successfully fetched from processor.",
            graph_desc,
        )
    except Exception as e:
        return proc_exception(
            "error",
            "An error occurred while fetching graph description from processor.",
            e,
        )
