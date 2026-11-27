"""Reading order: where `reading_order.place` puts the nodes of a graph.

The graphs are the ones `interaction_graph` makes of invented rows, so a
place asserted here is a place the Interactions graph is drawn at, and small
hand-built graphs for the placing of any other graph.

Mutations each test was seen to fail under are named in its docstring.
"""

from __future__ import annotations

import itertools

import networkx as nx
import pytest

from codecarto.models.plot_data import PlotOptions
from codecarto.services import interaction_graph, reading_order
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.services.position_service import Positions
from codecarto.services.reading_order import (BENEATH_GAP, BENEATH_ROOM, NAME_GAP, OVER_GAP, ROW,
                                              UNDER_GAP, X)
from tests.test_harness_graph import HARNESS, MANY, NOBODY, TURN, UNANSWERING, _rows
from tests.test_harness_interactions import _answer, _ask, _instruction, _run


def _turn(n: int, client: str, by: str | None, chat: bool = True) -> tuple[dict, dict, dict]:
    """A protocol turn: its instruction, its consent, and the consent's answer."""
    detail = {**TURN, "client": client, "session": f"s-{n}", "chat": f"c-{n}"}
    if not chat:
        detail = {"client": client}
    return (_instruction(n, f"2026-01-01T00:00:0{n}", "protocol", detail),
            _ask(n, f"2026-01-01T00:01:0{n}", "responded", {"instruction_id": f"ins-{n}"}),
            _answer(f"2026-01-01T00:02:0{n}", by))


def _placed(rows) -> dict:
    return reading_order.place(interaction_graph.as_graph(interaction_graph.picture(rows)))


def _two_turns(chat: bool = True) -> dict:
    first, second = _turn(1, "editor-one", "ada", chat), _turn(2, "terminal-two", "bob", chat)
    return _placed(_rows(instructions=[first[0], second[0]], asks=[first[1], second[1]],
                         responses={"ask-1": first[2], "ask-2": second[2]}))


def test_a_turn_is_a_straight_line_from_left_to_right():
    """Mutations: swap the question and answerer columns in `X` -- the answer
    is left of its question; place an instruction at its first row less one
    `ROW` -- it is off its turn's line."""
    found = _two_turns(chat=False)

    for n, client, by in ((1, "editor-one", "ada"), (2, "terminal-two", "bob")):
        path = [found[f"name:detail.client:{client}"], found[f"instruction:ins-{n}"],
                found[f"question:ask-{n}"], found[f"name:responded_by:{by}"]]
        assert [x for x, _ in path] == sorted(x for x, _ in path), path
        assert len({x for x, _ in path}) == 4, path
        assert len({y for _, y in path}) == 1, path
    assert [x for x, _ in (found["name:detail.client:editor-one"], found["instruction:ins-1"],
                           found["question:ask-1"], found["name:responded_by:ada"])] == [
        X["who"], X["instruction"], X["question"], X["answerer"]]
    # The second turn is the next row down.
    assert found["instruction:ins-2"][1] - found["instruction:ins-1"][1] == ROW


def test_a_turns_chat_and_session_are_tucked_under_it_and_the_next_row_starts_lower():
    """Mutations: leave no room under a row that carries a tucked node -- the
    next row is one `ROW` down and its name lies on the chat's; put a session
    in its chat's column -- the two are one on top of the other."""
    found = _two_turns()

    x, y = found["instruction:ins-1"]
    assert found["chat:c-1"] == (x, y + BENEATH_GAP)
    assert found["session:s-1"] == (X["question"], y + BENEATH_GAP)
    assert found["instruction:ins-2"][1] - y == ROW + BENEATH_ROOM
    assert found["chat:c-2"] == (X["instruction"], found["instruction:ins-2"][1] + BENEATH_GAP)


