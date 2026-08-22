"""The harness's topology, drawn on this project's canvas.

**THIS SERVES A CODECARTO GRAPH, NOT A PICTURE OF ONE.** The first version hand-
wrote SVG in this file, which put a second renderer beside codecarto's own: its
layouts, palettes, serializer and canvas were all bypassed. Now `/topology/gjgf`
returns the same graph format every other plot here produces, and the page
renders it with **gravis**, the same canvas -- so a topology can be laid out
with any registered layout and restyled by choosing a palette, because it is on
the path where those things happen.

**THE ROUTES, AND WHY THERE ARE THREE.**

- `/topology` -- the page a person opens. Interactive gravis canvas.
- `/topology/gjgf` -- the graph, in this project's format, for any other client.
- `/topology/data` -- what *this window drew*: widths, styles, and how many
  edges nobody measured. That is what makes it comparable with another window's
  answer, rather than merely with the payload both were handed.

**A HARNESS THAT IS NOT RUNNING IS THE ORDINARY CASE.** It is a separate process
on a separate port and very often has not been started. The page says so, says
what to run, and draws no canvas -- an empty graph looks like an answer.
"""

from __future__ import annotations

import html
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from codecarto.models.plot_data import PlotOptions
from codecarto.services import qmcp_client, topology_service
from codecarto.util.utilities import generate_return

TopologyRouter = APIRouter()

