"""What the derivation may claim, and the edge it must refuse to draw.

**THE DIAGRAM IS ABOUT THE SYSTEM THE REPOSITORY DESCRIBES.** Every component
and every edge here traces to a file whose meaning is fixed by the tool that
consumes it — Chart.yaml is what Helm reads, a `kind: Application` manifest is
what ArgoCD acts on. The tests build a miniature of moat's shape (a deployer
chart with Application manifests, plain charts, a terraform directory, a
Dockerfile app) in a real git repository, because every wrong answer a tool
like this can give is a wrong belief about files and refs, and a mock encodes
the belief and then agrees with it.

THE CASES ABOUT ABSENCE ARE THE POINT. A deploy path naming a component that
does not exist draws no edge; a helm template that cannot parse contributes
nothing; a nested directory inside a component is not a second component. In
each, the easy implementation produces a picture that looks like an answer.

THE MUTATIONS, per P16, quoted as they printed:

The Application `kind` check removed, so any template with a source.path
becomes a deploy edge:

    AssertionError: a non-Application manifest produced a deploy edge
    assert [Edge(source=...nd='deploys')] == []

The nested-component guard removed, so `infra/inner` appears beside `infra`
(the real repository's `tofu/moat` beside `tofu`):

    AssertionError: assert ['infra', 'infra/inner'] == ['infra']

The in-flight range reversed (`ref..base`), so a branch ahead reads as clean:

    AssertionError: assert [] == ['feature/db-tune']

External dependencies given invented nodes so their edges have somewhere to go:

    AssertionError: an edge was drawn to a component this repository does not
    define
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from codecarto.services import system_composer as sc


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={"GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.invalid",
             "GIT_COMMITTER_NAME": "T",
             "GIT_COMMITTER_EMAIL": "t@example.invalid",
             "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(repo),
             "PATH": __import__("os").environ["PATH"]})
    if done.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}:\n{done.stderr}")
    return done.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


APPLICATION = """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: web
spec:
  source:
    repoURL: git@example.invalid:homelab.git
    path: {path}