def test_named_rows_come_first_then_rows_of_nobody_then_counted_rows():
    """Mutations: order the rows by name alone, without `rank` -- the counted
    instructions stand above grace; put rows with no instruction before rows
    with one -- grace's question stands above the turns."""
    turn = _turn(1, "zed", "ada", chat=False)
    found = _placed(_rows(
        instructions=[turn[0],
                      _instruction(2, "2026-01-01T00:00:02", "voice"),
                      _instruction(3, "2026-01-01T00:00:03", "voice"),
                      _instruction(4, "2026-01-01T00:00:04", "voice")],
        asks=[turn[1],
              _ask(5, "2026-01-01T00:00:05", context={"issued_by": "grace"}),
              _ask(6, "2026-01-01T00:00:06", "responded", {"instruction_id": "ins-4"})],
        responses={"ask-1": turn[2], "ask-6": _answer("2026-01-01T00:00:07", "ada")}))

    down = [found[node][1] for node in (
        "instruction:ins-1",      # a named turn
        "question:ask-5",         # a named question, no instruction
        "instruction:ins-4",      # nobody's instruction, with its consent
        MANY)]                    # the counted instructions
    assert down == sorted(down) and len(set(down)) == 4, down
    assert [found[node][1] for node in ("instruction:ins-1", "question:ask-5")] == [0.0, ROW]


def test_a_name_in_several_rows_stands_at_their_middle_and_names_keep_apart():
    """Mutations: place a name at its first row -- ada is level with one turn
    and not between the two; spread names by nothing -- two names that want
    one height are drawn on one spot."""
    first, second = _turn(1, "amy", "ada", chat=False), _turn(2, "ben", "ada", chat=False)
    found = _placed(_rows(instructions=[first[0], second[0]], asks=[first[1], second[1]],
                          responses={"ask-1": first[2], "ask-2": second[2]}))
    assert found["name:responded_by:ada"] == (X["answerer"], ROW / 2)

    # ada answers the first and third turns and bob the second: both want the
    # height of the second row.
    turns = [_turn(1, "amy", "ada", chat=False), _turn(2, "ben", "bob", chat=False),
             _turn(3, "cat", "ada", chat=False)]
    placed = _placed(_rows(instructions=[turn[0] for turn in turns],
                           asks=[turn[1] for turn in turns],
                           responses={f"ask-{n}": turn[2] for n, turn in enumerate(turns, 1)}))
    assert placed["question:ask-2"][1] == ROW
    heights = sorted((placed["name:responded_by:ada"][1], placed["name:responded_by:bob"][1]))
    assert heights == [ROW, ROW + NAME_GAP]


def test_what_is_above_the_rows_is_right_of_the_instruction_column_and_under_the_head():
    """Mutations: start the nodes above the rows at the instruction column --
    an edge up to the first runs along the column through its nodes; give
    each the same room whatever its name -- a long name runs into the next;
    put the head over the first of them -- it is not over their middle."""
    found = _placed(_rows(instructions=[
        _instruction(1, "2026-01-01T00:00:01", "voice", {"client": "a"}),
        _instruction(2, "2026-01-01T00:00:02", "a-very-long-way-in-name", {"client": "b"}),
        _instruction(3, "2026-01-01T00:00:03", "typed", {"client": "c"})]))

    ways = [found[f"way:{name}"] for name in ("a-very-long-way-in-name", "typed", "voice")]
    assert all(y == -OVER_GAP for _, y in ways)
    assert [x for x, _ in ways] == sorted(x for x, _ in ways)
    assert ways[0][0] > X["instruction"]
    # The long name is given the room it needs; the short ones the least.
    assert ways[1][0] - ways[0][0] > ways[2][0] - ways[1][0] == reading_order.LEAST
    head = found[HARNESS]
    assert head[1] < -OVER_GAP
    assert ways[0][0] < head[0] < ways[-1][0]


def test_what_is_below_the_rows_is_under_the_end_of_the_reading_that_points_at_it():
    """Mutations: lay what the start of the reading points at with the rest --
    the tool is not under the column of whoever ran it; put the nodes below
    one `ROW` under the last -- they are in the rows, not under them; start
    the rest at the instruction column -- the edge down to the project runs
    along the column."""
    found = _placed(_rows(
        instructions=[_instruction(1, "2026-01-01T00:00:01", "voice", {"client": "a"},
                                   project="alpha")],
        runs=[_run(1, "2026-01-01T00:00:02")]))

    lowest = max(found[node][1] for node in ("instruction:ins-1", NOBODY))
    assert found["tool:echo"] == (X["who"], lowest + UNDER_GAP)
    assert found["project:alpha"][1] == lowest + UNDER_GAP
    assert found["project:alpha"][0] > X["instruction"]
    assert found["project:alpha"][0] - found["tool:echo"][0] >= reading_order.LEAST


