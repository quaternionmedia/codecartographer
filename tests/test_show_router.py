"""The showgraphs: every family and project, and every edge that must not lie.

**THE TESTS WORTH READING ARE ABOUT WHAT THE PICTURE MUST NOT ASSERT.** A
repository in two families placed inside one outline, a measured dependency
moving a member, a private member drawn by name, a families document this
window cannot read drawn as an empty estate. Each is the easy implementation,
and each produces a picture that looks like an answer.

The corpus here is invented and small, so every fact a test relies on is on
the page. The vocabulary -- which families exist, which sits within which --
belongs to the corpus, and the corpus's own `ci/families.py` tests it; what is
tested here is that this window draws what it was given and adds nothing.

THE MUTATIONS, quoted as they printed:

A shared member given the first claiming family's depth and `contains` edge:

    AssertionError: a member two families claim sat inside one outline
    assert 2 is None

Measured dependencies drawn as `contains` edges from the dependent:

    AssertionError: a measured link placed a member
    assert ['family::sou...'repo::alpha'] == ['family::sound']

A private member labelled with its reference:

    AssertionError: a private member was drawn by name
    assert 'private-07' == 'a private member'

The schema check reduced to "is an integer":

    AssertionError: a schema this window does not read drew a graph
    assert None is True
"""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app
from codecarto.services import show_service

FAMILIES = {
    "schema": 2,
    "generated_at": "2026-10-23T00:00:00Z",
    "reading": {"do_not": "read a family as attention"},
    "families": [
        {"name": "core", "drives": "the corpus", "within": None, "subfamilies": [],
         "members": ["qm", "alpha", "beta"], "all_members": ["qm", "alpha", "beta"]},
        {"name": "performing", "drives": "a show", "within": None,
         "subfamilies": ["sound"], "members": ["hub"],
         "all_members": ["hub", "gamma", "private-07", "delta"]},
        {"name": "sound", "drives": "the sound", "within": "performing",
         "subfamilies": [], "members": ["gamma", "private-07", "delta"],
         "all_members": ["gamma", "private-07", "delta"]},
        {"name": "irl", "drives": "matter", "within": None, "subfamilies": [],
         "members": ["delta"], "all_members": ["delta"]},
    ],
    "unstated": ["loner"],
}

ROSTER = """\
    schema: 1
    repositories:
      - {name: qm, role: corpus}
      - {name: alpha, role: project, phase: v0.0.1, phase_source: stated, attention: active, family: core}
      - {name: beta, role: unmanaged, family: core}
      - {name: gamma, role: unmanaged, family: sound}
      - {name: delta, role: unmanaged, family: [sound, irl]}
      - {name: hub, role: unmanaged, family: performing}
      - {name: loner, role: unmanaged}
      - {ref: private-07, role: unmanaged, family: sound}
"""

INVENTORY = {
    "schema": 1,
    "generator": {"org": "example"},
    "repositories": [
        {"name": "alpha", "private": False, "description": "the first", "recency": "live"},
        {"name": "gamma", "private": False, "description": "", "recency": "cold"},
    ],
}

INTEROP = """\
    schema: 1
    surfaces:
      - id: beta-contract
        protocol: HTTP + schema
        publisher: {repo: beta, file: vectors.json, json_key: version}
        implementations:
          - {repo: alpha, file: test.py, pattern: "x"}
"""

PALETTE = 'FAMILY = {"core": ("#111111", "#2a61bd"), "sound": ("#0a6f6b", "#43c6bf")}\n'


