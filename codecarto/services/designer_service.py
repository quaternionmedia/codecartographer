"""What the harness declares about each shape of collaboration, for the Designer panel.

Two documents are read over HTTP through `qmcp_client`, each as given: the
plane, which declares every shape with its status, what it spends, writes and
decides, why, and what it needs; and the harness's account of what could run
with what it has. `join` sets them side by side by shape name and computes
nothing else. Whether a shape could run is the second document's to say.

    shape  --needs-->  need

`picture` draws that one relation: a node for each shape and for each need a
shape states, and an edge between them, dashed when the harness reports that
need unmet for that shape. A need several shapes state is one node. A shape's
`kind` is its status as the plane writes it, so the canvas's key names it.

The vocabulary is the harness's. A status or a need key is carried as written;
this module holds no list of either, and gives a status its look from its
place in the list the plane states.

The plane is required: without it the answer is one problem. The second
document is not: a harness that serves the plane and not what could run shows
every shape, with the reason nothing says which could run.

This module reads. It posts nothing to the harness, stores nothing and starts
no process; `tests/test_boundaries.py` holds it to that.

What it cannot do: say whether a declaration is true. Every field of the plane
is a claim by whoever wrote the entry, and the plane's own `reading` says so;
it is carried verbatim. An option is listed under its shape and is not drawn.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any

from codecarto.services import interaction_service, qmcp_client
from codecarto.services.qmcp_client import Reach

PLANE = "/v1/orchestration/plane"
RUNNABLE = "/v1/orchestration/runnable"

SCHEMA = 1
"""The schema of both documents this module reads."""

NO_ROUTE = ("this build of the harness predates the orchestration plane; "
            "start a newer one")

LAYOUT = "Reading Order"
"""The layout the graph is drawn in unless another is asked for: each node one
column right of what points at it, so shapes stand in one column and needs in
the next."""

NEED = "need"
"""The `kind` of a need's node. A shape's is its status."""

NEEDS, UNMET = "needs", "needs, unmet"
"""The two kinds of edge."""

NO_STATUS = "no status stated"

MARKS = ("spends", "writes", "decides")
"""The three marks the plane states for a shape, each true or false."""

# A node's look is the palette's, named by type. A need is a gate a shape
# passes; a status takes the look at its place in the plane's `statuses`, and
# one the plane does not list takes the last.
NEED_TYPE = "Gate"
STATUS_TYPES = ("Worker", "Input", "Output", "Store")
UNLISTED_TYPE = "Store"

MET_COLOUR, UNMET_COLOUR = "#6b7480", "#e0c069"
MET_STYLE, UNMET_STYLE = "solid", "dashed"

CAVEAT = ("Each shape is joined to each need the harness's plane states for "
          "it. A dashed line is a need the harness reports unmet for that "
          "shape with what it has; a solid line is one it does not report "
          "unmet. A need several shapes share is one node. Every field is a "
          "declaration, read and not checked here. A shape's options are "
          "listed in the Designer panel and are not drawn")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [row for row in value or [] if isinstance(row, dict)] if isinstance(value, list) else []


def _problem(kind: str, problem: str, remedy: str, where: str) -> dict[str, Any]:
    return {kind: True, "problem": problem, "remedy": remedy, "where": where}


def absent(reach: Reach) -> dict[str, Any]:
    """A read that failed, as the envelope every estate route answers in.

    Nothing answering is `unreachable`. Anything that answered and did not
    give the document is `unreadable`.
    """
    kind = "unreachable" if reach.status is None and "not JSON" not in reach.problem else "unreadable"
    return _problem(kind, reach.problem, reach.remedy, reach.where)


def unread(reach: Reach, what: str) -> str:
    """Why a document that came back is not one this module reads, or ""."""
    document = reach.document
    if not isinstance(document, dict):
        return f"the harness's {what} is not a document"
    if document.get("schema") != SCHEMA:
        return (f"the harness's {what} states schema {document.get('schema')!r}, "
                f"and this window reads schema {SCHEMA}")
    return ""


def join(plane: dict[str, Any], runnable: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Every shape, with what each document says of it, in the plane's order.

    `declared` is the plane's entry and `could_run` the other document's, each
    as given, or None when that document does not name the shape; `missing`
    then says which. A shape only the second document names, or only an option
    names, follows the declared ones. `runnable` is None when it was not read,
    and nothing is then said to be missing from it.
    """
    rows: dict[str, dict[str, Any]] = {}

    def row(name: str) -> dict[str, Any]:
        return rows.setdefault(name, {"name": name, "declared": None, "could_run": None,
                                      "options": [], "missing": ""})

    for entry in _dicts(plane.get("capabilities")):
        if entry.get("topology"):
            row(str(entry["topology"]))["declared"] = entry
    for option in _dicts(plane.get("options")):
        varied = _dict(option.get("capability"))
        if varied.get("topology"):
            row(str(varied["topology"]))["options"].append({
                "setting": option.get("setting"), "value": option.get("value"),
                "declared": varied})
    for entry in _dicts(_dict(runnable).get("shapes")):
        if entry.get("topology"):
            row(str(entry["topology"]))["could_run"] = entry

    for found in rows.values():
        if found["declared"] is None:
            found["missing"] = "the plane declares no shape of this name"
        elif runnable is not None and found["could_run"] is None:
            found["missing"] = "the harness's account of what could run does not name this shape"
    return list(rows.values())


