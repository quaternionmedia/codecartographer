"""The harness's interactions as a graph this project already knows how to draw.

Every node is something a row of the harness names, and every edge is a field
of a row. `interaction_service.gather` reads the rows; this module turns them
into nodes and edges and hands them to the serializer every other graph here
goes through.

    name | nobody   --instructed-->   instruction
    instruction     --way in-->       the instruction's source
    source          --recorded by-->  harness        one edge per source, counted
    instruction     --for-->          project
    instruction     --turn-->         chat  --in session-->  session
    instruction     --asked-->        question       the consent an act on it raised
    name | nobody   --asked-->        question       its issuer
    question        --answered-->     name | nobody
    question        --for-->          project        when no drawn instruction raised it
    question        --recorded by-->  harness        when no drawn instruction raised it
    nobody          --ran-->          tool           counted
    tool            --recorded by-->  harness        counted

So a protocol turn reads as a path: the client, the instruction, the consent
question, and whoever answered it.

A name is what a row says, unchecked, and a name node keeps the field it was
read from: the same text under two fields is two nodes, because nothing says
they are one. A row that names nobody is joined to the one `nobody named`
node by a dashed edge. Rows that share both ends and a kind are one edge,
with their count on its hover and a width from that count.

A question is joined to its instruction by the instruction's
`consent_request_id` or the question's `context.instruction_id`. The
`recorded by` edges are the one thing here no single field states: every row
read is the one harness's, and each record that reaches it no other way is
joined to it so the picture is one piece.

What this cannot do: draw a machine, an address or an account, because no
field read holds one; say whether a name is a person's or a program's; or
draw time. Instructions and questions are drawn newest first up to `DRAWN`
each, and the rest are counted in the metadata.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any

from codecarto.services import interaction_service
from codecarto.services.interaction_service import Rows

DRAWN = 150
"""Instructions drawn as nodes, newest first, and questions likewise."""

LABEL = 48
"""Characters of an instruction's text or a question's prompt in a label."""

MIN_WIDTH = 1.0
MAX_WIDTH = 5.0
"""Line width for an edge of one row, and for the edge of the most rows."""

NAMED_STYLE = "solid"
UNNAMED_STYLE = "dashed"

# What each node is. The palette decides what a kind looks like;
# `palette_service.vocabulary` carries that onto the node.
NAME, NOBODY, WAY, INSTRUCTION, QUESTION = "name", "nobody named", "way in", "instruction", "question"
TOOL, PROJECT, HARNESS, SESSION, CHAT = "tool", "project", "harness", "session", "chat"

# A node's `kind` -> the node `type` the palette names, the join
# `topology_service.KIND_TO_TYPE` makes. The path a turn takes alternates
# three looks: who, the instruction, the question, who.
KIND_TO_TYPE = {
    NAME: "Input", NOBODY: "Input",
    INSTRUCTION: "Worker", TOOL: "Worker",
    QUESTION: "Gate",
    WAY: "Output", SESSION: "Output", CHAT: "Output",
    HARNESS: "Store", PROJECT: "Store",
}

NOBODY_ID = "nobody"
HARNESS_ID = "harness"

CAVEAT = ("Every node is something a row of the harness names and every edge "
          "is a field of a row, except `recorded by`, which joins a record to "
          "the one harness all of them were read from. A name is what a row "
          "says, unchecked, beside the field it came from. A dashed line is a "
          "row that names nobody. No node is a machine, an address or an "
          "account: no field read holds one")


@dataclass
class Picture:
    """Nodes and edges, before a graph library or a layout sees them."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)
    not_drawn: dict[str, int] = field(default_factory=dict)
    """Rows read and not drawn as nodes, by what they are."""

    def node(self, node_id: str, kind: str, label: str, hover: str, **more: Any) -> str:
        """Add a node once; a second mention of the same thing changes nothing."""
        self.nodes.setdefault(node_id, {"label": label, "kind": kind,
                                        "hover": hover, **more})
        return node_id

    def edge(self, source: str, target: str, kind: str, hover: str = "") -> None:
        """Add one row to the edge between two nodes, or start that edge."""
        held = self.edges.setdefault((source, target, kind), {
            "kind": kind, "count": 0, "hover": hover,
            "named": NOBODY_ID not in (source, target)})
        held["count"] += 1


