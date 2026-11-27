"""`/harness/gjgf`: the harness's interactions as a graph on the one canvas.

Most tests build the rows directly and read the nodes and edges
`interaction_graph.picture` makes of them, before any layout. The route tests
stand the harness in at `qmcp_client.fetch`, as `test_harness_interactions.py`
does, and run the real route, service, serializer and layout.
`test_reading_order.py` holds where the nodes are placed.

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
UNANSWERING = interaction_graph.NOBODY_ANSWERED_ID
MANY, MANY_ASKED = interaction_graph.INSTRUCTIONS_ID, interaction_graph.QUESTIONS_ID


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


def test_each_node_says_its_column_of_the_reading_and_the_side_its_name_goes_on():
    """Mutations: put a name read from `responded_by` in the `who` column --
    the answerer stands at the start; write an instruction's name `right` --
    it lies along the edge to its question."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "protocol", TURN)],
        asks=[_ask(1, "2026-01-01T00:00:02", "responded",
                   {"instruction_id": "ins-1", "issued_by": "grace"})],
        responses={"ask-1": _answer("2026-01-01T00:00:03", "ada")},
        runs=[_run(1, "2026-01-01T00:00:04")]))

    placed = {node_id: (node["column"], node["label_at"]) for node_id, node in made.nodes.items()}
    assert placed == {
        "name:detail.client:editor-7": ("who", "left"),
        "name:context.issued_by:grace": ("who", "left"),
        NOBODY: ("who", "left"),
        "instruction:ins-1": ("instruction", "above"),
        "question:ask-1": ("question", "above"),
        "name:responded_by:ada": ("answerer", "right"),
        HARNESS: ("head", "right"),
        "way:protocol": ("over", "right"),
        "project:alpha": ("under", "below"),
        "tool:echo": ("under", "below"),
        "chat:c-1": ("beneath", "below"),
        "session:s-1": ("beneath", "below"),
    }


@pytest.mark.parametrize("by", ["the instruction's consent_request_id",
                                "the question's context"])
def test_a_question_is_joined_to_its_instruction_by_either_row(by):
    """Mutations: return only `consents.get(...)` from `_raised_by` -- the
    context case is unjoined; never fill `consents` -- the other is; label a
    consent with its prompt -- it repeats the instruction beside it."""
    instruction = _instruction(1, "2026-01-01T00:00:01")
    ask = _ask(1, "2026-01-01T00:00:02")
    if by.startswith("the instruction"):
        instruction["consent_request_id"] = "ask-1"
    else:
        ask["context"] = {"instruction_id": "ins-1"}
    made = interaction_graph.picture(_rows(instructions=[instruction], asks=[ask]))

    assert ("instruction:ins-1", "question:ask-1", "asked") in made.edges
    assert (NOBODY, "question:ask-1", "asked") not in made.edges
    assert made.nodes["question:ask-1"]["label"] == "consent · pending"
    assert "act on 1?" in made.nodes["question:ask-1"]["hover"]


