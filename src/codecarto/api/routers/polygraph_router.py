from fastapi import APIRouter
from ...models.graph_data import get_graph_description

router = APIRouter()


@router.get("/graph/description")
async def get_graph_description() -> dict:
    return get_graph_description()
