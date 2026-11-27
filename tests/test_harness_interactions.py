"""`/harness/interactions`: who did what at the harness, through which way in.

The harness is stood in for at `qmcp_client.fetch`, the one function that
reaches it, so every test that goes through `_read` runs the real route, the
real service and the real client functions above that call.

Mutations each test was seen to fail under are named in its docstring.
"""

from __future__ import annotations

import io
import json
import urllib.parse
import urllib.request

import pytest
from fastapi.testclient import TestClient

from codecarto.services import interaction_service, qmcp_client
from codecarto.services.qmcp_client import Reach

HEALTH = {"status": "healthy", "version": "0.1.0", "pid": 4242, "port": 3999,
          "database_fingerprint": "0123456789abcdef",
          "started_at": "2026-01-01T00:00:00+00:00", "session": None}


def _instruction(n: int, at: str, source: str = "typed", detail: dict | None = None,
                 project: str | None = "alpha") -> dict:
    return {"id": f"ins-{n}", "text": f"do thing {n}", "project": project,
            "status": "recorded", "source": source, "created_at": at,
            "updated_at": at, "detail": detail or {}, "cwd": "not shown"}


def _ask(n: int, at: str, status: str = "pending", context: dict | None = None,
         ask_id: str | None = None) -> dict:
    return {"id": ask_id or f"ask-{n}", "prompt": f"act on {n}?", "status": status,
            "request_type": "approval", "options": ["approve", "hold"],
            "created_at": at, "expires_at": None, "context": context or {}}


def _answer(at: str, by: str | None, said: str = "approve") -> dict:
    return {"id": "r", "request_id": "x", "response": said, "responded_by": by,
            "response_metadata": {}, "created_at": at}


def _run(n: int, at: str) -> dict:
    return {"id": f"run-{n}", "tool_name": "echo", "status": "success",
            "created_at": at, "input_params": {"secret": "not shown"}}


class Harness:
    """A harness that answers its health, three lists and one question at a time."""

    def __init__(self, runs=(), asks=(), instructions=(), answers=None,
                 health=HEALTH, refuse=(), gone_after: int | None = None):
        self.lists = {"/v1/invocations": ("invocations", list(runs)),
                      "/v1/human/requests": ("requests", list(asks)),
                      "/v1/instructions": ("instructions", list(instructions))}
        self.answers = dict(answers or {})
        self.health = health
        self.refuse = dict(refuse)
        self.gone_after = gone_after
        self.asked: list[str] = []

    def __call__(self, path, base=None, remedy_404=None):
        if self.gone_after is not None and len(self.asked) >= self.gone_after:
            self.asked.append(path)
            return Reach(False, "http://harness" + path,
                         problem="nothing is answering at http://harness")
        self.asked.append(path)
        route, _, query = path.partition("?")
        where = "http://harness" + path
        if route in self.refuse:
            return Reach(False, where, status=self.refuse[route],
                         problem=f"the harness is running and has no {route}",
                         remedy=remedy_404 or "")
        if route == "/health":
            return Reach(True, where, dict(self.health), status=200)
        if route.startswith("/v1/human/requests/"):
            wanted = urllib.parse.unquote(route.rsplit("/", 1)[1])
            row = next(r for r in self.lists["/v1/human/requests"][1] if r["id"] == wanted)
            return Reach(True, where, {"request": row,
                                       "response": self.answers.get(wanted)}, status=200)
        key, rows = self.lists[route]
        limit = int(query.split("limit=")[1]) if "limit=" in query else len(rows)
        return Reach(True, where, {key: rows[:limit], "count": len(rows[:limit])},
                     status=200)


def _read(monkeypatch, harness) -> dict:
    monkeypatch.setattr(qmcp_client, "fetch", harness)
    from codecarto.main import app

    answer = TestClient(app).get("/harness/interactions")
    assert answer.status_code == 200
    return answer.json()["results"]


def _one(found: dict, act: str, ref: str) -> dict:
    rows = [r for r in found["interactions"]["rows"] if (r["act"], r["ref"]) == (act, ref)]
    assert len(rows) == 1, (act, ref, found["interactions"]["rows"])
    return rows[0]