def test_a_row_that_names_nobody_is_joined_to_nobody_at_its_end_of_the_reading_by_a_dashed_edge():
    """Mutations: set `named` to True on every edge -- nothing is dashed; give
    each unnamed row a node of its own in `_name` -- there are three; answer
    to the nobody at the start of the reading -- an answer runs backward."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "typed"),
                      _instruction(2, "2026-01-01T00:00:02", "protocol", TURN)],
        asks=[_ask(1, "2026-01-01T00:00:03", "responded")],
        responses={"ask-1": _answer("2026-01-01T00:00:04", None)}))

    nobodies = {node_id: node["column"] for node_id, node in made.nodes.items()
                if node["kind"] == "nobody named"}
    assert nobodies == {NOBODY: "who", UNANSWERING: "answerer"}
    assert made.nodes[NOBODY]["label"] == made.nodes[UNANSWERING]["label"] == "nobody named"
    unnamed = {key for key, edge in made.edges.items() if not edge["named"]}
    assert unnamed == {
        (NOBODY, "instruction:ins-1", "instructed"),
        (NOBODY, "question:ask-1", "asked"),
        ("question:ask-1", UNANSWERING, "answered"),
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


def test_instructions_that_name_nobody_and_raised_no_question_are_one_node_with_their_count():
    """Mutations: count an instruction a question was raised for among them --
    its consent hangs from nothing; draw each of them singly -- the counted
    node is gone; count one alone as `1 instructions` -- the single case is
    no longer its own node."""
    plain = [_instruction(n, f"2026-01-01T00:00:0{n}", source, project=project)
             for n, source, project in ((1, "voice", "alpha"), (2, "voice", None),
                                        (3, "typed", "alpha"))]
    made = interaction_graph.picture(_rows(
        instructions=plain + [_instruction(4, "2026-01-01T00:00:04", "voice"),
                              _instruction(5, "2026-01-01T00:00:05", "protocol", TURN)],
        asks=[_ask(1, "2026-01-01T00:00:06", context={"instruction_id": "ins-4"})]))

    many = made.nodes[MANY]
    assert (many["kind"], many["label"], many["count"]) == ("instructions", "3 instructions", 3)
    assert many["hover"] == ("3 instructions that name nobody and raised no question -- "
                             "newest: «do thing 1»; «do thing 2»; «do thing 3»")
    assert made.counted == {"instructions": 3}
    assert made.edges[(NOBODY, MANY, "instructed")]["count"] == 3
    assert made.edges[(MANY, "way:voice", "way in")]["count"] == 2
    assert made.edges[(MANY, "way:typed", "way in")]["count"] == 1
    assert made.edges[(MANY, "project:alpha", "for")]["count"] == 2
    # One a question was raised for, and one a client sent, are drawn singly.
    assert ("instruction:ins-4", "question:ask-1", "asked") in made.edges
    assert ("name:detail.client:editor-7", "instruction:ins-5", "instructed") in made.edges
    assert not [n for n in made.nodes if n in ("instruction:ins-1", "instruction:ins-2")]

    alone = interaction_graph.picture(_rows(instructions=plain[:1]))
    assert MANY not in alone.nodes
    assert alone.nodes["instruction:ins-1"]["label"] == "do thing 1"
    assert alone.counted == {}


def test_questions_that_name_nobody_and_no_instruction_raised_are_one_node_with_their_count():
    """Mutations: count a question a name answered among them -- ada's answer
    is gone; draw `answered` for each of them whether or not an answer was
    read -- two are answered, not one."""
    made = interaction_graph.picture(_rows(
        asks=[_ask(1, "2026-01-01T00:00:01", "responded"),
              _ask(2, "2026-01-01T00:00:02", "pending", {"project": "beta"}),
              _ask(3, "2026-01-01T00:00:03", "responded"),
              _ask(4, "2026-01-01T00:00:04", "pending", {"issued_by": "grace"})],
        responses={"ask-1": _answer("2026-01-01T00:00:05", None),
                   "ask-3": _answer("2026-01-01T00:00:06", "ada")}))

    many = made.nodes[MANY_ASKED]
    assert (many["kind"], many["label"], many["count"]) == ("questions", "2 questions", 2)
    assert many["hover"].startswith(
        "2 questions that name nobody and no instruction raised, 1 of them answered -- ")
    assert made.counted == {"questions": 2}
    assert made.edges[(NOBODY, MANY_ASKED, "asked")]["count"] == 2
    assert made.edges[(MANY_ASKED, UNANSWERING, "answered")]["count"] == 1
    assert made.edges[(MANY_ASKED, "project:beta", "for")]["count"] == 1
    # A question a name answered, and one a name issued, are drawn singly.
    assert ("question:ask-3", "name:responded_by:ada", "answered") in made.edges
    assert ("name:context.issued_by:grace", "question:ask-4", "asked") in made.edges
    assert not [n for n in made.nodes if n in ("question:ask-1", "question:ask-2")]


def test_rows_that_share_both_ends_are_one_edge_with_their_count_and_a_width_from_it():
    """Mutations: set the count to 1 instead of adding to it -- every edge is
    one row; return `MIN_WIDTH` from `_width` whatever the count -- the widths
    are equal; say the kind alone on a counted edge's hover -- `×3` is gone;
    join a tool to the harness -- an edge no row states crosses the reading."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "voice", {"client": "c-1"}),
                      _instruction(2, "2026-01-01T00:00:02", "voice", {"client": "c-2"})],
        runs=[_run(n, "2026-01-01T00:00:03") for n in range(3)]))

    assert made.edges[(NOBODY, "tool:echo", "ran")]["count"] == 3
    assert made.edges[("way:voice", HARNESS, "recorded by")]["count"] == 2
    assert made.edges[("name:detail.client:c-1", "instruction:ins-1", "instructed")]["count"] == 1
    assert sum(1 for node in made.nodes.values() if node["kind"] == "tool") == 1
    assert not [key for key in made.edges if key[0] == "tool:echo"]

    graph = interaction_graph.as_graph(made)
    ran = graph.edges[NOBODY, "tool:echo", "ran"]
    one = graph.edges["name:detail.client:c-1", "instruction:ins-1", "instructed"]
    two = graph.edges["way:voice", HARNESS, "recorded by"]
    assert (ran["label"], ran["hover"], ran["count"], ran["size"]) == (
        "ran", "ran ×3", 3, interaction_graph.MAX_WIDTH)
    assert (one["label"], one["hover"], one["count"], one["size"]) == (
        "instructed", "instructed", 1, interaction_graph.MIN_WIDTH)
    assert interaction_graph.MIN_WIDTH < two["size"] < interaction_graph.MAX_WIDTH
    # A layout reads `weight` as a distance, so no edge carries one.
    assert all("weight" not in data for _, _, data in graph.edges(data=True))


