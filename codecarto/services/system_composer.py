"""Derive a system diagram from what a repository declares, not from a drawing.

**THE DIAGRAM IS ABOUT THE SYSTEM THE REPOSITORY DESCRIBES, NOT THE
REPOSITORY.** moat is the worked case: a homelab whose whole shape — which
charts exist, what deploys what, what is infrastructure and what is an
application — is already written down in the repo's own files. A hand-drawn
diagram of it would be a second copy that nothing keeps true; this derives the
picture from the declarations, so a chart added to the repo appears on the
monitor without anyone editing a layout.

WHAT IS READ, AND WHAT EACH THING PROVES. Every rule reads a file whose
*meaning* is fixed by the tool that consumes it, never a naming convention:

  * A directory holding `Chart.yaml` is a **chart** — that file is what Helm
    reads, and its `name`/`version` are authoritative for the component.
  * A `kind: Application` manifest inside a chart's `templates/` is an ArgoCD
    Application; its `spec.source.path` names the component it deploys. That
    gives **deploy edges** (in moat: `groot -> monitoring`, `groot -> traefik`,
    ...) from the file ArgoCD itself acts on.
  * `Chart.yaml dependencies:` whose `name` matches another local component is
    a **dependency edge**; entries pointing at an external `repository` are
    counted onto the component as its upstreams rather than drawn, because an
    edge to a node this repo does not define is an edge to a guess.
  * A directory holding `*.tf` is **infrastructure**; one holding a
    `Dockerfile` (and no Chart.yaml) is an **application** this repo builds.

EVENTS COME FROM THE HISTORY OF THE SAME CONTENTS. A commit is mapped onto the
components whose files it touched, so the event stream is "what changed in the
system", not "what happened to the repository". Two boundaries are stated
rather than hidden:

  * **Pull request state lives on the host and is not read here.** moat's pull
    requests land squashed, so the default branch has no `Merge pull request`
    subjects at all — the anchor other tools in this estate use is *empty* on
    this repo, and an empty read is not a clean one. What is derivable offline
    is branches: a local or fetched branch ref ahead of the default branch is
    an **in-flight change**, mapped to the components its commits touch. That
    is the offline proxy for "open pull request", named as a proxy.
  * **Nothing here observes the cluster.** A component's node reflects what
    the repo declares and what changed, never whether the pod is up. Runtime
    monitoring is a different feed with different credentials, and drawing an
    "up" state this module cannot know would be the lie the PAM monitor was
    built to avoid.

WHAT THIS DOES NOT DO. Guess topology. A component with no declared edge to
anything is drawn unconnected rather than attached to something plausible;
the gaps in the derived picture are facts about the repository's declarations.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Roles a component can be derived into. The strings are the seam with the
# frontend's node-type colouring; they are data, not prose.
CHART = "chart"
DEPLOYER = "deployer"
INFRA = "infrastructure"
APP = "application"

# How deep to look for component directories. Two levels covers `charts/x`
# and top-level components; deeper is template internals, not components.
DEPTH = 2

# Directories that are never components, wherever they appear.
IGNORED = {".git", ".github", "node_modules", "__pycache__", "templates"}


@dataclass
class Component:
    """One thing the repository declares the system to contain."""

    id: str                      # path-derived, stable: "charts/monitoring"
    name: str                    # Chart.yaml name where there is one
    role: str                    # CHART | DEPLOYER | INFRA | APP
    group: str                   # parent directory: "charts" or "."
    version: str = ""
    upstreams: list[str] = field(default_factory=list)  # external dep names
    deploys: list[str] = field(default_factory=list)    # component ids


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: str                    # "deploys" | "depends"


@dataclass(frozen=True)
class Change:
    """One commit, mapped onto the components it touched."""

    sha: str
    when: str                    # ISO date, from the commit
    subject: str
    components: tuple[str, ...]  # component ids, possibly empty


@dataclass(frozen=True)
class InFlight:
    """A branch ahead of the default branch — the offline proxy for a PR.

    Named a proxy on purpose: whether a pull request exists for the branch,
    and whether it is open, lives on the host. What the clone proves is only
    that these commits are not on the default branch yet.
    """

    branch: str
    commits: int
    components: tuple[str, ...]


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(("git", "-C", str(repo), *args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return done.stdout if done.returncode == 0 else ""


def _chart_meta(chart_yaml: Path) -> dict:
    try:
        loaded = yaml.safe_load(chart_yaml.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, yaml.YAMLError):
        # An unreadable Chart.yaml is still a chart directory; the component
        # keeps its path name and simply has no declared version.
        return {}


def _application_paths(chart_dir: Path) -> list[str]:
    """`spec.source.path` of every ArgoCD Application manifest in the chart.

    Parsed with the YAML parser, not a regex: a manifest is a document whose
    `kind` is `Application`, and a template that merely mentions the word in
    a comment must not create a deploy edge.
    """
    found: list[str] = []
    templates = chart_dir / "templates"
    if not templates.is_dir():
        return found
    for manifest in sorted(templates.glob("*.yaml")):
        try:
            for doc in yaml.safe_load_all(manifest.read_text(encoding="utf-8")):
                if not isinstance(doc, dict) or doc.get("kind") != "Application":
                    continue
                path = (((doc.get("spec") or {}).get("source") or {})
                        .get("path"))
                if isinstance(path, str) and path.strip():
                    found.append(path.strip().strip("/"))
        except yaml.YAMLError:
            # A helm template with {{ }} inside may not parse as YAML. That is
            # ordinary, and a manifest this cannot read contributes no edge --
            # under-drawing is the safe direction.
            continue
    return found


def discover(repo: Path) -> list[Component]:
    """Every component the repository's contents declare."""
    repo = Path(repo)
    found: list[Component] = []

    def is_component_dir(directory: Path) -> bool:
        return ((directory / "Chart.yaml").is_file()
                or any(directory.glob("*.tf"))
                or (directory / "Dockerfile").is_file())

    candidates: list[Path] = []
    for child in sorted(repo.iterdir()):
        if not child.is_dir() or child.name in IGNORED:
            continue
        candidates.append(child)
        # A directory that is itself a component owns everything under it --
        # `tofu/` with its own *.tf must not also yield `tofu/moat` as a
        # second component, because the inner directory is the outer one's
        # content, not a sibling system part.
        if is_component_dir(child):
            continue
        for grand in sorted(child.iterdir()):
            if grand.is_dir() and grand.name not in IGNORED:
                candidates.append(grand)

    for directory in candidates:
        rel = directory.relative_to(repo).as_posix()
        if rel.count("/") >= DEPTH:
            continue
        chart_yaml = directory / "Chart.yaml"
        if chart_yaml.is_file():
            meta = _chart_meta(chart_yaml)
            deploys = _application_paths(directory)
            component = Component(
                id=rel,
                name=str(meta.get("name") or directory.name),
                role=DEPLOYER if deploys else CHART,
                group=rel.rsplit("/", 1)[0] if "/" in rel else ".",
                version=str(meta.get("version") or ""),
                deploys=deploys,
            )
            for dep in meta.get("dependencies") or []:
                if isinstance(dep, dict) and dep.get("name"):
                    component.upstreams.append(str(dep["name"]))
            found.append(component)
        elif any(directory.glob("*.tf")):
            found.append(Component(id=rel, name=directory.name, role=INFRA,
                                   group=rel.rsplit("/", 1)[0] if "/" in rel
                                   else "."))
        elif (directory / "Dockerfile").is_file():
            found.append(Component(id=rel, name=directory.name, role=APP,
                                   group=rel.rsplit("/", 1)[0] if "/" in rel
                                   else "."))
    return found


