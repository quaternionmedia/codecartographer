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
    a shorthand to another host's repository, and `delta`, an estate
    repository named only as a package."""
    where = tmp_path / "clones"
    alpha = where / "alpha"
    alpha.mkdir(parents=True)
    (alpha / "pyproject.toml").write_text(
        'dependencies = ["beta @ git+https://github.com/example/beta.git"]\n', encoding="utf-8")
    (alpha / "package.json").write_text(
        '{"dependencies": {"g": "github:x/y", "gamma": "^1.0.0", "delta": "^1.0.0", '
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


_FAMILY_OF_OTHER_SHAPES = {"schema": 2, "families": [
    {"name": "core", "drives": "x", "within": ["y"], "members": 5, "subfamilies": 5,
     "all_members": 5}], "unstated": 5}


@pytest.mark.parametrize(("name", "content", "answer"), [
    ("families.json", b"[]", "unreadable"),
    ("families.json", b"\xff\xfe{}", "unreadable"),
    ("families.json", b'{"schema": 2, "families": 5}', "unreadable"),
    ("families.json", json.dumps(_FAMILY_OF_OTHER_SHAPES).encode(), "drawn"),
    ("ci/workspace.yaml", b"- a list\n", "noted"),
    ("ci/workspace.yaml", b"\xff\n", "noted"),
    ("ci/workspace.yaml", b"repositories: 5\n", "drawn"),
    ("status/inventory.yaml", b"- a list\n", "noted"),
    ("status/inventory.yaml", b'{"generator": ["example"], "repositories": 5}', "noted"),
    ("ci/interop-registry.yaml", b"- a list\n", "noted"),
    ("ci/interop-registry.yaml",
     b"surfaces:\n  - {id: s, publisher: beta, implementations: [alpha, 5]}\n", "drawn"),
    ("ci/palette.py", b"FAMILY = []\n", "noted"),
    ("ci/palette.py", b"\xff\n", "noted"),
    ("ci/capability-registry.yaml", b"- a list\n", "drawn"),
    ("ci/capability-registry.yaml", b"\xff\n", "drawn"),
], ids=["families a list", "families not utf-8", "families' families a number",
        "a family's fields", "roster a list", "roster not utf-8", "roster's rows a number",
        "inventory a list", "inventory's generator a list", "registry a list",
        "a surface's ends", "palette a list", "palette not utf-8",
        "capabilities a list", "capabilities not utf-8"])
def test_a_document_of_another_shape_answers_rather_than_failing(corpus, monkeypatch,
                                                                 name, content, answer):
    # Each read called `.get` on whatever parsed, iterated whatever a key
    # held, and decoded as UTF-8 with nothing to catch it, so a list where a
    # mapping belongs, a number where a list does, or a file that is not
    # UTF-8 raised, and the route answered 500. Broken by taking any one of
    # the shape checks out, its case raises again.
    (corpus / name).write_bytes(content)
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(corpus.parent / "no-clones"))
    client = TestClient(app)
    for url in ("/show/subjects", "/show/index/gjgf", "/show/family/core/gjgf",
                "/show/project/alpha/gjgf", "/show/project/alpha/views"):
        results = _results(client, url)
        if answer == "unreadable":
            assert results.get("unreadable") is True, url
            assert "families.json" in results["problem"], url
        else:
            assert not results.get("unreadable"), f"{url}: {results.get('problem')}"
    if answer == "noted":
        notes = _results(client, "/show/subjects")["notes"]
        assert any(name in note for note in notes), notes


def test_a_status_line_with_no_cell_is_unstated(corpus, monkeypatch):
    # `| **Status**` with nothing after it split into two parts, and the
    # third was read: an IndexError, and a 500. Broken by reading the cell
    # unguarded again, it raises.
    _commit_all(corpus)
    _git(corpus, "switch", "-q", "-c", "project/alpha")
    adr = corpus / "adr"
    adr.mkdir()
    (adr / "DRAFT-bare.md").write_text("# Bare\n\n| **Status**\n", encoding="utf-8")
    _git(corpus, "add", "-A")
    _git(corpus, "commit", "-q", "-m", "record")
    _git(corpus, "switch", "-q", "main")
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    nodes = _nodes(_results(TestClient(app), "/show/project/alpha/gjgf"))
    assert nodes["record::adr/DRAFT-bare.md"]["status"] == "unstated"


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


def test_a_private_member_two_families_claim_is_counted_and_drawn_once(corpus, monkeypatch):
    # The count summed each family's private members, and the index walked
    # each family's list of them, so a private member in two families was
    # counted twice and given each `member_of` edge twice. Broken by counting
    # claims rather than members, `private` is 2; by walking the claims, the
    # edges are four.
    document = json.loads(json.dumps(FAMILIES))
    irl = next(f for f in document["families"] if f["name"] == "irl")
    irl["members"].append("private-07")
    irl["all_members"].append("private-07")
    (corpus / "families.json").write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(corpus.parent / "no-clones"))
    client = TestClient(app)
    assert _results(client, "/show/subjects")["private"] == 1, \
        "a private member was counted once per family"
    edges = sorted(e["target"] for e in _edges(_results(client, "/show/index/gjgf"))
                   if e["source"] == "repo::private-07" and e["kind"] == "member_of")
    assert edges == ["family::irl", "family::sound"], "a private member's claims were drawn twice"


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
    # `delta` is an estate repository that alpha's package.json names only as
    # a package. gamma is named so too, and also by its URL, so it cannot
    # tell the two readings apart. Broken by also reading a quoted package
    # name as a link, delta is drawn.
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(clones))
    reading = show_service.read()
    links, _ = show_service.measured_links(reading, ["alpha"], [clones])
    targets = sorted(link["target"] for link in links)
    assert "delta" not in targets, "a package that shares a repository's name was drawn as a link"
    assert targets == ["beta", "gamma"]
    assert all(link["file"] in ("pyproject.toml", "package.json") for link in links)


@pytest.mark.parametrize("line", [
    'dependencies = ["beta @ git+https://github.com/example/beta.git@v0.1.0"]\n',
    'dependencies = ["beta @ git+https://github.com/example/beta.git?rev=1"]\n',
    'dependencies = ["beta @ git+https://github.com/Example/beta"]\n',
], ids=["a tag after it", "a query after it", "the organisation's case"])
def test_a_host_url_names_its_repository_whatever_follows_it(corpus, tmp_path, monkeypatch, line):
    # The pattern ended a name only at a quote, a space, `/`, `#` or `)`, and
    # matched the organisation's case exactly, so a pinned tag, a query or
    # `github.com/Example` lost the link. Broken back to that ending, the
    # first two are lost; with the organisation's case matched, the third.
    alpha = tmp_path / "clones" / "alpha"
    alpha.mkdir(parents=True)
    (alpha / "pyproject.toml").write_text(line, encoding="utf-8")
    _commit_all(alpha)
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    links, unread = show_service.measured_links(show_service.read(), ["alpha"],
                                                [tmp_path / "clones"])
    assert unread == []
    assert [link["target"] for link in links] == ["beta"], f"{line.strip()} lost its link"


def test_a_clone_git_could_not_read_is_unread_and_read_again(corpus, clones, monkeypatch):
    # `git cat-file` exiting non-zero raises nothing, so its empty answer was
    # kept for the clone's commit as "no manifests" until a restart, and the
    # member counted as measured. Broken by taking a failure for no
    # manifests, alpha is not unread; by keeping the failure for the commit,
    # the second call is unread too.
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    reading = show_service.read()
    real, failed = subprocess.run, []

    def fails_once(args, *rest, **kwargs):
        if "cat-file" in args and not failed:
            failed.append(args)
            return subprocess.CompletedProcess(args, 128, b"", b"fatal: a test")
        return real(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "run", fails_once)
    links, unread = show_service.measured_links(reading, ["alpha"], [clones])
    assert failed, "the manifests were not read with git cat-file"
    assert (links, unread) == ([], ["alpha"]), "a clone git could not read was measured"
    links, unread = show_service.measured_links(reading, ["alpha"], [clones])
    assert unread == [], "a failed read was kept"
    assert sorted(link["target"] for link in links) == ["beta", "gamma"]


def test_only_a_measured_link_with_no_declared_seam_is_reported(client, clones, monkeypatch):
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(clones))
    metadata = _results(client, "/show/family/core/gjgf")["metadata"]
    assert metadata["undeclared"] == [{"source": "alpha", "target": "gamma"}]
    assert "alpha → gamma" in metadata["caveat"]


def test_a_member_with_no_clone_is_named_as_unmeasured(client):
    metadata = _results(client, "/show/family/core/gjgf")["metadata"]
    assert "alpha" in metadata["unread"] and "beta" in metadata["unread"]


@pytest.mark.parametrize("inventory", ["absent", "no organisation"])
def test_an_unknown_organisation_is_not_blamed_on_a_missing_clone(corpus, clones, monkeypatch,
                                                                  inventory):
    # With no organisation no host URL can be matched, so nothing is measured
    # for any member. The caveat said each "had no clone beside this one",
    # alpha among them, whose clone is right there. Broken by giving the clone
    # as the reason whatever the organisation, alpha is blamed again.
    path = corpus / "status" / "inventory.yaml"
    if inventory == "absent":
        path.unlink()
    else:
        path.write_text(json.dumps(dict(INVENTORY, generator={})), encoding="utf-8")
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(clones))
    metadata = _results(TestClient(app), "/show/family/core/gjgf")["metadata"]
    assert "alpha" in metadata["unread"], "a member nothing was measured for was not named"
    assert "no clone" not in metadata["caveat"], "a member with a clone was blamed on a missing one"
    assert "organisation" in metadata["caveat"]
    assert any("organisation" in note for note in metadata["notes"])


# --- a project's views ------------------------------------------------------

def test_a_project_says_which_views_it_can_draw(client):
    views = _results(client, "/show/project/alpha/views")
    assert views["estate"]["available"] is True
    assert views["code"]["url"] == "https://github.com/example/alpha"
    assert views["system"]["available"] is False
    assert "no clone" in views["system"]["problem"]


def test_the_code_view_is_offered_only_for_a_repository_the_host_lists(client):
    # beta is in a family and the roster and has no inventory row: the host
    # lists no public repository by that name. Offering its code map whenever
    # the organisation is known, as the route did, sends the panel to stream
    # an address that is not there.
    code = _results(client, "/show/project/beta/views")["code"]
    assert code["available"] is False, "a repository the host does not list offered its code map"
    assert "beta" in code["problem"] and "inventory" in code["problem"]
    assert "url" not in code


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
    # This project's own branch, without which the listing is a short one.
    _git(corpus, "branch", f"project/{show_service.THIS_PROJECT}")
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


@pytest.mark.parametrize("branches", [[], ["project/alpha"]], ids=["none", "another"])
def test_governance_is_unknown_when_the_listing_lacks_this_project_s_branch(
        corpus, monkeypatch, branches):
    # A checkout of the pin's commit alone, as CI's `--depth 1` makes, holds no
    # `project/*` ref: `git for-each-ref` lists nothing and exits 0. A
    # single-branch clone lists one branch at most. Reading either listing as
    # the whole answer, as `_governed` did, gives beta `False`: "not adopted".
    _commit_all(corpus)
    for branch in branches:
        _git(corpus, "branch", branch)
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    subjects = _results(TestClient(app), "/show/subjects")
    governed = {p["name"]: p["governed"] for p in subjects["projects"]}
    assert governed["beta"] is None, "a short listing drew a member as not adopted"
    assert governed["alpha"] is None
    assert any("shallow or single-branch" in note for note in subjects["notes"])


def test_a_flat_schema_draws_as_families_with_no_nesting(corpus, monkeypatch):
    flat = {"schema": 1, "families": [
        {"name": "core", "drives": "the corpus", "members": ["qm", "alpha"]}],
        "unstated": []}
    (corpus / "families.json").write_text(json.dumps(flat), encoding="utf-8")
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    nodes = _nodes(_results(TestClient(app), "/show/index/gjgf"))
    assert nodes["family::core"]["depth"] == 0
    assert nodes["repo::alpha"]["depth"] == 1


def test_a_corpus_named_by_the_override_is_named_without_the_home_directory(
        corpus, tmp_path, monkeypatch):
    # CODECARTO_CORPUS names a checkout by its absolute path, and every
    # drawing's `metadata.source` and `provenance.source`, every note and
    # every `unreadable` answer carried it, the account's home directory in
    # it. Broken by printing the path as it was given, the home is back.
    home = tmp_path.as_posix()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    (corpus / "ci" / "palette.py").unlink()  # a note that names a path
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    client = TestClient(app)
    drawn = _results(client, "/show/index/gjgf")["metadata"]
    subjects = _results(client, "/show/subjects")
    assert drawn["source"] == "~/qm/families.json", "the home directory was printed"
    assert drawn["provenance"]["source"] == "~/qm/families.json"
    assert subjects["provenance"]["source"] == "~/qm/families.json"
    assert any("~/qm/ci/palette.py" in note for note in subjects["notes"])
    assert not any(home in note for note in drawn["notes"] + subjects["notes"])
    monkeypatch.setenv("CODECARTO_CORPUS", str(tmp_path / "empty"))
    absent = _results(client, "/show/index/gjgf")
    assert absent["where"] == "~/empty/families.json"
    assert home not in absent["problem"]


def test_the_pin_is_named_as_it_is_mounted(corpus, monkeypatch):
    monkeypatch.chdir(corpus.parent)
    monkeypatch.setattr(show_service.corpus_root, "SUBMODULE", Path("qm"))
    assert show_service.read().source == "qm/families.json"


def test_the_seam_is_in_the_liveness_table(client):
    rows = _results(client, "/estate/seams")["seams"]
    families = next(r for r in rows if r["name"] == "families")
    assert families["ok"] is True and families["schema"] == 2
    assert families["panel"] == "show-panel"


# --- where the packed layout puts things ------------------------------------
#
# A showgraph opens in the compound layout, and `show_layout.pack` re-places
# it. The outlines are drawn in the browser around what each group holds, so
# here an outline is taken as the canvas takes it: the circle around a group's
# node reaching its farthest member, plus that member's drawn radius and the
# outline's padding.

def _xy(node: dict) -> tuple[float, float]:
    return node["x"], node["y"]


def _outline(nodes: dict[str, dict], edges: list[dict], hub: str) -> tuple[float, float, float]:
    """The circle a top-level group's outline is drawn as, around its hub."""
    held, todo = set(), [hub]
    while todo:
        here = todo.pop()
        for e in edges:
            if e["source"] == here and e["kind"] == "contains" and e["target"] not in held:
                held.add(e["target"])
                todo.append(e["target"])
    cx, cy = _xy(nodes[hub])
    reach = max((((nodes[n]["x"] - cx) ** 2 + (nodes[n]["y"] - cy) ** 2) ** 0.5 for n in held),
                default=0.0)
    return cx, cy, reach + 12 + 40


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def test_packed_outlines_do_not_overlap(client):
    results = _results(client, "/show/index/gjgf?layout=Compound")
    nodes, edges = _nodes(results), _edges(results)
    tops = [n for n, a in nodes.items() if a.get("depth") == 0]
    circles = {n: _outline(nodes, edges, n) for n in tops}
    for i, a in enumerate(tops):
        for b in tops[i + 1:]:
            ax, ay, ar = circles[a]
            bx, by, br = circles[b]
            assert _distance((ax, ay), (bx, by)) >= ar + br, \
                f"{a}'s outline overlapped {b}'s"