def test_the_edges_of_the_reading_have_a_colour_each_and_every_other_edge_one_grey():
    """Mutations: colour every edge `OTHER_COLOUR` -- the reading does not
    stand out; give `way in` a colour of its own -- an edge off the reading
    is drawn as part of it."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "protocol", TURN)],
        asks=[_ask(1, "2026-01-01T00:00:02", "responded", {"instruction_id": "ins-1"})],
        responses={"ask-1": _answer("2026-01-01T00:00:03", "ada")},
        runs=[_run(1, "2026-01-01T00:00:04")]))
    graph = interaction_graph.as_graph(made)

    colours: dict[str, set[str]] = {}
    for _, _, kind, data in graph.edges(keys=True, data=True):
        colours.setdefault(data["color"], set()).add(kind)
    assert colours == {
        interaction_graph.COLOURS["instructed"]: {"instructed"},
        interaction_graph.COLOURS["asked"]: {"asked"},
        interaction_graph.COLOURS["answered"]: {"answered"},
        interaction_graph.OTHER_COLOUR: {"way in", "for", "turn", "in session",
                                         "recorded by", "ran"},
    }
    assert len(colours) == 4


def test_a_question_no_drawn_instruction_raised_keeps_its_issuer_and_its_project():
    """Mutations: draw a question's project only when an instruction is drawn
    for it -- beta is not drawn; draw `asked` from nobody for a question an
    undrawn instruction raised -- it gains an asker it does not have."""
    made = interaction_graph.picture(_rows(asks=[
        _ask(1, "2026-01-01T00:00:01", context={"issued_by": "grace", "project": "beta"}),
        _ask(2, "2026-01-01T00:00:02", context={"instruction_id": "not-read"}),
        _ask(3, "2026-01-01T00:00:03"),
    ]))

    assert _edges(made) == {
        ("name:context.issued_by:grace", "question:ask-1", "asked"),
        ("question:ask-1", "project:beta", "for"),
        (NOBODY, "question:ask-3", "asked"),
    }
    # Raised by an act on an instruction that is not drawn: drawn, with no
    # edge, and named as a consent.
    assert made.nodes["question:ask-2"]["label"] == "consent · pending"
    assert made.nodes["question:ask-1"]["label"] == "act on 1?"


def test_a_question_whose_answer_was_not_read_is_drawn_with_no_answer():
    """Mutation: draw `answered` to nobody when no answer was read -- a
    waiting question reads as answered by nobody."""
    made = interaction_graph.picture(_rows(asks=[
        _ask(1, "2026-01-01T00:00:01", "pending", {"issued_by": "grace"}),
        _ask(2, "2026-01-01T00:00:02", "responded", {"issued_by": "grace"}),
    ]))

    assert not [key for key in made.edges if key[2] == "answered"]
    assert UNANSWERING not in made.nodes
    assert made.nodes["question:ask-1"]["status"] == "pending"
    assert made.nodes["question:ask-2"]["status"] == "responded"


def test_rows_older_than_the_ones_drawn_are_counted_and_still_counted_on_their_way_in():
    """Mutations: report `not_drawn` as 0 -- the count is lost; count a way
    in only for a drawn instruction -- `recorded by` reads 2, not 5."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(n, f"2026-01-01T00:00:0{9 - n}", "voice") for n in range(5)],
        asks=[_ask(n, f"2026-01-01T00:00:0{9 - n}") for n in range(4)]), drawn=2)

    assert made.nodes[MANY]["label"] == "2 instructions"
    assert made.nodes[MANY_ASKED]["label"] == "2 questions"
    assert made.not_drawn == {"instructions": 3, "questions": 2}
    assert made.edges[("way:voice", HARNESS, "recorded by")]["count"] == 5
    assert made.edges[(NOBODY, MANY, "instructed")]["count"] == 2


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


