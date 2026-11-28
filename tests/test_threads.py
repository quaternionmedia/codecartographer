"""`/harness/threads`, `/harness/thread` and `/harness/thread/gjgf`: the archive, read for a panel.

The harness is stood in for at `qmcp_client.fetch`, the one function that
reads it, so every test here runs the real routes and the real service above
that call. The picture is also tested as a function.

Mutations each test was seen to fail under are named in its docstring.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from codecarto.services import qmcp_client, thread_service
from codecarto.services.qmcp_client import Reach

BASE = "http://harness"
HEALTH = {"pid": 7, "port": 3999, "database_fingerprint": "abc", "started_at": None,
          "session": None, "version": "0"}


def _row(source: str, identifier: str, title: str, turns: int = 2) -> dict:
    return {"source": source, "id": identifier, "title": title, "turns": turns,
            "digest": "d", "first_seen": "2026-01-01T00:00:00Z", "last_seen": "2026-01-02T00:00:00Z",
            "diverged": False, "changes": 0, "address": f"alpha/delta/thread-{identifier}",
            "perspective": f"{source}/thread", "phase": "brainstorm", "delta_type": "thread"}


def _archive(rows: list[dict] | None = None, **over) -> dict:
    listed = rows if rows is not None else [
        _row("ink", "t-1", "Tidy the Shed"), _row("quill", "t-2", "Paint the fence"),
        _row("ink", "t-3", "shed roof")]
    return {"schema": 1, "generated_at": "2026-01-03T00:00:00Z",
            "totals": {"threads": len(listed), "diverged": 0, "unreadable": 0},
            "reading": {"the_index_is_a_reading": "it counts what was exported and indexed"},
            "threads": listed, **over}


def _turn(index: int, role: str, text: str | None = None) -> dict:
    return {"id": f"u-{index}", "role": role, "at": f"2026-01-01T00:00:{index:02d}Z",
            "text": text if text is not None else f"{role} says {index}"}


def _thread(roles: tuple[str, ...] = ("asker", "helper", "helper", "asker", "helper"), **over) -> dict:
    return {"source": "ink", "id": "t-1", "title": "Tidy the Shed", "started_at": "2026-01-01T00:00:00Z",
            "url": "https://example.invalid/t-1", "partial": False,
            "turns": [_turn(index + 1, role) for index, role in enumerate(roles)], **over}


ONE = thread_service.path("ink", "t-1")


class Harness:
    """Answers each path as told, and records what it was asked."""

    def __init__(self, archive=None, thread=None, down=False):
        self.answers = {thread_service.LIST: _archive() if archive is None else archive,
                        ONE: _thread() if thread is None else thread, "/health": HEALTH}
        self.down = down
        self.asked: list[str] = []

    def __call__(self, path, base=None, remedy_404=None):
        self.asked.append(path)
        where = BASE + path
        if self.down:
            return Reach(False, where, problem=f"nothing is answering at {BASE}",
                         remedy="start it with `uv run qm dashboard --start harness`")
        found = self.answers.get(path, 404)
        if isinstance(found, Reach):
            return found
        if found == 404:
            return Reach(False, where, status=404,
                         problem=f"the harness is running but does not serve {path}",
                         remedy=remedy_404 or "")
        return Reach(True, where, found, status=200)


@pytest.fixture()
def harness(monkeypatch):
    def stand(**how) -> Harness:
        made = Harness(**how)
        monkeypatch.setattr(qmcp_client, "fetch", made)
        return made
    return stand


def _get(route: str, **params) -> dict:
    from codecarto.main import app

    answer = TestClient(app).get(route, params=params)
    assert answer.status_code == 200
    return answer.json()["results"]


CHOSEN = {"source": "ink", "id": "t-1"}


def _graph(**params) -> tuple[dict, list, dict]:
    results = _get("/harness/thread/gjgf", **{**CHOSEN, **params})
    return results["graph"]["nodes"], results["graph"]["edges"], results["metadata"]


# --- the archive ----------------------------------------------------------------

def test_the_archive_is_listed_in_the_harnesss_order_with_what_it_says_of_itself(harness):
    """Mutations: sort the list by title -- the second row comes first; drop
    the archive's `reading` -- nothing says the index is a snapshot."""
    harness()
    results = _get("/harness/threads")
    assert [row["id"] for row in results["threads"]] == ["t-1", "t-2", "t-3"]
    assert results["threads"][0] == {"source": "ink", "id": "t-1", "title": "Tidy the Shed", "turns": 2,
                                     "last_seen": "2026-01-02T00:00:00Z", "diverged": False,
                                     "address": "alpha/delta/thread-t-1"}
    assert results["shown"] == 3 and results["more"] == 0
    assert results["sources"] == {"ink": 2, "quill": 1}
    assert results["reading"] == {"the_index_is_a_reading": "it counts what was exported and indexed"}
    assert results["generated_at"] == "2026-01-03T00:00:00Z"
    assert results["where"] == BASE + thread_service.LIST


