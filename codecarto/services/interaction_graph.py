"""The harness's interactions as a graph this project already knows how to draw.

Every node is something a row of the harness names, and every edge is a field
of a row. `interaction_service.gather` reads the rows; this module turns them
into nodes and edges and hands them to the serializer every other graph here
goes through.

    name | nobody   --instructed-->   instruction
    instruction     --asked-->        question       the consent an act on it raised
    name | nobody   --asked-->        question       its issuer
    question        --answered-->     name | nobody
    instruction     --way in-->       the instruction's source
    instruction     --for-->          project
    instruction     --turn-->         chat  --in session-->  session
    question        --for-->          project        when no drawn instruction raised it
    nobody          --ran-->          tool           counted
    source | tool   --recorded by-->  harness        counted

The first four are the reading: who, what they asked for, the question it
raised, who answered. Each node says which column of that reading it stands
in (`column`) and on which side its name goes (`label_at`), and
`reading_order.place` lays them out left to right from those. The rest say how
an instruction came in and what it was for, and stand above and below the
reading. So a protocol turn reads as a straight path: the client, the
instruction, the consent question, and whoever answered it.

A name is what a row says, unchecked, and a name node keeps the field it was
read from: the same text under two fields is two nodes, because nothing says
they are one. A row that names nobody is joined to a `nobody named` node by a
dashed edge: one at the start of the reading for whoever instructed, asked or
ran, one at its end for whoever answered. Rows that share both ends and a kind
are one edge, with their count on its hover and a width from that count.

Instructions that name nobody, raised no question and came in no protocol
session say nothing a reader follows across the picture, so two or more of
them are one node with their count; questions that name nobody on either side
and that no instruction raised likewise. The Interactions panel lists each of
those rows.

A question is joined to its instruction by the instruction's
`consent_request_id` or the question's `context.instruction_id`. `recorded by`
is the one edge no single field states: every row read is the one harness's,
and a source and a tool are joined to it.

What this cannot do: draw a machine, an address or an account, because no
field read holds one; say whether a name is a person's or a program's; or
draw time. Instructions and questions are read newest first up to `DRAWN`
each, and the rest are counted in the metadata.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any

from codecarto.services import interaction_service
from codecarto.services.interaction_service import Rows
from codecarto.services.reading_order import (ANSWERER, BENEATH, HEAD, INSTRUCTION_COLUMN,
                                              OVER, QUESTION_COLUMN, UNDER, WHO)

DRAWN = 150
"""Instructions drawn, newest first, and questions likewise."""

LABEL = 24
"""Characters of an instruction's text or a question's prompt in a label: what
a column of the reading has room for."""

TOLD = 3
"""Rows a counted node's hover quotes."""

MIN_WIDTH = 1.5
MAX_WIDTH = 5.0
"""Line width for an edge of one row, and for the edge of the most rows."""

LAYOUT = "Reading Order"
"""The layout this graph is drawn in unless another is asked for."""

NAMED_STYLE = "solid"
UNNAMED_STYLE = "dashed"

# What each node is. The palette decides what a kind looks like;
# `palette_service.vocabulary` carries that onto the node.
NAME, NOBODY, WAY, INSTRUCTION, QUESTION = "name", "nobody named", "way in", "instruction", "question"
TOOL, PROJECT, HARNESS, SESSION, CHAT = "tool", "project", "harness", "session", "chat"
INSTRUCTIONS, QUESTIONS = "instructions", "questions"

# A node's `kind` -> the node `type` the palette names, the join
# `topology_service.KIND_TO_TYPE` makes. The path a turn takes alternates
# three looks: who, the instruction, the question, who.
KIND_TO_TYPE = {
    NAME: "Input", NOBODY: "Input",
    INSTRUCTION: "Worker", INSTRUCTIONS: "Worker", TOOL: "Worker",
    QUESTION: "Gate", QUESTIONS: "Gate",
    WAY: "Output", SESSION: "Output", CHAT: "Output",
    HARNESS: "Store", PROJECT: "Store",
}

