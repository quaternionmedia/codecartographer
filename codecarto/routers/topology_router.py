"""The harness's topology, as a page.

**THIS IS THE HALF THAT WAS MISSING.** `topology_service` could resolve a
payload into channels and `qmcp_client` can fetch one, and until this router
existed neither was reachable from a browser -- so "codecarto is the harness's
front end on the web" was true of a module and false of the product. A renderer
nothing serves is a claim, and it reads exactly like a finished feature.

**THE PAGE DRAWS THE ENCODING, NOT ITS OWN TASTE.** Width carries strength.
Dashes carry unmeasured. Colour carries the kind of edge. Shape carries the kind
of box. Every one of those comes from the `encoding` block the harness serves
beside the payload, so when the harness changes its mind this page changes with
it instead of confidently drawing an old contract.

**AND AN UNMEASURED EDGE IS NEVER A THIN ONE.** It is the single thing both
front ends are tested for, in both repositories, because it is the one mistake
that produces a picture nobody can tell is wrong.
"""

from __future__ import annotations

import html
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from codecarto.services import qmcp_client
from codecarto.services.topology_service import RenderedTopology, render

TopologyRouter = APIRouter()

# Laid out in rings rather than by a solver: the payloads are small, a ring is
# stable between renders, and a reader comparing this with the terminal window
# needs the same node in the same place twice.
WIDTH, HEIGHT = 900, 520


@TopologyRouter.get("/data")
async def topology_data(
    kind: str = Query("delegation"),
    subject: str | None = Query(None),
    level: int = Query(2, ge=0, le=2),
) -> dict[str, Any]:
    """The resolved rendering, as JSON.

    Serves what this window *drew*, not what it was handed -- the widths, the
    styles and the count of unmeasured edges. That is what makes it comparable
    with another window's answer rather than merely with the same payload.
    """
    reach = (qmcp_client.relations(subject) if subject
             else qmcp_client.shape(kind, level))
    if not reach.ok:
        return {"ok": False, "problem": reach.problem, "remedy": reach.remedy,
                "where": reach.where}

    view = render(reach.document["payload"], reach.document.get("encoding"))
    return {
        "ok": True,
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
    }


@TopologyRouter.get("", response_class=HTMLResponse)
@TopologyRouter.get("/", response_class=HTMLResponse)
async def topology_page(
    kind: str = Query("delegation"),
    subject: str | None = Query(None),
    level: int = Query(2, ge=0, le=2),
) -> str:
    """The page a person opens."""
    listing = qmcp_client.topologies()
    reach = (qmcp_client.relations(subject) if subject
             else qmcp_client.shape(kind, level))

    if not reach.ok:
        return _shell(_problem(reach), listing, kind, subject)

    view = render(reach.document["payload"], reach.document.get("encoding"))
    body = _view(view, reach.document)
    return _shell(body, listing, kind, subject)


# --- rendering -----------------------------------------------------------------


def _positions(nodes: list[dict]) -> dict[str, tuple[float, float]]:
    """A subject in the middle, everything else on a ring around it.

    Deterministic, because two loads of the same topology that moved the nodes
    would make a reader think something changed.
    """
    import math

    if not nodes:
        return {}
    middle = [n for n in nodes if n.get("kind") == "input"] or [nodes[0]]
    ring = [n for n in nodes if n is not middle[0]]
    found = {middle[0]["id"]: (WIDTH / 2, HEIGHT / 2)}
    radius = min(WIDTH, HEIGHT) * 0.36
    for index, node in enumerate(ring):
        angle = -math.pi / 2 + (2 * math.pi * index / max(1, len(ring)))
        found[node["id"]] = (WIDTH / 2 + radius * math.cos(angle),
                             HEIGHT / 2 + radius * math.sin(angle))
    return found


