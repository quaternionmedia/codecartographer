"""Composing a design of collaboration in the window, and saving it to the harness.

A design is the harness's: a name, a kind, a description and a configuration
the harness validates through that kind's own class. Its configuration may
name reusable components (`components`) and other saved designs it is
composed of (`compose`). This module reads what the harness holds, relays one
design a person composed to `POST /v1/topologies`, and returns the row the
harness made, with the address and the verdict the harness gave it, or the
harness's refusal with each message beside the field it is about. It checks
nothing the harness checks and never sends twice.

    design | draft  --uses-->      component
    design | draft  --composes-->  design

`picture` draws those two relations for every saved design and for the draft
being composed, so each reference a person adds is a line on the canvas
before anything is saved. A reference to something the harness does not hold
is drawn dashed, to a node that says so.

Saving is a write, so `instruct_service.standing` decides whether a request
may be relayed at all, by the rule an instruction is relayed under: only for
a person at the machine the harness runs on.

This module stores nothing and starts no process; `tests/test_boundaries.py`
holds it to that.

What it cannot do: change or delete a saved design, save a component, or run
a design. The harness serves no deletion, and running a design is not this
window's.
"""

from __future__ import annotations

import html
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from codecarto.services import qmcp_client
from codecarto.services.qmcp_client import Reach

DESIGNS = "/v1/topologies"
COMPONENTS = "/v1/topology-components"
SCHEMA = "/v1/topology/schema/"

ROUTE = "/designer/designs"

NO_ROUTE = ("this build of the harness does not serve saved designs, or it is "
            "bound to an address other than this machine's own")

LAYOUT = "Reading Order"

DRAFT, DESIGN, COMPONENT, ABSENT = "draft", "design", "component", "not held"
"""What a node is: the design being composed, a saved one, a saved component,
and a reference to something the harness does not hold."""

USES, COMPOSES = "uses", "composes"

KIND_TO_TYPE = {DRAFT: "Input", DESIGN: "Worker", COMPONENT: "Store", ABSENT: "Output"}

HELD_STYLE, ABSENT_STYLE = "solid", "dashed"
COLOURS = {USES: "#5ac8b0", COMPOSES: "#6db2ff"}

CAVEAT = ("Every line is a reference a design's configuration states: `uses` "
          "to a component, `composes` to another design. A dashed line is a "
          "reference to something the harness does not hold in this project. "
          "The draft is what is being composed in this window and is not "
          "saved until the harness says so. A design with no reference stands "
          "alone")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _query(project: str | None) -> str:
    stated = (project or "").strip()
    return f"?project={urllib.parse.quote(stated, safe='')}" if stated else ""


def _absent(reach: Reach) -> dict[str, Any]:
    kind = "unreachable" if reach.status is None and "not JSON" not in reach.problem else "unreadable"
    return {kind: True, "problem": reach.problem, "remedy": reach.remedy, "where": reach.where}


def availability(why: str) -> dict[str, Any]:
    """Whether the window saves a design for this request, as a document."""
    if not why:
        return {"available": True, "problem": "", "remedy": ""}
    return {"available": False,
            "problem": f"a design is not saved from here: {why}",
            "remedy": "open this window on the machine the harness runs on"}


def read(project: str | None, why: str, base: str | None = None) -> dict[str, Any]:
    """The saved designs and components of one project, and whether one is saved here.

    The designs are required: without them the answer is one problem. The
    components are not; a harness that lists designs and not components shows
    the designs, with the reason no component is offered.
    """
    designs = qmcp_client.fetch(DESIGNS + _query(project), base, remedy_404=NO_ROUTE)
    if not designs.ok:
        return _absent(designs)
    document = designs.document
    if not isinstance(document, dict) or not isinstance(document.get("topologies"), list):
        return {"unreadable": True, "where": designs.where, "remedy": "",
                "problem": "the harness's answer carries no list of `topologies`"}
    components = qmcp_client.fetch(COMPONENTS + _query(project), base, remedy_404=NO_ROUTE)
    held = {"read": components.ok, "problem": components.problem,
            "remedy": components.remedy, "where": components.where}
    return {
        "project": document.get("project"),
        "designs": _dicts(document.get("topologies")),
        "components": _dicts(_dict(components.document).get("components")) if components.ok else [],
        "components_read": held,
        "saving": availability(why),
        "where": designs.where,
    }


