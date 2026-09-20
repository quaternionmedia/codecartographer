"""dossier's overview, drawn here, and every name it declines to invent.

**THE OTHER WINDOW PRODUCES, THIS ONE CONSUMES.** dossier reads the estate and
emits a seam; this window draws it. The tests worth reading are the ones about
what this window must *not* do: redact a name (the producer already did), invent
a node from a masthead figure (a count is not a relation), or read a seam whose
schema it does not know (two windows disagree the moment one guesses at a field).

THE MUTATIONS, per the corpus's P16, quoted as they printed:

The schema check removed, so an unknown seam version is read on the old
assumption:

    AssertionError: an unknown schema was drawn instead of declined
    assert True is False

The masthead drawn as nodes, so a count becomes a box with no edge:

    AssertionError: a masthead figure was drawn as a node
    assert 'masthead' not in {'scope', 'section', 'subject'}

A scope-to-subject edge added to make the picture connected:

    AssertionError: an edge nobody stated was drawn
    assert 109 == <more>
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app
from codecarto.services import overview_service as mod


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def seam(tmp_path: Path, doc: dict) -> Path:
    path = tmp_path / "overview.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


# A seam shaped like dossier's, with one private subject already redacted by the
# producer to `private/99` -- this window must carry that verbatim.
ONE = {
    "schema": 1,
    "scope": "3 repositories owned by quaternionmedia",
    "generated_from": "a sync 2d ago",
    "masthead": [{"label": "repositories", "value": "3", "note": ""}],
    "sections": [
        {"title": "Branch hygiene", "headers": ["repo", "branch"],
         "rows": [["qm", "main"], ["private/99", "evolve/x"]], "note": ""},
        {"title": "Outstanding", "headers": ["repo", "count"],
         "rows": [["qm", "2"]], "note": ""},
    ],
}


def test_the_graph_draws_the_scope_its_sections_and_their_subjects(tmp_path):
    reading = mod.read(seam(tmp_path, ONE))
    assert reading.ok
    graph = mod.as_graph(reading)
    kinds = sorted({d.get("kind") for _, d in graph.nodes(data=True)})
    assert kinds == [mod.SCOPE, mod.SECTION, mod.SUBJECT]
    # scope -> each section, section -> each distinct subject. No other edges.
    assert graph.number_of_edges() == 2 + 2 + 1  # 2 sections, (qm, private/99), (qm)


def test_a_private_subject_is_carried_verbatim_never_redacted_again(tmp_path):
    """The producer redacted; this window neither un-redacts nor re-redacts. A
    `private/99` reference drawn by dossier draws as `private/99` here."""
    graph = mod.as_graph(mod.read(seam(tmp_path, ONE)))
    labels = {d.get("label") for _, d in graph.nodes(data=True)}
    assert "private/99" in labels, "a producer's redacted reference was dropped"


def test_a_masthead_figure_is_not_drawn_as_a_node(tmp_path):
    """A count is a fact about the estate, not a relation between two things, so
    it rides in the metadata rather than becoming a node with no edge."""
    reading = mod.read(seam(tmp_path, ONE))
    graph = mod.as_graph(reading)
    labels = {str(d.get("label")) for _, d in graph.nodes(data=True)}
    assert "repositories" not in labels, "a masthead figure was drawn as a node"
    assert reading.masthead, "the masthead was dropped instead of kept in the reading"
    assert mod.metadata(reading)["masthead"] == ONE["masthead"]


def test_an_unknown_schema_is_declined_not_guessed(tmp_path):
    reading = mod.read(seam(tmp_path, {**ONE, "schema": 2}))
    assert not reading.ok
    assert "schema" in reading.reason


def test_a_missing_seam_answers_with_a_reason_not_an_empty_graph(tmp_path):
    reading = mod.read(tmp_path / "nope.json")
    assert not reading.ok and reading.reason


def test_the_route_serves_the_graph_and_the_data(client, tmp_path):
    path = seam(tmp_path, ONE)
    gjgf = client.get("/overview/gjgf", params={"seam": str(path)})
    assert gjgf.status_code == 200
    body = gjgf.json()["results"]
    assert "nodes" in body["graph"] and body["metadata"]["kind"] == "overview"

    data = client.get("/overview/data", params={"seam": str(path)}).json()["results"]
    assert data["scope"] == ONE["scope"]
    assert len(data["sections"]) == 2


def test_a_missing_seam_is_a_200_with_the_problem_in_results(client, tmp_path):
    """The route worked; the seam was not there. That is 200 with `unreadable`,
    the same envelope shape the capability window uses for an old pin."""
    r = client.get("/overview/gjgf", params={"seam": str(tmp_path / "absent.json")})
    assert r.status_code == 200
    assert r.json()["results"]["unreadable"] is True