def test_a_long_text_is_a_label_a_column_has_room_for_and_whole_on_hover_and_markup_is_escaped():
    """Mutations: label a node with its whole text -- the label is not cut;
    drop `html.escape` in `as_graph` -- the markup reaches the click panel."""
    text = "<b>rewrite</b> " + "the whole of the documentation " * 4
    instruction = _instruction(1, "2026-01-01T00:00:01")
    instruction["text"] = text
    made = interaction_graph.picture(_rows(instructions=[instruction]))

    node = made.nodes["instruction:ins-1"]
    assert node["label"] == "<b>rewrite</b> the whol…"
    assert len(node["label"]) == interaction_graph.LABEL
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
    assert "Not drawn: 2 older instructions." in said
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
                      _instruction(2, "2026-01-01T00:00:02", "voice"),
                      _instruction(3, "2026-01-01T00:00:03", "typed")],
        asks=[_ask(1, "2026-01-01T00:00:03", "responded", {"instruction_id": "ins-1"})],
        answers={"ask-1": _answer("2026-01-01T00:00:04", "ada")},
        runs=[_run(n, "2026-01-01T00:00:05") for n in range(3)])


@pytest.mark.parametrize(("query", "layout"), [
    ("", "Reading Order"), ("?layout=Reading_Order", "Reading_Order"),
    ("?layout=Kamada Kawai", "Kamada Kawai"), ("?layout=Circular", "Circular"),
])
def test_the_route_answers_a_graph_every_node_placed_and_styled(monkeypatch, query, layout):
    """Mutations: answer `kind: topology` in `metadata` -- the Interactions
    panel's strip would not show for it; add a node with no palette type --
    it has no shape; leave `names` out of `metadata` -- the canvas is not
    told to draw them; default the route's layout to `Kamada Kawai` -- the
    graph asked for with no layout is not in reading order."""
    found = _read(monkeypatch, _harness(), query)

    nodes = found["graph"]["nodes"]
    assert set(nodes) == {
        "harness", "nobody", "name:detail.client:editor-7", "instruction:ins-1",
        "question:ask-1", "name:responded_by:ada", "way:protocol", "way:voice",
        "way:typed", "tool:echo", "instructions:unnamed", "project:alpha",
        "chat:c-1", "session:s-1"}
    for node_id, node in nodes.items():
        held = node["metadata"]
        assert isinstance(held["x"], float) and isinstance(held["y"], float), node_id
        assert held["kind"] in interaction_graph.KIND_TO_TYPE, node_id
        assert held["shape"] and held["color"] and held["size"], node_id
        assert held["label_at"] in ("left", "right", "above", "below"), node_id
        assert node["label"], node_id
    edges = {(e["source"], e["target"], e["metadata"]["kind"]): e for e in found["graph"]["edges"]}
    answered = edges[("question:ask-1", "name:responded_by:ada", "answered")]
    assert answered["metadata"]["style"] == "solid"
    assert answered["metadata"]["color"] == interaction_graph.COLOURS["answered"]
    assert edges[("nobody", "tool:echo", "ran")]["metadata"]["style"] == "dashed"

    metadata = found["metadata"]
    assert metadata["kind"] == "interactions"
    assert metadata["names"] is True
    assert metadata["source"] == "http://harness/health"
    assert metadata["instance"]["pid"] == 4242
    assert metadata["layout"] == layout
    # The two unnamed instructions, the consent question and the tool runs name nobody.
    assert (metadata["rows"], metadata["unnamed"]) == (8, 6)
    assert metadata["counted"] == {"instructions": 2}
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
    assert "reading_order_layout" in found["remedy"]
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
