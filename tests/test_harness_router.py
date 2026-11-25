"""`/harness/data`: the harness's runs, queue and instructions, read for a panel.

The harness is stood in for at `qmcp_client.fetch`, the one function that
reaches it, so every test here runs the real route, the real service and the
real client functions above that call.

Mutations each test was seen to fail under are named in its docstring.
"""

from __future__ import annotations

import io
import json
import urllib.request

import pytest
from fastapi.testclient import TestClient

from codecarto.services import harness_service, qmcp_client
from codecarto.services.qmcp_client import Reach


def _run(n: int) -> dict:
    return {"id": f"run-{n}", "tool_name": "echo", "status": "success",
            "created_at": f"2026-01-01T00:00:{n % 60:02d}", "duration_ms": 1,
            "error": None, "input_params": {"secret": "not shown"},
            "result": "not shown"}


def _instruction(n: int, project: str | None, status: str, updated: str) -> dict:
    return {"id": f"ins-{n}", "text": f"do thing {n}", "project": project,
            "status": status, "source": "typed", "runtime": "local",
            "updated_at": updated, "outcome_text": None, "exit_code": None,
            "detail": {"heard": ["not shown"]}}


def _ask(n: int, project: str | None, status: str = "pending") -> dict:
    context = {"instruction_id": f"ins-{n}", "spend": {"authorised": 1}}
    if project:
        context["project"] = project
    return {"id": f"ask-{n}", "prompt": f"act on {n}?", "status": status,
            "request_type": "approval", "options": ["approve", "hold"],
            "created_at": "2026-01-01T00:00:00", "expires_at": "2026-01-01T00:10:00",
            "context": context}


class Harness:
    """A harness that answers three lists and records what it was asked."""

    def __init__(self, runs=(), asks=(), instructions=(), refuse=()):
        self.lists = {"/v1/invocations": ("invocations", list(runs)),
                      "/v1/human/requests": ("requests", list(asks)),
                      "/v1/instructions": ("instructions", list(instructions))}
        self.refuse = dict(refuse)
        self.asked: list[str] = []

    def __call__(self, path, base=None, remedy_404=None):
        self.asked.append(path)
        route, _, query = path.partition("?")
        where = "http://harness" + path
        if route in self.refuse:
            status = self.refuse[route]
            return Reach(False, where, status=status,
                         problem=f"the harness is running and has no {route}",
                         remedy=remedy_404 or "")
        key, rows = self.lists[route]
        limit = int(query.split("limit=")[1]) if "limit=" in query else len(rows)
        return Reach(True, where, {key: rows[:limit], "count": len(rows[:limit])},
                     status=200)


def _read(monkeypatch, harness) -> dict:
    monkeypatch.setattr(qmcp_client, "fetch", harness)
    from codecarto.main import app

    answer = TestClient(app).get("/harness/data")
    assert answer.status_code == 200
    return answer.json()["results"]


def test_each_list_is_the_harness_rows_cut_to_the_fields_a_panel_shows(monkeypatch):
    """Mutation: return the rows whole from `listing` -- `input_params` appears."""
    found = _read(monkeypatch, Harness(
        runs=[_run(1)], asks=[_ask(1, "alpha")],
        instructions=[_instruction(1, "alpha", "asking", "2026-01-01T00:00:01")]))

    assert found["runs"]["rows"] == [{
        "id": "run-1", "tool_name": "echo", "status": "success",
        "created_at": "2026-01-01T00:00:01", "duration_ms": 1, "error": None}]
    ask = found["queue"]["rows"][0]
    assert ask["project"] == "alpha"
    assert ask["instruction_id"] == "ins-1"
    assert ask["spend"] == {"authorised": 1}
    assert "context" not in ask
    assert "detail" not in found["instructions"]["rows"][0]
    assert found["caveat"] == harness_service.CAVEAT


def test_rows_beyond_the_ones_shown_are_counted_never_dropped(monkeypatch):
    """Mutation: report `more` as 0 in `listing` -- this fails on the count."""
    held = harness_service.SHOWN + 7
    found = _read(monkeypatch, Harness(asks=[_ask(n, None) for n in range(held)]))

    queue = found["queue"]
    assert queue["shown"] == harness_service.SHOWN
    assert len(queue["rows"]) == harness_service.SHOWN
    assert queue["more"] == 7
    assert queue["more_is_floor"] is False


def test_a_full_page_from_the_harness_says_it_may_hold_more(monkeypatch):
    """Mutation: compare with `>` instead of `>=` in `listing` -- this fails."""
    asked = harness_service.ASKED
    found = _read(monkeypatch, Harness(runs=[_run(n) for n in range(asked + 30)]))

    runs = found["runs"]
    assert runs["more"] == asked - harness_service.SHOWN
    assert runs["more_is_floor"] is True


