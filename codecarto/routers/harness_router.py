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

Each answers in `generate_return`'s envelope with status 200. A harness that
is not answering is a `results` carrying `unreachable`, a `problem`, a
`remedy` and a `where`, as every estate route reports an absent seam.

The routes read. Nothing here posts to the harness.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from codecarto.models.plot_data import PlotOptions
from codecarto.services import (estate_service, harness_service, interaction_graph,
                                interaction_service)
from codecarto.util.utilities import generate_return

HarnessRouter = APIRouter()


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
) -> dict[str, Any]:
    """The harness's interactions as `GraphData`, in this project's envelope.

    A plain `def`, so the reads of the harness and the layout run in the
    threadpool. A layout nobody registered is `unreadable` with the
    registered ones named, as on every estate route.
    """
    rows = interaction_service.gather()
    if not rows.answering:
        return generate_return(results=rows.unreachable())
    options = PlotOptions(layout=layout, palette_id=palette_id, type="d3")
    made = interaction_graph.picture(rows)
    try:
        graph = interaction_graph.as_gjgf(made, options, rows.health.where)
    except ValueError as error:
        return generate_return(results=estate_service.unknown_layout(
            error, f"/harness/gjgf?layout={layout}"))
    return generate_return(results={
        "graph": graph,
        "metadata": interaction_graph.metadata(rows, made, options),
    })
