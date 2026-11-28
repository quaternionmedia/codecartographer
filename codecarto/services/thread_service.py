"""The harness's archive of conversations, and one conversation as a graph.

`read_list` is what the harness lists, as it lists it. `read` is one
conversation's turns. `summary` is what a panel shows of one; `picture` turns
its turns into nodes and edges and hands them to the serializer every other
graph here goes through.

    role            --said-->      turn        a turn that opens an exchange
    turn            --replied-->   turn        each turn after it, until the next opens
    turn            --by-->        role        the role of a reply

The role of a conversation's first turn opens an exchange each time it
speaks; every other turn until the next is a reply to it. So a row reads left
to right: who spoke, what they said, a reply, who replied; an opening turn
with several replies stands at the middle of their rows. Each node says which
column it stands in and how far down (`rank`, its place among the turns), and
`reading_order.place` lays the rows out from those, set close and wrapped
into blocks.

A role is the word the harness's turn carries, and differs between the
sources a conversation was exported from; none is read as a person or a
program. The same role opening and replying is two nodes, one at each end.

What this cannot do: say that an archived conversation is still going on,
because the archive is what was exported and indexed, read again as it is
asked for; draw more than the newest `DRAWN` turns, the rest being counted;
or show a turn's whole text, which a hover holds the first `SAID` characters
of.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from codecarto.services import interaction_service, qmcp_client
from codecarto.services.qmcp_client import Reach
from codecarto.services.reading_order import (ANSWERER, INSTRUCTION_COLUMN, QUESTION_COLUMN,
                                              WHO)

LIST = "/v1/threads"

LISTED = 60
"""Conversations listed for a panel; the rest are counted."""

TOLD = 20
"""Turns listed for a panel, newest first; the rest are counted."""

DRAWN = 150
"""Turns drawn, the newest; the rest are counted."""

LABEL = 24
"""Characters of a turn's text in its name, the width `reading_order` leaves."""

SAID = 600
"""Characters of a turn's text on its hover and in a panel's list."""

LAYOUT = "Reading Order"

NO_ROUTE = ("this build of the harness serves no archive of conversations; "
            "update the harness")

NO_ROLE = "no role stated"

SAID_BY, REPLIED, BY = "said", "replied", "by"
COLOURS = {SAID_BY: "#6db2ff", REPLIED: "#e0c069", BY: "#5ac8b0"}

ROLE, OPENING, REPLY = "role", "opening", "reply"
KIND_TO_TYPE = {ROLE: "Input", OPENING: "Worker", REPLY: "Gate"}

CAVEAT = ("Read left to right: who spoke, what they said, a reply, who "
          "replied. Every node is a turn of the conversation or a role its "
          "turns carry. The role of the first turn opens a row each time it "
          "speaks, and every other turn until the next is drawn as a reply "
          "to it, because the archive states the order of turns and not "
          "which turn answers which. A role is the word the harness's turn "
          "carries, unchecked")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _problem(kind: str, problem: str, remedy: str, where: str) -> dict[str, Any]:
    return {kind: True, "problem": problem, "remedy": remedy, "where": where}


def absent(reach: Reach) -> dict[str, Any]:
    """A read that failed, as the envelope every estate route answers in.

    Nothing answering is `unreachable`. Anything that answered and did not
    give the document is `unreadable`, in the harness's own words when it
    gave any.
    """
    kind = "unreachable" if reach.status is None and "not JSON" not in reach.problem else "unreadable"
    return _problem(kind, reach.problem, reach.remedy, reach.where)


def _one_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def _cut(value: Any, limit: int) -> tuple[str, bool]:
    text = _one_line(value)
    return (text, False) if len(text) <= limit else (text[: limit - 1].rstrip() + "…", True)