def test_a_source_and_a_text_narrow_the_list_and_the_sources_are_counted_before(harness):
    """Mutations: match a title by its case -- `shed` finds one row; count the
    sources after narrowing -- the other source is gone from the choice."""
    harness()
    by_source = _get("/harness/threads", source="quill")
    assert [row["id"] for row in by_source["threads"]] == ["t-2"]
    assert by_source["sources"] == {"ink": 2, "quill": 1}
    by_title = _get("/harness/threads", titled=" shed ")
    assert [row["id"] for row in by_title["threads"]] == ["t-1", "t-3"]
    both = _get("/harness/threads", source="quill", titled="shed")
    assert both["threads"] == [] and both["shown"] == 0


def test_a_list_longer_than_is_listed_says_how_many_are_held_back(harness):
    """Mutation: list every row -- a long archive is sent whole to the panel."""
    many = [_row("ink", f"t-{index}", f"talk {index}") for index in range(thread_service.LISTED + 7)]
    harness(archive=_archive(many))
    results = _get("/harness/threads")
    assert len(results["threads"]) == thread_service.LISTED
    assert results["shown"] == thread_service.LISTED and results["more"] == 7
    assert results["threads"][0]["id"] == "t-0"


def test_a_harness_that_is_not_answering_is_unreachable_on_each_route(harness):
    """Mutation: answer an empty list when nothing answers -- a harness that
    is down reads as an archive that holds nothing."""
    harness(down=True)
    for route, params in (("/harness/threads", {}), ("/harness/thread", CHOSEN),
                          ("/harness/thread/gjgf", CHOSEN)):
        results = _get(route, **params)
        assert results.get("unreachable") is True, route
        assert "nothing is answering" in results["problem"]
        assert "--start harness" in results["remedy"]
        assert not {"threads", "turns", "graph"} & set(results), route


@pytest.mark.parametrize("archive", [{"schema": 1}, {"threads": "none"}, ["a list"]])
def test_an_archive_with_no_list_of_threads_is_unreadable(harness, archive):
    """Mutation: read a missing list as empty -- another server's document is
    an archive that holds nothing."""
    harness(archive=archive)
    results = _get("/harness/threads")
    assert results.get("unreadable") is True
    assert "no list of `threads`" in results["problem"]


def test_a_harness_with_no_archive_says_the_build_serves_none(harness):
    """Mutation: pass no `remedy_404` -- the remedy is the topology routes'."""
    harness(archive=404)
    results = _get("/harness/threads")
    assert results.get("unreadable") is True
    assert "serves no archive of conversations" in results["remedy"]


# --- one conversation -----------------------------------------------------------

def test_a_conversation_is_asked_for_by_its_two_words_each_quoted():
    """Mutation: join the words unquoted -- an id with a slash asks for another route."""
    assert thread_service.path("ink", "t-1") == "/v1/threads/ink/t-1"
    assert thread_service.path("a b", "x/y?z") == "/v1/threads/a%20b/x%2Fy%3Fz"


def test_a_conversations_counts_and_newest_turns_are_what_the_panel_is_given(harness):
    """Mutations: list the oldest turns first -- turn 1 heads the list; count
    roles in name order -- `asker` is no longer first of the roles."""
    harness(thread=_thread(("helper", "asker", "helper")))
    results = _get("/harness/thread", **CHOSEN)
    assert results["title"] == "Tidy the Shed" and results["source"] == "ink" and results["id"] == "t-1"
    assert results["where"] == BASE + ONE
    assert results["turns"]["count"] == 3
    assert list(results["turns"]["roles"].items()) == [("helper", 2), ("asker", 1)]
    assert [row["index"] for row in results["turns"]["rows"]] == [3, 2, 1]
    assert results["turns"]["rows"][0] == {"index": 3, "id": "u-3", "role": "helper",
                                           "at": "2026-01-01T00:00:03Z", "text": "helper says 3", "cut": False}
    assert results["turns"]["more"] == 0 and results["drawn"] == 3


def test_a_long_conversation_lists_its_newest_turns_and_a_long_turn_is_cut_and_says_so(harness):
    """Mutations: list every turn -- a long conversation is sent whole; cut a
    text without saying so -- a reader takes the start of a turn for all of it."""
    roles = ("asker", "helper") * (thread_service.TOLD)
    thread = _thread(roles)
    thread["turns"][-1]["text"] = "word " * 400
    thread["turns"][-2]["text"] = "two\n  lines"
    harness(thread=thread)
    turns = _get("/harness/thread", **CHOSEN)["turns"]
    assert turns["count"] == 2 * thread_service.TOLD
    assert turns["shown"] == thread_service.TOLD and turns["more"] == thread_service.TOLD
    newest = turns["rows"][0]
    assert newest["cut"] is True and len(newest["text"]) <= thread_service.SAID and newest["text"].endswith("…")
    assert turns["rows"][1]["text"] == "two lines" and turns["rows"][1]["cut"] is False


