"""Lexicon API routes.

Exposes the hand-authored language lexicons as graphs that ride codecarto's
existing graph-visualization pipeline.

    GET /lexicon/                -> list available languages
    GET /lexicon/{language}      -> full lexicon (validated JSON)
    GET /lexicon/{language}/graph-> gJGF graph for the plotter
    GET /lexicon/{language}/index-> token -> [layer/group contexts], the index
                                    the join to parsed code reads (Option B)
    GET /lexicon/constructs      -> the construct vocabulary, as an index
    GET /lexicon/chrestomathy/{construct}       -> one construct across languages
    GET /lexicon/chrestomathy/{construct}/gjgf  -> the same, as GraphData

Mount in main.py alongside the other routers, e.g.::

    from codecarto.routers.lexicon_router import LexiconRouter
    app.include_router(LexiconRouter, prefix="/lexicon", tags=["lexicon"])
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from codecarto.models.plot_data import PlotOptions
from codecarto.services import construct_service
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


# ── Constructs and the chrestomathy ──────────────────────────────────────────
# Registered before `/{language}`: routes match in order, and a language named
# `constructs` would otherwise answer 404 for the vocabulary.


@LexiconRouter.get("/constructs")
async def list_constructs() -> dict:
    """Every construct the vocabulary names, and which languages spell or
    parse each -- the index a Chrestomathy panel chooses from."""
    return generate_return(message="list_constructs - Success",
                           results=construct_service.table())


class CensusRequest(BaseModel):
    """The nodes on a canvas: each needs `id`, `language` and `kind`; a
    stamped node's `construct` and `meta.facets` are kept as they arrived."""

    nodes: list[dict] = []


@LexiconRouter.post("/chrestomathy/census")
async def chrestomathy_census(request: CensusRequest) -> dict:
    """The chrestomathy of whatever graph is drawn: the constructs its nodes
    are, in which languages, the ids of the nodes that are each, and what the
    vocabulary could not place -- so any graph, from any panel, can be set
    beside the other languages that write the same things."""
    return generate_return(message="chrestomathy_census - Success",
                           results=construct_service.census(request.nodes))


def _no_construct(construct: str) -> dict:
    """An unknown construct, as a sentence in a 200 like every graph route here."""
    known = [c["id"] for c in construct_service.table()["constructs"]]
    return generate_return(results={
        "unreadable": True,
        "problem": f"no construct named '{construct}' in the vocabulary",
        "remedy": "choose one of: " + ", ".join(known),
        "where": construct_service.VOCABULARY.name,
    })


@LexiconRouter.get("/chrestomathy/{construct}")
async def get_chrestomathy(construct: str) -> dict:
    """One construct across every language: its tokens and the lexicon layer
    each sits on, the parser kinds that realise it, and each language's note --
    including the languages that have no spelling for it at all."""
    found = construct_service.reading(construct)
    if found is None:
        return _no_construct(construct)
    return generate_return(message="get_chrestomathy - Success", results=found)


@LexiconRouter.get("/chrestomathy/{construct}/gjgf")
async def get_chrestomathy_graph(construct: str, layout: str = "Kamada Kawai") -> dict:
    """The same reading as `GraphData`: the construct at the centre, each
    language around it, tokens coloured by their abstraction layer."""
    graph = construct_service.as_graph(construct)
    if graph is None:
        return _no_construct(construct)
    options = PlotOptions(layout=layout, type="d3")
    try:
        gjgf = GraphSerializer.serialize_to_gjgf(graph, options)
    except ValueError as error:
        from codecarto.services import estate_service

        return generate_return(results=estate_service.unknown_layout(
            error, f"/lexicon/chrestomathy/{construct}/gjgf?layout={layout}"))
    return generate_return(message="get_chrestomathy_graph - Success", results={
        "graph": gjgf, "metadata": construct_service.metadata(construct, options)})


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
    """Token-spelling -> contexts lookup, the index the join to parsed code
    (Option B, lexicon_bridge) reads."""
    try:
        lex = LexiconService.load(language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return generate_return(
        message="get_lexicon_index - Success", results=lex.index_by_token()
    )