def read(base: str | None = None) -> dict[str, Any]:
    """Everything the panel shows, or the one problem when the plane was not read."""
    plane = qmcp_client.fetch(PLANE, base, remedy_404=NO_ROUTE)
    if not plane.ok:
        return absent(plane)
    why = unread(plane, "plane")
    if not why and not isinstance(plane.document.get("capabilities"), list):
        why = "the harness's plane carries no list of `capabilities`"
    if why:
        return _problem("unreadable", why, "", plane.where)

    runnable = qmcp_client.fetch(RUNNABLE, base, remedy_404=NO_ROUTE)
    could = {"read": True, "problem": "", "remedy": "", "where": runnable.where}
    if not runnable.ok:
        could.update(read=False, problem=runnable.problem, remedy=runnable.remedy)
    elif unread(runnable, "account of what could run"):
        could.update(read=False, problem=unread(runnable, "account of what could run"))
    told = _dict(runnable.document) if could["read"] else None

    document = plane.document
    return {
        "instance": interaction_service.instance(qmcp_client.health(base)),
        "where": plane.where,
        "shapes": join(document, told),
        "could_run": could,
        "have": _dict(told.get("have")) if told is not None else None,
        "never_supplied": told.get("never_supplied") if told is not None else None,
        "statuses": document.get("statuses") or [],
        "needs": document.get("needs") or [],
        "attested": document.get("attested") or [],
        "drift": _dict(document.get("drift")),
        "reading": _dict(document.get("reading")),
    }


@dataclass
class Picture:
    """Nodes and edges, before a graph library or a layout sees them."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)


def _status(row: dict[str, Any]) -> str:
    """A shape's status as either document writes it; the plane's first."""
    for entry in (row["declared"], row["could_run"]):
        if entry and entry.get("status"):
            return str(entry["status"])
    return NO_STATUS


def _said(row: dict[str, Any]) -> str:
    """What a shape's node says on hover: its status, its marks, and why."""
    declared = _dict(row["declared"])
    parts = [f"{row['name']} -- {_status(row)}"]
    marks = [mark for mark in MARKS if declared.get(mark) is True]
    if marks:
        parts.append(", ".join(marks))
    could = row["could_run"]
    if could is not None:
        parts.append("could run now" if could.get("runnable") is True else "could not run now")
    if declared.get("why"):
        parts.append(str(declared["why"]))
    if row["missing"]:
        parts.append(row["missing"])
    return " -- ".join(parts)


