"""`/harness/gjgf`: the harness's interactions as a graph on the one canvas.

Most tests build the rows directly and read the nodes and edges
`interaction_graph.picture` makes of them, before any layout. The route tests
stand the harness in at `qmcp_client.fetch`, as `test_harness_interactions.py`
does, and run the real route, service, serializer and layout.

Mutations each test was seen to fail under are named in its docstring.
"""

from __future__ import annotations

import io
import json
import urllib.request

import pytest
from fastapi.testclient import TestClient

from codecarto.services import interaction_graph, qmcp_client
from codecarto.services.interaction_service import Rows
from codecarto.services.qmcp_client import Reach
from tests.test_harness_interactions import HEALTH, Harness, _answer, _ask, _instruction, _run

TURN = {"surface": "agent-host-protocol", "session": "s-1", "chat": "c-1",
        "turn": "t-1", "client": "editor-7"}
NOBODY, HARNESS = interaction_graph.NOBODY_ID, interaction_graph.HARNESS_ID


def _rows(instructions=(), asks=(), runs=(), responses=None, health=HEALTH,
          **more) -> Rows:
    return Rows(health=Reach(True, "http://harness/health", dict(health), status=200),
                instructions=list(instructions), asks=list(asks), runs=list(runs),
                responses=dict(responses or {}),
                answers=more.pop("answers", {"read": 0, "unread": 0, "limit": 20}),
                **more)


def _edges(made) -> set[tuple[str, str, str]]:
    return set(made.edges)


def test_a_protocol_turn_reads_as_a_path_from_its_client_to_whoever_answered():
    """Mutations: drop the edge from the instruction to the question it raised
    -- the path is cut; draw `asked` from nobody for a question an act raised
    -- the consent gains a second asker."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "protocol", TURN)],
        asks=[_ask(1, "2026-01-01T00:00:02", "responded",
                   {"instruction_id": "ins-1", "project": "alpha"})],
        responses={"ask-1": _answer("2026-01-01T00:00:03", "ada", "hold")}))

    assert _edges(made) == {
        ("name:detail.client:editor-7", "instruction:ins-1", "instructed"),
        ("instruction:ins-1", "question:ask-1", "asked"),
        ("question:ask-1", "name:responded_by:ada", "answered"),
        ("instruction:ins-1", "way:protocol", "way in"),
        ("way:protocol", HARNESS, "recorded by"),
        ("instruction:ins-1", "project:alpha", "for"),
        ("instruction:ins-1", "chat:c-1", "turn"),
        ("chat:c-1", "session:s-1", "in session"),
    }
    assert NOBODY not in made.nodes
    assert {node["kind"] for node in made.nodes.values()} == {
        "name", "instruction", "question", "way in", "harness", "project",
        "chat", "session"}
    assert made.edges[("question:ask-1", "name:responded_by:ada", "answered")][
        "hover"] == "answered hold"
    assert made.edges[("instruction:ins-1", "chat:c-1", "turn")]["hover"] == "turn t-1"


@pytest.mark.parametrize("by", ["the instruction's consent_request_id",
                                "the question's context"])
def test_a_question_is_joined_to_its_instruction_by_either_row(by):
    """Mutations: return only `consents.get(...)` from `_raised_by` -- the
    context case is unjoined; never fill `consents` -- the other is."""
    instruction = _instruction(1, "2026-01-01T00:00:01")
    ask = _ask(1, "2026-01-01T00:00:02")
    if by.startswith("the instruction"):
        instruction["consent_request_id"] = "ask-1"
    else:
        ask["context"] = {"instruction_id": "ins-1"}
    made = interaction_graph.picture(_rows(instructions=[instruction], asks=[ask]))

    assert ("instruction:ins-1", "question:ask-1", "asked") in made.edges
    assert ("question:ask-1", HARNESS, "recorded by") not in made.edges
    assert (NOBODY, "question:ask-1", "asked") not in made.edges


def test_a_row_that_names_nobody_is_joined_to_the_one_nobody_node_by_a_dashed_edge():
    """Mutations: set `named` to True on every edge -- nothing is dashed; give
    each unnamed row a node of its own in `_name` -- there are three."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "typed"),
                      _instruction(2, "2026-01-01T00:00:02", "protocol", TURN)],
        asks=[_ask(1, "2026-01-01T00:00:03", "responded")],
        responses={"ask-1": _answer("2026-01-01T00:00:04", None)}))

    assert [n for n, node in made.nodes.items() if node["kind"] == "nobody named"] == [NOBODY]
    assert made.nodes[NOBODY]["label"] == "nobody named"
    unnamed = {key for key, edge in made.edges.items() if not edge["named"]}
    assert unnamed == {
        (NOBODY, "instruction:ins-1", "instructed"),
        (NOBODY, "question:ask-1", "asked"),
        ("question:ask-1", NOBODY, "answered"),
    }
    graph = interaction_graph.as_graph(made)
    styles = {(s, t, k): data["style"] for s, t, k, data in graph.edges(keys=True, data=True)}
    assert styles[(NOBODY, "instruction:ins-1", "instructed")] == "dashed"
    assert styles[("name:detail.client:editor-7", "instruction:ins-2", "instructed")] == "solid"
    assert {style for style in styles.values()} == {"dashed", "solid"}


