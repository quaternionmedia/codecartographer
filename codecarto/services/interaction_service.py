"""Who did what at the harness, and through which way in, read for a panel.

The harness records four kinds of row that carry a time: an instruction, a
question put to a person, the answer to one, and a tool run. This module reads
them through `qmcp_client` and returns each as one interaction: when, what was
done, the way in the row names, and who the row names.

Who is what a row says, and nothing here checks it. Three fields name
somebody: the id a protocol client gave, in an instruction's `detail.client`;
`responded_by` on an answer; and `issued_by` in a question's context. A row
with none of them names nobody and is returned that way. The way in is an
instruction's `source`; no other row names one.

The harness's health answer says which server answered: its pid, its port, a
fingerprint of its database and when it started. Every row read is that one
server's.

This module reads. It posts nothing to the harness, stores nothing and starts
no process; `tests/test_boundaries.py` holds it to that.

What it cannot do: name a machine, an address or an account, because no field
it reads holds one; say whether a name is a person's or a program's; or read
a second harness. The harness lists its questions without their answers, so
an answer is one read each: at most `ANSWERS_READ` are read and the rest are
counted.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from codecarto.services import qmcp_client
from codecarto.services.harness_service import ASKED
from codecarto.services.qmcp_client import Reach

SHOWN = 30
"""Interactions a panel is handed, newest first."""

WHO_SHOWN = 20
"""Rows of the who table a panel is handed."""

ANSWERS_READ = 20
"""Answers read per reading, newest question first. Each is one request."""

CELLS = 48
"""Equal spans of time each lane of `over_time` is counted into."""

INSTANCE_FIELDS = ("pid", "port", "database_fingerprint", "started_at",
                   "session", "version")

ACTS = ("instructed", "asked", "answered", "ran")
"""What a row records somebody doing, in the order the lanes are listed."""

CAVEAT = ("who is what a row says, unchecked: a protocol client's id on an "
          "instruction, `responded_by` on an answer, `issued_by` on a question. "
          "A row with none of them names nobody. The way in is an "
          "instruction's source, and no other row names one. No field read "
          "here names a machine, an address or an account, and every row "
          "comes from the one harness this reading names")

NOT_IDENTIFIED = ("what answered names no pid and no port, so it does not say "
                  "which server it is")

_STAMP = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?"
    r"(Z|[+-]\d{2}:?\d{2})?$")


def moment(value: Any) -> float | None:
    """A harness timestamp as seconds since the epoch, or None.

    The harness writes UTC with no zone on a stored time, so a time with no
    zone is read as UTC.
    """
    found = _STAMP.match(value) if isinstance(value, str) else None
    if found is None:
        return None
    year, month, day, hour, minute, second = (int(part) for part in found.groups()[:6])
    fraction, zone = found.group(7), found.group(8)
    offset = timedelta(0)
    if zone and zone != "Z":
        digits = zone[1:].replace(":", "")
        offset = timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        if zone[0] == "-":
            offset = -offset
    try:
        stamp = datetime(year, month, day, hour, minute, second,
                         tzinfo=timezone(offset))
    except ValueError:
        return None
    return stamp.timestamp() + (float(f"0.{fraction}") if fraction else 0.0)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _named(value: Any) -> str | None:
    """A name as a row gave it, or None for a blank or a missing one."""
    text = str(value).strip() if value is not None else ""
    return text or None


def _interaction(at: Any, act: str, ref: Any, what: Any, *, way: Any = None,
                 who: Any = None, who_from: str = "", project: Any = None,
                 session: Any = None, chat: Any = None, turn: Any = None,
                 ) -> dict[str, Any]:
    name = _named(who)
    return {"at": at, "act": act, "way": _named(way), "who": name,
            "who_from": who_from if name else None, "what": what, "ref": ref,
            "project": project, "session": session, "chat": chat, "turn": turn}


def instructed(row: dict[str, Any]) -> dict[str, Any]:
    """An instruction: its source is the way in, and a protocol turn names a client."""
    detail = _dict(row.get("detail"))
    return _interaction(
        row.get("created_at"), "instructed", row.get("id"), row.get("text"),
        way=row.get("source"), who=detail.get("client"), who_from="detail.client",
        project=row.get("project"), session=detail.get("session"),
        chat=detail.get("chat"), turn=detail.get("turn"))


def asked(row: dict[str, Any]) -> dict[str, Any]:
    """A question put to a person, with whoever its context says issued it."""
    context = _dict(row.get("context"))
    return _interaction(
        row.get("created_at"), "asked", row.get("id"), row.get("prompt"),
        who=context.get("issued_by"), who_from="context.issued_by",
        project=context.get("project"))


def answered(row: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """The answer to a question, with whoever it says responded."""
    return _interaction(
        response.get("created_at"), "answered", row.get("id"),
        response.get("response"), who=response.get("responded_by"),
        who_from="responded_by", project=_dict(row.get("context")).get("project"))


def ran(row: dict[str, Any]) -> dict[str, Any]:
    """A tool run. Its row names no caller and no way in."""
    return _interaction(row.get("created_at"), "ran", row.get("id"),
                        row.get("tool_name"))


def instance(reach: Reach) -> dict[str, Any]:
    """Which server answered, as its health answer states it."""
    stated = {name: None for name in INSTANCE_FIELDS}
    if not reach.ok:
        return {"identified": False, "where": reach.where, **stated,
                "problem": reach.problem, "remedy": reach.remedy}
    document = _dict(reach.document)
    stated = {name: document.get(name) for name in INSTANCE_FIELDS}
    identified = (isinstance(stated["pid"], int)
                  and isinstance(stated["port"], int))
    return {"identified": identified, "where": reach.where, **stated,
            "problem": "" if identified else NOT_IDENTIFIED, "remedy": ""}


def newest_first(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Interactions by time, newest first; one with no readable time is last."""
    def key(row: dict[str, Any]) -> tuple[int, float]:
        at = moment(row.get("at"))
        return (1, at) if at is not None else (0, 0.0)
    return sorted(found, key=key, reverse=True)