def _node_shape(node: dict, x: float, y: float) -> str:
    """A box drawn as its kind. A gate is a gate at any size."""
    label = html.escape(str(node.get("label", "")))
    shape = node.get("shape", "box")
    title = html.escape(str(node.get("note") or node.get("label", "")))
    common = 'class="node" fill="var(--node)" stroke="var(--node-line)" stroke-width="1.5"'
    if shape == "ellipse":
        body = f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="62" ry="26" {common}/>'
    elif shape == "diamond":
        body = (f'<polygon points="{x:.1f},{y - 30:.1f} {x + 66:.1f},{y:.1f} '
                f'{x:.1f},{y + 30:.1f} {x - 66:.1f},{y:.1f}" {common}/>')
    elif shape == "cylinder":
        body = (f'<rect x="{x - 58:.1f}" y="{y - 24:.1f}" width="116" '
                f'height="48" rx="16" {common}/>')
    else:
        body = (f'<rect x="{x - 62:.1f}" y="{y - 24:.1f}" width="124" '
                f'height="48" rx="3" {common}/>')
    return (f'<g><title>{title}</title>{body}'
            f'<text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" '
            f'class="node-label">{label}</text></g>')


def _view(view: RenderedTopology, document: dict) -> str:
    """The topology as SVG, plus what a reader must be told about it."""
    at = _positions(view.nodes)
    parts = []

    # Edges first, so a node never sits under a line.
    seen: dict[tuple[str, str], int] = {}
    for edge in view.edges:
        start, end = at.get(edge.source), at.get(edge.target)
        if not start or not end:
            continue
        # Parallel edges are bowed apart by increasing amounts. Three readings
        # of one relation drawn on top of each other would look like one.
        key = (edge.source, edge.target)
        seen[key] = seen.get(key, 0) + 1
        bow = (seen[key] - 1) * 26
        mx = (start[0] + end[0]) / 2
        my = (start[1] + end[1]) / 2 - bow
        dash = ' stroke-dasharray="8 6"' if edge.style == "dashed" else ""
        parts.append(
            f'<g><title>{html.escape(edge.title)}</title>'
            f'<path d="M {start[0]:.1f} {start[1]:.1f} Q {mx:.1f} {my:.1f} '
            f'{end[0]:.1f} {end[1]:.1f}" fill="none" '
            f'stroke="{edge.colour}" stroke-width="{edge.width:.2f}"{dash}/>'
            f'<text x="{mx:.1f}" y="{my - 6:.1f}" text-anchor="middle" '
            f'class="edge-label">{html.escape(edge.label)}</text></g>')

    for node in view.nodes:
        x, y = at.get(node["id"], (0, 0))
        parts.append(_node_shape(node, x, y))

    source = html.escape(str(document.get("source", "")))
    surveyed = document.get("surveyed")
    provenance = f"from the {source}" if source else ""
    if surveyed:
        provenance += f", {surveyed} thread(s) read"

    return f"""
    <div class="head">
      <h1>{html.escape(view.topology)}</h1>
      <p class="caption">{html.escape(view.caption)}</p>
      <p class="provenance">{html.escape(provenance)}</p>
    </div>

    <p class="caveat {'warn' if view.unmeasured else 'clean'}">
      {html.escape(view.caveat())}
    </p>

    <div class="canvas">
      <svg viewBox="0 0 {WIDTH} {HEIGHT}" width="100%"
           role="img" aria-label="{html.escape(view.topology)} topology">
        {''.join(parts)}
      </svg>
    </div>

    {_legend()}
    """


