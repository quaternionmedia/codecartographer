"""The harness's topology, drawn as a graph, in this window.

**THE SAME PAYLOAD `dossier` DRAWS AS TEXT.** `qmcp` decides what the topology
is; this decides what it looks like here. The two windows differ in resolution
and in nothing else, which is the property that makes them worth having: a
reader who sees a box in one and not the other has found a defect rather than a
rendering choice.

**NOTHING HERE IMPORTS `qmcp`.** It cannot -- the two repositories do not depend
on each other -- and that is the seam working rather than an inconvenience. This
reads a document: `topology`, `boxes`, `arrows`, and the `encoding` block that
says which visual channel carries which data axis. A field this does not
recognise is carried through untouched, so the far side can add one without this
side needing a release.

**THE ENCODING IS READ, NOT ASSUMED.** `qmcp.topology_view.ENCODING` is served
alongside the view for exactly this reason. A window that hard-coded "thicker
means stronger" would keep drawing that after the harness changed its mind, and
the picture would be confidently wrong -- which is worse than blank, because
nothing about it looks stale.

WHAT THIS REFUSES TO DO. Draw an unmeasured edge as a thin one. A null weight
means nobody measured that relation; a thin line means somebody measured it and
found it weak. Rendering the first as the second is not a visual shortcut, it is
a claim the data does not make, and it is the single thing both windows are
tested for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Line width in points, for the strength axis. The floor is deliberately
# visible: a measured-but-negligible edge is a finding, and an edge that
# vanished into the background would read as absent.
MIN_WIDTH = 0.8
MAX_WIDTH = 4.5

# The style that carries `measured`. Solid is measured; dashed is not. Dashing
# is used rather than a lighter colour on purpose -- lightness reads as
# less-of-something, which is the very confusion this axis exists to prevent.
MEASURED_STYLE = "solid"
UNMEASURED_STYLE = "dashed"

# `unmeasured` gets its own width, off the strength scale entirely. It is not
# MIN_WIDTH: that is the width of a measured near-zero edge, and the two must
# not collide.
UNMEASURED_WIDTH = 1.6

SHAPES = {
    "input": "ellipse",
    "worker": "box",
    "gate": "diamond",
    "store": "cylinder",
    "output": "ellipse",
}
DEFAULT_SHAPE = "box"

COLOURS = {
    "flow": "#6db2ff",
    "feedback": "#5ac8b0",
    "refusal": "#e06c75",
}
DEFAULT_COLOUR = "#9aa0a6"


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
    """A whole view, ready for whatever actually puts pixels down."""

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
           encoding: list[dict[str, Any]] | None = None) -> RenderedTopology:
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
        view.nodes.append({
            "id": str(box.get("id") or ""),
            "label": str(box.get("label") or ""),
            "shape": SHAPES.get(str(box.get("kind") or ""), DEFAULT_SHAPE),
            "kind": str(box.get("kind") or ""),
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
    """The same thing as a `networkx` graph, for this project's plotters.

    Imported inside the function so that reading a payload does not require a
    graph library. A window that could not render should still be able to say
    what it was given.

    **`MultiDiGraph`, AND THE CHOICE IS THE WHOLE POINT.** `DiGraph` keeps one
    edge per ordered pair: a second `a -> b` silently replaces the first. Several
    relations reaching one address is the ordinary case in a real archive --
    three separate readings of one delta, each with its own weight and basis --
    and a plain `DiGraph` drew all three as whichever happened to be last. No
    error, no warning, and a picture that looks complete.
    """
    import networkx as nx

    graph = nx.MultiDiGraph(topology=view.topology, caption=view.caption,
                            status=view.status, unmeasured=view.unmeasured)
    for node in view.nodes:
        graph.add_node(node["id"], **node)
    for edge in view.edges:
        graph.add_edge(edge.source, edge.target, label=edge.label,
                       width=edge.width, style=edge.style, color=edge.colour,
                       measured=edge.measured, weight=edge.weight,
                       title=edge.title)
    return graph


def _axes(encoding: list[dict[str, Any]] | None) -> dict[str, str]:
    """Channel to axis, as the harness declared it."""
    if not encoding:
        return {"line_weight": "strength", "line_style": "measured",
                "line_colour": "relation_kind", "node_shape": "box_kind"}
    return {str(c.get("channel")): str(c.get("axis")) for c in encoding}


def _clamp(value: float) -> float:
    return 0.0 if value < 0 else 1.0 if value > 1 else value
