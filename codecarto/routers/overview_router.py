"""`dossier`'s org overview, on this project's canvas.

**THIS SERVES A CODECARTO GRAPH, NOT A PICTURE OF ONE**, the same rule
`capability_router` and `topology_router` follow: `/overview/gjgf` returns the
graph format every other plot here produces, so the page renders it with the
same canvas, layouts, palettes and radial menu. A bespoke shape here would mean
a bespoke renderer there.

**THE ROUTES, AND WHAT EACH ANSWERS.**

- `/overview/gjgf` -- dossier's reading as `GraphData`, which is what the
  application's panel plots. The primary route.
- `/overview/data` -- the sections themselves, without a layout: the same
  reading the terminal prints as tables, so this window's answer is comparable
  with dossier's rather than only with the seam both read.

**A MISSING SEAM IS THE ORDINARY CASE**, not an error. The overview is one
window's live reading, generated on demand and not committed; a checkout that
has not been handed one legitimately has no seam. That answers 200 with
`unreadable` and draws no canvas -- an empty graph would look like an estate of
nothing, which is a different and much worse claim.

Every route answers in `generate_return`'s envelope, like every other router
here.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from codecarto.models.plot_data import PlotOptions
from codecarto.services import overview_service
from codecarto.util.utilities import generate_return

OverviewRouter = APIRouter()


def _options(layout: str, palette_id: str) -> PlotOptions:
    return PlotOptions(layout=layout, palette_id=palette_id, type="d3")


def _unreadable(reading) -> dict[str, Any]:
    """A reachable route reporting a seam it could not read.

    **STATUS 200, AND THE PROBLEM IN `results`**, exactly as
    `capability_router._unreadable` does: this route worked, and the envelope
    status is about this route, not about whether a seam was there to read.
    """
    return generate_return(results={
        "unreadable": True,
        "problem": reading.reason,
        "remedy": ("The producer writes the seam with "
                   "`dossier overview --json`; point this window at it with "
                   f"the {overview_service.SEAM_ENV} environment variable or "
                   "place it in the working directory."),
        "where": reading.source,
    })


@OverviewRouter.get("/gjgf")
async def overview_gjgf(
    seam: str | None = Query(None),
    layout: str = Query("Kamada Kawai"),
    palette_id: str = Query("0"),
) -> dict[str, Any]:
    """dossier's overview as `GraphData`, in this project's envelope.

    The only relation drawn is that a section lists a subject; the masthead
    figures ride in `metadata.masthead`, and every name is whatever the producer
    published -- this window redacts nothing and invents nothing.
    """
    reading = overview_service.read(seam)
    if not reading.ok:
        return _unreadable(reading)

    options = _options(layout, palette_id)
    return generate_return(results={
        "graph": overview_service.as_gjgf(reading, options),
        "metadata": overview_service.metadata(reading, options),
    })


@OverviewRouter.get("/data")
async def overview_data(seam: str | None = Query(None)) -> dict[str, Any]:
    """The sections themselves, without a layout -- the reading the terminal
    prints as tables, handed over as data so the two windows can be compared."""
    reading = overview_service.read(seam)
    if not reading.ok:
        return _unreadable(reading)

    return generate_return(results={
        "source": reading.source,
        "scope": reading.scope,
        "generated_from": reading.generated_from,
        "masthead": reading.masthead,
        "sections": reading.sections,
        "caveat": overview_service.caveat(reading),
    })
