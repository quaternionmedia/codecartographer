"""The harness's topology, as a codecarto graph.

**IT GOES THROUGH THIS PROJECT'S PIPELINE, NOT AROUND IT.** The first version of
this module resolved the payload into widths and colours and the router hand-
wrote SVG, which meant a second renderer living beside codecarto's own: its
layouts, its palette, its serializer and its canvas were all bypassed, and a
topology could not be laid out with `Kamada Kawai` or restyled by choosing a
palette, because none of that was in the path.

So the shape of this module is: **build a `networkx` graph whose nodes speak the
palette's vocabulary, and hand it to `GraphSerializer`.** Everything downstream
-- layout, positions, gJGF, gravis -- is the same code every other graph in this
project goes through. A topology is now a graph codecarto draws, rather than a
picture something else drew nearby.

**WHAT IS SPECIAL ABOUT A TOPOLOGY, AND IT IS ONLY THIS.** An edge carries a
`weight` that may be `None`, and `None` means *nobody measured this* rather than
*this is small*. Every other graph here has edges that are simply present. So
this module's whole contribution is putting `measured` on its own visual channel
-- line style -- and keeping it off the width scale, so a reader can tell an
unlooked-at relation from a weak one. That distinction is the reason the harness
sends a `weight` of `null` instead of a `0`, and losing it here would waste the
care taken at the other end.

**A MULTIGRAPH, DELIBERATELY.** Three threads each finding a relation to one
delta is three observations with three weights, not one. `MultiDiGraph` keeps
them; `DiGraph` silently keeps the last.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from codecarto.models.plot_data import Palette, PlotOptions
from codecarto.services import palette_service

# A topology box's `kind` -> the node `type` the palette names. The palette
# speaks in capitalised type names (`ClassDef`, `Worker`) and maps those to
# dotted bases; this is the join, and it lives here because the harness's
# vocabulary is the harness's to change.
KIND_TO_TYPE = {
    "input": "Input",
    "worker": "Worker",
    "gate": "Gate",
    "store": "Store",
    "output": "Output",
}
DEFAULT_TYPE = "Worker"

# Line width in points, for the strength axis. The floor is deliberately
# visible: a measured-but-negligible edge is a finding, and an edge that
# vanished into the background would read as absent.
MIN_WIDTH = 0.8
MAX_WIDTH = 4.5

MEASURED_STYLE = "solid"
UNMEASURED_STYLE = "dashed"

# `unmeasured` gets its own width, off the strength scale entirely. It is not
# MIN_WIDTH: that is the width of a measured near-zero edge, and the two must
# not collide.
UNMEASURED_WIDTH = 1.6

COLOURS = {
    "flow": "#6db2ff",
    "feedback": "#5ac8b0",
    "refusal": "#e06c75",
}
DEFAULT_COLOUR = "#9aa0a6"


# --- where the thing a node represents actually lives --------------------------
#
# **`content` IS A GENERAL NODE ATTRIBUTE, NOT A TOPOLOGY ONE.** It means "where
# the thing this node stands for can be read". For a topology box it is the
# repository the address names; for a parsed-code node it would be the file. A
# renderer that knows how to open `content` can therefore navigate any graph
# this project draws, which is the point of putting it on the node rather than
# in the topology page.
#
# **DERIVED FROM THE ADDRESS, AND NONE WHEN THERE IS NOT ONE.** An address is
# `<owner>/<repo>/<kind>/<id>`; the first two segments name the repository. A
# box with no address -- a gate, a stage, anything that is not a place --
# carries no content, and inventing a URL for it would send a reader somewhere
# nobody named.

FORGE = "https://github.com"
"""Where an `<owner>/<repo>` is read. **A default, not a fact**: an address says
which account owns a repository and not which forge hosts it. Override with
`CODECARTO_FORGE` for an installation whose repositories live elsewhere."""


def content_for(address: str) -> str | None:
    """The URL where the thing at `address` can be read, or None.

    None rather than a guess: a topology box that is a stage in a pipeline is
    not a place, and a link to nowhere is worse than no link because it looks
    like it goes somewhere.
    """
    import os

    parts = [p for p in str(address or "").split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    forge = (os.environ.get("CODECARTO_FORGE") or FORGE).rstrip("/")
    return f"{forge}/{owner}/{repo}"


@dataclass
class RenderedEdge:
    """One arrow, with every channel resolved and each traceable to an axis."""

    source: str
    target: str
    label: str = ""
    width: float = UNMEASURED_WIDTH
    style: str = UNMEASURED_STYLE
    colour: str = DEFAULT_COLOUR
    measured: bool = False
    weight: float | None = None
    basis: str = ""

    @property
    def title(self) -> str:
        """Hover text. **The place the caveat survives.**

        A picture cannot say "nobody measured this" in a way that stays attached
        to the line, so the sentence rides the edge itself rather than a legend
        somebody scrolls past.
        """
        if not self.measured:
            return (f"{self.label or 'relation'}: not measured. This edge is "
                    f"drawn dashed because nobody looked, which is different "
                    f"from looking and finding it weak")
        detail = f", from {self.basis}" if self.basis else ""
        return f"{self.label or 'relation'}: strength {self.weight:.2f}{detail}"


@dataclass
class RenderedTopology:
    """A whole view, in a form this project's renderers accept."""

    topology: str = ""
    level: int = 0
    caption: str = ""
    status: str = ""
    marks: list[str] = field(default_factory=list)
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[RenderedEdge] = field(default_factory=list)
    unmeasured: int = 0
    """How many edges nobody measured. **Surfaced rather than derivable**: a
    picture where most lines are dashed is a different artefact from one where
    none are, and a reader should not have to count."""

    @property
    def measured(self) -> int:
        return len(self.edges) - self.unmeasured

    def caveat(self) -> str:
        """What a reader must be told before believing the shape."""
        if not self.edges:
            return "nothing to draw"
        if self.unmeasured == 0:
            return f"every one of {len(self.edges)} edge(s) is measured"
        if self.unmeasured == len(self.edges):
            return (f"none of the {len(self.edges)} edge(s) is measured -- this "
                    f"is the shape of the relation and says nothing about "
                    f"strength")
        return (f"{self.measured} of {len(self.edges)} edge(s) measured; the "
                f"rest are drawn dashed because nobody looked")


