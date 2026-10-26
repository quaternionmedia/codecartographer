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
    monkeypatch.setenv("CODECARTO_REPO_ROOTS", str(clones))
    reading = show_service.read()
    links, _ = show_service.measured_links(reading, ["alpha"], [clones])
    assert sorted(link["target"] for link in links) == ["beta", "gamma"]
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