def test_each_row_is_one_interaction_with_the_way_in_and_the_name_it_carries(monkeypatch):
    """Mutations: read `who` from `detail.get("surface")` in `instructed` --
    the client is not named; pass `way=row.get("request_type")` in `asked` --
    a question gains a way in."""
    turn = {"surface": "agent-host-protocol", "session": "s-1", "chat": "c-1",
            "turn": "t-1", "client": "editor-7"}
    found = _read(monkeypatch, Harness(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "protocol", turn),
                      _instruction(2, "2026-01-01T00:00:02", "voice")],
        asks=[_ask(1, "2026-01-01T00:00:03", "responded",
                   {"project": "alpha", "issued_by": "grace"})],
        answers={"ask-1": _answer("2026-01-01T00:00:04", "ada", "hold")},
        runs=[_run(1, "2026-01-01T00:00:05")]))

    assert _one(found, "instructed", "ins-1") == {
        "at": "2026-01-01T00:00:01", "act": "instructed", "way": "protocol",
        "who": "editor-7", "who_from": "detail.client", "what": "do thing 1",
        "ref": "ins-1", "project": "alpha", "session": "s-1", "chat": "c-1",
        "turn": "t-1"}
    spoken = _one(found, "instructed", "ins-2")
    assert (spoken["way"], spoken["who"], spoken["who_from"]) == ("voice", None, None)
    question = _one(found, "asked", "ask-1")
    assert (question["way"], question["who"], question["who_from"]) == (
        None, "grace", "context.issued_by")
    answer = _one(found, "answered", "ask-1")
    assert (answer["at"], answer["way"], answer["who"], answer["who_from"],
            answer["what"], answer["project"]) == (
        "2026-01-01T00:00:04", None, "ada", "responded_by", "hold", "alpha")
    run = _one(found, "ran", "run-1")
    assert (run["way"], run["who"], run["what"]) == (None, None, "echo")
    assert found["caveat"] == interaction_service.CAVEAT


def test_interactions_of_every_kind_are_one_list_newest_first(monkeypatch):
    """Mutation: drop `reverse=True` in `newest_first` -- the order inverts."""
    found = _read(monkeypatch, Harness(
        instructions=[_instruction(1, "2026-01-01T00:00:02")],
        asks=[_ask(1, "2026-01-01T00:00:04")],
        runs=[_run(1, "2026-01-01T00:00:03"), _run(2, "2026-01-01T00:00:01"),
              _run(3, "not a time")]))

    assert [(r["act"], r["ref"]) for r in found["interactions"]["rows"]] == [
        ("asked", "ask-1"), ("ran", "run-1"), ("instructed", "ins-1"),
        ("ran", "run-2"), ("ran", "run-3")]


@pytest.mark.parametrize("by", [None, "", "   "])
def test_an_answer_that_names_nobody_is_returned_naming_nobody(monkeypatch, by):
    """Mutation: return `str(value)` from `_named` -- a blank or `None` becomes
    a name."""
    found = _read(monkeypatch, Harness(
        asks=[_ask(1, "2026-01-01T00:00:01", "responded")],
        answers={"ask-1": _answer("2026-01-01T00:00:02", by)}))

    answer = _one(found, "answered", "ask-1")
    assert answer["who"] is None
    assert answer["who_from"] is None


def test_the_who_table_counts_what_names_nobody_beside_what_names_somebody(monkeypatch):
    """Mutations: skip rows whose `who` is None in `who_table` -- the tool runs
    and the typed instructions vanish; key the groups without `way` -- voice
    and typed merge."""
    found = _read(monkeypatch, Harness(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "typed"),
                      _instruction(2, "2026-01-01T00:00:02", "typed"),
                      _instruction(3, "2026-01-01T00:00:03", "voice")],
        asks=[_ask(n, f"2026-01-01T00:01:0{n}", "responded") for n in (1, 2, 3)],
        answers={"ask-1": _answer("2026-01-01T00:02:01", "ada"),
                 "ask-2": _answer("2026-01-01T00:02:05", "ada"),
                 "ask-3": _answer("2026-01-01T00:02:03", None)},
        runs=[_run(1, "2026-01-01T00:00:09")]))

    rows = found["who"]["rows"]
    assert {"who": "ada", "who_from": "responded_by", "act": "answered",
            "way": None, "count": 2, "last": "2026-01-01T00:02:05"} in rows
    assert {"who": None, "who_from": None, "act": "answered", "way": None,
            "count": 1, "last": "2026-01-01T00:02:03"} in rows
    assert {"who": None, "who_from": None, "act": "instructed", "way": "typed",
            "count": 2, "last": "2026-01-01T00:00:02"} in rows
    assert {"who": None, "who_from": None, "act": "instructed", "way": "voice",
            "count": 1, "last": "2026-01-01T00:00:03"} in rows
    assert {"who": None, "who_from": None, "act": "ran", "way": None,
            "count": 1, "last": "2026-01-01T00:00:09"} in rows
    # Newest group first.
    assert rows[0]["who"] == "ada"
    assert found["who"]["more"] == 0