def read_list(source: str = "", titled: str = "", base: str | None = None) -> dict[str, Any]:
    """The conversations the harness lists, in its order, or the one problem.

    `source` keeps the conversations of one source and `titled` those whose
    title holds that text, whatever its case; both are counted before the
    list is cut to `LISTED`.
    """
    reach = qmcp_client.fetch(LIST, base, remedy_404=NO_ROUTE)
    if not reach.ok:
        return absent(reach)
    document = reach.document
    if not isinstance(document, dict) or not isinstance(document.get("threads"), list):
        return _problem("unreadable", "the harness's archive carries no list of `threads`",
                        "", reach.where)
    rows = _dicts(document["threads"])
    sources: dict[str, int] = {}
    for row in rows:
        name = str(row.get("source") or "")
        sources[name] = sources.get(name, 0) + 1
    wanted = titled.strip().lower()
    kept = [row for row in rows
            if (not source or str(row.get("source") or "") == source)
            and (not wanted or wanted in str(row.get("title") or "").lower())]
    return {
        "instance": interaction_service.instance(qmcp_client.health(base)),
        "where": reach.where,
        "threads": [{key: row.get(key) for key in
                     ("source", "id", "title", "turns", "last_seen", "diverged", "address")}
                    for row in kept[:LISTED]],
        "shown": min(len(kept), LISTED),
        "more": max(len(kept) - LISTED, 0),
        "sources": sources,
        "totals": _dict(document.get("totals")),
        "generated_at": document.get("generated_at"),
        "reading": _dict(document.get("reading")),
    }


def path(source: str, identifier: str) -> str:
    """The harness's route for one conversation."""
    return f"{LIST}/{quote(source, safe='')}/{quote(identifier, safe='')}"


def read(source: str, identifier: str, base: str | None = None) -> dict[str, Any]:
    """One conversation as the harness gives it, or the one problem.

    A conversation the archive lists and the harness does not serve is
    `unreadable` with the harness's sentence.
    """
    if not source.strip() or not identifier.strip():
        return _problem("unreadable", "no conversation is named: a source and an id are both needed",
                        "", f"{base or qmcp_client.base_url()}{LIST}")
    reach = qmcp_client.fetch(path(source, identifier), base, remedy_404=NO_ROUTE)
    if not reach.ok:
        found = absent(reach)
        if isinstance(reach.detail, str) and reach.detail:
            found.update(problem=reach.detail, remedy="")
        return found
    document = reach.document
    if not isinstance(document, dict) or not isinstance(document.get("turns"), list):
        return _problem("unreadable", "the harness's conversation carries no list of `turns`",
                        "", reach.where)
    return {
        "instance": interaction_service.instance(qmcp_client.health(base)),
        "where": reach.where,
        "source": document.get("source", source),
        "id": document.get("id", identifier),
        "title": document.get("title"),
        "url": document.get("url"),
        "started_at": document.get("started_at"),
        "partial": document.get("partial"),
        "turns": _dicts(document["turns"]),
    }


def _role(turn: dict[str, Any]) -> str:
    return str(turn.get("role") or NO_ROLE)


def mark(document: dict[str, Any]) -> str:
    """One string two reads of a conversation share only when its turns are as many and end alike."""
    turns = document.get("turns") or []
    last = turns[-1] if turns else {}
    return f"{len(turns)} {last.get('id') or ''} {len(str(last.get('text') or ''))}"


def summary(document: dict[str, Any]) -> dict[str, Any]:
    """What a panel shows of one conversation: its counts and its newest turns."""
    turns = document.get("turns") or []
    roles: dict[str, int] = {}
    for turn in turns:
        roles[_role(turn)] = roles.get(_role(turn), 0) + 1
    rows = []
    for index in range(len(turns) - 1, max(len(turns) - TOLD, 0) - 1, -1):
        turn = turns[index]
        text, cut = _cut(turn.get("text"), SAID)
        rows.append({"index": index + 1, "id": turn.get("id"), "role": _role(turn),
                     "at": turn.get("at"), "text": text, "cut": cut})
    return {
        **{key: document.get(key) for key in
           ("instance", "where", "source", "id", "title", "url", "started_at", "partial")},
        "turns": {"count": len(turns), "roles": roles, "rows": rows, "shown": len(rows),
                  "more": len(turns) - len(rows)},
        "drawn": min(len(turns), DRAWN),
        "mark": mark(document),
        "caveat": caveat(document),
    }