def picture(document: dict[str, Any]) -> Picture:
    """The reading as nodes and edges. Reads nothing and lays out nothing."""
    made = Picture()
    never = _dict(document.get("never_supplied"))
    for row in document.get("shapes") or []:
        shape = f"shape:{row['name']}"
        made.nodes[shape] = {"label": row["name"], "kind": _status(row),
                             "hover": _said(row), "label_at": "left"}
        unmet = {str(need.get("key")): need
                 for need in _dicts(_dict(row["could_run"]).get("unmet")) if need.get("key")}
        stated = {str(need.get("key")): need
                  for need in _dicts(_dict(row["declared"]).get("needs")) if need.get("key")}
        for key in list(stated) + [key for key in unmet if key not in stated]:
            need = f"need:{key}"
            hover = f"need: {key}"
            if never.get("key") == key and never.get("because"):
                hover += f" -- {never['because']}"
            made.nodes.setdefault(need, {"label": key, "kind": NEED, "hover": hover,
                                         "label_at": "right"})
            told = unmet.get(key) or stated[key]
            made.edges[(shape, need)] = {
                "kind": UNMET if key in unmet else NEEDS,
                "hover": " -- ".join(str(told[part]) for part in ("because", "supplied_by")
                                     if told.get(part)) or key}
    return made


def as_graph(made: Picture, statuses: list[Any] | None = None, source: str = ""):
    """The picture as a `networkx` graph this project's serializer accepts.

    Imported inside the function so that reading the harness does not require
    a graph library, the choice `topology_service.as_graph` makes.
    """
    import networkx as nx

    from codecarto.services import palette_service

    listed = [str(status) for status in statuses or []]

    def look(kind: str) -> str:
        if kind == NEED:
            return NEED_TYPE
        if kind in listed:
            return STATUS_TYPES[listed.index(kind) % len(STATUS_TYPES)]
        return UNLISTED_TYPE

    graph = nx.MultiDiGraph(kind="designer", source=source)
    for node_id, node in made.nodes.items():
        graph.add_node(node_id, **node, **palette_service.vocabulary(look(node["kind"])),
                       click=f"<p>{html.escape(str(node['hover']))}</p>")
    for (source_id, target_id), edge in made.edges.items():
        unmet = edge["kind"] == UNMET
        graph.add_edge(
            source_id, target_id, key=edge["kind"], label=edge["kind"], kind=edge["kind"],
            color=UNMET_COLOUR if unmet else MET_COLOUR,
            style=UNMET_STYLE if unmet else MET_STYLE,
            hover=edge["hover"], title=edge["hover"])
    return graph


def caveat(document: dict[str, Any]) -> str:
    """The sentence a reader needs before believing the shape."""
    parts = [CAVEAT]
    could = _dict(document.get("could_run"))
    if not could.get("read"):
        parts.append("What could run was not read, so no line is dashed: "
                     f"{could.get('problem')}")
    parts.extend(str(said) for said in _dict(document.get("reading")).values() if said)
    return ". ".join(part.rstrip(".") for part in parts) + "."


def metadata(document: dict[str, Any], made: Picture, options: Any = None) -> dict[str, Any]:
    """Graph-level facts the canvas and any other client both read."""
    return {
        "kind": "designer",
        "source": document.get("where", ""),
        "layout": getattr(options, "layout", LAYOUT),
        "type": getattr(options, "type", None),
        "palette_id": getattr(options, "palette_id", "0"),
        # Every node's name is what this graph is for: the canvas draws them
        # without the reader turning names on.
        "names": True,
        "instance": document.get("instance"),
        "shapes": sum(1 for node in made.nodes.values() if node["kind"] != NEED),
        "needs": sum(1 for node in made.nodes.values() if node["kind"] == NEED),
        "unmet": sum(1 for edge in made.edges.values() if edge["kind"] == UNMET),
        "caveat": caveat(document),
    }


def as_gjgf(document: dict[str, Any], made: Picture, options: Any = None) -> dict[str, Any]:
    """The picture in this project's graph format, laid out by its layouts."""
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    chosen = options or PlotOptions(layout=LAYOUT)
    graph = as_graph(made, document.get("statuses"), str(document.get("where", "")))
    return GraphSerializer.serialize_to_gjgf(graph, chosen)