def schema(kind: str, base: str | None = None) -> dict[str, Any]:
    """The harness's schema of one kind's configuration, as given."""
    reach = qmcp_client.fetch(SCHEMA + urllib.parse.quote(kind, safe=""), base,
                              remedy_404="the harness has no configuration for this kind")
    if not reach.ok:
        return _absent(reach)
    if not isinstance(_dict(reach.document).get("json_schema"), dict):
        return {"unreadable": True, "where": reach.where, "remedy": "",
                "problem": "the harness's answer carries no `json_schema`"}
    return {**reach.document, "where": reach.where}


def errors(detail: Any) -> list[dict[str, str]]:
    """The harness's refusal as messages, each with the field it is about.

    The harness answers a design it will not save with a sentence, or with a
    list of errors each naming a location. `field` is that location joined by
    dots, or empty when the refusal is about the design as a whole.
    """
    if isinstance(detail, dict) and isinstance(detail.get("errors"), list):
        found = []
        for error in _dicts(detail["errors"]):
            where = [str(part) for part in error.get("loc") or []]
            if detail.get("where") == "config":
                where = ["config", *where]
            found.append({"field": ".".join(where), "message": str(error.get("msg", ""))})
        return found
    said = detail if isinstance(detail, str) else ("" if detail is None else str(detail))
    return [{"field": "", "message": said}] if said else []


def save(body: dict[str, Any], why: str, base: str | None = None) -> dict[str, Any]:
    """Send one design, and return the harness's row or why there is none.

    `why` is `instruct_service.standing`'s answer for the request being
    served. A design with no name or no kind is not sent: the sentence here
    says what to fill in. Every other judgement is the harness's.
    """
    if why:
        stood = availability(why)
        return {"refused": True, "problem": stood["problem"], "remedy": stood["remedy"],
                "where": ROUTE, "errors": []}
    name = str(body.get("name") or "").strip()
    kind = str(body.get("topology_type") or "").strip()
    missing = [{"field": field, "message": said}
               for field, value, said in (("name", name, "a design needs a name"),
                                          ("topology_type", kind, "a design needs a kind"))
               if not value]
    if missing:
        return {"refused": True, "problem": "the design was not sent",
                "remedy": "fill in what is marked", "where": ROUTE, "errors": missing}
    payload: dict[str, Any] = {"name": name, "topology_type": kind,
                               "config": _dict(body.get("config"))}
    for optional in ("description", "project"):
        stated = str(body.get(optional) or "").strip()
        if stated:
            payload[optional] = stated
    reach = qmcp_client.send(DESIGNS, payload, base, remedy_404=NO_ROUTE)
    if reach.ok:
        return {"saved": True, "design": reach.document, "where": reach.where}
    if reach.status is None:
        return {"unreachable": True, "problem": reach.problem, "remedy": reach.remedy,
                "where": reach.where, "errors": []}
    told = errors(reach.detail)
    return {"refused": True, "status": reach.status,
            "problem": f"the harness did not save the design ({reach.status})",
            "remedy": reach.remedy, "where": reach.where,
            "errors": told or [{"field": "", "message": reach.problem}]}


@dataclass
class Picture:
    """Nodes and edges, before a graph library or a layout sees them."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)


def _names(value: Any) -> list[str]:
    """The names a list of references states: a string, or a mapping's `name`."""
    found = []
    for entry in value if isinstance(value, list) else []:
        name = entry.get("name") if isinstance(entry, dict) else entry
        if isinstance(name, str) and name.strip():
            found.append(name.strip())
    return found