# Where each kind stands in the reading, and the side its name goes on so no
# edge of the reading runs through it: outward at the two ends, above in the
# middle, and away from the reading above and below it.
PLACED = {
    INSTRUCTION: (INSTRUCTION_COLUMN, "above"), INSTRUCTIONS: (INSTRUCTION_COLUMN, "above"),
    QUESTION: (QUESTION_COLUMN, "above"), QUESTIONS: (QUESTION_COLUMN, "above"),
    HARNESS: (HEAD, "right"), WAY: (OVER, "right"),
    TOOL: (UNDER, "below"), PROJECT: (UNDER, "below"),
    CHAT: (BENEATH, "below"), SESSION: (BENEATH, "below"),
}

# The colour of each edge of the reading, as `topology_service.COLOURS` gives
# a relation its own. Every other edge is the one grey.
COLOURS = {"instructed": "#6db2ff", "asked": "#e0c069", "answered": "#5ac8b0"}
OTHER_COLOUR = "#6b7480"

NOBODY_ID = "nobody"
NOBODY_ANSWERED_ID = "nobody:answered"
HARNESS_ID = "harness"
INSTRUCTIONS_ID = "instructions:unnamed"
QUESTIONS_ID = "questions:unnamed"

CAVEAT = ("Read left to right: who, the instruction, the question it raised, "
          "who answered. Every node is something a row of the harness names "
          "and every edge is a field of a row, except `recorded by`, which "
          "joins a source and a tool to the one harness all rows were read "
          "from. A name is what a row says, unchecked, beside the field it "
          "came from. A dashed line is a row that names nobody. Instructions "
          "that name nobody and raised no question are one node with their "
          "count, and so are questions that name nobody and no instruction "
          "raised. No node is a machine, an address or an account: no field "
          "read holds one")


