"""Lexicon API routes.

Exposes the hand-authored language lexicons as graphs that ride codecarto's
existing graph-visualization pipeline.

    GET /lexicon/                -> list available languages
    GET /lexicon/{language}      -> full lexicon (validated JSON)
    GET /lexicon/{language}/graph-> node-link graph for the plotter
    GET /lexicon/{language}/index-> token -> [layer/group contexts] (Option B)

Mount in main.py alongside the other routers, e.g.::

    from codecarto.routers.lexicon_router import LexiconRouter
    app.include_router(LexiconRouter, prefix="/lexicon", tags=["lexicon"])
"""

from fastapi import APIRouter, HTTPException

from codecarto.services.lexicon_service import LexiconService

LexiconRouter = APIRouter()


@LexiconRouter.get("/")
async def list_lexicons() -> dict:
    return {"languages": LexiconService.available()}


@LexiconRouter.get("/{language}")
async def get_lexicon(language: str) -> dict:
    try:
        lex = LexiconService.load(language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return lex.model_dump()


@LexiconRouter.get("/{language}/graph")
async def get_lexicon_graph(language: str) -> dict:
    try:
        lex = LexiconService.load(language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return LexiconService.to_json(lex)


@LexiconRouter.get("/{language}/index")
async def get_lexicon_index(language: str) -> dict:
    """Token-spelling -> contexts lookup, for parser enrichment (Option B)."""
    try:
        lex = LexiconService.load(language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return lex.index_by_token()