"""


@pytest.fixture()
def homelab(tmp_path: Path) -> Path:
    """A miniature of moat's shape, as a real repository with real history."""
    repo = tmp_path / "homelab"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")

    write(repo / "charts/web/Chart.yaml",
          "apiVersion: v2\nname: web\nversion: 1.2.0\n")
    write(repo / "charts/db/Chart.yaml",
          "apiVersion: v2\nname: db\nversion: 0.3.0\n"
          "dependencies:\n- name: web\n  version: 1.2.0\n"
          "- name: postgresql\n  repository: oci://example.invalid/charts\n"
          "  version: 16.0.0\n")
    write(repo / "charts/groot/Chart.yaml",
          "apiVersion: v2\nname: groot\nversion: 0.1.0\n")
    write(repo / "charts/groot/templates/web.yaml",
          APPLICATION.format(path="charts/web"))
    write(repo / "infra/main.tf", 'provider "example" {}\n')
    write(repo / "infra/inner/also.tf", "# nested, owned by infra\n")
    write(repo / "tower/Dockerfile", "FROM scratch\n")
    write(repo / "README.md", "homelab\n")

    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "bootstrap the homelab")
    write(repo / "charts/web/values.yaml", "replicas: 2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "scale web out")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


# ─── Discovery ────────────────────────────────────────────────────────────────


def test_components_are_what_the_files_declare(homelab):
    found = {c.id: c for c in sc.discover(homelab)}

    assert set(found) == {"charts/web", "charts/db", "charts/groot",
                          "infra", "tower"}
    assert found["charts/web"].role == sc.CHART
    assert found["charts/web"].version == "1.2.0"
    assert found["charts/groot"].role == sc.DEPLOYER
    assert found["infra"].role == sc.INFRA
    assert found["tower"].role == sc.APP


def test_a_directory_inside_a_component_is_not_a_second_component(homelab):
    """`infra/inner` holds .tf files and is `infra`'s content, the way
    `tofu/moat` is tofu's in the real repository."""
    infra = [c.id for c in sc.discover(homelab) if c.role == sc.INFRA]
    assert infra == ["infra"]


def test_an_external_dependency_is_an_upstream_not_an_edge(homelab):
    components = sc.discover(homelab)
    db = next(c for c in components if c.id == "charts/db")
    edges = sc.edges_of(components)

    assert "postgresql" in db.upstreams
    assert not any("postgresql" in (e.source, e.target) for e in edges), (
        "an edge was drawn to a component this repository does not define")


def test_deploy_edges_come_from_application_manifests(homelab):
    edges = sc.edges_of(sc.discover(homelab))

    assert sc.Edge("charts/groot", "charts/web", "deploys") in edges
    assert sc.Edge("charts/db", "charts/web", "depends") in edges


def test_a_manifest_that_is_not_an_application_yields_no_edge(homelab):
    """`kind` is checked, not the presence of a source.path — a ConfigMap
    mentioning a path must not become a deploy edge."""
    write(homelab / "charts/groot/templates/note.yaml",
          "kind: ConfigMap\nmetadata:\n  name: n\nspec:\n  source:\n"
          "    path: charts/db\n")

    edges = [e for e in sc.edges_of(sc.discover(homelab))
             if e.target == "charts/db" and e.kind == "deploys"]

    assert edges == [], "a non-Application manifest produced a deploy edge"


def test_a_deploy_path_naming_nothing_draws_nothing(homelab):
    write(homelab / "charts/groot/templates/ghost.yaml",
          APPLICATION.format(path="charts/not-there"))

    targets = {e.target for e in sc.edges_of(sc.discover(homelab))}

    assert "charts/not-there" not in targets


def test_an_unparseable_helm_template_contributes_nothing(homelab):
    """Helm templates full of {{ }} are ordinary and must not crash the
    derivation or invent edges."""
    write(homelab / "charts/groot/templates/tpl.yaml",
          "kind: {{ .Values.kind }}\n: not yaml at all {{\n")

    components = sc.discover(homelab)  # must not raise
    assert any(c.id == "charts/groot" for c in components)


# ─── History and in-flight ────────────────────────────────────────────────────


def test_history_maps_commits_onto_the_components_they_touched(homelab):
    components = sc.discover(homelab)
    changes = sc.history(homelab, components)

    assert changes[-1].subject == "scale web out"
    assert changes[-1].components == ("charts/web",)
    assert changes[0].subject == "bootstrap the homelab"
    assert set(changes[0].components) >= {"charts/web", "infra", "tower"}


def test_history_is_replayed_oldest_first(homelab):
    changes = sc.history(homelab, sc.discover(homelab))
    assert [c.subject for c in changes] == ["bootstrap the homelab",
                                           "scale web out"]


def test_a_branch_ahead_of_the_default_is_in_flight(homelab):
    git(homelab, "checkout", "-q", "-b", "feature/db-tune")
    write(homelab / "charts/db/values.yaml", "tuned: true\n")
    git(homelab, "add", "-A")
    git(homelab, "commit", "-q", "-m", "tune the db")
    git(homelab, "checkout", "-q", "main")

    flights = sc.in_flight(homelab, sc.discover(homelab))

    assert [f.branch for f in flights] == ["feature/db-tune"]
    assert flights[0].commits == 1
    assert flights[0].components == ("charts/db",)


def test_the_default_branch_is_never_in_flight(homelab):
    assert sc.in_flight(homelab, sc.discover(homelab)) == []


# ─── The composed documents ───────────────────────────────────────────────────


def test_compose_carries_its_provenance(homelab):
    doc = sc.compose(homelab)

    assert doc["system"] == "homelab"
    assert doc["commit"] == git(homelab, "rev-parse", "--short", "HEAD")
    assert len(doc["components"]) == 5
    assert {e["kind"] for e in doc["edges"]} == {"deploys", "depends"}


def test_events_name_the_in_flight_proxy_for_what_it_is(homelab):
    git(homelab, "checkout", "-q", "-b", "wip")
    write(homelab / "tower/main.py", "print('hi')\n")
    git(homelab, "add", "-A")
    git(homelab, "commit", "-q", "-m", "start the tower app")
    git(homelab, "checkout", "-q", "main")

    doc = sc.events(homelab)

    assert doc["in_flight"][0]["branch"] == "wip"
    assert "pull request" in doc["in_flight"][0]["note"], (
        "the offline proxy must say that PR state lives on the host")
