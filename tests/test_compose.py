"""The designer's composing routes: saved designs read, one design relayed once.

The harness is stood in for at `qmcp_client.fetch` and `qmcp_client.send`, the
two functions that reach it, so every test here runs the real routes and the
real service above those calls. `test_a_refusal_keeps_the_harnesss_detail`
stands lower, at `urlopen`, to hold the client to what it hands the service.

Mutations each test was seen to fail under are named in its docstring.
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest
from fastapi.testclient import TestClient

from codecarto.services import compose_service, qmcp_client
from codecarto.services.qmcp_client import Reach

BASE = "http://harness"
HERE = ("127.0.0.1", 50000)


def _design(name: str, kind: str = "delegation", **config) -> dict:
    return {"id": f"id-{name}", "project": "alpha", "name": name, "description": f"about {name}",
            "topology_type": kind, "version": "1.0.0", "config": config,
            "address": f"qm://alpha/topology/{name}",
            "capability": {"status": "runs", "refusal": None}}


HELD = {"schema": 1, "project": "alpha", "count": 2, "topologies": [
    _design("intake", components=[{"name": "reader", "route_terms": []}]),
    _design("review", "crosscheck", compose=["intake", "elsewhere/gone"]),
]}
PARTS = {"schema": 1, "project": "alpha", "components": [
    {"name": "reader", "description": "reads a page", "instruction": "not shown"}]}


class Harness:
    """Answers reads as told, records every read and every post."""

    def __init__(self, designs=HELD, components=PARTS, down=False, saved=None, refuse=None):
        self.designs, self.components, self.down = designs, components, down
        self.saved, self.refuse = saved, refuse
        self.read: list[str] = []
        self.posted: list[tuple[str, dict]] = []

    def fetch(self, path, base=None, remedy_404=None):
        self.read.append(path)
        where = BASE + path
        if self.down:
            return Reach(False, where, problem=f"nothing is answering at {BASE}",
                         remedy="start it with `uv run qm dashboard --start harness`")
        found = self.designs if path.startswith(compose_service.DESIGNS) else self.components
        if path.startswith(compose_service.SCHEMA):
            found = {"schema": 1, "topology": path.rsplit("/", 1)[1],
                     "json_schema": {"properties": {"compose": {"type": "array"}}}}
        if found == 404:
            return Reach(False, where, status=404, remedy=remedy_404 or "",
                         problem=f"the harness is running but does not serve {path}")
        return Reach(True, where, found, status=200)

    def send(self, path, payload, base=None, remedy_404=None):
        self.posted.append((path, payload))
        where = BASE + path
        if self.down:
            return Reach(False, where, problem=f"nothing is answering at {BASE}", remedy="start it")
        if self.refuse is not None:
            status, detail = self.refuse
            return Reach(False, where, status=status, detail=detail,
                         problem=f"the harness refused: {status} {detail}")
        return Reach(True, where, self.saved or _design(payload["name"], payload["topology_type"]),
                     status=201)


@pytest.fixture()
def harness(monkeypatch):
    def stand(**how) -> Harness:
        made = Harness(**how)
        monkeypatch.setattr(qmcp_client, "fetch", made.fetch)
        monkeypatch.setattr(qmcp_client, "send", made.send)
        return made
    return stand


def _client(here: bool = True) -> TestClient:
    from codecarto.main import app

    if here:
        return TestClient(app, base_url="http://127.0.0.1:2718", client=HERE)
    return TestClient(app, base_url="http://192.168.1.20:2718", client=("192.168.1.30", 50000))


BODY = {"name": "triage", "topology_type": "delegation", "description": "routes work",
        "config": {"compose": ["intake"], "load_balance": False}}


# --- reading what the harness holds ---------------------------------------------

def test_the_designs_and_components_are_the_harnesss_rows_for_the_project_asked(harness):
    """Mutation: drop the project from the read -- the harness is asked for
    its own default."""
    stood = harness()
    results = _client().get("/designer/designs", params={"project": "al pha"}).json()["results"]
    assert results["designs"] == HELD["topologies"]
    assert results["components"] == PARTS["components"]
    assert results["project"] == "alpha"
    assert results["saving"]["available"] is True
    assert results["components_read"]["read"] is True
    assert stood.read == ["/v1/topologies?project=al%20pha", "/v1/topology-components?project=al%20pha"]
    assert stood.posted == []


def test_a_harness_that_is_not_answering_is_unreachable_and_asked_once(harness):
    """Mutation: read the components after the designs found nothing answering."""
    stood = harness(down=True)
    for route in ("/designer/designs", "/designer/composition/gjgf"):
        stood.read.clear()
        results = _client().get(route).json()["results"]
        assert results.get("unreachable") is True, route
        assert "--start harness" in results["remedy"]
        assert "designs" not in results and "graph" not in results
        assert stood.read == ["/v1/topologies"], route


def test_a_harness_without_the_routes_or_with_another_answer_is_unreadable(harness):
    """Mutations: pass no `remedy_404` -- the remedy is the topology routes'
    sentence about an archive; drop the `topologies` check -- an answer with
    no list reads as a harness holding no design."""
    harness(designs=404)
    missing = _client().get("/designer/designs").json()["results"]
    assert missing.get("unreadable") is True
    assert "does not serve saved designs" in missing["remedy"]
    harness(designs={"status": "ok"})
    other = _client().get("/designer/designs").json()["results"]
    assert other.get("unreadable") is True and "no list of `topologies`" in other["problem"]


def test_components_that_were_not_read_leave_the_designs_listed(harness):
    """Mutation: answer the components' problem for the whole reading -- no
    design is listed."""
    harness(components=404)
    results = _client().get("/designer/designs").json()["results"]
    assert [row["name"] for row in results["designs"]] == ["intake", "review"]
    assert results["components"] == []
    assert results["components_read"]["read"] is False
    assert "does not serve" in results["components_read"]["problem"]


def test_the_schema_is_the_harnesss_and_one_with_no_schema_in_it_is_a_sentence(harness, monkeypatch):
    """Mutations: pass the kind through unquoted -- `odd kind` is asked for
    with a space in the address; drop the `json_schema` check -- an answer
    without one reaches the form as a schema."""
    stood = harness()
    results = _client().get("/designer/schema/odd kind").json()["results"]
    assert results["json_schema"] == {"properties": {"compose": {"type": "array"}}}
    assert results["topology"] == "odd%20kind"
    assert stood.read == ["/v1/topology/schema/odd%20kind"]
    monkeypatch.setattr(qmcp_client, "fetch",
                        lambda path, base=None, remedy_404=None: Reach(True, BASE + path, {"schema": 1}, status=200))
    other = _client().get("/designer/schema/delegation").json()["results"]
    assert other.get("unreadable") is True and "no `json_schema`" in other["problem"]


# --- saving ---------------------------------------------------------------------

def test_a_design_is_posted_once_as_filled_in_and_the_harnesss_row_comes_back(harness):
    """Mutations: send twice -- two posts are recorded; drop `config` from the
    payload -- the references are not sent; send an empty `description` --
    the payload carries a key nobody filled."""
    stood = harness()
    results = _client().post("/designer/designs", json=BODY).json()["results"]
    assert results["saved"] is True
    assert results["design"]["name"] == "triage"
    assert results["design"]["address"] == "qm://alpha/topology/triage"
    assert stood.posted == [("/v1/topologies", {
        "name": "triage", "topology_type": "delegation", "description": "routes work",
        "config": {"compose": ["intake"], "load_balance": False}})]
    stood.posted.clear()
    _client().post("/designer/designs", json={**BODY, "description": "  ", "project": " alpha "})
    assert "description" not in stood.posted[0][1]
    assert stood.posted[0][1]["project"] == "alpha"


def test_a_design_from_another_machine_is_not_relayed_and_the_reading_says_so(harness):
    """Mutation: pass "" as the standing in the save route -- a request from
    another machine is posted to the harness."""
    stood = harness()
    away = _client(here=False)
    results = away.post("/designer/designs", json=BODY).json()["results"]
    assert results["refused"] is True
    assert "a design is not saved from here" in results["problem"]
    assert stood.posted == []
    reading = away.get("/designer/designs").json()["results"]
    assert reading["saving"]["available"] is False
    assert "another machine" in reading["saving"]["problem"] or "other than this machine" in reading["saving"]["problem"]
    assert [row["name"] for row in reading["designs"]] == ["intake", "review"]


def test_a_design_with_no_name_or_no_kind_is_not_sent_and_says_which(harness):
    """Mutation: send whatever was typed -- a blank name is posted."""
    stood = harness()
    results = _client().post("/designer/designs", json={"name": " ", "config": {}}).json()["results"]
    assert results["refused"] is True
    assert {error["field"] for error in results["errors"]} == {"name", "topology_type"}
    assert stood.posted == []


def test_the_harnesss_refusal_puts_each_message_beside_its_field(harness):
    """Mutations: join the errors into one sentence -- no message names a
    field; leave off the `config` prefix -- a message about a configuration
    field stands beside nothing."""
    harness(refuse=(422, {"where": "config", "errors": [
        {"loc": ["max_queue_size"], "msg": "Input should be greater than or equal to 10"},
        {"loc": ["components", 0, "name"], "msg": "Field required"}]}))
    results = _client().post("/designer/designs", json=BODY).json()["results"]
    assert results["refused"] is True and results["status"] == 422
    assert results["errors"] == [
        {"field": "config.max_queue_size", "message": "Input should be greater than or equal to 10"},
        {"field": "config.components.0.name", "message": "Field required"}]
    harness(refuse=(422, {"where": "design", "errors": [{"loc": ["name"], "msg": "bad name"}]}))
    named = _client().post("/designer/designs", json=BODY).json()["results"]
    assert named["errors"] == [{"field": "name", "message": "bad name"}]


def test_a_refusal_that_is_a_sentence_is_about_the_design_as_a_whole(harness):
    """Mutation: drop a detail that is not a document -- a name already taken
    is refused with no reason."""
    harness(refuse=(409, "a design named 'triage' exists in project 'alpha'"))
    results = _client().post("/designer/designs", json=BODY).json()["results"]
    assert results["status"] == 409
    assert results["errors"] == [{"field": "", "message": "a design named 'triage' exists in project 'alpha'"}]


def test_a_harness_that_stops_answering_during_a_save_is_unreachable(harness):
    """Mutation: call every failed post a refusal -- a reader is told the
    harness judged a design it never received."""
    harness(down=True)
    results = _client().post("/designer/designs", json=BODY).json()["results"]
    assert results.get("unreachable") is True and "refused" not in results


def test_a_refusal_keeps_the_harnesss_detail(monkeypatch):
    """Mutation: keep only `str(detail)` on the `Reach` -- the service is
    handed a sentence and cannot tell which field a message is about."""
    detail = {"where": "config", "errors": [{"loc": ["num_checkers"], "msg": "too few"}]}

    def refuse(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 422, "refused", {},
                                     io.BytesIO(json.dumps({"detail": detail}).encode()))

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    reach = qmcp_client.send("/v1/topologies", {"name": "x"}, base=BASE)
    assert reach.ok is False and reach.status == 422
    assert reach.detail == detail
    assert "422" in reach.problem


# --- the composition, drawn -----------------------------------------------------

def _drawn(**params) -> tuple[dict, dict, dict]:
    results = _client().get("/designer/composition/gjgf", params=params).json()["results"]
    edges = {(edge["source"], edge["target"]): edge["metadata"] for edge in results["graph"]["edges"]}
    return results["graph"]["nodes"], edges, results["metadata"]


def test_every_saved_design_is_joined_to_what_its_configuration_names(harness):
    """Mutations: draw only designs that reference something -- a design that
    stands alone is missing; read `compose` entries as mappings only -- no
    `composes` line is drawn."""
    held = {**HELD, "topologies": [*HELD["topologies"], _design("alone")]}
    harness(designs=held)
    nodes, edges, metadata = _drawn()
    assert set(nodes) == {"design:intake", "design:review", "design:alone", "component:reader",
                          "design:elsewhere/gone"}
    assert edges[("design:intake", "component:reader")]["kind"] == compose_service.USES
    assert edges[("design:review", "design:intake")]["kind"] == compose_service.COMPOSES
    assert metadata["kind"] == "composition" and metadata["draft"] is False
    assert metadata["designs"] == 3 and metadata["components"] == 1


def test_a_reference_the_harness_does_not_hold_is_dashed_to_a_node_that_says_so(harness):
    """Mutation: draw every line solid -- a reference to nothing reads as held."""
    harness()
    nodes, edges, metadata = _drawn()
    assert edges[("design:review", "design:elsewhere/gone")]["style"] == "dashed"
    assert edges[("design:review", "design:intake")]["style"] == "solid"
    assert nodes["design:elsewhere/gone"]["metadata"]["kind"] == compose_service.ABSENT
    assert "holds no design" in nodes["design:elsewhere/gone"]["metadata"]["hover"]
    assert metadata["not_held"] == 1


def test_the_draft_is_drawn_with_each_reference_named_so_far_and_nothing_is_posted(harness):
    """Mutation: ignore `draft` -- the design being composed is not drawn."""
    stood = harness()
    nodes, edges, metadata = _drawn(draft="true", name="triage", kind="delegation",
                                    compose="intake, review", components="reader,ghost")
    assert nodes["draft"]["metadata"]["kind"] == compose_service.DRAFT
    assert nodes["draft"]["label"] == "triage"
    assert "not saved" in nodes["draft"]["metadata"]["hover"]
    for target, style in (("design:intake", "solid"), ("design:review", "solid"),
                          ("component:reader", "solid"), ("component:ghost", "dashed")):
        assert edges[("draft", target)]["style"] == style, target
    assert metadata["draft"] is True
    assert stood.posted == []
    unnamed, _, _ = _drawn(draft="true")
    assert unnamed["draft"]["label"] == "unnamed draft"


def test_an_unknown_layout_is_a_sentence_naming_the_registered_ones(harness):
    """Mutation: let the `ValueError` through -- the route answers 500."""
    harness()
    answer = _client().get("/designer/composition/gjgf", params={"layout": "Nonsense"})
    assert answer.status_code == 200
    results = answer.json()["results"]
    assert results.get("unreadable") is True and "graph" not in results