def test_nothing_answering_is_one_problem_and_two_reads_not_made(monkeypatch):
    """Mutation: drop the early return in `read` -- three reads are recorded."""
    asked: list[str] = []

    def down(path, base=None, remedy_404=None):
        asked.append(path)
        return Reach(False, "http://harness" + path,
                     problem="nothing is answering at http://harness",
                     remedy="start it with `uv run qm dashboard --start harness`")

    found = _read(monkeypatch, down)
    assert found["unreachable"] is True
    assert "nothing is answering" in found["problem"]
    assert "dashboard --start harness" in found["remedy"]
    assert "runs" not in found
    assert len(asked) == 1


def test_a_list_the_harness_does_not_serve_leaves_the_others_shown(monkeypatch):
    """Mutation: return the unreachable envelope for any failed read -- the
    runs disappear."""
    found = _read(monkeypatch, Harness(
        runs=[_run(1)], asks=[_ask(1, "alpha")],
        refuse={"/v1/instructions": 404}))

    assert found["runs"]["shown"] == 1
    assert found["instructions"]["rows"] == []
    assert "has no /v1/instructions" in found["instructions"]["problem"]
    assert found["instructions"]["remedy"] == qmcp_client.LOOPBACK_ONLY
    # The pending question still gives its project a state.
    assert found["states"] == [{
        "project": "alpha", "state": "active",
        "because": "request ask-1 is waiting on a person"}]


@pytest.mark.parametrize(("status", "state"), sorted(harness_service.STATE_OF.items()))
def test_an_instruction_on_the_act_path_gives_its_project_a_state(status, state):
    found = harness_service.states(
        [_instruction(1, "alpha", status, "2026-01-01T00:00:01")], [])
    assert found == [{"project": "alpha", "state": state,
                      "because": f"instruction ins-1 is {status}"}]


@pytest.mark.parametrize("status", ["recorded", "unresolved"])
def test_a_record_nothing_was_run_for_gives_no_state(status):
    """Mutation: add `recorded` to `STATE_OF` -- a state appears."""
    assert harness_service.states(
        [_instruction(1, "alpha", status, "2026-01-01T00:00:01")], []) == []


def test_the_newest_acted_on_instruction_decides_whatever_the_order():
    """Mutation: keep the first row seen per project -- the older `failed` wins."""
    older = _instruction(1, "alpha", "failed", "2026-01-01T00:00:01")
    newer = _instruction(2, "alpha", "done", "2026-01-02T00:00:01")
    for rows in ([older, newer], [newer, older]):
        assert harness_service.states(rows, [])[0]["state"] == "success"


def test_a_pending_question_makes_its_project_active_over_a_finished_act():
    """Mutation: skip the loop over the questions -- the state stays `success`."""
    done = _instruction(1, "alpha", "done", "2026-01-01T00:00:01")
    found = harness_service.states([done], [_ask(9, "alpha")])
    assert found == [{"project": "alpha", "state": "active",
                      "because": "request ask-9 is waiting on a person"}]
    # An answered question does not.
    assert harness_service.states([done], [_ask(9, "alpha", "responded")])[0][
        "state"] == "success"


def test_rows_that_name_no_project_are_counted_with_the_reason(monkeypatch):
    """Mutation: return an empty list from `unplaced` -- this fails."""
    found = _read(monkeypatch, Harness(
        runs=[_run(1), _run(2)],
        asks=[_ask(1, None)],
        instructions=[_instruction(1, None, "unresolved", "2026-01-01T00:00:01"),
                      _instruction(2, "alpha", "done", "2026-01-01T00:00:02")]))

    assert found["unplaced"] == [
        {"what": "tool runs", "count": 2, "why": "a tool run names no project"},
        {"what": "instructions", "count": 1, "why": "no project was resolved for them"},
        {"what": "questions", "count": 1, "why": "their context names no project"},
    ]
    assert [s["project"] for s in found["states"]] == ["alpha"]


def test_the_route_only_reads_the_harness(monkeypatch):
    """Every request the route makes of the harness is a GET with no body.

    Mutation: pass `data=b"{}"` to `urllib.request.Request` in
    `qmcp_client.fetch` -- this fails."""
    seen: list[tuple[str, bytes | None, str]] = []

    def record(request, timeout=None):
        seen.append((request.get_method(), request.data, request.full_url))
        return _Answer({"invocations": [], "requests": [], "instructions": []})

    monkeypatch.setattr(urllib.request, "urlopen", record)
    from codecarto.main import app

    assert TestClient(app).get("/harness/data").status_code == 200
    assert len(seen) == 3, seen
    assert all(method == "GET" and data is None for method, data, _ in seen), seen


class _Answer(io.BytesIO):
    status = 200

    def __init__(self, document: dict):
        super().__init__(json.dumps(document).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