# Every layout `Positions` registers is offered. Named here rather than
# hard-coded into the page so the picker cannot drift from what exists.
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
        return generate_return(
            status=503, message=reach.problem,
            results={"problem": reach.problem, "remedy": reach.remedy,
                     "where": reach.where})

    options = _options(layout, palette_id)
    view = topology_service.render(reach.document["payload"],
                                   reach.document.get("encoding"))
    return generate_return(results={
        "graph": topology_service.as_gjgf(view, options),
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
        return generate_return(
            status=503, message=reach.problem,
            results={"problem": reach.problem, "remedy": reach.remedy,
                     "where": reach.where, "topologies": []})
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
        return generate_return(
            status=503, message=reach.problem,
            results={"problem": reach.problem, "remedy": reach.remedy,
                     "where": reach.where})

    view = topology_service.render(reach.document["payload"],
                                   reach.document.get("encoding"))
    return generate_return(results={
        "source": reach.document.get("source", ""),
        "topology": view.topology,
        "caveat": view.caveat(),
        "measured": view.measured,
        "unmeasured": view.unmeasured,
        "nodes": view.nodes,
        "edges": [{"source": e.source, "target": e.target, "label": e.label,
                   "width": e.width, "style": e.style, "colour": e.colour,
                   "measured": e.measured, "weight": e.weight,
                   "title": e.title} for e in view.edges],
    })


@TopologyRouter.get("", response_class=HTMLResponse)
@TopologyRouter.get("/", response_class=HTMLResponse)
async def topology_page(
    kind: str = Query("delegation"),
    subject: str | None = Query(None),
    level: int = Query(2, ge=0, le=2),
    layout: str = Query("Kamada Kawai"),
    palette_id: str = Query("0"),
) -> str:
    """The page a person opens."""
    listing = qmcp_client.topologies()
    reach = await _fetch(kind, subject, level)

    if not reach.ok:
        return _shell(_problem(reach), listing, kind, subject, layout)

    options = _options(layout, palette_id)
    view = topology_service.render(reach.document["payload"],
                                   reach.document.get("encoding"))
    canvas, note = _canvas(view, reach.document, options)
    return _shell(_view(view, reach.document, canvas, note), listing, kind,
                  subject, layout)


# --- the canvas ----------------------------------------------------------------


def _canvas(view, document, options) -> tuple[str, str]:
    """The gravis figure, as embeddable HTML.

    Returns the note as well as the canvas: a figure that could not be built is
    a thing to say out loud, not a blank rectangle. gravis is imported here
    rather than at module load because the rest of these routes -- and the
    honest "harness is down" page -- must work without it.
    """
    try:
        import gravis as gv
    except Exception as error:                     # noqa: BLE001
        return "", f"gravis is not installed here ({error})"

    try:
        graph = {"graph": topology_service.as_gjgf(view, options)}
        graph["graph"]["metadata"] = topology_service.metadata(
            view, document, options)
        figure = gv.d3(
            graph,
            graph_height=520,
            edge_curvature=0.2,          # parallel readings must not overlap
            edge_label_data_source="label",
            node_label_data_source="label",
            show_edge_label=True,
            node_hover_neighborhood=True,
            zoom_factor=1.1,
            use_edge_size_normalization=False,   # width already carries strength
            use_node_size_normalization=False,   # size already carries kind
        )
        return figure.to_html_partial(), ""
    except Exception as error:                     # noqa: BLE001
        return "", f"the canvas could not be built: {type(error).__name__}: {error}"


def _view(view, document: dict, canvas: str, note: str) -> str:
    """The drawing, and what a reader must be told about it."""
    source = html.escape(str(document.get("source", "")))
    surveyed = document.get("surveyed")
    provenance = f"from the {source}" if source else ""
    if surveyed:
        provenance += f", {surveyed} thread(s) read"

    body = (f'<div class="canvas">{canvas}</div>' if canvas
            else f'<div class="problem"><p class="what">{html.escape(note)}</p>'
                 f'<p class="note">No canvas was drawn. An empty one would look '
                 f'like an answer.</p></div>')

    return f"""
    <div class="head">
      <h1>{html.escape(view.topology)}</h1>
      <p class="caption">{html.escape(view.caption)}</p>
      <p class="provenance">{html.escape(provenance)}</p>
    </div>

    <p class="caveat {'warn' if view.unmeasured else 'clean'}">
      {html.escape(view.caveat())}
    </p>

    {body}
    {_legend()}
    """


def _legend() -> str:
    """What each channel carries, drawn with real lines. A legend that described
    the encoding in words would not show the difference this page exists to
    preserve."""
    return """
    <div class="legend">
      <h2>What the lines mean</h2>
      <div class="legend-grid">
        <svg viewBox="0 0 120 20"><line x1="2" y1="10" x2="118" y2="10"
             stroke="#6db2ff" stroke-width="4.5"/></svg>
        <span><b>Measured, strong</b>Somebody looked and found a lot.</span>

        <svg viewBox="0 0 120 20"><line x1="2" y1="10" x2="118" y2="10"
             stroke="#6db2ff" stroke-width="0.9"/></svg>
        <span><b>Measured, negligible</b>Somebody looked and found almost
        nothing. That is a finding.</span>

        <svg viewBox="0 0 120 20"><line x1="2" y1="10" x2="118" y2="10"
             stroke="#8b93a1" stroke-width="1.6" stroke-dasharray="8 6"/></svg>
        <span><b>Unmeasured</b>Nobody looked. Off the strength scale entirely
        &mdash; it has no width to read. Hover any line for its own sentence.</span>
      </div>
    </div>
    """


def _problem(reach) -> str:
    """The harness is not reachable. Say what, and what to do."""
    remedy = (f'<p class="remedy">{html.escape(reach.remedy)}</p>'
              if reach.remedy else "")
    return f"""
    <div class="head"><h1>No topology to draw</h1></div>
    <div class="problem">
      <p class="what">{html.escape(reach.problem)}</p>
      {remedy}
      <p class="where">tried <code>{html.escape(reach.where)}</code></p>
      <p class="note">This page draws what the harness says. It has not drawn
      an empty graph, because an empty graph would look like an answer.</p>
    </div>
    """


def _shell(body: str, listing, kind: str, subject: str | None,
           layout: str) -> str:
    """The page around it, with pickers for whatever actually exists."""
    picks = ""
    if listing.ok:
        picks = "".join(
            f'<a class="pick{" on" if t["topology"] == kind and not subject else ""}"'
            f' href="/topology?kind={html.escape(t["topology"])}'
            f'&layout={html.escape(layout)}">{html.escape(t["topology"])}</a>'
            for t in listing.document.get("topologies", []))

    layouts = "".join(
        f'<option value="{html.escape(name)}"'
        f'{" selected" if name == layout else ""}>{html.escape(name)}</option>'
        for name in _layouts())

    controls = (
        f'<form class="controls" method="get" action="/topology">'
        f'<input type="hidden" name="kind" value="{html.escape(kind)}"/>'
        f'<select name="layout" aria-label="layout">{layouts}</select>'
        f'<input name="subject" placeholder="a project, from the archive" '
        f'value="{html.escape(subject or "")}" aria-label="subject"/>'
        f'<button type="submit">draw</button></form>')

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Topology &mdash; codecarto</title>
<style>
:root {{
  --bg:#0e1116; --panel:#151a21; --line:#2a323d; --ink:#e4e9f0;
  --mute:#8b93a1; --accent:#6db2ff; --warn:#e0c069; --ok:#5ac8b0;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.6 ui-sans-serif, system-ui, "Segoe UI", sans-serif; }}
.wrap {{ max-width:1040px; margin:0 auto; padding:2rem 1.25rem 4rem; }}
.bar {{ display:flex; flex-wrap:wrap; gap:.4rem; align-items:center;
  padding-bottom:1.25rem; border-bottom:1px solid var(--line); margin-bottom:1.75rem; }}
.pick {{ font:500 12px ui-monospace,monospace; letter-spacing:.04em;
  color:var(--mute); text-decoration:none; padding:.3rem .6rem;
  border:1px solid var(--line); border-radius:3px; }}
.pick:hover {{ color:var(--ink); border-color:var(--accent); }}
.pick.on {{ color:var(--bg); background:var(--accent); border-color:var(--accent); }}
.controls {{ margin-left:auto; display:flex; gap:.35rem; }}
.controls input, .controls select {{ background:var(--panel);
  border:1px solid var(--line); color:var(--ink); padding:.3rem .55rem;
  border-radius:3px; }}
.controls input {{ min-width:14rem; }}
.controls button {{ background:var(--accent); border:0; color:var(--bg);
  padding:.3rem .8rem; border-radius:3px; font-weight:600; cursor:pointer; }}
h1 {{ font-size:1.7rem; margin:0 0 .2rem; letter-spacing:-.02em; }}
h2 {{ font-size:.8rem; text-transform:uppercase; letter-spacing:.1em;
  color:var(--mute); margin:0 0 .9rem; }}
.caption {{ margin:0; color:var(--mute); }}
.provenance {{ margin:.15rem 0 0; color:var(--mute); font:12px ui-monospace,monospace; }}
.caveat {{ margin:1.25rem 0; padding:.7rem 1rem; border-radius:3px;
  border-left:3px solid var(--ok); background:var(--panel); font-size:.92rem; }}
.caveat.warn {{ border-left-color:var(--warn); }}
.canvas {{ background:var(--panel); border:1px solid var(--line);
  border-radius:4px; padding:.5rem; overflow-x:auto; }}
.legend {{ margin-top:2rem; padding-top:1.5rem; border-top:1px solid var(--line); }}
.legend-grid {{ display:grid; grid-template-columns:7.5rem 1fr; gap:.9rem 1.25rem;
  align-items:center; }}
.legend-grid svg {{ width:100%; height:1.25rem; }}
.legend-grid b {{ display:block; color:var(--ink); }}
.legend-grid span {{ color:var(--mute); font-size:.87rem; line-height:1.45; }}
.problem {{ background:var(--panel); border:1px solid var(--line);
  border-left:3px solid var(--warn); border-radius:3px; padding:1.25rem 1.4rem; }}
.problem .what {{ margin:0 0 .6rem; font-size:1.05rem; }}
.problem code {{ background:#0b0e13; padding:.1em .4em; border-radius:3px; }}
.problem .where, .problem .note {{ color:var(--mute); font-size:.87rem; margin:.4rem 0 0; }}
</style></head>
<body><div class="wrap">
  <nav class="bar">{picks}{controls}</nav>
  {body}
</div></body></html>"""