def test_a_shared_member_is_packed_outside_every_outline(client):
    results = _results(client, "/show/index/gjgf?layout=Compound")
    nodes, edges = _nodes(results), _edges(results)
    delta = _xy(nodes["repo::delta"])
    for top in (n for n, a in nodes.items() if a.get("depth") == 0):
        cx, cy, r = _outline(nodes, edges, top)
        assert _distance(delta, (cx, cy)) > r, \
            f"a member two families claim was packed inside {top}'s outline"


def test_every_name_on_a_ring_has_room(corpus, monkeypatch):
    # Twelve members, so the ring is as wide as its names need rather than
    # its smallest size.
    crowd = [f"m{i:02d}" for i in range(12)]
    document = json.loads(json.dumps(FAMILIES))
    document["families"][0]["members"] += crowd
    document["families"][0]["all_members"] += crowd
    (corpus / "families.json").write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setenv("CODECARTO_CORPUS", str(corpus))
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(corpus.parent / "no-clones"))
    nodes = _nodes(_results(TestClient(app), "/show/family/core/gjgf?layout=Compound"))
    placed = [(n, _xy(a)) for n, a in nodes.items() if a.get("label_at") not in (None, "none")]
    assert len(placed) >= 12
    for i, (a, pa) in enumerate(placed):
        for b, pb in placed[i + 1:]:
            assert _distance(pa, pb) >= 60, f"{a} and {b} were packed too close to name"


