"""The harness's interactions drawn as rows: `/harness/gjgf?detail=rows`.

The reading alone -- who, the instruction, the question, who answered -- with
what else a row says in names and hovers, set close and wrapped into blocks.
`test_harness_graph.py` holds the graph with every node, and
`test_reading_order.py` where that one is placed.

Mutations each test was seen to fail under are named in its docstring.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from codecarto.services import interaction_graph, qmcp_client, reading_order
from codecarto.services.interaction_graph import ROWS
from codecarto.services.reading_order import DENSE_ROW, DENSE_X, blocks, breaks
from tests.test_harness_graph import NOBODY, TURN, _harness, _read, _rows
from tests.test_harness_interactions import _answer, _ask, _instruction, _run


def test_drawn_as_rows_a_turn_is_the_reading_alone_with_the_rest_in_its_name_and_hover():
    """Mutations: drop the early return in `_joined` -- the way in, the
    project, the chat and the session are nodes again; leave the way in out of
    the instruction's name -- the name is the text alone; leave `_FOLDED` empty
    -- the hover says no project, session, chat or turn."""
    made = interaction_graph.picture(_rows(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "protocol", TURN)],
        asks=[_ask(1, "2026-01-01T00:00:02", "responded", {"instruction_id": "ins-1"})],
        responses={"ask-1": _answer("2026-01-01T00:00:03", "ada", "hold")}), detail=ROWS)

    assert set(made.edges) == {
        ("name:detail.client:editor-7", "instruction:ins-1", "instructed"),
        ("instruction:ins-1", "question:ask-1", "asked"),
        ("question:ask-1", "name:responded_by:ada", "answered"),
    }
    assert {node["kind"] for node in made.nodes.values()} == {"name", "instruction", "question"}
    instruction = made.nodes["instruction:ins-1"]
    assert instruction["label"] == "protocol · do thing 1"
    for said in ("way in protocol", "project alpha", "session s-1", "chat c-1", "turn t-1"):
        assert said in instruction["hover"], said


def test_drawn_as_rows_a_tool_stands_in_the_instruction_column_and_a_project_is_on_a_hover():
    """Mutations: place a tool as the graph with every node does -- it stands
    under the rows, where a dense graph has no room; draw the `for` edge of a
    question no instruction raised -- its project is a node."""
    made = interaction_graph.picture(_rows(
        asks=[_ask(1, "2026-01-01T00:00:02", "pending", {"issued_by": "grace", "project": "beta"})],
        runs=[_run(1, "2026-01-01T00:00:04")]), detail=ROWS)

    assert (made.nodes["tool:echo"]["column"], made.nodes["tool:echo"]["label_at"]) == (
        "instruction", "above")
    assert set(made.edges) == {
        ("name:context.issued_by:grace", "question:ask-1", "asked"),
        (NOBODY, "tool:echo", "ran"),
    }
    assert "project beta" in made.nodes["question:ask-1"]["hover"]
    assert {node["column"] for node in made.nodes.values()} <= set(DENSE_X)


def _placed(rows) -> dict:
    return reading_order.place(
        interaction_graph.as_graph(interaction_graph.picture(rows, detail=ROWS)))


def test_rows_stand_closer_and_the_middle_columns_further_apart():
    """Mutation: place a graph that says it is dense as any other reading --
    the rows are a `ROW` apart and the columns `X`."""
    found = _placed(_rows(
        instructions=[_instruction(n, f"2026-01-01T00:00:0{n}", "protocol", {"client": f"c-{n}"})
                      for n in (1, 2)],
        asks=[_ask(n, f"2026-01-01T00:01:0{n}", "responded", {"instruction_id": f"ins-{n}"})
              for n in (1, 2)],
        responses={f"ask-{n}": _answer(f"2026-01-01T00:02:0{n}", "ada") for n in (1, 2)}))

    assert [found[node][0] for node in ("name:detail.client:c-1", "instruction:ins-1",
                                        "question:ask-1", "name:responded_by:ada")] == [
        DENSE_X["who"], DENSE_X["instruction"], DENSE_X["question"], DENSE_X["answerer"]]
    assert found["instruction:ins-2"][1] - found["instruction:ins-1"][1] == DENSE_ROW


def _asked_by(names: dict[str, int]) -> dict:
    """Questions each name issued, each answered by that name's own answerer."""
    asks, responses, n = [], {}, 0
    for name, count in names.items():
        for _ in range(count):
            n += 1
            asks.append(_ask(n, f"2026-01-01T00:00:{n % 60:02d}", "responded", {"issued_by": name}))
            responses[f"ask-{n}"] = _answer("2026-01-01T00:01:00", f"{name}-answers")
    return _placed(_rows(asks=asks, responses=responses))


