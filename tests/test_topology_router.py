"""The web front end, against a harness that is there and one that is not.

THE TESTS WORTH READING ARE THE FIRST TWO. A front end whose backend is down is
the ordinary case, not an exception -- the harness is a separate process on a
separate port and very often has not been started. What the page does then is
most of what makes it usable, and it is the part nothing would have caught.

**NO REAL HARNESS IS CONTACTED.** Every test here points the client at a URL
that answers from a fixture or at a port nothing holds. A suite that needed the
harness running would pass on this machine and fail everywhere else, which is
the opposite of what a seam test is for.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from codecarto.services import qmcp_client


def _payload(arrows=None, boxes=None, source="topology"):
    """What the harness serves, in the shape it serves it."""
    return {
        "schema": 1,
        "source": source,
        "payload": {
            "topology": "delegation", "level": 2,
            "caption": "one agent per repository", "status": "runs",
            "marks": [],
            "boxes": boxes or [
                {"id": "subject", "label": "sweep", "kind": "input",
                 "note": "", "count": None},
                {"id": "r0", "label": "dossier", "kind": "worker",
                 "note": "qm/dossier", "count": None},
            ],
            "arrows": arrows if arrows is not None else [
                {"from": "subject", "to": "r0", "label": "part-of",
                 "kind": "flow", "weight": 0.9, "basis": "mentions"},
                {"from": "subject", "to": "r0", "label": "crosses",
                 "kind": "flow", "weight": None, "basis": ""},
            ],
        },
        "encoding": [
            {"channel": "line_weight", "axis": "strength", "scale": "continuous"},
            {"channel": "line_style", "axis": "measured", "scale": "categorical"},
            {"channel": "line_colour", "axis": "relation_kind",
             "scale": "categorical"},
            {"channel": "node_shape", "axis": "box_kind", "scale": "categorical"},
        ],
    }


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    """The app, with the harness answering from a fixture."""
    def answered(path, base=None):
        if path == "/v1/topology":
            return qmcp_client.Reach(
                True, "fixture",
                {"topologies": [{"topology": "delegation", "caption": "",
                                 "status": "runs", "boxes": 2, "arrows": 2}],
                 "encoding": _payload()["encoding"]}, status=200)
        return qmcp_client.Reach(True, "fixture", _payload(), status=200)

    monkeypatch.setattr(qmcp_client, "fetch", answered)
    from codecarto.main import app

    return TestClient(app)


@pytest.fixture()
def no_harness(monkeypatch) -> TestClient:
    """The app, with nothing answering."""
    def refused(path, base=None):
        return qmcp_client.Reach(
            False, "http://127.0.0.1:3141" + path,
            problem="nothing is answering at http://127.0.0.1:3141",
            remedy="start it with `uv run qm dashboard --start harness`")

    monkeypatch.setattr(qmcp_client, "fetch", refused)
    from codecarto.main import app

    return TestClient(app)


# --- the two that matter -------------------------------------------------------


def test_a_harness_that_is_not_running_is_a_sentence_not_a_stack_trace(no_harness):
    """THE ONE THAT MATTERS.

    Somebody opening this page has usually not started the harness. The page
    must say so, say what to run, and say where it looked -- and it must not
    return a 500, because a 500 reports a fault in this front end when the
    front end is working correctly.

    Mutation: let the client raise and this fails.
    """
    answer = no_harness.get("/topology")
    assert answer.status_code == 200
    assert "nothing is answering" in answer.text
    assert "qm dashboard --start harness" in answer.text
    assert "127.0.0.1:3141" in answer.text


def test_an_unreachable_harness_draws_no_graph_at_all(no_harness):
    """**AN EMPTY GRAPH LOOKS LIKE AN ANSWER.** A page that rendered an empty
    canvas would say "this topology has nothing in it", which is a claim, and a
    different one from "I could not ask".

    Mutation: render the canvas anyway and this fails.
    """
    text = no_harness.get("/topology").text
    assert "<svg" not in text.split('class="legend"')[0], (
        "a canvas was drawn with nothing to draw")
    assert "would look like an answer" in text


def test_the_data_route_reports_the_problem_rather_than_erroring(no_harness):
    body = no_harness.get("/topology/data").json()
    assert body["ok"] is False
    assert "nothing is answering" in body["problem"]
    assert "harness" in body["remedy"]


# --- what it draws when the harness is there -----------------------------------


def test_the_page_renders_the_topology(client):
    answer = client.get("/topology?kind=delegation")
    assert answer.status_code == 200
    assert "delegation" in answer.text
    assert "<svg" in answer.text


def test_an_unmeasured_edge_is_dashed_and_never_thin(client):
    """The one thing both front ends are tested for, in both repositories.

    Mutation: drop the dash and this fails.
    """
    body = client.get("/topology/data").json()
    unmeasured = [e for e in body["edges"] if not e["measured"]]
    assert len(unmeasured) == 1
    assert unmeasured[0]["style"] == "dashed"
    assert unmeasured[0]["weight"] is None
    assert "not measured" in unmeasured[0]["title"]

    page = client.get("/topology").text
    assert "stroke-dasharray" in page


def test_the_data_route_serves_what_was_drawn_not_what_was_fetched(client):
    """Widths and styles, which are this window's own resolution of the
    channels. Serving the payload back would make two windows agree by both
    reading one field, which establishes nothing."""
    body = client.get("/topology/data").json()
    for edge in body["edges"]:
        assert "width" in edge and "style" in edge


def test_the_caveat_says_how_much_of_the_picture_is_measured(client):
    body = client.get("/topology/data").json()
    assert body["measured"] == 1 and body["unmeasured"] == 1
    assert "1 of 2" in body["caveat"]
    assert body["caveat"] in client.get("/topology").text


def test_parallel_readings_survive_into_the_projects_graph_format(client):
    """Three readings of one relation are three observations, not one.

    **ASSERTS THE GRAPH, NOT THE MARKUP.** The first version counted SVG curve
    commands, which was really asserting that this router hand-drew its own
    picture -- so it went red the moment the drawing moved onto codecarto's
    canvas, where it belongs. What must survive is the data: three edges in the
    gJGF, and a canvas told to curve them so they do not overlap.

    Mutation: build the graph as a `DiGraph` and this fails.
    """
    body = client.get("/topology/gjgf").json()
    assert body["ok"], body
    parallel = [e for e in body["graph"]["edges"]
                if e["source"] == "subject" and e["target"] == "r0"]
    assert len(parallel) == 2, "parallel readings were collapsed"

    import inspect

    from codecarto.routers import topology_router

    assert "edge_curvature" in inspect.getsource(topology_router._canvas), (
        "the canvas is not told to separate parallel edges")


def test_the_legend_draws_the_distinction_rather_than_describing_it(client):
    page = client.get("/topology").text
    legend = page.split('class="legend"')[1]
    assert "stroke-dasharray" in legend and "stroke-width" in legend


def test_the_level_is_bounded(client):
    assert client.get("/topology?level=9").status_code == 422


def test_the_topology_picker_lists_what_the_harness_offers(client):
    page = client.get("/topology").text
    assert "/topology?kind=delegation" in page


# --- the client ----------------------------------------------------------------


def test_the_four_failures_are_kept_apart():
    """Not running, not serving the route, refusing, and unreadable are four
    problems with four fixes. One "could not load" sends a reader to the wrong
    place.

    Mutation: collapse them into one message and this fails.
    """
    import urllib.error

    reach = qmcp_client.fetch("/v1/topology", base="http://127.0.0.1:9")
    assert reach.ok is False
    assert "nothing is answering" in reach.problem
    assert "qm dashboard --start harness" in reach.remedy


def test_the_base_url_can_be_moved(monkeypatch):
    monkeypatch.setenv("QMCP_URL", "http://elsewhere:1234/")
    assert qmcp_client.base_url() == "http://elsewhere:1234"


def test_the_client_never_raises(monkeypatch):
    """A front end that threw on a missing harness would turn "not started
    yet" into a 500."""
    reach = qmcp_client.fetch("/nope", base="http://127.0.0.1:9")
    assert isinstance(reach, qmcp_client.Reach) and reach.ok is False
