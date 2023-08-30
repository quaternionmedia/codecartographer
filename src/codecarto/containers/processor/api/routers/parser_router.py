from fastapi import APIRouter

ParserRoute = APIRouter()


@ParserRoute.get("/parse")
async def parse():
    pass