@dataclass
class Picture:
    """Nodes and edges, before a graph library or a layout sees them."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)
    not_drawn: dict[str, int] = field(default_factory=dict)
    """Rows read and not drawn, by what they are."""

    counted: dict[str, int] = field(default_factory=dict)
    """Rows drawn as one counted node, by what they are."""

    def node(self, node_id: str, kind: str, label: str, hover: str, **more: Any) -> str:
        """Add a node once; a second mention of the same thing changes nothing."""
        column, side = more.pop("placed", None) or PLACED[kind]
        self.nodes.setdefault(node_id, {"label": label, "kind": kind, "hover": hover,
                                        "column": column, "label_at": side, **more})
        return node_id

    def edge(self, source: str, target: str, kind: str, hover: str = "") -> None:
        """Add one row to the edge between two nodes, or start that edge."""
        held = self.edges.setdefault((source, target, kind), {
            "kind": kind, "count": 0, "hover": hover,
            "named": not {source, target} & {NOBODY_ID, NOBODY_ANSWERED_ID}})
        held["count"] += 1


def _short(value: Any, limit: int = LABEL) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _name(picture: Picture, who: str | None, who_from: str | None,
          answering: bool = False) -> str:
    """The node for whoever a row names, or for nobody, at its end of the reading."""
    placed = (ANSWERER, "right") if answering else (WHO, "left")
    if not who:
        return picture.node(
            NOBODY_ANSWERED_ID if answering else NOBODY_ID, NOBODY, NOBODY,
            ("answers that carry no name" if answering
             else "rows of the harness that carry no name"), placed=placed, rank=1)
    return picture.node(f"name:{who_from}:{who}", NAME, who,
                        f"{who} -- as `{who_from}` gives it, unchecked",
                        who_from=who_from, placed=placed)


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


def _project(picture: Picture, name: Any) -> str:
    return picture.node(f"project:{name}", PROJECT, str(name), f"project {name}")


def _way(picture: Picture, way: str) -> str:
    return picture.node(f"way:{way}", WAY, way, f"instructions whose source is {way}")


def _told(texts: list[Any]) -> str:
    quoted = "; ".join(f"«{_short(text, 40)}»" for text in texts[:TOLD])
    return f"newest: {quoted}" + ("; …" if len(texts) > TOLD else "")


def _instructions(made: Picture, rows: Rows, drawn: int, harness: str,
                  raised: set[str]) -> dict[str, str]:
    """Draw the instructions; return the node of each one drawn singly, by id."""
    singly: dict[str, str] = {}
    plain: list[tuple[dict[str, Any], dict[str, Any]]] = []

    def one(row: dict[str, Any], seen: dict[str, Any]) -> None:
        node = made.node(
            f"instruction:{row.get('id')}", INSTRUCTION, _short(seen["what"]),
            f"instruction {row.get('id')}: {seen['what']} -- {row.get('status')}",
            status=row.get("status"), at=seen["at"])
        singly[str(row.get("id"))] = node
        _joined(made, node, seen)

    for index, row in enumerate(rows.instructions):
        seen = interaction_service.instructed(row)
        if seen["way"]:
            made.edge(_way(made, seen["way"]), harness, "recorded by")
        if index >= drawn:
            continue
        follows = seen["who"] or seen["session"] or seen["chat"] or str(row.get("id")) in raised
        if follows:
            one(row, seen)
        else:
            plain.append((row, seen))
    made.not_drawn["instructions"] = max(0, len(rows.instructions) - drawn)

    if len(plain) == 1:
        one(*plain[0])
    elif plain:
        node = made.node(
            INSTRUCTIONS_ID, INSTRUCTIONS, f"{len(plain)} instructions",
            f"{len(plain)} instructions that name nobody and raised no question -- "
            + _told([seen["what"] for _, seen in plain]), count=len(plain), rank=2)
        made.counted["instructions"] = len(plain)
        for _, seen in plain:
            _joined(made, node, seen)
    return singly


def _joined(made: Picture, node: str, seen: dict[str, Any]) -> None:
    """One instruction's edges, from its own node or the node it is counted in."""
    made.edge(_name(made, seen["who"], seen["who_from"]), node, "instructed")
    if seen["way"]:
        made.edge(node, _way(made, seen["way"]), "way in")
    if seen["project"]:
        made.edge(node, _project(made, seen["project"]), "for")
    session = (made.node(f"session:{seen['session']}", SESSION, str(seen["session"]),
                         f"protocol session {seen['session']}")
               if seen["session"] else None)
    turn = f"turn {seen['turn']}" if seen["turn"] else ""
    if seen["chat"]:
        chat = made.node(f"chat:{seen['chat']}", CHAT, str(seen["chat"]),
                         f"protocol chat {seen['chat']}")
        made.edge(node, chat, "turn", turn)
        if session:
            made.edge(chat, session, "in session")
    elif session:
        made.edge(node, session, "turn", turn)


def _questions(made: Picture, rows: Rows, drawn: int, singly: dict[str, str],
               consents: dict[str, str]) -> None:
    plain: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]] = []
    for row in rows.asks[:drawn]:
        seen = interaction_service.asked(row)
        response = rows.responses.get(str(row.get("id")))
        answer = (interaction_service.answered(row, response)
                  if response is not None else None)
        raised = _raised_by(row, consents)
        if not raised and not seen["who"] and not (answer and answer["who"]):
            plain.append((row, seen, answer))
            continue
        _question(made, row, seen, answer, raised, singly)
    made.not_drawn["questions"] = max(0, len(rows.asks) - drawn)

    if len(plain) == 1:
        _question(made, *plain[0], None, singly)
    elif plain:
        answered = sum(1 for _, _, answer in plain if answer is not None)
        node = made.node(
            QUESTIONS_ID, QUESTIONS, f"{len(plain)} questions",
            f"{len(plain)} questions that name nobody and no instruction raised, "
            f"{answered} of them answered -- "
            + _told([seen["what"] for _, seen, _ in plain]), count=len(plain), rank=2)
        made.counted["questions"] = len(plain)
        for _, seen, answer in plain:
            made.edge(_name(made, None, None), node, "asked")
            if seen["project"]:
                made.edge(node, _project(made, seen["project"]), "for")
            if answer is not None:
                made.edge(node, _name(made, None, None, answering=True), "answered")


