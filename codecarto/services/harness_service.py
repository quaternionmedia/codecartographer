"""What the harness is running and what it is asking, read for a panel.

Three lists are read over HTTP through `qmcp_client`: the tool runs, the
questions held for a person, and the instructions. Each is returned as the
harness gave it, cut to the rows a panel shows, with the number held back
stated beside it.

A run state is derived for each project an instruction or a pending question
names, and for nothing else. The harness's rows name a project, never a box, so
the window joins a state to the boxes it drew by the repository in each box's
address. A tool run names no project; it is listed and counted, and gives no
box a state.

This module reads. It posts nothing to the harness, stores nothing and starts
no process; `tests/test_boundaries.py` holds it to that.

What it cannot do: say that a project named in a row is the one a box means.
The join is by name, and two owners with a repository of one name would share a
state.
"""

from __future__ import annotations

from typing import Any

from codecarto.services import qmcp_client
from codecarto.services.qmcp_client import Reach

SHOWN = 20
"""Rows of each list a panel is handed."""

ASKED = 500
"""Rows asked of the harness per list, which is the most its routes return."""

# Where an instruction's status puts its project, and only for the statuses an
# act walks. `recorded` and `unresolved` describe a record nothing was asked or
# run for, so they give no state.
STATE_OF = {
    "asking": "active",
    "consented": "active",
    "acting": "active",
    "done": "success",
    "failed": "failed",
    "refused": "idle",
    "unanswered": "idle",
}

RUN_FIELDS = ("id", "tool_name", "status", "created_at", "duration_ms", "error")
ASK_FIELDS = ("id", "prompt", "status", "request_type", "options", "created_at",
              "expires_at")
INSTRUCTION_FIELDS = ("id", "text", "project", "status", "source", "runtime",
                      "updated_at", "outcome_text", "exit_code")

CAVEAT = ("a box's state comes from the newest instruction acted on for its "
          "project and from questions still waiting on a person. A tool run "
          "names no project, so it is listed and lights no box")


def _rows(reach: Reach, key: str) -> list[dict[str, Any]]:
    found = reach.document.get(key) if isinstance(reach.document, dict) else None
    return [row for row in found or [] if isinstance(row, dict)]


def listing(reach: Reach, key: str, fields: tuple[str, ...],
            shown: int = SHOWN, asked: int = ASKED) -> dict[str, Any]:
    """One list as a panel shows it, or why it could not be read.

    `more` is how many rows the harness returned beyond the ones shown. When
    the harness returned as many as were asked for it may hold others, and
    `more_is_floor` says so.
    """
    if not reach.ok:
        return {"rows": [], "shown": 0, "more": 0, "more_is_floor": False,
                "problem": reach.problem, "remedy": reach.remedy,
                "where": reach.where}
    rows = _rows(reach, key)
    page = rows[:shown]
    return {
        "rows": [{name: row.get(name) for name in fields} for row in page],
        "shown": len(page),
        "more": len(rows) - len(page),
        "more_is_floor": len(rows) >= asked,
        "problem": "", "remedy": "", "where": reach.where,
    }


def _ask_row(row: dict[str, Any]) -> dict[str, Any]:
    """A question, with the three things its context says an act is for."""
    context = row.get("context") if isinstance(row.get("context"), dict) else {}
    shown = {name: row.get(name) for name in ASK_FIELDS}
    shown["project"] = context.get("project")
    shown["instruction_id"] = context.get("instruction_id")
    shown["spend"] = context.get("spend")
    return shown


def states(instructions: list[dict[str, Any]],
           asks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One state per project named, each saying which row gave it.

    The newest instruction on the act path decides its project's state. A
    question still pending for a project makes it `active` whatever its
    instructions say, because something is waiting on a person now.
    """
    newest: dict[str, dict[str, Any]] = {}
    for row in instructions:
        project = row.get("project")
        if not project or row.get("status") not in STATE_OF:
            continue
        held = newest.get(project)
        if held is None or str(row.get("updated_at") or "") > str(held.get("updated_at") or ""):
            newest[project] = row

    found: dict[str, dict[str, Any]] = {}
    for project, row in newest.items():
        found[project] = {
            "project": project,
            "state": STATE_OF[row["status"]],
            "because": f"instruction {row.get('id')} is {row['status']}",
        }
    for row in asks:
        context = row.get("context") if isinstance(row.get("context"), dict) else {}
        project = context.get("project")
        if not project or row.get("status") != "pending":
            continue
        found[project] = {
            "project": project,
            "state": "active",
            "because": f"request {row.get('id')} is waiting on a person",
        }
    return [found[project] for project in sorted(found)]


def unplaced(runs: list[dict[str, Any]], instructions: list[dict[str, Any]],
             asks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What was read and gives no box a state, counted with the reason."""
    counts = (
        ("tool runs", len(runs), "a tool run names no project"),
        ("instructions", sum(1 for r in instructions if not r.get("project")),
         "no project was resolved for them"),
        ("questions", sum(
            1 for r in asks
            if not (r.get("context") or {}).get("project")),
         "their context names no project"),
    )
    return [{"what": what, "count": count, "why": why}
            for what, count, why in counts if count]


def read(base: str | None = None) -> dict[str, Any]:
    """Everything the panel shows, from three reads of the harness.

    When the first read finds nothing answering, the other two are not made
    and the answer is that one problem. Otherwise each list carries its own
    problem, so a harness that lists its runs and not its instructions shows
    the runs.
    """
    runs = qmcp_client.invocations(ASKED, base)
    if not runs.ok and runs.status is None:
        return {"unreachable": True, "problem": runs.problem,
                "remedy": runs.remedy, "where": runs.where}
    asks = qmcp_client.queue(ASKED, base)
    instructions = qmcp_client.instructions(ASKED, base)

    run_rows = _rows(runs, "invocations") if runs.ok else []
    ask_rows = _rows(asks, "requests") if asks.ok else []
    instruction_rows = _rows(instructions, "instructions") if instructions.ok else []

    queue = listing(asks, "requests", ASK_FIELDS)
    queue["rows"] = [_ask_row(row) for row in ask_rows[:queue["shown"]]]
    return {
        "runs": listing(runs, "invocations", RUN_FIELDS),
        "queue": queue,
        "instructions": listing(instructions, "instructions", INSTRUCTION_FIELDS),
        "states": states(instruction_rows, ask_rows),
        "unplaced": unplaced(run_rows, instruction_rows, ask_rows),
        "caveat": CAVEAT,
    }
