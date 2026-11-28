"""`/designer/data` and `/designer/gjgf`: what the harness declares, read for a panel.

The harness is stood in for at `qmcp_client.fetch`, the one function that
reads it, so every test here runs the real routes and the real service above
that call. The join and the picture are also tested as functions.

Mutations each test was seen to fail under are named in its docstring.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from codecarto.services import designer_service, estate_service, qmcp_client
from codecarto.services.qmcp_client import Reach

BASE = "http://harness"


def _need(key: str) -> dict:
    return {"key": key, "because": f"because of {key}", "supplied_by": f"supply {key}"}


def _shape(name: str, status: str, needs: tuple[str, ...], **marks: bool) -> dict:
    return {"topology": name, "status": status, "can_run": status == "runs",
            "spends": False, "writes": False, "decides": False, **marks,
            "why": f"why {name}", "needs": [_need(key) for key in needs]}


def _plane(**over) -> dict:
    return {
        "schema": 1,
        "capabilities": [
            _shape("relay", "runs", ("workers",)),
            _shape("panel", "sketch", ("build", "budget"), spends=True, decides=True),
            _shape("solo", "runs", ()),
        ],
        "options": [{"setting": "quiet", "value": False,
                     "capability": _shape("panel", "sketch", ("build",), spends=True)}],
        "statuses": ["runs", "sketch"],
        "needs": ["build", "budget", "workers"],
        "attested": ["sign a record"],
        "drift": {"undeclared": [], "stubs": ["panel"]},
        "reading": {"declared_not_discovered": "every field is a claim"},
        **over,
    }


def _runnable(**over) -> dict:
    return {
        "schema": 1,
        "have": {"workers": 2, "budget": 0, "model": False, "built": None},
        "shapes": [
            {"topology": "relay", "status": "runs", "runnable": True, "unmet": []},
            {"topology": "panel", "status": "sketch", "runnable": False,
             "unmet": [_need("budget")]},
            {"topology": "solo", "status": "runs", "runnable": True, "unmet": []},
        ],
        "never_supplied": {"key": "person", "because": "a person decides"},
        **over,
    }


HEALTH = {"pid": 7, "port": 3999, "database_fingerprint": "abc", "started_at": None,
          "session": None, "version": "0"}


class Harness:
    """Answers each path as told, and records what it was asked."""

    def __init__(self, plane=None, runnable=None, down=False):
        self.answers = {designer_service.PLANE: _plane() if plane is None else plane,
                        designer_service.RUNNABLE: _runnable() if runnable is None else runnable,
                        "/health": HEALTH}
        self.down = down
        self.asked: list[str] = []

    def __call__(self, path, base=None, remedy_404=None):
        self.asked.append(path)
        where = BASE + path
        if self.down:
            return Reach(False, where, problem=f"nothing is answering at {BASE}",
                         remedy="start it with `uv run qm dashboard --start harness`")
        found = self.answers.get(path)
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


def _client() -> TestClient:
    from codecarto.main import app

    return TestClient(app)


def _data() -> dict:
    answer = _client().get("/designer/data")
    assert answer.status_code == 200
    return answer.json()["results"]


def _by_name(results: dict) -> dict[str, dict]:
    return {row["name"]: row for row in results["shapes"]}


# --- the join -----------------------------------------------------------------

def test_every_shape_carries_both_entries_as_given_in_the_planes_order(harness):
    """Mutation: sort the rows by name -- the order is not the plane's."""
    stood = harness()
    results = _data()
    assert [row["name"] for row in results["shapes"]] == ["relay", "panel", "solo"]
    rows = _by_name(results)
    assert rows["panel"]["declared"] == _plane()["capabilities"][1]
    assert rows["panel"]["could_run"] == _runnable()["shapes"][1]
    assert rows["relay"]["missing"] == ""
    assert results["have"] == _runnable()["have"]
    assert results["never_supplied"] == _runnable()["never_supplied"]
    assert results["attested"] == ["sign a record"]
    assert results["drift"] == {"undeclared": [], "stubs": ["panel"]}
    assert results["reading"] == {"declared_not_discovered": "every field is a claim"}
    assert results["statuses"] == ["runs", "sketch"]
    assert results["instance"]["identified"] is True and results["instance"]["port"] == 3999
    assert results["where"] == BASE + designer_service.PLANE
    assert set(stood.asked) == {designer_service.PLANE, designer_service.RUNNABLE, "/health"}


def test_an_option_is_listed_under_the_shape_it_varies():
    """Mutation: skip the plane's options -- `panel` has none."""
    rows = designer_service.join(_plane(), _runnable())
    panel = next(row for row in rows if row["name"] == "panel")
    assert [row["name"] for row in rows].count("panel") == 1
    assert panel["options"] == [{"setting": "quiet", "value": False,
                                 "declared": _plane()["options"][0]["capability"]}]
    assert next(row for row in rows if row["name"] == "relay")["options"] == []