def _question(made: Picture, row: dict[str, Any], seen: dict[str, Any],
              answer: dict[str, Any] | None, raised: str | None,
              singly: dict[str, str]) -> None:
    """One question drawn singly, with whoever asked and whoever answered."""
    # A consent's prompt repeats its instruction, which stands beside it; its
    # status is what the reading needs there.
    label = f"consent · {row.get('status')}" if raised else _short(seen["what"])
    node = made.node(
        f"question:{row.get('id')}", QUESTION, label,
        f"question {row.get('id')}: {seen['what']} -- {row.get('status')}",
        status=row.get("status"), at=seen["at"])
    origin = singly.get(raised) if raised else None
    if origin:
        made.edge(origin, node, "asked")
    elif seen["project"]:
        made.edge(node, _project(made, seen["project"]), "for")
    # Who issued it, when the row says. A question an act raised names nobody
    # and is not drawn as asked by nobody: its instruction asked.
    if seen["who"] or not raised:
        made.edge(_name(made, seen["who"], seen["who_from"]), node, "asked")
    if answer is not None:
        made.edge(node, _name(made, answer["who"], answer["who_from"], answering=True),
                  "answered", f"answered {answer['what']}")


def picture(rows: Rows, drawn: int = DRAWN) -> Picture:
    """The rows as nodes and edges. Reads nothing and lays out nothing."""
    made = Picture()
    harness = _harness(made, rows)

    consents = {str(row["consent_request_id"]): str(row.get("id"))
                for row in rows.instructions if row.get("consent_request_id")}
    raised = {found for found in (_raised_by(row, consents) for row in rows.asks[:drawn])
              if found}
    singly = _instructions(made, rows, drawn, harness, raised)
    _questions(made, rows, drawn, singly, consents)

    for row in rows.runs:
        seen = interaction_service.ran(row)
        tool = made.node(f"tool:{seen['what']}", TOOL, str(seen["what"]),
                         f"tool {seen['what']}", rank=2)
        made.edge(_name(made, None, None), tool, "ran")
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
            color=COLOURS.get(kind, OTHER_COLOUR),
            style=NAMED_STYLE if edge["named"] else UNNAMED_STYLE,
            named=edge["named"], hover=said, title=said)
    return graph


def caveat(rows: Rows, made: Picture) -> str:
    """The sentence a reader needs before believing the shape."""
    parts = [CAVEAT]
    held = [f"{count} older {what}" for what, count in made.not_drawn.items() if count]
    if held:
        parts.append(f"Not drawn: {', '.join(held)}")
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
        "layout": getattr(options, "layout", LAYOUT),
        "type": getattr(options, "type", None),
        "palette_id": getattr(options, "palette_id", "0"),
        # Every node's name is what this graph is for: the canvas draws them
        # without the reader turning names on.
        "names": True,
        "instance": interaction_service.instance(rows.health),
        "rows": len(found),
        "unnamed": sum(1 for row in found if not row["who"]),
        "counted": dict(made.counted),
        "not_drawn": dict(made.not_drawn),
        "answers": dict(rows.answers),
        "may_hold_more": rows.full,
        "caveat": caveat(rows, made),
    }


def as_gjgf(made: Picture, options: Any = None, source: str = "") -> dict[str, Any]:
    """The picture in this project's graph format, laid out by its layouts."""
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    chosen = options or PlotOptions(layout=LAYOUT)
    return GraphSerializer.serialize_to_gjgf(as_graph(made, source), chosen)
