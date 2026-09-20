"""The harness's topology, as graph data this project already knows how to draw.

**THIS SERVES A CODECARTO GRAPH, NOT A PICTURE OF ONE.** An earlier version
hand-wrote SVG in this file, which put a second renderer beside codecarto's own:
its layouts, palettes, serializer and canvas were all bypassed. `/topology/gjgf`
returns the same graph format every other plot here produces, so a topology can
be laid out with any registered layout and restyled by choosing a palette,
because it is on the path where those things happen.

**THE ROUTES, AND WHAT EACH ANSWERS.**

- `/topology/gjgf` -- the graph as `GraphData`, which is what the application's
  Topology panel plots. The primary route.
- `/topology/available` -- what the harness offers and what can lay it out, so
  a picker fills itself without drawing anything first.
- `/topology/data` -- what *this window drew*: widths, styles, and how many
  edges nobody measured. That is what makes it comparable with another window's
  answer, rather than merely with the payload both were handed.

Every one answers in `generate_return`'s envelope, like every other router here.

**THERE IS NO PAGE HERE ANY MORE, AND THAT IS THE POINT.** This router used to
also serve a standalone server-rendered page, justified as the build-free thing
to open when the question was whether the harness answered at all. It drew the
same payload the Topology panel draws, with its own gravis figure, its own CSS
and its own legend -- a second implementation of the one thing this router
exists to avoid. The panel is the front end; `/topology/available` answers the
liveness question without rendering anything.

**A HARNESS THAT IS NOT RUNNING IS THE ORDINARY CASE.** It is a separate process
on a separate port and very often has not been started. Every route here reports
that as a `problem` carrying the command that starts it, rather than as an empty
graph -- an empty graph looks like an answer.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from codecarto.models.plot_data import PlotOptions
from codecarto.services import estate_service, qmcp_client, topology_service
from codecarto.util.utilities import generate_return

TopologyRouter = APIRouter()

# Every layout `Positions` registers is offered. Read from the registry
# rather than listed here, so the picker cannot drift from what exists.
def _layouts() -> list[str]:
    from codecarto.services.position_service import Positions

    found = []
    for layout in Positions(include_networkx=True, include_custom=True)._layouts:
        name = str(layout.get("name", ""))
        if name.endswith("_layout"):
            found.append(name[: -len("_layout")].replace("_", " ").title())
    return found or ["Spring"]


def _options(layout: str, palette_id: str) -> PlotOptions:
    return PlotOptions(layout=layout, palette_id=palette_id, type="d3")


async def _fetch(kind: str, subject: str | None, level: int):
    return (qmcp_client.relations(subject) if subject
            else qmcp_client.shape(kind, level))


def _unreachable(reach) -> dict[str, Any]:
    """A reachable route reporting an unreachable harness.

    **STATUS 200, AND THE PROBLEM IN `results`.** This route worked -- it is the
    thing behind it that did not, and an envelope status of 503 would say this
    service is unavailable, which is false. It also matters mechanically:
    `RequestHandler.handleResponse` treats any status but 200 as a hard error
    and parses the message with `split('\n\tmessage:')[2]`, which raises on
    every message not in that exact shape. So a non-200 envelope reached the
    browser as a `TypeError` with no detail at all.
    """
    return generate_return(results={
        "unreachable": True,
        "problem": reach.problem,
        "remedy": reach.remedy,
        "where": reach.where,
    })


@TopologyRouter.get("/gjgf")
async def topology_gjgf(
    kind: str = Query("delegation"),
    subject: str | None = Query(None),
    level: int = Query(2, ge=0, le=2),
    layout: str = Query("Kamada Kawai"),
    palette_id: str = Query("0"),
) -> dict[str, Any]:
    """The topology as `GraphData`, in this project's response envelope.

    **THE SHAPE IS THE FRONT END'S `GraphData`, EXACTLY.** `{graph, metadata}`
    with `layout`, `type`, `nodeCount`, `edgeCount` and `palette_id` -- so the
    web application plots a topology through `handlePlotData` like any other
    graph, and inherits its renderer, its styling, its zoom and drag and
    tooltip extensions and its radial menu. A bespoke shape here would have
    meant a bespoke renderer there, which is what this whole pass is undoing.

    `generate_return` is the envelope every other router here uses. A route
    that invented its own would make the client special-case one endpoint.
    """
    reach = await _fetch(kind, subject, level)
    if not reach.ok:
        return _unreachable(reach)

    options = _options(layout, palette_id)
    view = topology_service.render(reach.document["payload"],
                                   reach.document.get("encoding"))
    try:
        graph = topology_service.as_gjgf(view, options)
    except ValueError as error:
        # A layout nobody registered. The seam answered; the window could not
        # lay it out as asked, and says so rather than raising.
        return generate_return(results=estate_service.unknown_layout(
            error, f"/topology/gjgf?layout={layout}"))
    return generate_return(results={
        "graph": graph,
        "metadata": topology_service.metadata(view, reach.document, options),
    })


@TopologyRouter.get("/available")
async def topology_available() -> dict[str, Any]:
    """Every topology the harness offers, for a picker to fill itself from.

    Separate from the views so a control panel can populate without drawing
    anything -- the front end asks this once and the answer is small.
    """
    reach = qmcp_client.topologies()
    if not reach.ok:
        found = _unreachable(reach)
        found["results"]["topologies"] = []
        found["results"]["layouts"] = _layouts()
        return found
    return generate_return(results={
        "topologies": reach.document.get("topologies", []),
        "encoding": reach.document.get("encoding", []),
        "layouts": _layouts(),
    })


@TopologyRouter.get("/data")
async def topology_data(
    kind: str = Query("delegation"),
    subject: str | None = Query(None),
    level: int = Query(2, ge=0, le=2),
) -> dict[str, Any]:
    """The resolved rendering: what this window drew, edge by edge.

    Not the graph and not the payload -- the widths and styles this side
    resolved. That is what makes it comparable with another window's answer
    rather than with the document both were handed.
    """
    reach = await _fetch(kind, subject, level)
    if not reach.ok:
        return _unreachable(reach)

    view = topology_service.render(reach.document["payload"],
                                   reach.document.get("encoding"))
    return generate_return(results={
        "source": reach.document.get("source", ""),
        "topology": view.topology,
        "caveat": view.caveat(),
        "measured": view.measured,
        "unmeasured": view.unmeasured,
        # Nodes carry `address` and `content`: what the harness called it, and
        # where the thing it names can actually be read.
        "nodes": view.nodes,
        "edges": [{"source": e.source, "target": e.target, "label": e.label,
                   "width": e.width, "style": e.style, "colour": e.colour,
                   "measured": e.measured, "weight": e.weight,
                   "title": e.title} for e in view.edges],
    })

