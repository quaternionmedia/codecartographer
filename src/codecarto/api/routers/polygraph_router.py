from fastapi import APIRouter
from codecarto import Model

router = APIRouter()


@router.get("/graph/description")
async def get_graph_description() -> dict:
    return Model.get_graph_description()
