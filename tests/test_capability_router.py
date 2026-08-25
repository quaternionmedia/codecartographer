"""The capability registry as a graph, and every edge it declines to draw.

**THE TESTS WORTH READING ARE THE ONES ABOUT WHAT IS ABSENT.** A rung nobody has
established draws nothing at all, and a governance pin older than the registry
answers with a reason rather than an empty canvas. Both are cases where the easy
implementation produces a picture that looks like an answer, which is what this
whole view exists to avoid.

**THE VOCABULARY IS NOT TESTED HERE.** The four rungs belong to `governance/qm`,
and `ci/capabilities.py` in that corpus tests them. What is tested here is that
this window reads the file faithfully and adds nothing -- a rung that meant
something different here than in `dossier` would give two readings of one estate.

THE MUTATIONS, per P16, quoted as they printed:

The `continue` that skips an unknown rung removed, so an absence becomes a node:

    AssertionError: an unestablished rung was drawn as a node
    assert 'unknown' not in ['A thing', 'deployment', 'design', 'execution',
    'monitoring', 'owner/repo', ...]

An edge added from each capability to every rung it has reached:

    AssertionError: one stated claim was drawn as more than one edge
    assert 3 == 1

An absent registry returning an empty `Reading` rather than a reason:

    AssertionError: a pin older than the registry drew an empty estate
    assert True is False
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app
from codecarto.services import capability_service as mod


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def corpus(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "ci" / "capability-registry.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return tmp_path


ONE = """\
    schema: 1
    capabilities:
      - id: a/thing
        title: A thing
        repo: owner/repo
        phase: execution
        stated_by: Somebody
        stated_on: 2026-08-25
        what: It does a thing.
        evidence:
          design: records/DRAFT-x.md
          deployment: uv run thing
          execution: owner/repo/delta/x
          monitoring: null
        cannot_see: Whether it is any good.
    """


def kinds(graph) -> dict[str, int]:
    found: dict[str, int] = {}
    for _, data in graph.nodes(data=True):
        found[data.get("kind")] = found.get(data.get("kind"), 0) + 1
    return found


# --- what it declines to draw ---------------------------------------------------


def test_an_unestablished_rung_draws_nothing_at_all(tmp_path: Path):
    """THE ONE THAT MATTERS.

    No node, no edge, no placeholder. An absence rendered as a box is a thing
    nobody could measure drawn like a thing measured and found wanting.
    """
    graph = mod.as_graph(mod.read(corpus(tmp_path, ONE)))
    labels = sorted(str(data.get("label")) for _, data in graph.nodes(data=True))

    assert mod.UNKNOWN not in labels, (
        "an unestablished rung was drawn as a node")
    assert not any(data.get("label") == "monitoring"
                   for _, _, data in graph.edges(data=True)), (
        "an unestablished rung was drawn as an edge")


def test_the_count_of_what_is_not_drawn_is_reported(tmp_path: Path):
    """A reader must be able to tell a sparse estate from a sparsely drawn one."""
    reading = mod.read(corpus(tmp_path, ONE))

    assert mod.unmeasured(reading) == 1
    assert mod.metadata(reading)["unmeasured"] == 1


def test_one_stated_claim_is_one_edge(tmp_path: Path):
    """A capability at `execution` has reached `design` and `deployment`, and
    the registry declares one phase. Drawing an edge to each reached rung would
    turn one stated fact into three drawn ones."""
    graph = mod.as_graph(mod.read(corpus(tmp_path, ONE)))
    claims = [e for e in graph.edges(data=True) if e[2].get("label") == "claims"]

    assert len(claims) == 1, "one stated claim was drawn as more than one edge"
    assert claims[0][1] == "execution"


def test_every_edge_carries_the_relation_the_registry_declared(tmp_path: Path):
    """Nothing is added to make the graph connected."""
    graph = mod.as_graph(mod.read(corpus(tmp_path, ONE)))
    labels = {data["label"] for _, _, data in graph.edges(data=True)}

    assert labels <= {"claims", "lives-in", *mod.RUNGS}
    assert all(data.get("stated") for _, _, data in graph.edges(data=True))


# --- what it draws --------------------------------------------------------------


def test_a_capability_reaches_its_repository_and_its_evidence(tmp_path: Path):
    graph = mod.as_graph(mod.read(corpus(tmp_path, ONE)))

    assert graph.has_edge("a/thing", "owner/repo")
    assert graph.has_edge("a/thing", "records/DRAFT-x.md")
    assert graph.has_edge("a/thing", "owner/repo/delta/x")


def test_all_four_rungs_are_present_even_when_nothing_claims_them(tmp_path: Path):
    """That a rung has nothing at it is one of the more useful things this view
    can show, and a node appearing only once claimed would hide it."""
    graph = mod.as_graph(mod.read(corpus(tmp_path, ONE)))

    for rung in mod.RUNGS:
        assert graph.has_node(rung)
    assert graph.in_degree("design") == 0
    assert kinds(graph)["rung"] == 4


def test_two_capabilities_in_one_repository_share_that_node(tmp_path: Path):
    """A shared node is a fact rather than a layout choice."""
    root = corpus(tmp_path, """\
        capabilities:
          - id: a/one
            repo: owner/repo
            phase: design
            evidence: {design: records/DRAFT-x.md}
          - id: a/two
            repo: owner/repo
            phase: design
            evidence: {design: records/DRAFT-y.md}
        """)
    graph = mod.as_graph(mod.read(root))

    assert graph.in_degree("owner/repo") == 2
    assert kinds(graph)["repo"] == 1


def test_the_caveat_says_a_pointer_is_not_a_finding(tmp_path: Path):
    """The sentence that stops the picture reading as a verified one."""
    text = mod.caveat(mod.read(corpus(tmp_path, ONE)))

    assert "declared in the registry" in text
    assert "does not exist draws like one that works" in text


# --- a pin older than the registry ----------------------------------------------


def test_an_absent_registry_is_a_reason_and_not_an_empty_estate(tmp_path: Path):
    reading = mod.read(tmp_path)

    assert reading.ok is False, "a pin older than the registry drew an empty estate"
    assert "pin may predate it" in reading.reason


def test_a_registry_that_does_not_parse_says_so(tmp_path: Path):
    reading = mod.read(corpus(tmp_path, "capabilities: [unclosed\n"))

    assert not reading.ok
    assert "did not parse" in reading.reason


def test_a_row_with_no_id_is_dropped_rather_than_named(tmp_path: Path):
    root = corpus(tmp_path, "capabilities:\n  - title: Nameless\n")

    assert mod.read(root).capabilities == []


# --- the routes -----------------------------------------------------------------


def test_the_graph_route_answers_in_this_project_s_envelope(client: TestClient):
    body = client.get("/capabilities/gjgf").json()

    assert body["results"].keys() >= {"graph", "metadata"}
    assert body["results"]["metadata"]["rungs"] == list(mod.RUNGS)


def test_the_data_route_carries_the_claim_and_the_pointers_apart(
        client: TestClient):
    """Nothing reconciles them, which is the comparison the record exists for."""
    results = client.get("/capabilities/data").json()["results"]

    assert results["rungs"] == list(mod.RUNGS)
    for row in results["capabilities"]:
        assert "phase" in row and "evidence" in row
        assert set(row["evidence"]) == set(mod.RUNGS)


def test_an_unreadable_registry_answers_200_with_the_problem_in_results(
        client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """**STATUS 200, AND THE PROBLEM IN `results`.**

    The route worked; the registry is what could not be read. A non-200
    envelope also reaches this front end as a `TypeError` with no detail,
    because `RequestHandler.handleResponse` parses the message in one exact
    shape -- the failure `topology_router._unreachable` documents.
    """
    monkeypatch.setattr(mod, "CORPUS", tmp_path)

    response = client.get("/capabilities/gjgf")

    assert response.status_code == 200
    results = response.json()["results"]
    assert results["unreadable"] is True
    assert "pin may predate it" in results["problem"]
    assert "propagate/" in results["remedy"]
    assert "graph" not in results, "an unreadable registry drew a canvas"


def test_this_window_agrees_with_the_corpus_about_the_rungs():
    """Two windows onto one file must not disagree about its vocabulary."""
    source = Path(mod.CORPUS) / "ci" / "capabilities.py"
    if not source.is_file():
        pytest.skip("no corpus checkout at this pin carries ci/capabilities.py")

    text = source.read_text(encoding="utf-8")
    for rung in mod.RUNGS:
        assert f'"{rung}"' in text, f"{rung} is not a rung in the corpus"
