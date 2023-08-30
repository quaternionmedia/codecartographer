from fastapi import APIRouter

PolyGraphRoute = APIRouter()


@PolyGraphRoute.get("/get_graph_desc")
async def get_graph_desc() -> dict:
    """Returns a dict[str:str] of graph description"""
    from src.models.graph_data import get_graph_description

    try:
        graph_desc: dict = get_graph_description()

        return {
            "graph_desc": graph_desc,
            "status": "completed",
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed",
        }