def edges_of(components: list[Component]) -> list[Edge]:
    """Deploy and dependency edges, only between components that exist.

    A deploy path or a dependency name that resolves to no component yields no
    edge. The alternative -- inventing a node so the edge has somewhere to go
    -- would put things on the diagram the repository does not declare.
    """
    by_id = {c.id: c for c in components}
    by_name = {c.name: c for c in components}
    found: list[Edge] = []
    for component in components:
        for path in component.deploys:
            target = by_id.get(path)
            if target is not None and target.id != component.id:
                found.append(Edge(component.id, target.id, "deploys"))
        for upstream in component.upstreams:
            target = by_name.get(upstream)
            # A chart's dependency on its own name (argo-cd wrapping the
            # upstream argo-cd chart) is packaging, not an edge to itself.
            if target is not None and target.id != component.id:
                found.append(Edge(component.id, target.id, "depends"))
    return found


def _components_touched(repo: Path, sha: str,
                        components: list[Component]) -> tuple[str, ...]:
    files = _git(repo, "show", "--name-only", "--format=", sha).splitlines()
    prefixes = {c.id: c for c in sorted(components, key=lambda c: -len(c.id))}
    touched: list[str] = []
    for name in files:
        for prefix in prefixes:
            if name == prefix or name.startswith(prefix + "/"):
                if prefix not in touched:
                    touched.append(prefix)
                break
    return tuple(touched)