def _git(where: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(where), "-c", "user.name=t", "-c", "user.email=t@t",
                    "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True)


def _commit_all(where: Path) -> None:
    _git(where, "init", "-q", "-b", "main")
    _git(where, "add", "-A")
    _git(where, "commit", "-q", "-m", "c")


@pytest.fixture()
def corpus(tmp_path: Path) -> Path:
    root = tmp_path / "qm"
    (root / "ci").mkdir(parents=True)
    (root / "status").mkdir()
    (root / "families.json").write_text(json.dumps(FAMILIES), encoding="utf-8")
    (root / "ci" / "workspace.yaml").write_text(textwrap.dedent(ROSTER), encoding="utf-8")
    (root / "status" / "inventory.yaml").write_text(json.dumps(INVENTORY), encoding="utf-8")
    (root / "ci" / "interop-registry.yaml").write_text(textwrap.dedent(INTEROP), encoding="utf-8")
    (root / "ci" / "palette.py").write_text(PALETTE, encoding="utf-8")
    return root


@pytest.fixture()
def clones(tmp_path: Path) -> Path:
    """alpha's manifests: one URL to a declared seam, one to an undeclared one,
    and one bare name that resolves to nothing."""
    where = tmp_path / "clones"
    alpha = where / "alpha"
    alpha.mkdir(parents=True)
    (alpha / "pyproject.toml").write_text(
        'dependencies = ["beta @ git+https://github.com/example/beta.git"]\n', encoding="utf-8")
    (alpha / "package.json").write_text(
        '{"dependencies": {"g": "github:x/y", "gamma": "^1.0.0", '
        '"gg": "git+https://github.com/example/gamma.git"}}\n', encoding="utf-8")
    _commit_all(alpha)
    return where


@pytest.fixture()
def client(corpus: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(corpus.parent / "no-clones"))
    return TestClient(app)


def _results(client: TestClient, url: str) -> dict:
    response = client.get(url)
    assert response.status_code == 200, response.text
    return response.json()["results"]


def _nodes(results: dict) -> dict[str, dict]:
    """Each node's attributes, its gJGF `label` among them."""
    return {node_id: {"label": node.get("label"), **node["metadata"]}
            for node_id, node in results["graph"]["nodes"].items()}


def _edges(results: dict) -> list[dict]:
    return [{"source": e["source"], "target": e["target"], "label": e.get("label"),
             **e.get("metadata", {})}
            for e in results["graph"]["edges"]]


# --- absences ---------------------------------------------------------------

def test_a_missing_families_document_is_a_sentence(tmp_path, monkeypatch):
    monkeypatch.setenv("CODECARTO_CORPUS", str(tmp_path / "empty"))
    results = _results(TestClient(app), "/show/index/gjgf")
    assert results.get("unreadable") is True
    assert "families document" in results["problem"]
    assert "graph" not in results


def test_a_schema_this_window_does_not_read_draws_nothing(corpus, monkeypatch):
    document = dict(FAMILIES, schema=3)
    (corpus / "families.json").write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    results = _results(TestClient(app), "/show/index/gjgf")
    assert results.get("unreadable") is True, \
        "a schema this window does not read drew a graph"
    assert "schema 3" in results["problem"]


def test_a_family_the_corpus_does_not_declare_is_named_with_the_ones_it_does(client):
    results = _results(client, "/show/family/nowhere/gjgf")
    assert results["unreadable"] is True
    assert "core" in results["remedy"] and "sound" in results["remedy"]


def test_a_private_member_has_no_project_view(client):
    results = _results(client, "/show/project/private-07/gjgf")
    assert results["unreadable"] is True
    assert "private" in results["problem"]


def test_a_repository_nobody_placed_has_no_project_view(client):
    results = _results(client, "/show/project/stranger/gjgf")
    assert results["unreadable"] is True


# --- claims -----------------------------------------------------------------

def test_a_member_two_families_claim_is_drawn_once_outside_both(client):
    results = _results(client, "/show/index/gjgf")
    nodes = _nodes(results)
    assert "repo::delta" in nodes
    assert nodes["repo::delta"].get("depth") is None, \
        "a member two families claim sat inside one outline"
    into = [e for e in _edges(results) if e["target"] == "repo::delta" and e["kind"] == "contains"]
    assert into == []
    out = sorted(e["target"] for e in _edges(results)
                 if e["source"] == "repo::delta" and e["kind"] == "member_of")
    assert out == ["family::irl", "family::sound"]


def test_a_family_page_holds_its_shared_member_and_points_at_the_other(client):
    results = _results(client, "/show/family/irl/gjgf")
    nodes = _nodes(results)
    assert nodes["repo::delta"]["depth"] == 1
    assert nodes["repo::delta"]["also_in"] == ["sound"]
    assert nodes["family::sound"]["elsewhere"] is True
    assert nodes["family::sound"].get("depth") is None, \
        "a marker for another family was drawn as an outline"


def test_a_subfamily_nests_one_level_down(client):
    results = _results(client, "/show/family/performing/gjgf")
    nodes = _nodes(results)
    assert nodes["family::performing"]["depth"] == 0
    assert nodes["family::sound"]["depth"] == 1
    assert nodes["repo::gamma"]["depth"] == 2
    assert nodes["repo::hub"]["depth"] == 1


def test_a_private_member_is_counted_and_not_named(client):
    nodes = _nodes(_results(client, "/show/family/sound/gjgf"))
    private = nodes["repo::private-07"]
    assert private["label"] == "a private member", "a private member was drawn by name"
    assert "show" not in private, "a private member could be opened"
    subjects = _results(client, "/show/subjects")
    assert "private-07" not in [p["name"] for p in subjects["projects"]]
    assert subjects["private"] == 1


def test_the_hue_is_the_corpus_palette_s(client):
    nodes = _nodes(_results(client, "/show/family/core/gjgf"))
    assert nodes["family::core"]["color"] == "#2a61bd"


def test_unstated_is_counted_and_never_drawn_as_a_family(client):
    subjects = _results(client, "/show/subjects")
    assert subjects["unstated"] == 1
    index = _results(client, "/show/index/gjgf")
    assert "repo::loner" not in _nodes(index)
    assert "loner" in [p["name"] for p in subjects["projects"]], \
        "a rostered repository with no family has no project view"


# --- declared and measured --------------------------------------------------

def test_a_declared_seam_is_drawn_with_its_protocol(client):
    edges = _edges(_results(client, "/show/family/core/gjgf"))
    seam = [e for e in edges if e["kind"] == "seam"]
    assert [(e["source"], e["target"], e["label"], e["basis"]) for e in seam] == [
        ("repo::alpha", "repo::beta", "HTTP + schema", "declared")]


def test_a_measured_link_is_dashed_and_never_places_a_member(client, clones, monkeypatch):
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(clones))
    results = _results(client, "/show/index/gjgf")
    edges = _edges(results)
    measured = [e for e in edges if e["basis"] == "measured"]
    assert sorted((e["source"], e["target"]) for e in measured) == [
        ("repo::alpha", "repo::beta"), ("repo::alpha", "repo::gamma")]
    assert {e["style"] for e in measured} == {"dashed"}
    parents = sorted(e["source"] for e in edges
                     if e["target"] == "repo::gamma" and e["kind"] in ("contains", "member_of"))
    assert parents == ["family::sound"], "a measured link placed a member"