def _short(value: Any, limit: int = LABEL) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _name(picture: Picture, who: str | None, who_from: str | None) -> str:
    """The node for whoever a row names, or the one node for nobody."""
    if not who:
        return picture.node(NOBODY_ID, NOBODY, NOBODY,
                            "rows of the harness that carry no name")
    return picture.node(f"name:{who_from}:{who}", NAME, who,
                        f"{who} -- as `{who_from}` gives it, unchecked",
                        who_from=who_from)


def _harness(picture: Picture, rows: Rows) -> str:
    stated = interaction_service.instance(rows.health)
    port = stated.get("port")
    label = f"harness :{port}" if stated["identified"] else "harness"
    said = ", ".join(f"{name} {stated[name]}" for name in interaction_service.INSTANCE_FIELDS
                     if stated.get(name) not in (None, ""))
    hover = (f"{stated['where']} -- {said}" if stated["identified"]
             else f"{stated['where']} -- {stated['problem']}")
    return picture.node(HARNESS_ID, HARNESS, label, hover)


def _raised_by(ask: dict[str, Any], consents: dict[str, str]) -> str | None:
    """The id of the instruction a question is the consent for, or None."""
    context = ask.get("context") if isinstance(ask.get("context"), dict) else {}
    stated = context.get("instruction_id")
    return str(stated) if stated else consents.get(str(ask.get("id")))


def picture(rows: Rows, drawn: int = DRAWN) -> Picture:
    """The rows as nodes and edges. Reads nothing and lays out nothing."""
    made = Picture()
    harness = _harness(made, rows)

    instructions: dict[str, str] = {}
    consents: dict[str, str] = {}
    for row in rows.instructions:
        seen = interaction_service.instructed(row)
        if row.get("consent_request_id"):
            consents[str(row["consent_request_id"])] = str(row.get("id"))
        if seen["way"]:
            way = made.node(f"way:{seen['way']}", WAY, seen["way"],
                            f"instructions whose source is {seen['way']}")
            made.edge(way, harness, "recorded by")
        if len(instructions) >= drawn:
            continue
        node = made.node(
            f"instruction:{row.get('id')}", INSTRUCTION, _short(seen["what"]),
            f"instruction {row.get('id')}: {seen['what']} -- {row.get('status')}",
            status=row.get("status"), at=seen["at"])
        instructions[str(row.get("id"))] = node
        made.edge(_name(made, seen["who"], seen["who_from"]), node, "instructed")
        if seen["way"]:
            made.edge(node, f"way:{seen['way']}", "way in")
        if seen["project"]:
            made.edge(node, made.node(f"project:{seen['project']}", PROJECT,
                                      str(seen["project"]), f"project {seen['project']}"),
                      "for")
        session = (made.node(f"session:{seen['session']}", SESSION, str(seen["session"]),
                             f"protocol session {seen['session']}")
                   if seen["session"] else None)
        if seen["chat"]:
            chat = made.node(f"chat:{seen['chat']}", CHAT, str(seen["chat"]),
                             f"protocol chat {seen['chat']}")
            made.edge(node, chat, "turn", f"turn {seen['turn']}" if seen["turn"] else "")
            if session:
                made.edge(chat, session, "in session")
        elif session:
            made.edge(node, session, "turn", f"turn {seen['turn']}" if seen["turn"] else "")
    made.not_drawn["instructions"] = len(rows.instructions) - len(instructions)

    questions = 0
    for row in rows.asks:
        if questions >= drawn:
            break
        questions += 1
        seen = interaction_service.asked(row)
        node = made.node(
            f"question:{row.get('id')}", QUESTION, _short(seen["what"]),
            f"question {row.get('id')}: {seen['what']} -- {row.get('status')}",
            status=row.get("status"), at=seen["at"])
        raised = _raised_by(row, consents)
        origin = instructions.get(raised) if raised else None
        if origin:
            made.edge(origin, node, "asked")
        else:
            made.edge(node, harness, "recorded by")
            if seen["project"]:
                made.edge(node, made.node(f"project:{seen['project']}", PROJECT,
                                          str(seen["project"]), f"project {seen['project']}"),
                          "for")
        # Who issued it, when the row says. A question an act raised names
        # nobody and is not drawn as asked by nobody: its instruction asked.
        if seen["who"] or not raised:
            made.edge(_name(made, seen["who"], seen["who_from"]), node, "asked")
        response = rows.responses.get(str(row.get("id")))
        if response is not None:
            answer = interaction_service.answered(row, response)
            made.edge(node, _name(made, answer["who"], answer["who_from"]), "answered",
                      f"answered {answer['what']}")
    made.not_drawn["questions"] = len(rows.asks) - questions

    for row in rows.runs:
        seen = interaction_service.ran(row)
        tool = made.node(f"tool:{seen['what']}", TOOL, str(seen["what"]),
                         f"tool {seen['what']}")
        made.edge(_name(made, None, None), tool, "ran")
        made.edge(tool, harness, "recorded by")
    return made