def test_many_rows_wrap_into_blocks_and_one_names_rows_stay_in_one_block():
    """Mutations: have `blocks` answer one -- sixty rows are one column far
    taller than wide; start a block every `per` rows whatever name starts the
    row -- a name's questions stand in two blocks; place a node of a later
    block at the first block's columns -- every name stands at one x."""
    found = _asked_by({name: 15 for name in ("ada", "bob", "cy", "dee")})

    xs = [x for x, _ in found.values()]
    ys = [y for _, y in found.values()]
    assert max(xs) - min(xs) > max(ys) - min(ys)
    starts = {found[f"name:context.issued_by:{name}"][0] for name in ("ada", "bob", "cy", "dee")}
    assert len(starts) == 4
    by_name: dict[float, set[float]] = {}
    for n in range(1, 61):
        who_x = found[f"name:context.issued_by:{('ada', 'bob', 'cy', 'dee')[(n - 1) // 15]}"][0]
        by_name.setdefault(who_x, set()).add(found[f"question:ask-{n}"][0])
    # Each name's questions are one column, a question column right of the name.
    assert by_name == {x: {x + DENSE_X["question"]} for x in starts}
    assert len(set(found.values())) == len(found)


def test_a_few_rows_are_one_block():
    """Mutation: have `blocks` answer two for any rows -- seven rows are cut
    into two blocks a canvas has no need of."""
    found = _asked_by({"ada": 3, "bob": 4})

    assert {found[f"name:context.issued_by:{name}"][0] for name in ("ada", "bob")} == {0.0}
    assert (blocks(7, 900.0), blocks(0, 900.0)) == (1, 1)
    assert blocks(60, 900.0) > 1


def test_a_names_rows_start_the_next_block_whole_and_are_cut_only_when_too_many():
    """Mutations: treat no name's rows as whole -- fifteen rows after seven
    are cut at the eleventh; treat every name's rows as whole -- forty rows of
    one name are one block; never start a block before rows that overflow --
    the second name's rows run on in the first block."""
    assert breaks([2, 5, 15], 11) == {0, 7}
    assert breaks([40], 11) == {0, 11, 22, 33}
    assert breaks([8, 8], 11) == {0, 8}
    assert breaks([3, 4], 11) == {0}


def test_the_route_draws_rows_when_asked_and_refuses_a_detail_it_does_not_know(monkeypatch):
    """Mutations: have the route draw every node whatever `detail` says --
    the harness and the ways in are nodes; say `all` in `metadata` -- a client
    cannot tell which it was given; use the caveat of the graph with every
    node -- it says `recorded by`, which is not drawn."""
    found = _read(monkeypatch, _harness(), "?detail=rows")

    nodes = found["graph"]["nodes"]
    assert set(nodes) == {
        "nobody", "name:detail.client:editor-7", "instruction:ins-1", "question:ask-1",
        "name:responded_by:ada", "tool:echo", "instructions:unnamed"}
    assert nodes["instruction:ins-1"]["label"].startswith("protocol · ")
    for node_id, node in nodes.items():
        assert isinstance(node["metadata"]["x"], float), node_id
    assert found["metadata"]["detail"] == "rows"
    assert found["metadata"]["caveat"] == interaction_graph.ROWS_CAVEAT + "."
    assert "recorded by" not in found["metadata"]["caveat"]

    assert _read(monkeypatch, _harness())["metadata"]["detail"] == "all"
    monkeypatch.setattr(qmcp_client, "fetch", _harness())
    from codecarto.main import app
    assert TestClient(app).get("/harness/gjgf?detail=nonsense").status_code == 422