def render(payload: dict[str, Any],
           encoding: list[dict[str, Any]] | None = None,
           palette: Palette | None = None) -> RenderedTopology:
    """A payload from the harness, resolved into channels.

    `encoding` is the harness's own declaration of which channel carries which
    axis. Passing it is how this window stays honest when the far side changes;
    omitting it falls back to the mapping documented above, which is the same
    mapping and may go stale.
    """
    axes = _axes(encoding)
    view = RenderedTopology(
        topology=str(payload.get("topology") or ""),
        level=int(payload.get("level") or 0),
        caption=str(payload.get("caption") or ""),
        status=str(payload.get("status") or ""),
        marks=list(payload.get("marks") or []),
    )

    for box in payload.get("boxes") or []:
        kind = str(box.get("kind") or "")
        node_type = KIND_TO_TYPE.get(kind, DEFAULT_TYPE)
        style = palette_service.style_for_type(node_type, palette)
        address = str(box.get("note") or "")
        view.nodes.append({
            "id": str(box.get("id") or ""),
            "label": str(box.get("label") or ""),
            # The address the harness sent, and where it can be read. Both are
            # carried so a renderer can show one and open the other.
            "address": address,
            "content": content_for(address),
            # The palette's vocabulary, carried on the node so anything else in
            # this project can restyle it without knowing what a topology is.
            "type": node_type,
            "base": style.base,
            "kind": kind,
            "shape": style.shape,
            "color": style.color,
            "size": style.size,
            "note": str(box.get("note") or ""),
            "count": box.get("count"),
        })

    colour_carries_kind = axes.get("line_colour") == "relation_kind"

    for arrow in payload.get("arrows") or []:
        weight = arrow.get("weight")
        # **`is None`, NOT FALSINESS.** A measured weight of 0.0 is a real
        # finding -- somebody looked and found nothing there -- and `if not
        # weight` would file it with the unlooked-at.
        measured = weight is not None
        edge = RenderedEdge(
            source=str(arrow.get("from") or ""),
            target=str(arrow.get("to") or ""),
            label=str(arrow.get("label") or ""),
            measured=measured,
            weight=None if not measured else float(weight),
            basis=str(arrow.get("basis") or ""),
            colour=(COLOURS.get(str(arrow.get("kind") or ""), DEFAULT_COLOUR)
                    if colour_carries_kind else DEFAULT_COLOUR),
        )
        if measured:
            edge.width = MIN_WIDTH + (MAX_WIDTH - MIN_WIDTH) * _clamp(edge.weight)
            edge.style = MEASURED_STYLE
        else:
            edge.width = UNMEASURED_WIDTH
            edge.style = UNMEASURED_STYLE
            view.unmeasured += 1
        view.edges.append(edge)

    return view