def test_a_conversation_the_harness_does_not_serve_is_the_harnesss_sentence(harness):
    """Mutation: keep the client's sentence for a 404 -- a conversation the
    archive lists and the harness cannot find reads as a missing route."""
    stood = harness()
    stood.answers[ONE] = Reach(False, BASE + ONE, status=404, problem="the harness refused (404)",
                               remedy="update the harness", detail="no ink thread 't-1'")
    for route in ("/harness/thread", "/harness/thread/gjgf"):
        results = _get(route, **CHOSEN)
        assert results.get("unreadable") is True, route
        assert results["problem"] == "no ink thread 't-1'" and results["remedy"] == ""


def test_no_conversation_named_is_a_sentence_and_the_harness_is_not_asked(harness):
    """Mutation: ask the harness with an empty word -- the archive's list
    comes back and is read as a conversation with no turns."""
    stood = harness()
    for params in ({}, {"source": "ink"}, {"id": "t-1"}, {"source": " ", "id": "t-1"}):
        stood.asked.clear()
        results = _get("/harness/thread", **params)
        assert results.get("unreadable") is True
        assert "a source and an id are both needed" in results["problem"]
        assert stood.asked == []


def test_a_conversation_with_no_list_of_turns_is_unreadable(harness):
    """Mutation: read missing turns as none -- another document is an empty conversation."""
    harness(thread={"source": "ink", "id": "t-1"})
    results = _get("/harness/thread", **CHOSEN)
    assert results.get("unreadable") is True and "no list of `turns`" in results["problem"]


def test_the_mark_moves_when_a_turn_arrives_or_the_last_one_grows(harness):
    """Mutations: mark by the count alone -- a last turn still being written
    is the same mark; mark by the last id alone -- a turn added before it is."""
    thread = _thread()
    first = thread_service.mark(thread)
    assert thread_service.mark(_thread()) == first
    longer = _thread()
    longer["turns"].append(_turn(6, "asker"))
    assert thread_service.mark(longer) != first
    grown = _thread()
    grown["turns"][-1]["text"] += " and more"
    assert thread_service.mark(grown) != first
    earlier = _thread()
    earlier["turns"].insert(0, _turn(0, "asker"))
    assert thread_service.mark(earlier) != first
    harness()
    assert _get("/harness/thread", **CHOSEN)["mark"] == first
    assert _graph()[2]["mark"] == first


# --- the picture ------------------------------------------------------------------

def test_the_first_turns_role_opens_a_row_and_each_turn_after_is_a_reply_to_it(harness):
    """Mutations: open a row at a role named `user` -- no turn of these roles
    opens one; join a reply to the turn before it -- the second reply hangs
    off the first."""
    harness()
    nodes, edges, _ = _graph()
    assert set(nodes) == {"said:asker", "replied:helper", "turn:u-1", "turn:u-2", "turn:u-3",
                          "turn:u-4", "turn:u-5"}
    found = {(edge["source"], edge["target"], edge["metadata"]["kind"]) for edge in edges}
    assert found == {
        ("said:asker", "turn:u-1", "said"), ("said:asker", "turn:u-4", "said"),
        ("turn:u-1", "turn:u-2", "replied"), ("turn:u-1", "turn:u-3", "replied"),
        ("turn:u-4", "turn:u-5", "replied"),
        ("turn:u-2", "replied:helper", "by"), ("turn:u-3", "replied:helper", "by"),
        ("turn:u-5", "replied:helper", "by")}
    kinds = {name: node["metadata"]["kind"] for name, node in nodes.items()}
    assert kinds["turn:u-1"] == "opening" and kinds["turn:u-2"] == "reply" and kinds["said:asker"] == "role"
    assert nodes["turn:u-2"]["metadata"]["role"] == "helper"


def test_a_role_that_opens_and_a_role_that_replies_are_separate_nodes_per_role(harness):
    """Mutation: one node per role whatever it does -- a third role's replies
    are joined to the opener's node."""
    harness(thread=_thread(("asker", "helper", "tool", "asker")))
    nodes, edges, _ = _graph()
    assert {name for name in nodes if not name.startswith("turn:")} == {
        "said:asker", "replied:helper", "replied:tool"}
    assert ("turn:u-3", "replied:tool") in {(edge["source"], edge["target"]) for edge in edges}