def test_a_shape_in_one_document_alone_says_which_does_not_name_it():
    """Mutations: join only a shape the plane declares -- `ghost` is gone;
    leave `missing` empty when the second document does not name a shape --
    `solo` reads as if nothing were absent."""
    told = _runnable()
    told["shapes"] = [told["shapes"][0],
                      {"topology": "ghost", "status": "runs", "runnable": True, "unmet": []}]
    rows = {row["name"]: row for row in designer_service.join(_plane(), told)}
    assert rows["ghost"]["declared"] is None
    assert rows["ghost"]["could_run"]["runnable"] is True
    assert "plane declares no shape" in rows["ghost"]["missing"]
    assert rows["solo"]["could_run"] is None
    assert "does not name this shape" in rows["solo"]["missing"]
    assert rows["relay"]["missing"] == ""


def test_nothing_is_said_to_be_missing_from_a_document_that_was_not_read():
    """Mutation: say `missing` whenever `could_run` is None -- every shape of
    a harness without the second route reads as left out of it."""
    rows = designer_service.join(_plane(), None)
    assert [row["missing"] for row in rows] == ["", "", ""]
    assert all(row["could_run"] is None for row in rows)


# --- each absence ---------------------------------------------------------------

def test_a_harness_that_is_not_answering_is_unreachable_and_asked_once(harness):
    """Mutations: answer `unreadable` for every failed read -- a reader is not
    told to start the harness; read the second document after the first found
    nothing answering -- two more reads are made."""
    stood = harness(down=True)
    for route in ("/designer/data", "/designer/gjgf"):
        stood.asked.clear()
        results = _client().get(route).json()["results"]
        assert results.get("unreachable") is True, route
        assert "nothing is answering" in results["problem"]
        assert "--start harness" in results["remedy"]
        assert results["where"] == BASE + designer_service.PLANE
        assert "shapes" not in results and "graph" not in results
        assert stood.asked == [designer_service.PLANE], route


def test_a_harness_with_no_plane_is_unreadable_and_says_the_build_predates_it(harness):
    """Mutation: pass no `remedy_404` -- the remedy is the topology routes'
    sentence about an archive."""
    harness(plane=404)
    results = _data()
    assert results.get("unreadable") is True
    assert "does not serve" in results["problem"]
    assert "predates the orchestration plane" in results["remedy"]
    assert "shapes" not in results


@pytest.mark.parametrize("plane, said", [
    ({**_plane(), "schema": 2}, "schema 2"),
    ({"capabilities": []}, "schema None"),
    ({"schema": 1, "capabilities": "eight"}, "no list of `capabilities`"),
    (["a", "list"], "not a document"),
])
def test_a_plane_this_window_does_not_read_is_unreadable(harness, plane, said):
    """Mutations: drop the schema check -- a schema-2 plane is listed as if
    read; drop the `capabilities` check -- a plane with no list shows no shape
    and no problem."""
    harness(plane=plane)
    results = _data()
    assert results.get("unreadable") is True, results
    assert said in results["problem"]
    assert "shapes" not in results


@pytest.mark.parametrize("runnable, said", [
    (404, "does not serve"),
    ({**_runnable(), "schema": 9}, "schema 9"),
])
def test_what_could_run_not_read_still_shows_every_shape_and_says_why(harness, runnable, said):
    """Mutations: answer the plane's problem shape when the second read fails
    -- no shape is listed; leave `could_run.read` true -- the panel says
    nothing about why no shape says whether it could run."""
    harness(runnable=runnable)
    results = _data()
    assert [row["name"] for row in results["shapes"]] == ["relay", "panel", "solo"]
    assert results["could_run"]["read"] is False
    assert said in results["could_run"]["problem"]
    assert results["have"] is None and results["never_supplied"] is None
    assert all(row["could_run"] is None and row["missing"] == "" for row in results["shapes"])


# --- the graph ------------------------------------------------------------------

def _graph(results: dict) -> tuple[dict, list]:
    return results["graph"]["nodes"], results["graph"]["edges"]


def test_shapes_are_joined_to_the_needs_they_state_and_a_shared_need_is_one_node(harness):
    """Mutations: key a need's node by shape and key -- `build` is two nodes;
    skip a shape that states no need -- `solo` is not drawn."""
    plane = _plane()
    plane["capabilities"].append(_shape("mesh", "sketch", ("build",)))
    harness(plane=plane)
    results = _client().get("/designer/gjgf").json()["results"]
    nodes, edges = _graph(results)
    assert set(nodes) == {"shape:relay", "shape:panel", "shape:solo", "shape:mesh",
                          "need:workers", "need:build", "need:budget"}
    pairs = {(edge["source"], edge["target"]) for edge in edges}
    assert pairs == {("shape:relay", "need:workers"), ("shape:panel", "need:build"),
                     ("shape:panel", "need:budget"), ("shape:mesh", "need:build")}
    assert results["metadata"]["shapes"] == 4 and results["metadata"]["needs"] == 3
    assert results["metadata"]["kind"] == "designer"