def test_the_same_name_under_two_fields_is_two_nodes():
    """Mutation: name the node `name:{who}` with no field -- the two become one."""
    made = interaction_graph.picture(_rows(
        asks=[_ask(1, "2026-01-01T00:00:01", "responded", {"issued_by": "grace"})],
        responses={"ask-1": _answer("2026-01-01T00:00:02", "grace")}))

    assert made.nodes["name:context.issued_by:grace"]["who_from"] == "context.issued_by"
    assert made.nodes["name:responded_by:grace"]["who_from"] == "responded_by"
    assert "as `responded_by` gives it, unchecked" in made.nodes["name:responded_by:grace"]["hover"]
    assert ("name:context.issued_by:grace", "question:ask-1", "asked") in made.edges
    assert ("question:ask-1", "name:responded_by:grace", "answered") in made.edges


def test_rows_that_share_both_ends_are_one_edge_with_their_count_and_a_width_from_it():
    """Mutations: set the count to 1 instead of adding to it -- every edge is
    one row; return `MIN_WIDTH` from `_width` whatever the count -- the widths
    are equal; say the kind alone on a counted edge's hover -- `×3` is gone."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "voice"),
                      _instruction(2, "2026-01-01T00:00:02", "voice")],
        runs=[_run(n, "2026-01-01T00:00:03") for n in range(3)]))

    assert made.edges[(NOBODY, "tool:echo", "ran")]["count"] == 3
    assert made.edges[("tool:echo", HARNESS, "recorded by")]["count"] == 3
    assert made.edges[("way:voice", HARNESS, "recorded by")]["count"] == 2
    assert made.edges[(NOBODY, "instruction:ins-1", "instructed")]["count"] == 1
    assert sum(1 for node in made.nodes.values() if node["kind"] == "tool") == 1

    graph = interaction_graph.as_graph(made)
    ran = graph.edges[NOBODY, "tool:echo", "ran"]
    one = graph.edges[NOBODY, "instruction:ins-1", "instructed"]
    two = graph.edges["way:voice", HARNESS, "recorded by"]
    assert (ran["label"], ran["hover"], ran["count"], ran["size"]) == (
        "ran", "ran ×3", 3, interaction_graph.MAX_WIDTH)
    assert (one["label"], one["hover"], one["count"], one["size"]) == (
        "instructed", "instructed", 1, interaction_graph.MIN_WIDTH)
    assert interaction_graph.MIN_WIDTH < two["size"] < interaction_graph.MAX_WIDTH
    # A layout reads `weight` as a distance, so no edge carries one.
    assert all("weight" not in data for _, _, data in graph.edges(data=True))


def test_a_question_no_drawn_instruction_raised_is_joined_to_the_harness():
    """Mutations: do not add `recorded by` for such a question -- it floats
    free of the harness; draw its project only when an instruction is drawn
    -- beta is not drawn."""
    made = interaction_graph.picture(_rows(asks=[
        _ask(1, "2026-01-01T00:00:01", context={"issued_by": "grace", "project": "beta"}),
        _ask(2, "2026-01-01T00:00:02", context={"instruction_id": "not-read"}),
        _ask(3, "2026-01-01T00:00:03"),
    ]))

    assert _edges(made) == {
        ("name:context.issued_by:grace", "question:ask-1", "asked"),
        ("question:ask-1", HARNESS, "recorded by"),
        ("question:ask-1", "project:beta", "for"),
        # Raised by an act on an instruction that is not drawn: joined to the
        # harness, and not drawn as asked by nobody.
        ("question:ask-2", HARNESS, "recorded by"),
        ("question:ask-3", HARNESS, "recorded by"),
        (NOBODY, "question:ask-3", "asked"),
    }


def test_a_question_whose_answer_was_not_read_is_drawn_with_no_answer():
    """Mutation: draw `answered` to nobody when no answer was read -- a
    waiting question reads as answered by nobody."""
    made = interaction_graph.picture(_rows(asks=[
        _ask(1, "2026-01-01T00:00:01", "pending"),
        _ask(2, "2026-01-01T00:00:02", "responded"),
    ]))

    assert not [key for key in made.edges if key[2] == "answered"]
    assert made.nodes["question:ask-1"]["status"] == "pending"
    assert made.nodes["question:ask-2"]["status"] == "responded"


def test_rows_older_than_the_ones_drawn_are_counted_and_still_counted_on_their_way_in():
    """Mutations: report `not_drawn` as 0 -- the count is lost; count a way
    in only for a drawn instruction -- `recorded by` reads 2, not 5."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(n, f"2026-01-01T00:00:0{9 - n}", "voice") for n in range(5)],
        asks=[_ask(n, f"2026-01-01T00:00:0{9 - n}") for n in range(4)]), drawn=2)

    assert sorted(n for n in made.nodes if n.startswith("instruction:")) == [
        "instruction:ins-0", "instruction:ins-1"]
    assert sorted(n for n in made.nodes if n.startswith("question:")) == [
        "question:ask-0", "question:ask-1"]
    assert made.not_drawn == {"instructions": 3, "questions": 2}
    assert made.edges[("way:voice", HARNESS, "recorded by")]["count"] == 5


