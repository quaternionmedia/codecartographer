"""Lexicon API routes.

Exposes the hand-authored language lexicons as graphs that ride codecarto's
existing graph-visualization pipeline.

    GET /lexicon/                -> list available languages
    GET /lexicon/{language}      -> full lexicon (validated JSON)
    GET /lexicon/{language}/graph-> gJGF graph for the plotter
    GET /lexicon/{language}/index-> token -> [layer/group contexts] (Option B)

Mount in main.py alongside the other routers, e.g.::

    from codecarto.routers.lexicon_router import LexiconRouter
    app.include_router(LexiconRouter, prefix="/lexicon", tags=["lexicon"])
"""

from fastapi import APIRouter, HTTPException

from codecarto.models.plot_data import PlotOptions
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.services.lexicon_service import LexiconService
from codecarto.util.utilities import generate_return

LexiconRouter = APIRouter()


@LexiconRouter.get("/")
async def list_lexicons() -> dict:
    return generate_return(
        message="list_lexicons - Success",
        results={"languages": LexiconService.available()},
    )


@LexiconRouter.get("/{language}")
async def get_lexicon(language: str) -> dict:
    try:
        lex = LexiconService.load(language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return generate_return(message="get_lexicon - Success", results=lex.model_dump())


@LexiconRouter.get("/{language}/graph")
async def get_lexicon_graph(language: str) -> dict:
    """gJGF-shaped graph ({graph: {nodes, edges}, metadata}), via the same
    GraphSerializer.serialize_to_gjgf pipeline every parsed-code graph
    uses (layout positions, depth/size, etc.) — not LexiconService.to_json's
    plain node-link dump, which the frontend's D3GraphRenderer.canHandle
    doesn't recognize (verified directly, not assumed — a mismatch the
    original "renders through the existing frontend with no plotter
    changes" claim missed).
    """
    try:
        lex = LexiconService.load(language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    graph = LexiconService.to_graph(lex)
    options = PlotOptions(layout="Spring", type="d3")
    gjgf = GraphSerializer.serialize_to_gjgf(graph, options)
    metadata = GraphSerializer.create_metadata(graph, options)
    return generate_return(
        message="get_lexicon_graph - Success",
        results={"graph": gjgf, "metadata": metadata},
    )


@LexiconRouter.get("/{language}/index")
async def get_lexicon_index(language: str) -> dict:
    """Token-spelling -> contexts lookup, for parser enrichment (Option B)."""
    try:
        lex = LexiconService.load(language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return generate_return(
        message="get_lexicon_index - Success", results=lex.index_by_token()
    )