def test_a_name_goes_outward_and_an_outline_s_node_is_not_named_twice(client):
    results = _results(client, "/show/family/performing/gjgf?layout=Compound")
    nodes = _nodes(results)
    assert nodes["family::performing"]["label_at"] == "none"
    assert nodes["family::sound"]["label_at"] == "none"
    sx, _ = _xy(nodes["family::sound"])
    for member in ("repo::gamma", "repo::delta"):
        side = nodes[member]["label_at"]
        if side in ("left", "right"):
            assert (side == "right") == (nodes[member]["x"] > sx), \
                f"{member}'s name faced into its ring"


def test_the_packed_index_is_smaller_than_the_code_layout_s(client, corpus):
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    reading = show_service.read(corpus)
    graph = show_service.index_graph(reading)
    options = PlotOptions(layout="Compound", palette_id="0", type="d3")

    def extent(drawn: dict) -> float:
        xs = [n["metadata"]["x"] for n in drawn["nodes"].values()]
        ys = [n["metadata"]["y"] for n in drawn["nodes"].values()]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    unpacked = extent(GraphSerializer.serialize_to_gjgf(graph, options))
    packed = extent(show_service.as_gjgf(graph, options))
    assert packed < unpacked / 2, "packing did not make the estate smaller"


def test_a_layout_the_reader_picks_is_left_as_it_draws(client):
    results = _results(client, "/show/index/gjgf?layout=Spectral")
    assert not any("label_at" in a for a in _nodes(results).values())