def test_names_beyond_the_ones_shown_are_counted(monkeypatch):
    """Mutation: report the who table's `more` as 0 -- this fails on the count."""
    held = interaction_service.WHO_SHOWN + 4
    found = _read(monkeypatch, Harness(instructions=[
        _instruction(n, f"2026-01-01T00:{n:02d}:00", "protocol", {"client": f"client-{n}"})
        for n in range(held)]))

    assert found["who"]["shown"] == interaction_service.WHO_SHOWN
    assert len(found["who"]["rows"]) == interaction_service.WHO_SHOWN
    assert found["who"]["more"] == 4


def test_interactions_beyond_the_ones_shown_are_counted_never_dropped(monkeypatch):
    """Mutation: report `more` as 0 for the interactions -- this fails."""
    held = interaction_service.SHOWN + 7
    found = _read(monkeypatch, Harness(
        runs=[_run(n, f"2026-01-01T00:{n:02d}:00") for n in range(held)]))

    listed = found["interactions"]
    assert listed["shown"] == interaction_service.SHOWN
    assert len(listed["rows"]) == interaction_service.SHOWN
    assert listed["more"] == 7
    assert listed["more_is_floor"] is False
    assert listed["rows"][0]["ref"] == f"run-{held - 1}"


def test_a_full_page_from_the_harness_says_it_may_hold_more(monkeypatch):
    """Mutation: compare with `>` instead of `>=` in `gather` -- this fails."""
    asked = interaction_service.ASKED
    found = _read(monkeypatch, Harness(
        runs=[_run(n, "2026-01-01T00:00:00") for n in range(asked + 5)]))

    assert found["interactions"]["more"] == asked - interaction_service.SHOWN
    assert found["interactions"]["more_is_floor"] is True


def test_each_way_in_is_a_lane_counted_into_spans_from_oldest_to_newest():
    """Mutations: put every interaction in span 0 -- the newest is not in the
    last; leave undated rows out of `undated` -- the count is 0; order the
    lanes by name -- `asked` comes before `instructed`."""
    rows = [interaction_service.instructed(_instruction(1, "2026-01-01T00:00:00", "voice")),
            interaction_service.instructed(_instruction(2, "2026-01-01T00:00:10", "typed")),
            interaction_service.instructed(_instruction(3, "2026-01-01T00:00:40", "typed")),
            interaction_service.asked(_ask(1, "2026-01-01T00:00:20")),
            interaction_service.ran(_run(1, "sometime"))]
    found = interaction_service.over_time(rows, cells=4)

    assert (found["from"], found["to"]) == ("2026-01-01T00:00:00", "2026-01-01T00:00:40")
    assert found["cells"] == 4
    assert found["undated"] == 1
    assert found["lanes"] == [
        {"act": "instructed", "way": "typed", "count": 2, "cells": [0, 1, 0, 1]},
        {"act": "instructed", "way": "voice", "count": 1, "cells": [1, 0, 0, 0]},
        {"act": "asked", "way": None, "count": 1, "cells": [0, 0, 1, 0]},
    ]


