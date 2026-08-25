"""The estate's capabilities, on this project's canvas.

**THIS SERVES A CODECARTO GRAPH, NOT A PICTURE OF ONE**, the same rule
`topology_router` follows and for the same reason: `/capabilities/gjgf` returns
the graph format every other plot here produces, so the page renders it with the
same canvas, the same layouts, the same palettes and the same radial menu. A
bespoke shape here would mean a bespoke renderer there.

**THE ROUTES, AND WHAT EACH ANSWERS.**

- `/capabilities/gjgf` -- the graph as `GraphData`, which is what the
  application's panel plots. The primary route.
- `/capabilities/data` -- the reading itself: every declaration, its rungs and
  its pointers, without a layout. That is what makes this window's answer
  comparable with `dossier`'s, rather than only with the file both read.

**A PIN THAT PREDATES THE REGISTRY IS THE ORDINARY CASE**, not an error. The
governance submodule is pinned per project and moves on a propagation, so a
checkout can legitimately be older than the file. That answers 200 with
`unreadable` in the results and draws no canvas -- an empty graph would look
like an estate that declares no capabilities, which is a different and much
worse claim.

Every route answers in `generate_return`'s envelope, like every other router
here.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from codecarto.models.plot_data import PlotOptions
from codecarto.services import capability_service
from codecarto.util.utilities import generate_return

CapabilityRouter = APIRouter()


def _options(layout: str, palette_id: str) -> PlotOptions:
    return PlotOptions(layout=layout, palette_id=palette_id, type="d3")


def _unreadable(reading) -> dict[str, Any]:
    """A reachable route reporting a registry it could not read.

    **STATUS 200, AND THE PROBLEM IN `results`**, exactly as
    `topology_router._unreachable` does: this route worked, and the envelope
    status is about this route. `RequestHandler.handleResponse` also treats any
    status but 200 as a hard error and parses the message in one exact shape,
    so a non-200 envelope reaches the browser as a `TypeError` with no detail.
    """
    return generate_return(results={
        "unreadable": True,
        "problem": reading.reason,
        "remedy": ("A propagation moves this project's governance pin: "
                   "`propagate/<name>-<date>` in the corpus, merged into "
                   "`project/<name>`, then the submodule moved to that tip."),
        "where": reading.source,
    })


@CapabilityRouter.get("/gjgf")
async def capabilities_gjgf(
    layout: str = Query("Kamada Kawai"),
    palette_id: str = Query("0"),
) -> dict[str, Any]:
    """The capability registry as `GraphData`, in this project's envelope.

    Every edge is one the registry declared. Nothing is added to make the graph
    connected, and a rung naming no evidence draws nothing at all -- the count
    of those rides in `metadata.unmeasured`, with the sentence a reader needs in
    `metadata.caveat`.
    """
    reading = capability_service.read()
    if not reading.ok:
        return _unreadable(reading)

    options = _options(layout, palette_id)
    return generate_return(results={
        "graph": capability_service.as_gjgf(reading, options),
        "metadata": capability_service.metadata(reading, options),
    })


@CapabilityRouter.get("/data")
async def capabilities_data() -> dict[str, Any]:
    """Every declaration and its rungs, without a layout.

    The claim and the pointers side by side, which is the comparison the record
    exists for: nothing here reconciles them, and a rung with no pointer reads
    `unknown` rather than `false`.
    """
    reading = capability_service.read()
    if not reading.ok:
        return _unreadable(reading)

    rows = []
    for entry in reading.capabilities:
        rows.append({
            "id": entry["id"],
            "title": entry.get("title", ""),
            "repo": entry.get("repo", ""),
            "phase": entry.get("phase", capability_service.UNKNOWN),
            "stated_by": entry.get("stated_by", ""),
            "stated_on": str(entry.get("stated_on", "")),
            "what": (entry.get("what") or "").strip(),
            "cannot_see": (entry.get("cannot_see") or "").strip(),
            "evidence": {rung: capability_service.pointer(entry, rung)
                         for rung in capability_service.RUNGS},
        })

    return generate_return(results={
        "source": reading.source,
        "rungs": list(capability_service.RUNGS),
        "capabilities": rows,
        "unmeasured": capability_service.unmeasured(reading),
        "caveat": capability_service.caveat(reading),
    })