def test_a_project_s_view_is_a_ring_around_the_project(client):
    results = _results(client, "/show/project/alpha/gjgf?layout=Compound")
    nodes = _nodes(results)
    assert _xy(nodes["repo::alpha"]) == (0.0, 0.0)
    others = [_distance(_xy(a), (0.0, 0.0)) for n, a in nodes.items() if n != "repo::alpha"]
    assert min(others) > 30, "something was packed onto the project itself"


# --- the whole corpus: the index with each project's code in it --------------
#
# A project's code is the code map its show document in the corpus holds,
# read as data (`docs/show/project/<name>/show.json`); nothing is parsed or
# fetched to draw it.

def _code_document(where: Path, name: str, files: int = 3, commit: str = "c" * 40) -> None:
    """A show document for `name` holding a code map: its root, one
    subdirectory, and `files` files in each."""
    root = f"dir::example/{name}"
    sub = f"{root}/src"
    nodes = {root: {"id": root, "label": f"example/{name}", "depth": 0, "kind": "directory"},
             sub: {"id": sub, "label": "src", "depth": 0, "kind": "directory"}}
    edges = [{"source": root, "target": sub, "metadata": {"kind": "contains"}}]
    for holder in (root, sub):
        for i in range(files):
            leaf = f"file::{holder.removeprefix('dir::')}/f{i}.py"
            nodes[leaf] = {"id": leaf, "label": f"f{i}.py", "depth": 1, "kind": "file"}
            edges.append({"source": holder, "target": leaf, "metadata": {"kind": "contains"}})
    folder = where / "project" / name
    folder.mkdir(parents=True)
    (folder / "show.json").write_text(json.dumps({
        "schema": 1, "subject": {"kind": "project", "name": name},
        "provenance": {"source": {"repo": f"example/{name}", "commit": commit}},
        "views": {"code": {"graph": {"nodes": nodes, "edges": edges}}}, "files": {}}), encoding="utf-8")