def test_interactions_at_one_instant_or_with_no_time_still_make_lanes():
    """Mutation: divide by the span without the guard -- one instant raises."""
    same = [interaction_service.ran(_run(n, "2026-01-01T00:00:00")) for n in (1, 2)]
    assert interaction_service.over_time(same, cells=3)["lanes"] == [
        {"act": "ran", "way": None, "count": 2, "cells": [2, 0, 0]}]

    none = interaction_service.over_time(
        [interaction_service.ran(_run(1, None))], cells=3)
    assert none == {"from": None, "to": None, "cells": 3, "lanes": [], "undated": 1}


@pytest.mark.parametrize(("stamp", "seconds"), [
    ("1970-01-01T00:00:10", 10.0),
    ("1970-01-01 00:00:10", 10.0),
    ("1970-01-01T00:00:10Z", 10.0),
    ("1970-01-01T00:00:10.5", 10.5),
    ("1970-01-01T00:00:10+00:00", 10.0),
    ("1970-01-01T01:00:10+01:00", 10.0),
    ("1969-12-31T23:00:10-0100", 10.0),
])
def test_a_harness_time_is_read_as_utc_unless_it_states_an_offset(stamp, seconds):
    """Mutation: ignore the offset in `moment` -- the two offset cases are an
    hour out."""
    assert interaction_service.moment(stamp) == seconds


@pytest.mark.parametrize("stamp", [None, 7, "", "yesterday", "2026-13-01T00:00:00"])
def test_what_is_not_a_time_has_no_moment(stamp):
    """Mutation: let the `ValueError` out of `moment` -- month 13 raises."""
    assert interaction_service.moment(stamp) is None


def test_answers_are_read_up_to_a_limit_and_the_rest_are_counted(monkeypatch):
    """Mutations: read every answered question in `answers` -- more reads are
    made than the limit; report `unread` as 0 -- this fails on the count."""
    held = interaction_service.ANSWERS_READ + 3
    asks = [_ask(n, f"2026-01-01T00:{59 - n:02d}:00", "responded") for n in range(held)]
    harness = Harness(
        asks=asks + [_ask(99, "2026-01-01T00:00:00", "pending")],
        answers={f"ask-{n}": _answer("2026-01-02T00:00:00", "ada") for n in range(held)})
    found = _read(monkeypatch, harness)

    one_by_one = [p for p in harness.asked if p.startswith("/v1/human/requests/")]
    assert len(one_by_one) == interaction_service.ANSWERS_READ
    # The newest answered questions, and never one still pending.
    assert one_by_one[0] == "/v1/human/requests/ask-0"
    assert "/v1/human/requests/ask-99" not in one_by_one
    assert found["answers"] == {"read": interaction_service.ANSWERS_READ,
                                "unread": 3,
                                "limit": interaction_service.ANSWERS_READ}
    assert found["interactions"]["more_is_floor"] is True


def test_a_question_id_is_quoted_into_the_path(monkeypatch):
    """Mutation: drop `urllib.parse.quote` in `qmcp_client.question` -- the
    path is asked with its slash and its space."""
    odd = "governed-1a2b:drafted/v 2"
    harness = Harness(
        asks=[_ask(1, "2026-01-01T00:00:01", "responded", ask_id=odd)],
        answers={odd: _answer("2026-01-01T00:00:02", "ada")})
    found = _read(monkeypatch, harness)

    assert "/v1/human/requests/governed-1a2b%3Adrafted%2Fv%202" in harness.asked
    assert _one(found, "answered", odd)["who"] == "ada"


def test_nothing_answering_is_one_problem_and_no_other_read(monkeypatch):
    """Mutation: never take the early return in `gather` -- the lists are
    asked for too."""
    harness = Harness(gone_after=0)
    found = _read(monkeypatch, harness)

    assert found["unreachable"] is True
    assert "nothing is answering" in found["problem"]
    assert found["where"] == "http://harness/health"
    assert "interactions" not in found
    assert harness.asked == ["/health"]


def test_a_harness_that_goes_away_ends_the_reading_of_answers(monkeypatch):
    """Mutation: `continue` instead of `break` in `answers` -- every answered
    question is still asked for."""
    asks = [_ask(n, f"2026-01-01T00:0{n}:00", "responded") for n in range(5)]
    # Health, three lists and one answer are served; then nothing answers.
    harness = Harness(asks=asks, gone_after=5, answers={
        f"ask-{n}": _answer("2026-01-02T00:00:00", "ada") for n in range(5)})
    found = _read(monkeypatch, harness)

    one_by_one = [p for p in harness.asked if p.startswith("/v1/human/requests/")]
    assert len(one_by_one) == 2
    assert found["answers"]["read"] == 1
    assert found["answers"]["unread"] == 4
    assert found["interactions"]["more_is_floor"] is True