def _width(count: int, most: int) -> float:
    if most <= 1:
        return MIN_WIDTH
    return MIN_WIDTH + (MAX_WIDTH - MIN_WIDTH) * (count - 1) / (most - 1)


def as_graph(made: Picture, source: str = ""):
    """The picture as a `networkx` graph this project's serializer accepts.

    Imported inside the function so that reading the rows does not require a
    graph library, the choice `topology_service.as_graph` makes.
    """
    import networkx as nx

    from codecarto.services import palette_service

    graph = nx.MultiDiGraph(kind="interactions", source=source)
    for node_id, node in made.nodes.items():
        graph.add_node(
            node_id, **node,
            **palette_service.vocabulary(KIND_TO_TYPE.get(node["kind"], "Worker")),
            click=f"<p>{html.escape(str(node['hover']))}</p>")
    most = max((edge["count"] for edge in made.edges.values()), default=1)
    for (source_id, target_id, kind), edge in made.edges.items():
        count = edge["count"]
        # The label is the kind alone, so the canvas's key has one row per
        # kind; the count is on the hover, in `count` and in the width.
        counted = kind if count == 1 else f"{kind} ×{count}"
        said = edge["hover"] if count == 1 and edge["hover"] else counted
        graph.add_edge(
            source_id, target_id, key=kind, label=kind, kind=kind,
            # `count`, never `weight`: a layout reads `weight` as a distance.
            count=count, size=_width(count, most),
            style=NAMED_STYLE if edge["named"] else UNNAMED_STYLE,
            named=edge["named"], hover=said, title=said)
    return graph


def caveat(rows: Rows, made: Picture) -> str:
    """The sentence a reader needs before believing the shape."""
    parts = [CAVEAT]
    held = [f"{count} older {what}" for what, count in made.not_drawn.items() if count]
    if held:
        parts.append(f"Not drawn as nodes: {', '.join(held)}")
    unread = rows.answers.get("unread", 0)
    if unread:
        parts.append(f"{unread} answered question(s) are drawn with no answer, "
                     f"because an answer is one read each and at most "
                     f"{rows.answers.get('limit')} are read")
    for missing in rows.unread_lists:
        parts.append(f"The {missing['what']} were not read: {missing['problem']}")
    if rows.full:
        parts.append("A list came back as long as was asked for, so the harness "
                     "may hold rows that are not here")
    return ". ".join(parts) + "."


def metadata(rows: Rows, made: Picture, options: Any = None) -> dict[str, Any]:
    """Graph-level facts the canvas and any other client both read."""
    found = rows.interactions()
    return {
        "kind": "interactions",
        "source": rows.health.where,
        "layout": getattr(options, "layout", "Kamada Kawai"),
        "type": getattr(options, "type", None),
        "palette_id": getattr(options, "palette_id", "0"),
        "instance": interaction_service.instance(rows.health),
        "rows": len(found),
        "unnamed": sum(1 for row in found if not row["who"]),
        "not_drawn": dict(made.not_drawn),
        "answers": dict(rows.answers),
        "may_hold_more": rows.full,
        "caveat": caveat(rows, made),
    }


def as_gjgf(made: Picture, options: Any = None, source: str = "") -> dict[str, Any]:
    """The picture in this project's graph format, laid out by its layouts."""
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    chosen = options or PlotOptions(layout="Kamada Kawai")
    return GraphSerializer.serialize_to_gjgf(as_graph(made, source), chosen)