def _legend() -> str:
    """What each channel carries. Drawn with real lines, because a legend that
    described the encoding in words would not show the difference this page
    exists to preserve."""
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
        &mdash; it has no width to read.</span>
      </div>
    </div>
    """


def _problem(reach: qmcp_client.Reach) -> str:
    """The harness is not reachable. Say what and what to do."""
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


def _shell(body: str, listing: qmcp_client.Reach, kind: str,
           subject: str | None) -> str:
    """The page around it, with a picker for whatever the harness offers."""
    options = ""
    if listing.ok:
        options = "".join(
            f'<a class="pick{" on" if t["topology"] == kind and not subject else ""}"'
            f' href="/topology?kind={html.escape(t["topology"])}">'
            f'{html.escape(t["topology"])}</a>'
            for t in listing.document.get("topologies", []))
    subject_box = (
        f'<form class="subject" method="get" action="/topology">'
        f'<input name="subject" placeholder="a project, from the archive" '
        f'value="{html.escape(subject or "")}" aria-label="subject"/>'
        f'<button type="submit">read</button></form>')

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Topology &mdash; codecarto</title>
<style>
:root {{
  --bg: #0e1116; --panel: #151a21; --line: #2a323d;
  --ink: #e4e9f0; --mute: #8b93a1;
  --node: #1b212a; --node-line: #6db2ff;
  --warn: #e0c069; --ok: #5ac8b0;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.6 ui-sans-serif, system-ui, "Segoe UI", sans-serif; }}
.wrap {{ max-width: 1000px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
.bar {{ display: flex; flex-wrap: wrap; gap: .4rem; align-items: center;
  padding-bottom: 1.25rem; border-bottom: 1px solid var(--line);
  margin-bottom: 1.75rem; }}
.pick {{ font: 500 12px ui-monospace, monospace; letter-spacing: .04em;
  color: var(--mute); text-decoration: none; padding: .3rem .6rem;
  border: 1px solid var(--line); border-radius: 3px; }}
.pick:hover {{ color: var(--ink); border-color: var(--node-line); }}
.pick.on {{ color: var(--bg); background: var(--node-line);
  border-color: var(--node-line); }}
.subject {{ margin-left: auto; display: flex; gap: .35rem; }}
.subject input {{ background: var(--panel); border: 1px solid var(--line);
  color: var(--ink); padding: .3rem .55rem; border-radius: 3px; min-width: 15rem; }}
.subject button {{ background: var(--node-line); border: 0; color: var(--bg);
  padding: .3rem .8rem; border-radius: 3px; font-weight: 600; cursor: pointer; }}
h1 {{ font-size: 1.7rem; margin: 0 0 .2rem; letter-spacing: -.02em; }}
h2 {{ font-size: .8rem; text-transform: uppercase; letter-spacing: .1em;
  color: var(--mute); margin: 0 0 .9rem; }}
.caption {{ margin: 0; color: var(--mute); }}
.provenance {{ margin: .15rem 0 0; color: var(--mute);
  font: 12px ui-monospace, monospace; }}
.caveat {{ margin: 1.25rem 0; padding: .7rem 1rem; border-radius: 3px;
  border-left: 3px solid var(--ok); background: var(--panel); font-size: .92rem; }}
.caveat.warn {{ border-left-color: var(--warn); }}
.canvas {{ background: var(--panel); border: 1px solid var(--line);
  border-radius: 4px; padding: .5rem; overflow-x: auto; }}
.node-label {{ fill: var(--ink); font: 600 13px ui-sans-serif, system-ui;
  pointer-events: none; }}
.edge-label {{ fill: var(--mute); font: 11px ui-monospace, monospace;
  pointer-events: none; }}
.legend {{ margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid var(--line); }}
.legend-grid {{ display: grid; grid-template-columns: 7.5rem 1fr; gap: .9rem 1.25rem;
  align-items: center; }}
.legend-grid svg {{ width: 100%; height: 1.25rem; }}
.legend-grid b {{ display: block; color: var(--ink); }}
.legend-grid span {{ color: var(--mute); font-size: .87rem; line-height: 1.45; }}
.problem {{ background: var(--panel); border: 1px solid var(--line);
  border-left: 3px solid var(--warn); border-radius: 3px; padding: 1.25rem 1.4rem; }}
.problem .what {{ margin: 0 0 .6rem; font-size: 1.05rem; }}
.problem .remedy {{ margin: 0 0 .6rem; }}
.problem code {{ background: #0b0e13; padding: .1em .4em; border-radius: 3px;
  font-size: .88em; }}
.problem .where, .problem .note {{ color: var(--mute); font-size: .87rem;
  margin: .4rem 0 0; }}
</style></head>
<body><div class="wrap">
  <nav class="bar">{options}{subject_box}</nav>
  {body}
</div></body></html>"""