def who_table(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per name, act and way in, with a count and the newest time.

    Rows that name nobody are one group per act and way in, so what the
    harness recorded with no name is counted beside what it recorded with one.
    """
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in found:
        key = (row["who"], row["who_from"], row["act"], row["way"])
        at = moment(row.get("at"))
        held = groups.get(key)
        if held is None:
            groups[key] = {"who": row["who"], "who_from": row["who_from"],
                           "act": row["act"], "way": row["way"], "count": 1,
                           "last": row.get("at"), "_last": at}
            continue
        held["count"] += 1
        if at is not None and (held["_last"] is None or at > held["_last"]):
            held["last"], held["_last"] = row.get("at"), at
    ordered = sorted(groups.values(),
                     key=lambda g: (g["_last"] is not None, g["_last"] or 0.0),
                     reverse=True)
    return [{name: value for name, value in group.items() if name != "_last"}
            for group in ordered]


def over_time(found: list[dict[str, Any]], cells: int = CELLS) -> dict[str, Any]:
    """Each act and way in as a lane, counted into equal spans of time.

    The spans run from the oldest interaction read to the newest. An
    interaction with no readable time is in no span, and `undated` counts
    them.
    """
    dated = [(at, row) for at, row in ((moment(row.get("at")), row) for row in found)
             if at is not None]
    if not dated:
        return {"from": None, "to": None, "cells": cells, "lanes": [],
                "undated": len(found)}
    start, oldest = min(dated, key=lambda pair: pair[0])
    end, newest = max(dated, key=lambda pair: pair[0])
    span = end - start
    lanes: dict[tuple[str, Any], dict[str, Any]] = {}
    for at, row in dated:
        key = (row["act"], row["way"])
        lane = lanes.setdefault(key, {"act": row["act"], "way": row["way"],
                                      "count": 0, "cells": [0] * cells})
        index = min(cells - 1, int((at - start) / span * cells)) if span else 0
        lane["count"] += 1
        lane["cells"][index] += 1
    ordered = sorted(lanes.values(),
                     key=lambda lane: (ACTS.index(lane["act"]), lane["way"] or ""))
    return {"from": oldest.get("at"), "to": newest.get("at"), "cells": cells,
            "lanes": ordered, "undated": len(found) - len(dated)}


def _rows(reach: Reach, key: str) -> list[dict[str, Any]]:
    found = _dict(reach.document).get(key) if reach.ok else None
    return [row for row in found or [] if isinstance(row, dict)]


def answers(asks: list[dict[str, Any]], base: str | None = None,
            limit: int = ANSWERS_READ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The answers to the newest answered questions, and how many were not read.

    A read that finds nothing answering ends the reading of answers: the
    rest are counted as unread and nothing more is asked.
    """
    responded = [row for row in asks if row.get("status") == "responded"]
    found: list[dict[str, Any]] = []
    for row in responded[:limit]:
        reach = qmcp_client.question(str(row.get("id")), base)
        if not reach.ok and reach.status is None:
            break
        response = _dict(reach.document).get("response") if reach.ok else None
        if isinstance(response, dict):
            found.append(answered(row, response))
    return found, {"read": len(found), "unread": len(responded) - len(found),
                   "limit": limit}


def read(base: str | None = None) -> dict[str, Any]:
    """Everything the panel shows.

    The health answer is read first. When nothing answers, no other read is
    made and the answer is that one problem. Otherwise a list the harness
    would not serve is named in `unread_lists` and the others are shown.
    """
    health = qmcp_client.health(base)
    if not health.ok and health.status is None:
        return {"unreachable": True, "problem": health.problem,
                "remedy": health.remedy, "where": health.where}

    reads = (("instructions", qmcp_client.instructions(ASKED, base), "instructions", instructed),
             ("questions", qmcp_client.queue(ASKED, base), "requests", asked),
             ("tool runs", qmcp_client.invocations(ASKED, base), "invocations", ran))
    found: list[dict[str, Any]] = []
    unread_lists: list[dict[str, Any]] = []
    full = False
    asks: list[dict[str, Any]] = []
    for what, reach, key, shape in reads:
        if not reach.ok:
            unread_lists.append({"what": what, "problem": reach.problem,
                                 "remedy": reach.remedy, "where": reach.where})
            continue
        rows = _rows(reach, key)
        full = full or len(rows) >= ASKED
        found.extend(shape(row) for row in rows)
        if what == "questions":
            asks = rows

    given, counted = answers(asks, base)
    found.extend(given)

    ordered = newest_first(found)
    page = ordered[:SHOWN]
    table = who_table(found)
    return {
        "instance": instance(health),
        "interactions": {"rows": page, "shown": len(page),
                         "more": len(ordered) - len(page),
                         "more_is_floor": full or counted["unread"] > 0},
        "who": {"rows": table[:WHO_SHOWN], "shown": len(table[:WHO_SHOWN]),
                "more": len(table) - len(table[:WHO_SHOWN])},
        "over_time": over_time(found),
        "answers": counted,
        "unread_lists": unread_lists,
        "caveat": CAVEAT,
    }