def test_the_harness_node_says_which_server_it_is_or_that_it_does_not_say():
    """Mutation: label the node `harness` whatever the health answer states --
    the port is gone."""
    named = interaction_graph.picture(_rows()).nodes[HARNESS]
    assert named["label"] == "harness :3999"
    assert named["hover"] == ("http://harness/health -- pid 4242, port 3999, "
                              "database_fingerprint 0123456789abcdef, "
                              "started_at 2026-01-01T00:00:00+00:00, version 0.1.0")

    unnamed = interaction_graph.picture(_rows(health={"status": "healthy"})).nodes[HARNESS]
    assert unnamed["label"] == "harness"
    assert "names no pid and no port" in unnamed["hover"]


def test_a_long_text_is_a_short_label_and_whole_on_hover_and_markup_is_escaped():
    """Mutations: label a node with its whole text -- the label is not cut;
    drop `html.escape` in `as_graph` -- the markup reaches the click panel."""
    text = "<b>rewrite</b> " + "the whole of the documentation " * 4
    instruction = _instruction(1, "2026-01-01T00:00:01")
    instruction["text"] = text
    made = interaction_graph.picture(_rows(instructions=[instruction]))

    node = made.nodes["instruction:ins-1"]
    assert len(node["label"]) == interaction_graph.LABEL
    assert node["label"].endswith("…")
    assert text.strip() in node["hover"]
    click = interaction_graph.as_graph(made).nodes["instruction:ins-1"]["click"]
    assert "<b>" not in click
    assert "&lt;b&gt;rewrite&lt;/b&gt;" in click


def test_the_caveat_says_what_is_not_drawn_not_read_and_may_be_missing():
    """Mutation: leave the unread answers out of `caveat` -- a reader is not
    told why answered questions have no answer."""
    rows = _rows(
        instructions=[_instruction(n, "2026-01-01T00:00:01") for n in range(3)],
        answers={"read": 20, "unread": 4, "limit": 20}, full=True,
        unread_lists=[{"what": "tool runs", "problem": "the harness refused: 500",
                       "remedy": "", "where": "http://harness/v1/invocations"}])
    said = interaction_graph.caveat(rows, interaction_graph.picture(rows, drawn=1))

    assert said.startswith(interaction_graph.CAVEAT)
    assert "Not drawn as nodes: 2 older instructions." in said
    assert "4 answered question(s) are drawn with no answer" in said
    assert "at most 20 are read" in said
    assert "The tool runs were not read: the harness refused: 500." in said
    assert "may hold rows that are not here" in said
    # With nothing held back, the caveat is the standing sentence alone.
    plain = _rows()
    assert interaction_graph.caveat(plain, interaction_graph.picture(plain)) == (
        interaction_graph.CAVEAT + ".")