def test_a_turn_is_named_by_the_start_of_its_text_and_its_hover_says_who_and_when(harness):
    """Mutations: name a turn by its id -- the picture is a column of ids;
    leave the role off the hover -- a reply does not say whose it is."""
    thread = _thread()
    thread["turns"][0]["text"] = "Please tidy the shed before the rain comes on Thursday"
    thread["turns"][1]["text"] = ""
    harness(thread=thread)
    nodes, _, _ = _graph()
    first = nodes["turn:u-1"]
    assert first["label"].startswith("Please tidy the shed") and len(first["label"]) <= thread_service.LABEL
    assert first["metadata"]["hover"] == ("turn 1 · asker · 2026-01-01T00:00:01Z — "
                                          "Please tidy the shed before the rain comes on Thursday")
    assert nodes["turn:u-2"]["label"] == "turn 2"


def test_rows_run_top_to_bottom_in_the_order_of_the_turns_and_left_to_right_by_column(harness):
    """Mutation: put a reply in the opening's column -- the two stand in one column."""
    harness()
    nodes, _, _ = _graph()
    at = {name: (node["metadata"]["x"], node["metadata"]["y"]) for name, node in nodes.items()}
    assert at["said:asker"][0] < at["turn:u-1"][0] < at["turn:u-2"][0] < at["replied:helper"][0]
    assert at["turn:u-1"][0] == at["turn:u-4"][0] and at["turn:u-2"][0] == at["turn:u-5"][0]
    assert at["turn:u-2"][1] < at["turn:u-3"][1] < at["turn:u-5"][1]
    assert at["turn:u-1"][1] < at["turn:u-4"][1]


def test_only_the_newest_turns_are_drawn_and_the_rest_are_counted(harness):
    """Mutations: draw the oldest turns -- the newest turn is not on the
    canvas; leave the count out of the caveat -- a cut picture reads as whole."""
    roles = ("asker", "helper") * (thread_service.DRAWN // 2 + 3)
    harness(thread=_thread(roles))
    nodes, edges, metadata = _graph()
    turns = [name for name in nodes if name.startswith("turn:")]
    assert len(turns) == thread_service.DRAWN
    assert f"turn:u-{len(roles)}" in nodes and "turn:u-1" not in nodes
    assert metadata["turns"] == len(roles) and metadata["not_drawn"] == 6
    assert "Not drawn: 6 older turn(s)" in metadata["caveat"]
    harness()
    assert "Not drawn" not in _graph()[2]["caveat"]


def test_a_reply_drawn_without_its_opening_turn_still_names_its_role(harness):
    """Mutations: join the first drawn reply to an opening that is not drawn
    -- the picture carries an edge to a node it does not hold; give every
    turn rank 0 -- the reply with no opening is placed under the rows after it."""
    made = thread_service.picture({"turns": _thread()["turns"]}, drawn=3)
    assert set(made.nodes) == {"turn:u-3", "turn:u-4", "turn:u-5", "said:asker", "replied:helper"}
    assert ("turn:u-3", "replied:helper") in made.edges
    assert all(source in made.nodes and target in made.nodes for source, target in made.edges)
    assert not any(target == "turn:u-3" for _, target in made.edges)
    assert made.not_drawn == 2
    placed = thread_service.as_gjgf({"where": ""}, made)["nodes"]
    assert placed["turn:u-3"]["metadata"]["y"] < placed["turn:u-4"]["metadata"]["y"]


def test_the_graph_says_which_conversation_it_is_and_what_cannot_be_read_from_it(harness):
    """Mutations: leave the conversation off the metadata -- a panel cannot
    tell whose graph the canvas holds; drop the partial sentence."""
    harness(thread=_thread(partial=True))
    _, _, metadata = _graph()
    assert metadata["kind"] == "thread"
    assert metadata["thread"] == {"source": "ink", "id": "t-1", "title": "Tidy the Shed"}
    assert metadata["source"] == BASE + ONE
    assert "not which turn answers which" in metadata["caveat"].replace("\n", " ")
    assert "The harness says this conversation is partial" in metadata["caveat"]
    assert metadata["names"] is True


def test_a_conversation_with_no_turn_is_an_empty_graph_that_says_so(harness):
    """Mutation: read the first turn of none -- the route answers 500."""
    harness(thread=_thread(()))
    nodes, edges, metadata = _graph()
    assert nodes == {} and edges == [] and metadata["turns"] == 0


def test_an_unknown_layout_is_a_sentence_naming_the_registered_ones(harness):
    """Mutation: let the `ValueError` through -- the route answers 500."""
    harness()
    results = _get("/harness/thread/gjgf", **CHOSEN, layout="Nonsense")
    assert results.get("unreadable") is True
    assert "kamada_kawai_layout" in results["remedy"]
    assert "graph" not in results