def test_a_name_that_only_matches_is_not_a_link(client, clones, monkeypatch):
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(clones))
    reading = show_service.read()
    links, _ = show_service.measured_links(reading, ["alpha"], [clones])
    assert sorted(link["target"] for link in links) == ["beta", "gamma"]
    assert all(link["file"] in ("pyproject.toml", "package.json") for link in links)


def test_only_a_measured_link_with_no_declared_seam_is_reported(client, clones, monkeypatch):
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(clones))
    metadata = _results(client, "/show/family/core/gjgf")["metadata"]
    assert metadata["undeclared"] == [{"source": "alpha", "target": "gamma"}]
    assert "alpha → gamma" in metadata["caveat"]


def test_a_member_with_no_clone_is_named_as_unmeasured(client):
    metadata = _results(client, "/show/family/core/gjgf")["metadata"]
    assert "alpha" in metadata["unread"] and "beta" in metadata["unread"]


# --- a project's views ------------------------------------------------------

def test_a_project_says_which_views_it_can_draw(client):
    views = _results(client, "/show/project/alpha/views")
    assert views["estate"]["available"] is True
    assert views["code"]["url"] == "https://github.com/example/alpha"
    assert views["system"]["available"] is False
    assert "no clone" in views["system"]["problem"]


def test_a_project_s_claims_and_measurement_sit_side_by_side(client):
    edges = _edges(_results(client, "/show/project/alpha/gjgf"))
    by_label = {e["label"]: e["basis"] for e in edges if e["source"] == "repo::alpha"}
    assert by_label["phase"] == "claim"
    assert by_label["attention"] == "claim"
    assert by_label["recency"] == "measured"


def test_records_on_a_project_branch_are_drawn_with_their_status(corpus, monkeypatch):
    adr = corpus / "adr"
    adr.mkdir()
    (adr / "README.md").write_text("# index\n", encoding="utf-8")
    _commit_all(corpus)
    _git(corpus, "switch", "-q", "-c", "project/alpha")
    (adr / "DRAFT-one-thing.md").write_text(
        "# ADR-XXXX — One thing\n\n| | |\n|---|---|\n| **Status** | Proposed |\n",
        encoding="utf-8")
    _git(corpus, "add", "-A")
    _git(corpus, "commit", "-q", "-m", "record")
    _git(corpus, "switch", "-q", "main")
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    nodes = _nodes(_results(TestClient(app), "/show/project/alpha/gjgf"))
    record = nodes["record::adr/DRAFT-one-thing.md"]
    assert record["label"] == "ADR-XXXX — One thing"
    assert record["status"] == "Proposed"
    assert "record::adr/README.md" not in nodes
    subjects = _results(TestClient(app), "/show/subjects")
    governed = {p["name"]: p["governed"] for p in subjects["projects"]}
    assert governed["alpha"] is True and governed["beta"] is False
    assert governed["qm"] is True, "the corpus was drawn as ungoverned"


def test_governance_is_unknown_without_git_and_not_drawn_as_not_adopted(client):
    subjects = _results(client, "/show/subjects")
    assert {p["governed"] for p in subjects["projects"]} == {None}
    assert any("git" in note for note in subjects["notes"])


def test_a_flat_schema_draws_as_families_with_no_nesting(corpus, monkeypatch):
    flat = {"schema": 1, "families": [
        {"name": "core", "drives": "the corpus", "members": ["qm", "alpha"]}],
        "unstated": []}
    (corpus / "families.json").write_text(json.dumps(flat), encoding="utf-8")
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    nodes = _nodes(_results(TestClient(app), "/show/index/gjgf"))
    assert nodes["family::core"]["depth"] == 0
    assert nodes["repo::alpha"]["depth"] == 1


def test_the_seam_is_in_the_liveness_table(client):
    rows = _results(client, "/estate/seams")["seams"]
    families = next(r for r in rows if r["name"] == "families")
    assert families["ok"] is True and families["schema"] == 2
    assert families["panel"] == "show-panel"