def _read(monkeypatch, harness, query: str = "") -> dict:
    monkeypatch.setattr(qmcp_client, "fetch", harness)
    from codecarto.main import app

    answer = TestClient(app).get("/harness/gjgf" + query)
    assert answer.status_code == 200
    return answer.json()["results"]


def _harness() -> Harness:
    return Harness(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "protocol", TURN),
                      _instruction(2, "2026-01-01T00:00:02", "voice")],
        asks=[_ask(1, "2026-01-01T00:00:03", "responded", {"instruction_id": "ins-1"})],
        answers={"ask-1": _answer("2026-01-01T00:00:04", "ada")},
        runs=[_run(n, "2026-01-01T00:00:05") for n in range(3)])


@pytest.mark.parametrize("layout", ["Kamada Kawai", "Circular", "spring_layout"])
def test_the_route_answers_a_graph_every_node_placed_and_styled(monkeypatch, layout):
    """Mutations: answer `kind: topology` in `metadata` -- the Interactions
    panel's strip would not show for it; add a node with no palette type --
    it has no shape."""
    found = _read(monkeypatch, _harness(), f"?layout={layout}")

    nodes = found["graph"]["nodes"]
    assert {"harness", "nobody", "name:detail.client:editor-7", "instruction:ins-1",
            "question:ask-1", "name:responded_by:ada", "way:protocol", "way:voice",
            "tool:echo"} <= set(nodes)
    for node_id, node in nodes.items():
        held = node["metadata"]
        assert isinstance(held["x"], float) and isinstance(held["y"], float), node_id
        assert held["kind"] in interaction_graph.KIND_TO_TYPE, node_id
        assert held["shape"] and held["color"] and held["size"], node_id
        assert node["label"], node_id
    edges = {(e["source"], e["target"], e["metadata"]["kind"]): e for e in found["graph"]["edges"]}
    answered = edges[("question:ask-1", "name:responded_by:ada", "answered")]
    assert answered["metadata"]["style"] == "solid"
    assert edges[("nobody", "tool:echo", "ran")]["metadata"]["style"] == "dashed"

    metadata = found["metadata"]
    assert metadata["kind"] == "interactions"
    assert metadata["source"] == "http://harness/health"
    assert metadata["instance"]["pid"] == 4242
    assert metadata["layout"] == layout
    # The spoken instruction, the consent question and the tool runs name nobody.
    assert (metadata["rows"], metadata["unnamed"]) == (7, 5)
    assert metadata["not_drawn"] == {"instructions": 0, "questions": 0}
    assert metadata["caveat"] == interaction_graph.CAVEAT + "."


def test_nothing_answering_is_one_problem_and_no_graph(monkeypatch):
    """Mutation: never take the early return in `harness_gjgf` -- a lone
    harness node is drawn for a harness that is not there."""
    harness = Harness(gone_after=0)
    found = _read(monkeypatch, harness)

    assert found["unreachable"] is True
    assert "nothing is answering" in found["problem"]
    assert "graph" not in found
    assert harness.asked == ["/health"]


def test_a_layout_nobody_registered_is_a_sentence_naming_the_ones_that_are(monkeypatch):
    """Mutation: let the `ValueError` out of `harness_gjgf` -- the route
    raises instead of answering."""
    found = _read(monkeypatch, _harness(), "?layout=Nonsense")

    assert found["unreadable"] is True
    assert "does not exist" in found["problem"]
    assert "kamada_kawai_layout" in found["remedy"]
    assert found["where"] == "/harness/gjgf?layout=Nonsense"
    assert "graph" not in found


def test_the_graph_route_only_reads_the_harness(monkeypatch):
    """Every request the route makes of the harness is a GET with no body.

    Mutation: pass `data=b"{}"` to `urllib.request.Request` in
    `qmcp_client.fetch` -- this fails."""
    seen: list[tuple[str, bytes | None, str]] = []
    ask = _ask(1, "2026-01-01T00:00:01", "responded")

    def record(request, timeout=None):
        seen.append((request.get_method(), request.data, request.full_url))
        if request.full_url.endswith("/v1/human/requests/ask-1"):
            return _Answer({"request": ask, "response": _answer("2026-01-01T00:00:02", "ada")})
        return _Answer({**HEALTH, "invocations": [], "requests": [ask], "instructions": []})

    monkeypatch.setattr(urllib.request, "urlopen", record)
    from codecarto.main import app

    answer = TestClient(app).get("/harness/gjgf")
    assert answer.status_code == 200
    assert "name:responded_by:ada" in answer.json()["results"]["graph"]["nodes"]
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