def as_graph(view: RenderedTopology):
    """The view as a `networkx` graph this project's serializer accepts.

    Imported inside the function so that reading a payload does not require a
    graph library. A window that could not render should still be able to say
    what it was given.
    """
    import networkx as nx

    graph = nx.MultiDiGraph(topology=view.topology, caption=view.caption,
                            status=view.status, unmeasured=view.unmeasured)
    for node in view.nodes:
        # `content` travels on the node, so any renderer that knows how to open
        # it can navigate any graph -- not only a topology.
        graph.add_node(node["id"], **{k: v for k, v in node.items()
                                      if k != "id"},
                       hover=_hover_for(node),
                       # **THE NAVIGATION.** gravis renders `click` as a detail
                       # panel and keeps the markup, so a node whose content is
                       # known becomes a way into the code it represents. A node
                       # that is not a place gets a sentence saying so rather
                       # than a dead link.
                       click=_click_for(node))
    for edge in view.edges:
        graph.add_edge(
            edge.source, edge.target,
            label=edge.label,
            # gravis reads `size` for edge thickness and `color` for its
            # colour, so the channels arrive named as the canvas expects.
            size=edge.width, color=edge.colour,
            # `hover` is where the unmeasured caveat survives a picture.
            hover=edge.title,
            style=edge.style, measured=edge.measured,
            # **NOT `weight`.** `weight` is networkx's own edge attribute:
            # `kamada_kawai_layout` and every shortest-path layout read it as a
            # distance. An unmeasured edge carries `None`, and networkx compared
            # `None` with a float and raised from inside the layout -- an error
            # about types, several frames below anything that mentions
            # topologies. The harness's measurement is `strength` here, which
            # no layout claims.
            strength=edge.weight,
            title=edge.title,
        )
    return graph


def _click_for(node: dict[str, Any]) -> str:
    """The detail panel for one node: what it is, and a way to the code.

    **A NODE THAT IS NOT A PLACE SAYS SO.** A gate or a stage has no repository,
    and a link to nowhere is worse than no link because it looks like it goes
    somewhere. That distinction is the same one the whole encoding turns on --
    an absence stated, rather than filled in.
    """
    import html as _html

    label = _html.escape(str(node.get("label") or node.get("id") or ""))
    address = _html.escape(str(node.get("address") or ""))
    content = node.get("content")

    lines = [f"<b>{label}</b>"]
    if address:
        lines.append(f"<div><code>{address}</code></div>")
    if content:
        safe = _html.escape(str(content), quote=True)
        lines.append(
            f'<div><a href="{safe}" target="_blank" rel="noreferrer">'
            f"open the code this represents</a></div>")
    else:
        lines.append("<div><i>not a place &mdash; nothing to open</i></div>")
    return "".join(lines)


def _hover_for(node: dict[str, Any]) -> str:
    """What a reader sees on the node, including where it goes.

    The address alone does not say it is followable, and a link with no address
    does not say what it points at. Both, or neither.
    """
    address = str(node.get("note") or "")
    label = str(node.get("label") or "")
    if node.get("content"):
        return f"{address or label}  --  open the repository"
    return address or label


def as_gjgf(view: RenderedTopology, options: PlotOptions | None = None
            ) -> dict[str, Any]:
    """The view in this project's own graph format, laid out by its layouts.

    **THE WHOLE REASON THIS MODULE EXISTS IN THIS SHAPE.** Everything after this
    call -- positions, scaling, gJGF, gravis -- is the path every other graph in
    codecarto takes. A topology that rendered itself would have to reimplement
    all of it, and would drift from it the first time either changed.
    """
    from codecarto.services.graph_serializer import GraphSerializer

    chosen = options or PlotOptions(layout="Kamada Kawai")
    return GraphSerializer.serialize_to_gjgf(as_graph(view), chosen)


def metadata(view: RenderedTopology, document: dict[str, Any],
             options: PlotOptions | None = None) -> dict[str, Any]:
    """Graph-level facts the canvas and the page both read.

    The caveat is here rather than only on the page: a client rendering this
    gJGF somewhere else must be able to reach the sentence that says how much
    of the picture was measured.
    """
    chosen = options or PlotOptions(layout="Kamada Kawai")
    return {
        "layout": chosen.layout,
        "type": chosen.type,
        "palette_id": chosen.palette_id,
        "topology": view.topology,
        "caption": view.caption,
        "source": document.get("source", ""),
        "surveyed": document.get("surveyed"),
        "nodeCount": len(view.nodes),
        "edgeCount": len(view.edges),
        "measured": view.measured,
        "unmeasured": view.unmeasured,
        "caveat": view.caveat(),
        "background_color": "#151a21",
        "node_label_color": "#e4e9f0",
        "edge_label_color": "#8b93a1",
    }


def _axes(encoding: list[dict[str, Any]] | None) -> dict[str, str]:
    """Channel to axis, as the harness declared it."""
    if not encoding:
        return {"line_weight": "strength", "line_style": "measured",
                "line_colour": "relation_kind", "node_shape": "box_kind"}
    return {str(c.get("channel")): str(c.get("axis")) for c in encoding}


def _clamp(value: float) -> float:
    return 0.0 if value < 0 else 1.0 if value > 1 else value