def test_the_whole_corpus_draws_each_project_s_code_inside_it(corpus, client):
    _code_document(corpus / "docs" / "show", "alpha")
    results = _results(client, "/show/corpus/gjgf")
    nodes, edges = _nodes(results), _edges(results)
    code = {n: a for n, a in nodes.items() if n.startswith("code::alpha::")}
    assert len(code) == 8
    assert all(a.get("code") is True for a in code.values())
    # One depth below the project for each depth it had in its map.
    assert nodes["code::alpha::dir::example/alpha"]["depth"] == nodes["repo::alpha"]["depth"] + 1
    assert nodes["code::alpha::file::example/alpha/src/f0.py"]["depth"] == nodes["repo::alpha"]["depth"] + 2
    holds = {(e["source"], e["target"]) for e in edges if e.get("basis") == "parsed"}
    assert ("repo::alpha", "code::alpha::dir::example/alpha") in holds
    assert ("code::alpha::dir::example/alpha", "code::alpha::dir::example/alpha/src") in holds
    # Every family is still drawn, and the reader is told which projects have no code.
    assert {"family::core", "family::sound"} <= set(nodes)
    assert results["metadata"]["code"] == {"alpha": "c" * 40}
    assert "parsed" in results["metadata"]["bases"]
    assert "1 project(s)" in results["metadata"]["caveat"] and "gamma" in results["metadata"]["caveat"]