def test_no_two_nodes_of_a_reading_share_a_place_and_the_ends_of_an_edge_never_do():
    """Mutation: give every node above the rows one x -- the ways are stacked."""
    turn = _turn(1, "editor-one", None)
    found = _placed(_rows(
        instructions=[turn[0]] + [_instruction(n, f"2026-01-01T00:00:0{n}", source)
                                  for n, source in ((2, "voice"), (3, "typed"), (4, "page"))],
        asks=[turn[1], _ask(5, "2026-01-01T00:00:05"), _ask(6, "2026-01-01T00:00:06"),
              _ask(7, "2026-01-01T00:00:07", "responded", {"issued_by": "grace"})],
        responses={"ask-1": turn[2], "ask-7": _answer("2026-01-01T00:00:08", "ada")},
        runs=[_run(1, "2026-01-01T00:00:09")]))

    assert {UNANSWERING, NOBODY, MANY} <= set(found)
    for (a, where_a), (b, where_b) in itertools.combinations(found.items(), 2):
        assert where_a != where_b, (a, b)
        apart = abs(where_a[0] - where_b[0]) + abs(where_a[1] - where_b[1])
        assert apart >= NAME_GAP, (a, b, where_a, where_b)


def test_a_graph_that_names_no_column_is_placed_along_its_arrows():
    """Mutations: never move a node right of what points at it -- every node
    is in the first column; put what is on a cycle in the first column -- it
    is not right of what leads into it; put every node of a column on one row
    -- siblings share a place."""
    graph = nx.DiGraph()
    graph.add_edges_from([("a", "b"), ("b", "c"), ("a", "c"), ("a", "d")])
    found = reading_order.place(graph)
    assert [found[node][0] for node in "abc"] == [0.0, reading_order.STEP, 2 * reading_order.STEP]
    # `c` is one column right of `b`, the furthest of the two that point at it.
    assert found["d"][0] == found["b"][0] and found["d"][1] != found["b"][1]

    looped = nx.DiGraph()
    looped.add_edges_from([("a", "b"), ("b", "c"), ("c", "b"), ("x", "x")])
    placed = reading_order.place(looped)
    assert set(placed) == {"a", "b", "c", "x"}
    assert placed["b"][0] == placed["c"][0] > placed["a"][0]
    assert len(set(placed.values())) == 4
    assert reading_order.place(nx.DiGraph()) == {}


def test_a_graph_with_one_node_that_names_no_column_is_not_placed_as_a_reading():
    """Mutation: place a graph as a reading when any node names a column --
    the node that names none has no place and the layout raises."""
    graph = nx.DiGraph()
    graph.add_node("a", column="who", label="a")
    graph.add_node("b")
    graph.add_edge("a", "b")
    assert reading_order.place(graph) == {"a": (0.0, 0.0), "b": (reading_order.STEP, 0.0)}


@pytest.mark.parametrize("spelling", ["Reading Order", "Reading_Order", "reading_order_layout"])
def test_the_layout_is_registered_and_the_serializer_places_nodes_where_it_says(spelling):
    """Mutations: leave the layout out of `add_custom_layouts` -- asking for
    it by name raises; return the places undivided from
    `reading_order_layout` -- every node is a hundred times too far out."""
    assert "reading_order_layout" in Positions(True, True).get_layout_names()
    turn = _turn(1, "editor-one", "ada")
    made = interaction_graph.picture(_rows(instructions=[turn[0]], asks=[turn[1]],
                                           responses={"ask-1": turn[2]}))
    gjgf = interaction_graph.as_gjgf(made, PlotOptions(layout=spelling))
    wanted = reading_order.place(interaction_graph.as_graph(made))

    for node_id, node in gjgf["nodes"].items():
        got = (node["metadata"]["x"], node["metadata"]["y"])
        assert got == pytest.approx(wanted[node_id]), node_id
    # And any other graph can be asked for it by name.
    plain = nx.DiGraph([("a", "b")])
    drawn = GraphSerializer.serialize_to_gjgf(plain, PlotOptions(layout=spelling))
    assert drawn["nodes"]["b"]["metadata"]["x"] == pytest.approx(reading_order.STEP)