def picture(document: dict[str, Any], draft: dict[str, Any] | None = None) -> Picture:
    """The saved designs, the draft and what each references, as nodes and edges."""
    made = Picture()
    designs = {str(row.get("name")): row for row in document.get("designs") or [] if row.get("name")}
    components = {str(row.get("name")): row for row in document.get("components") or []
                  if row.get("name")}

    def component(name: str) -> tuple[str, bool]:
        held = name in components
        node = f"component:{name}"
        said = (str(components[name].get("description") or name) if held
                else f"{name} -- the harness holds no component of this name")
        made.nodes.setdefault(node, {"label": name, "kind": COMPONENT if held else ABSENT,
                                     "hover": f"component {said}" if held else said,
                                     "label_at": "right"})
        return node, held

    def design(name: str) -> tuple[str, bool]:
        held = name in designs
        node = f"design:{name}"
        if node not in made.nodes:
            row = designs.get(name, {})
            said = (f"design {name} -- {row.get('topology_type')}" if held
                    else f"{name} -- the harness holds no design of this name in this project")
            made.nodes[node] = {"label": name, "kind": DESIGN if held else ABSENT,
                                "hover": said, "label_at": "left" if held else "right"}
        return node, held

    def joined(source: str, config: Any) -> None:
        stated = _dict(config)
        for name in _names(stated.get("components")):
            target, held = component(name)
            made.edges[(source, target, USES)] = {"kind": USES, "held": held}
        for name in _names(stated.get("compose")):
            target, held = design(name)
            made.edges[(source, target, COMPOSES)] = {"kind": COMPOSES, "held": held}

    for name, row in designs.items():
        joined(design(name)[0], row.get("config"))
    if draft is not None:
        name = str(draft.get("name") or "").strip() or "unnamed draft"
        kind = str(draft.get("topology_type") or "").strip()
        made.nodes["draft"] = {"label": name, "kind": DRAFT, "label_at": "left",
                               "hover": f"draft {name}" + (f" -- {kind}" if kind else "")
                                        + " -- not saved"}
        joined("draft", draft.get("config"))
    return made


def as_graph(made: Picture, source: str = ""):
    """The picture as a `networkx` graph this project's serializer accepts."""
    import networkx as nx

    from codecarto.services import palette_service

    graph = nx.MultiDiGraph(kind="composition", source=source)
    for node_id, node in made.nodes.items():
        graph.add_node(node_id, **node,
                       **palette_service.vocabulary(KIND_TO_TYPE[node["kind"]]),
                       click=f"<p>{html.escape(str(node['hover']))}</p>")
    for (source_id, target_id, kind), edge in made.edges.items():
        graph.add_edge(source_id, target_id, key=kind, label=kind, kind=kind,
                       color=COLOURS[kind],
                       style=HELD_STYLE if edge["held"] else ABSENT_STYLE,
                       hover=kind, title=kind)
    return graph


def metadata(document: dict[str, Any], made: Picture, options: Any = None) -> dict[str, Any]:
    """Graph-level facts the canvas and any other client both read."""
    kinds = [node["kind"] for node in made.nodes.values()]
    return {
        "kind": "composition",
        "source": document.get("where", ""),
        "layout": getattr(options, "layout", LAYOUT),
        "type": getattr(options, "type", None),
        "palette_id": getattr(options, "palette_id", "0"),
        "names": True,
        "project": document.get("project"),
        "designs": kinds.count(DESIGN),
        "components": kinds.count(COMPONENT),
        "draft": DRAFT in kinds,
        "not_held": kinds.count(ABSENT),
        "caveat": CAVEAT + ".",
    }


def as_gjgf(made: Picture, options: Any = None, source: str = "") -> dict[str, Any]:
    """The picture in this project's graph format, laid out by its layouts."""
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    chosen = options or PlotOptions(layout=LAYOUT)
    return GraphSerializer.serialize_to_gjgf(as_graph(made, source), chosen)
