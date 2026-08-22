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



def results(response) -> dict:
    """The inner document of codecarto's standard envelope.

    Every route here answers `{status, message, results}`. These tests read the
    inner document directly until the topology routes were moved onto the house
    style, and then failed with `KeyError` -- which looked like a broken route
    and was a test reading the wrong shape. One helper, so the next envelope
    change is one edit.
    """
    body = response.json()
    assert "results" in body, f"not the standard envelope: {sorted(body)}"
    return body["results"]


def status_of(response) -> int:
    """The envelope's own status, which is not the HTTP status.

    A reachable route reporting an unreachable *harness* answers HTTP 200 with
    an envelope status of 503 -- the front end is working, the thing behind it
    is not, and collapsing those into one number would lose the distinction.
    """
    return int(response.json().get("status", 200))


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
    answer = no_harness.get("/topology/data")
    assert answer.status_code == 200, "the front end itself is fine"
    # **STATUS 200, WITH THE PROBLEM IN `results`.** An envelope status of 503
    # would say *this service* is unavailable, which is false -- and the browser
    # client treats any status but 200 as a hard error, parsing the message with
    # the message parser, which raises on every message not in that
    # exact shape. So a non-200 envelope arrived as a `TypeError` with no detail.
    assert status_of(answer) == 200, "this route worked; the harness did not"
    body = results(answer)
    assert body["unreachable"] is True
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
    body = results(client.get("/topology/data"))
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
    body = results(client.get("/topology/data"))
    for edge in body["edges"]:
        assert "width" in edge and "style" in edge


def test_the_caveat_says_how_much_of_the_picture_is_measured(client):
    body = results(client.get("/topology/data"))
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
    body = results(client.get("/topology/gjgf"))
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


# --- the application, and where its API is -------------------------------------


def test_the_root_serves_the_application_when_there_is_one(client):
    """**A REDIRECT TO `/docs` IS NOT A FRONT END.**

    Opening this port used to give an API schema, which is correct and is not
    what anybody who was told "the web front end is up" meant.

    Mutation: redirect unconditionally and this fails.
    """
    from codecarto.routers.app_router import build_present

    answer = client.get("/", follow_redirects=False)
    expected = "/app" if build_present() else "/docs"
    assert answer.headers["location"] == expected


def test_the_application_is_told_where_its_api_is(client):
    """**THE BUNDLE MUST NOT CARRY A PORT.** `appsettings.json` said 8000; the
    container publishes 2020 and the trio runs 2718, so a build could only
    ever talk to one machine's guess. The server injects the origin it served
    from, and `ConfigManager` prefers it over everything else.

    Mutation: stop injecting the meta tag and this fails.
    """
    from codecarto.routers.app_router import build_present

    if not build_present():
        import pytest

        pytest.skip("no web build on disk; `cd web && npm run build`")

    page = client.get("/app").text
    assert 'name="codecarto-api"' in page
    # Before the module script, or the bundle never sees it.
    assert page.index('name="codecarto-api"') < page.index("<script")


def test_a_missing_build_is_a_sentence_rather_than_a_404(monkeypatch, client):
    """Somebody who has not run `npm run build` should be told which command
    to run, and that a dev server is the other option."""
    from codecarto.routers import app_router

    monkeypatch.setattr(app_router, "build_present", lambda: False)
    page = client.get("/app").text
    assert "not built" in page
    assert app_router.BUILD_COMMAND in page
    assert "npm run dev" in page


def test_available_lists_what_the_harness_offers_and_what_can_lay_it_out(client):
    """A picker fills itself from this. It must not need a drawing first."""
    body = results(client.get("/topology/available"))
    assert body["topologies"]
    assert body["layouts"], "no layout can be chosen"
    assert "Kamada Kawai" in body["layouts"] or "Spring" in body["layouts"]


def test_the_client_gets_the_inner_document_not_the_envelope(client):
    """**THE BUG THAT KEPT THE PANEL ON "ASKING".**

    `RequestHandler.handleResponse` returns `responseData.results`, so the
    browser never sees `{status, message, results}` at all. A service written
    against the outer shape read `.results` off the results, got `undefined`,
    and threw on the next access — with a successful 200 in the network log.

    This test pins the contract from the server side: whatever a route puts in
    `results` is exactly what the browser receives.
    """
    body = results(client.get("/topology/available"))
    assert "topologies" in body and "layouts" in body
    assert "results" not in body, "the envelope is nested twice"


def test_an_unreachable_harness_is_flagged_inside_results(no_harness):
    """The browser cannot see the envelope status, so the flag has to be in the
    document. Without it a front end cannot tell a problem from a graph.

    Mutation: drop `unreachable` and this fails.
    """
    for route in ("/topology/available", "/topology/gjgf", "/topology/data"):
        body = results(no_harness.get(route))
        assert body.get("unreachable") is True, f"{route} does not say so"
        assert body["problem"] and body["where"]


def test_available_still_offers_layouts_when_the_harness_is_down(no_harness):
    """Layouts are this server's own; they do not depend on the harness. A
    picker that emptied itself because something else was down would be
    reporting the wrong outage."""
    body = results(no_harness.get("/topology/available"))
    assert body["topologies"] == []
    assert body["layouts"], "this server can still lay a graph out"
