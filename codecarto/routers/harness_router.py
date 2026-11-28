"""What the harness is running and asking, for the Harness panel.

- `/harness/data` -- the tool runs, the questions held for a person and the
  instructions, each cut to the rows a panel shows with the number held back,
  and a run state for each project those rows name.
- `/harness/interactions` -- the same rows and the answers to the questions,
  as one list ordered by time: what was done, the way in and the name each
  row carries, and which harness answered.
- `/harness/gjgf` -- those interactions as `GraphData`, the graph format
  every other plot here produces, so the page draws them on the one canvas
  with the same layouts, palettes and menu.
- `/harness/threads` -- the conversations the harness's archive lists, in its
  order, narrowed by a source and a text when given and cut to the rows a
  panel shows, with what the archive says of itself.
- `/harness/thread` -- one conversation's counts and its newest turns.
- `/harness/thread/gjgf` -- that conversation's turns as `GraphData`.

- `GET /harness/instructions` -- whether this window relays an instruction
  for the request asking, and where one is given when it does not.
- `POST /harness/instructions` -- one instruction a person typed, relayed to
  the harness, which records it and runs nothing.

Each answers in `generate_return`'s envelope with status 200. A harness that
is not answering is a `results` carrying `unreachable`, a `problem`, a
`remedy` and a `where`, as every estate route reports an absent seam. An
instruction that was not recorded is a `results` carrying `refused` with the
same three.

Every route but the last reads. The last sends one document and keeps none.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from codecarto.models.plot_data import PlotOptions
from codecarto.services import (estate_service, harness_service, instruct_service,
                                interaction_graph, interaction_service, thread_service)
from codecarto.util.utilities import generate_return

HarnessRouter = APIRouter()


class Instruction(BaseModel):
    """What a person typed: the instruction, and the project when stated."""

    text: str
    project: str | None = None


def _standing(request: Request) -> str:
    """Why this request's instruction is not relayed, or "" when it is."""
    server = request.scope.get("server") or (None, None)
    client = request.client.host if request.client else None
    return instruct_service.standing(server[0], client, request.headers)


@HarnessRouter.get("/instructions")
def instruct_standing(request: Request) -> dict[str, Any]:
    """Whether an instruction typed here is relayed, for the panel's form."""
    return generate_return(
        results=instruct_service.availability(_standing(request)))


@HarnessRouter.post("/instructions")
def instruct(body: Instruction, request: Request) -> dict[str, Any]:
    """Relay one instruction to the harness, which records it and runs nothing.

    A plain `def`, so the post to the harness runs in the threadpool. The
    harness's row is returned as it gave it, and its refusal in its own words.
    """
    return generate_return(results=instruct_service.record(
        body.text, body.project, _standing(request)))


@HarnessRouter.get("/data")
async def harness_data() -> dict[str, Any]:
    """The harness's runs, queue and instructions, and the states they give.

    Read in the threadpool: the client blocks on HTTP for up to its timeout on
    each of three reads, and the event loop keeps serving meanwhile.
    """
    return generate_return(results=await run_in_threadpool(harness_service.read))


@HarnessRouter.get("/interactions")
async def harness_interactions() -> dict[str, Any]:
    """Who did what at the harness, through which way in, newest first.

    Read in the threadpool, as `/harness/data` is: the answers are one read
    of the harness each.
    """
    return generate_return(results=await run_in_threadpool(interaction_service.read))


@HarnessRouter.get("/gjgf")
def harness_gjgf(
    layout: str = Query(interaction_graph.LAYOUT),
    palette_id: str = Query("0"),
    detail: str = Query(interaction_graph.ALL, pattern="^(all|rows)$"),
) -> dict[str, Any]:
    """The harness's interactions as `GraphData`, in this project's envelope.

    `detail=rows` draws the reading alone, with each instruction's way in in
    its name and the rest on hovers, set closer and wrapped into blocks.

    A plain `def`, so the reads of the harness and the layout run in the
    threadpool. A layout nobody registered is `unreadable` with the
    registered ones named, as on every estate route.
    """
    rows = interaction_service.gather()
    if not rows.answering:
        return generate_return(results=rows.unreachable())
    options = PlotOptions(layout=layout, palette_id=palette_id, type="d3")
    made = interaction_graph.picture(rows, detail=detail)
    try:
        graph = interaction_graph.as_gjgf(made, options, rows.health.where)
    except ValueError as error:
        return generate_return(results=estate_service.unknown_layout(
            error, f"/harness/gjgf?layout={layout}"))
    return generate_return(results={
        "graph": graph,
        "metadata": interaction_graph.metadata(rows, made, options),
    })


@HarnessRouter.get("/threads")
def harness_threads(source: str = Query(""), titled: str = Query("")) -> dict[str, Any]:
    """The conversations the harness's archive lists, in the archive's order.

    A plain `def`, so the read of the harness runs in the threadpool.
    """
    return generate_return(results=thread_service.read_list(source, titled))


@HarnessRouter.get("/thread")
def harness_thread(source: str = Query(""), id: str = Query("")) -> dict[str, Any]:
    """One conversation's counts and its newest turns, or why it was not read."""
    document = thread_service.read(source, id)
    if "turns" not in document:
        return generate_return(results=document)
    return generate_return(results=thread_service.summary(document))


@HarnessRouter.get("/thread/gjgf")
def harness_thread_gjgf(
    source: str = Query(""),
    id: str = Query(""),
    layout: str = Query(thread_service.LAYOUT),
    palette_id: str = Query("0"),
) -> dict[str, Any]:
    """One conversation's newest turns as `GraphData`, in this project's envelope.

    A layout nobody registered is `unreadable` with the registered ones
    named, as on every estate route.
    """
    document = thread_service.read(source, id)
    if "turns" not in document:
        return generate_return(results=document)
    options = PlotOptions(layout=layout, palette_id=palette_id, type="d3")
    made = thread_service.picture(document)
    try:
        graph = thread_service.as_gjgf(document, made, options)
    except ValueError as error:
        return generate_return(results=estate_service.unknown_layout(
            error, f"/harness/thread/gjgf?layout={layout}"))
    return generate_return(results={
        "graph": graph,
        "metadata": thread_service.metadata(document, made, options),
    })