def history(repo: Path, components: list[Component],
            limit: int = 30) -> list[Change]:
    """The most recent changes, each mapped to the components it touched.

    Oldest first, because the consumer replays them in order and a monitor
    that plays history backwards reads as a system unwinding.
    """
    repo = Path(repo)
    out = _git(repo, "log", f"-{limit}", "--format=%h%x09%as%x09%s")
    changes: list[Change] = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        sha, when, subject = parts
        changes.append(Change(sha, when, subject,
                              _components_touched(repo, sha, components)))
    changes.reverse()
    return changes


def in_flight(repo: Path, components: list[Component]) -> list[InFlight]:
    """Branches ahead of the default branch, mapped to touched components.

    Reads refs this clone already has -- local heads and remote-tracking
    branches -- and fetches nothing. A branch that exists only on the host is
    invisible here, and that is a boundary of the offline reading, not a
    claim that nothing else is in flight.
    """
    repo = Path(repo)
    head = _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD").strip()
    default = head.rsplit("/", 1)[-1] if head else "main"
    base = f"origin/{default}"
    if not _git(repo, "rev-parse", "--verify", base).strip():
        base = default

    refs = [r.strip() for r in _git(
        repo, "for-each-ref", "--format=%(refname:short)",
        "refs/heads", "refs/remotes/origin").splitlines() if r.strip()]

    found: list[InFlight] = []
    seen: set[str] = set()
    for ref in refs:
        short = ref[len("origin/"):] if ref.startswith("origin/") else ref
        if short in (default, "HEAD") or short in seen:
            continue
        seen.add(short)
        count_text = _git(repo, "rev-list", "--count", f"{base}..{ref}").strip()
        count = int(count_text) if count_text.isdigit() else 0
        if not count:
            continue
        shas = _git(repo, "rev-list", f"{base}..{ref}").split()
        touched: list[str] = []
        for sha in shas[:20]:
            for component in _components_touched(repo, sha, components):
                if component not in touched:
                    touched.append(component)
        found.append(InFlight(short, count, tuple(touched)))
    return found


def compose(repo: Path) -> dict:
    """The whole derived picture, as one JSON-ready document.

    Carries its own provenance -- the commit the derivation read -- because a
    diagram is a claim about a tree at a commit and nowhere else.
    """
    repo = Path(repo)
    components = discover(repo)
    return {
        "system": repo.name,
        "commit": _git(repo, "rev-parse", "--short", "HEAD").strip(),
        "derived_from": "the repository's own declarations; see the module "
                        "docstring of system_composer.py for each rule",
        "components": [
            {
                "id": c.id, "name": c.name, "role": c.role, "group": c.group,
                "version": c.version, "upstreams": c.upstreams,
            }
            for c in components
        ],
        "edges": [
            {"source": e.source, "target": e.target, "kind": e.kind}
            for e in edges_of(components)
        ],
    }


def events(repo: Path, limit: int = 30) -> dict:
    """History and in-flight changes, mapped onto the derived components."""
    repo = Path(repo)
    components = discover(repo)
    return {
        "system": repo.name,
        "commit": _git(repo, "rev-parse", "--short", "HEAD").strip(),
        "changes": [
            {"sha": c.sha, "when": c.when, "subject": c.subject,
             "components": list(c.components)}
            for c in history(repo, components, limit)
        ],
        "in_flight": [
            {"branch": b.branch, "commits": b.commits,
             "components": list(b.components),
             "note": "a branch ahead of the default branch; whether a pull "
                     "request exists for it lives on the host and is not "
                     "read here"}
            for b in in_flight(repo, components)
        ],
    }