def test_a_private_member_s_code_is_never_drawn(corpus, client):
    # Mutation: read a document for every member the index draws -- the
    # private member's code is drawn, with its own path, and this fails.
    _code_document(corpus / "docs" / "show", "private-07")
    nodes = _nodes(_results(client, "/show/corpus/gjgf"))
    assert not [n for n in nodes if n.startswith("code::private-07::")]
    assert not [a for a in nodes.values() if a.get("code") and "private-07" in str(a.get("hover"))]


def test_the_whole_corpus_reads_the_code_maps_an_export_writes(corpus, client, tmp_path, monkeypatch):
    # The export writes every project's code map, then draws the index from
    # them, wherever it writes. Mutation: read the corpus's own docs/show
    # alone -- the export's fresh code maps are not drawn, and this fails.
    written = tmp_path / "out"
    _code_document(written, "alpha")
    monkeypatch.setenv("CODECARTO_SHOW_DOCS", str(written))
    nodes = _nodes(_results(client, "/show/corpus/gjgf"))
    assert "code::alpha::dir::example/alpha" in nodes


def test_a_project_s_code_is_packed_round_it_inside_its_family_s_outline(corpus, client):
    # Mutation: pack a project as a single node -- its code keeps the compound
    # layout's places, out across the estate, and this fails.
    _code_document(corpus / "docs" / "show", "alpha", files=12)
    _code_document(corpus / "docs" / "show", "gamma", files=6)
    results = _results(client, "/show/corpus/gjgf?layout=Compound")
    nodes, edges = _nodes(results), _edges(results)
    tops = [n for n, a in nodes.items() if a.get("depth") == 0 and not a.get("code")]
    circles = {n: _outline(nodes, edges, n) for n in tops}
    for project, family in (("alpha", "family::core"), ("gamma", "family::performing")):
        cx, cy, r = circles[family]
        for node_id in (n for n in nodes if n.startswith(f"code::{project}::")):
            assert _distance(_xy(nodes[node_id]), (cx, cy)) < r, \
                f"{node_id} was drawn outside {family}'s outline"
    for i, a in enumerate(tops):
        for b in tops[i + 1:]:
            ax, ay, ar = circles[a]
            bx, by, br = circles[b]
            assert _distance((ax, ay), (bx, by)) >= ar + br, f"{a}'s outline overlapped {b}'s"


def test_a_shared_member_carries_its_code_outside_every_outline(corpus, client):
    # delta is claimed by sound and by irl, so it sits outside both; its code
    # goes with it. Mutation: place a shared member alone -- its code keeps the
    # compound layout's places, and this fails.
    _code_document(corpus / "docs" / "show", "delta", files=8)
    results = _results(client, "/show/corpus/gjgf?layout=Compound")
    nodes, edges = _nodes(results), _edges(results)
    delta = _xy(nodes["repo::delta"])
    code = [_xy(a) for n, a in nodes.items() if n.startswith("code::delta::")]
    # No depth, as delta has none: the canvas groups a node into an outline by
    # its depth, and one with a depth and no parent at the depth above went
    # into the nearest outline. Mutation: give its code a depth below delta's
    # -- and this fails.
    assert all("depth" not in a for n, a in nodes.items() if n.startswith("code::delta::"))
    reach = max(_distance(delta, xy) for xy in code)
    for top in (n for n, a in nodes.items() if a.get("depth") == 0 and not a.get("code")):
        cx, cy, r = _outline(nodes, edges, top)
        for xy in code:
            assert _distance(xy, (cx, cy)) > r, f"delta's code was drawn inside {top}'s outline"
    assert reach < 600, f"delta's code reached {reach:.0f} from it"