def test_the_instance_is_what_the_health_answer_states(monkeypatch):
    """Mutation: return `document` whole from `instance` -- `status` appears."""
    found = _read(monkeypatch, Harness(runs=[_run(1, "2026-01-01T00:00:00")]))

    assert found["instance"] == {
        "identified": True, "where": "http://harness/health", "pid": 4242,
        "port": 3999, "database_fingerprint": "0123456789abcdef",
        "started_at": "2026-01-01T00:00:00+00:00", "session": None,
        "version": "0.1.0", "problem": "", "remedy": ""}


@pytest.mark.parametrize("health", [
    {"status": "healthy", "version": "0.0.9"},
    {"status": "healthy", "pid": "4242", "port": 3999},
])
def test_a_health_answer_with_no_pid_and_port_does_not_identify_a_server(monkeypatch, health):
    """Mutation: set `identified` to True whatever was stated -- this fails."""
    found = _read(monkeypatch, Harness(runs=[_run(1, "2026-01-01T00:00:00")],
                                      health=health))

    assert found["instance"]["identified"] is False
    assert found["instance"]["problem"] == interaction_service.NOT_IDENTIFIED
    # The rows are still read: an unnamed server's rows are still rows.
    assert found["interactions"]["shown"] == 1


def test_no_health_route_leaves_the_rows_shown_and_says_so(monkeypatch):
    """Mutation: have `Rows.answering` be `health.ok` alone, so any failed
    health read is nothing answering -- the rows disappear."""
    found = _read(monkeypatch, Harness(runs=[_run(1, "2026-01-01T00:00:00")],
                                      refuse={"/health": 404}))

    assert found["instance"]["identified"] is False
    assert "has no /health" in found["instance"]["problem"]
    assert found["instance"]["pid"] is None
    assert found["interactions"]["shown"] == 1


def test_a_list_the_harness_does_not_serve_is_named_and_the_others_shown(monkeypatch):
    """Mutation: do not append to `unread_lists` in `gather` -- the missing
    list is silent."""
    found = _read(monkeypatch, Harness(
        runs=[_run(1, "2026-01-01T00:00:00")],
        refuse={"/v1/instructions": 404}))

    assert found["interactions"]["shown"] == 1
    assert found["unread_lists"] == [{
        "what": "instructions",
        "problem": "the harness is running and has no /v1/instructions",
        "remedy": qmcp_client.LOOPBACK_ONLY,
        "where": f"http://harness/v1/instructions?limit={interaction_service.ASKED}"}]


def test_the_route_only_reads_the_harness(monkeypatch):
    """Every request the route makes of the harness is a GET with no body,
    the one made per answer among them.

    Mutation: pass `data=b"{}"` to `urllib.request.Request` in
    `qmcp_client.fetch` -- this fails."""
    seen: list[tuple[str, bytes | None, str]] = []
    ask = _ask(1, "2026-01-01T00:00:01", "responded")

    def record(request, timeout=None):
        seen.append((request.get_method(), request.data, request.full_url))
        if request.full_url.endswith("/v1/human/requests/ask-1"):
            return _Answer({"request": ask, "response": _answer("2026-01-01T00:00:02", "ada")})
        return _Answer({**HEALTH, "invocations": [], "requests": [ask],
                        "instructions": []})

    monkeypatch.setattr(urllib.request, "urlopen", record)
    from codecarto.main import app

    answer = TestClient(app).get("/harness/interactions")
    assert answer.status_code == 200
    assert answer.json()["results"]["answers"]["read"] == 1
    assert len(seen) == 5, seen
    assert all(method == "GET" and data is None for method, data, _ in seen), seen


class _Answer(io.BytesIO):
    status = 200

    def __init__(self, document: dict):
        super().__init__(json.dumps(document).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