def test_a_need_reported_unmet_is_dashed_and_one_not_reported_is_solid(harness):
    """Mutation: draw every edge solid -- the budget `panel` lacks reads as met."""
    harness()
    results = _client().get("/designer/gjgf").json()["results"]
    _, edges = _graph(results)
    by_pair = {(edge["source"], edge["target"]): edge["metadata"] for edge in edges}
    unmet = by_pair[("shape:panel", "need:budget")]
    assert unmet["style"] == "dashed" and unmet["kind"] == designer_service.UNMET
    assert "because of budget" in unmet["hover"]
    for pair in (("shape:panel", "need:build"), ("shape:relay", "need:workers")):
        assert by_pair[pair]["style"] == "solid", pair
        assert by_pair[pair]["kind"] == designer_service.NEEDS
    assert results["metadata"]["unmet"] == 1


def test_a_status_is_the_nodes_kind_as_written_and_an_unlisted_one_is_drawn(harness):
    """Mutations: give every shape the kind `shape` -- the key names no
    status; raise on a status the plane's vocabulary does not list -- the
    route answers 500."""
    plane = _plane()
    plane["capabilities"].append(_shape("odd", "half-built", ()))
    harness(plane=plane)
    nodes, _ = _graph(_client().get("/designer/gjgf").json()["results"])
    kinds = {name: node["metadata"]["kind"] for name, node in nodes.items()}
    assert kinds["shape:relay"] == "runs" and kinds["shape:panel"] == "sketch"
    assert kinds["shape:odd"] == "half-built"
    assert kinds["need:build"] == designer_service.NEED
    types = {name: node["metadata"]["type"] for name, node in nodes.items()}
    assert types["shape:relay"] != types["shape:panel"]
    assert types["need:build"] == designer_service.NEED_TYPE


def test_a_shapes_hover_names_only_the_marks_the_plane_states(harness):
    """Mutation: list every mark on every hover -- `relay` reads as spending."""
    harness()
    nodes, _ = _graph(_client().get("/designer/gjgf").json()["results"])
    panel = nodes["shape:panel"]["metadata"]["hover"]
    assert "spends, decides" in panel and "writes" not in panel
    assert "could not run now" in panel and "why panel" in panel
    relay = nodes["shape:relay"]["metadata"]["hover"]
    assert "spends" not in relay and "could run now" in relay


def test_shapes_stand_in_one_column_and_needs_in_the_next(harness):
    """Mutation: lay out with a layout that ignores direction as the default
    -- a need stands among the shapes."""
    harness()
    nodes, _ = _graph(_client().get("/designer/gjgf").json()["results"])
    xs = {name: node["metadata"]["x"] for name, node in nodes.items()}
    shapes = {x for name, x in xs.items() if name.startswith("shape:")}
    needs = {x for name, x in xs.items() if name.startswith("need:")}
    assert len(shapes) == 1 and len(needs) == 1
    assert max(shapes) < min(needs)


def test_the_graphs_caveat_says_when_no_line_could_be_dashed(harness):
    """Mutation: leave the caveat alone when the second document was not read
    -- every solid line reads as a need the harness does not report unmet."""
    harness(runnable=404)
    results = _client().get("/designer/gjgf").json()["results"]
    assert "was not read, so no line is dashed" in results["metadata"]["caveat"]
    assert all(edge["metadata"]["style"] == "solid" for edge in results["graph"]["edges"])
    harness()
    read = _client().get("/designer/gjgf").json()["results"]["metadata"]["caveat"]
    assert "was not read" not in read
    assert "every field is a claim" in read


def test_an_unknown_layout_is_a_sentence_naming_the_registered_ones(harness):
    """Mutation: let the `ValueError` through -- the route answers 500."""
    harness()
    answer = _client().get("/designer/gjgf", params={"layout": "Nonsense"})
    assert answer.status_code == 200
    results = answer.json()["results"]
    assert results.get("unreadable") is True
    assert "kamada_kawai_layout" in results["remedy"]
    assert "graph" not in results


# --- the seam's row -------------------------------------------------------------

def test_the_plane_is_a_seam_naming_the_panel_that_draws_it(harness):
    """Mutations: name no panel on the seam -- the Estate panel offers no way
    to it; count any 200 as the plane -- another server on the port is listed
    as the plane."""
    seam = estate_service.BY_NAME["plane"]
    assert seam.panel == "designer-panel"
    assert seam.routes == ("/designer/data", "/designer/gjgf")
    harness()
    found = estate_service.probe_plane()
    assert found.ok and found.schema == 1 and "3 shape(s)" in found.detail
    harness(plane={"status": "ok"})
    other = estate_service.probe_plane()
    assert not other.ok and "did not describe an orchestration plane" in other.problem
    harness(plane=404)
    old = estate_service.probe_plane()
    assert not old.ok and "predates the orchestration plane" in old.remedy