@dataclass
class Picture:
    """Nodes and edges, before a graph library or a layout sees them."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    not_drawn: int = 0


def _said(turn: dict[str, Any], index: int) -> str:
    text, _ = _cut(turn.get("text"), SAID)
    when = f" · {turn['at']}" if turn.get("at") else ""
    return f"turn {index + 1} · {_role(turn)}{when} — {text}"


def picture(document: dict[str, Any], drawn: int = DRAWN) -> Picture:
    """The conversation's newest turns as nodes and edges. Reads nothing and lays out nothing."""
    turns = document.get("turns") or []
    made = Picture(not_drawn=max(len(turns) - drawn, 0))
    if not turns:
        return made
    opener = _role(turns[0])
    opening: str | None = None
    for index in range(made.not_drawn, len(turns)):
        turn = turns[index]
        role = _role(turn)
        node = f"turn:{turn.get('id') or index + 1}"
        label, _ = _cut(turn.get("text"), LABEL)
        opens = role == opener
        made.nodes[node] = {
            "label": label or f"turn {index + 1}", "kind": OPENING if opens else REPLY,
            "role": role, "hover": _said(turn, index), "rank": index, "label_at": "above",
            "column": INSTRUCTION_COLUMN if opens else QUESTION_COLUMN}
        if opens:
            opening = node
            who = f"said:{role}"
            made.nodes.setdefault(who, {"label": role, "kind": ROLE, "role": role, "hover": role,
                                        "rank": 0, "label_at": "left", "column": WHO})
            made.edges[(who, node)] = {"kind": SAID_BY, "hover": f"{role} said turn {index + 1}"}
            continue
        replier = f"replied:{role}"
        made.nodes.setdefault(replier, {"label": role, "kind": ROLE, "role": role, "hover": role,
                                        "rank": 0, "label_at": "right", "column": ANSWERER})
        made.edges[(node, replier)] = {"kind": BY, "hover": f"turn {index + 1} is {role}'s"}
        if opening is not None:
            made.edges[(opening, node)] = {"kind": REPLIED,
                                           "hover": f"turn {index + 1} follows it"}
    return made


def as_graph(made: Picture, source: str = ""):
    """The picture as a `networkx` graph this project's serializer accepts.

    Imported inside the function so that reading the harness does not require
    a graph library, the choice `topology_service.as_graph` makes.
    """
    import networkx as nx

    from codecarto.services import palette_service

    graph = nx.MultiDiGraph(kind="thread", source=source, dense=True)
    for node_id, node in made.nodes.items():
        graph.add_node(node_id, **node, **palette_service.vocabulary(KIND_TO_TYPE[node["kind"]]),
                       click=f"<p>{html.escape(str(node['hover']))}</p>")
    for (source_id, target_id), edge in made.edges.items():
        graph.add_edge(source_id, target_id, key=edge["kind"], label=edge["kind"],
                       kind=edge["kind"], color=COLOURS[edge["kind"]], style="solid",
                       hover=edge["hover"], title=edge["hover"])
    return graph


def caveat(document: dict[str, Any]) -> str:
    """The sentence a reader needs before believing the shape."""
    parts = [CAVEAT]
    held = max(len(document.get("turns") or []) - DRAWN, 0)
    if held:
        parts.append(f"Not drawn: {held} older turn(s)")
    if document.get("partial"):
        parts.append("The harness says this conversation is partial")
    return ". ".join(parts) + "."


def metadata(document: dict[str, Any], made: Picture, options: Any = None) -> dict[str, Any]:
    """Graph-level facts the canvas and any other client both read."""
    return {
        "kind": "thread",
        "source": document.get("where", ""),
        "layout": getattr(options, "layout", LAYOUT),
        "type": getattr(options, "type", None),
        "palette_id": getattr(options, "palette_id", "0"),
        # Every node's name is what this graph is for: the canvas draws them
        # without the reader turning names on.
        "names": True,
        "instance": document.get("instance"),
        "thread": {"source": document.get("source"), "id": document.get("id"),
                   "title": document.get("title")},
        "turns": len(document.get("turns") or []),
        "not_drawn": made.not_drawn,
        "mark": mark(document),
        "caveat": caveat(document),
    }


def as_gjgf(document: dict[str, Any], made: Picture, options: Any = None) -> dict[str, Any]:
    """The picture in this project's graph format, laid out by its layouts."""
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    chosen = options or PlotOptions(layout=LAYOUT)
    return GraphSerializer.serialize_to_gjgf(as_graph(made, str(document.get("where", ""))), chosen)
