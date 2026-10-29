"""Every family and project the corpus names, drawn as the triplet's graph leg.

The corpus's docs site gives each family and each public project a page, with
pictures a person picked (`ci/showcase.yaml`). This draws the same subjects as
graphs, from the same claims those pages are generated from, so a page's
pictures and its showgraph are two readings of one document. The plan is
`plans/the-triplet.md` in the corpus.

**THE VOCABULARY IS THE CORPUS'S.** Which families exist, what each drives, which
sits within which, and who is in each come from `families.json`. Phase and
attention come from the roster, recency from the inventory, family hues from
`ci/palette.py`, and seams from `ci/interop-registry.yaml`. A family renamed
there is renamed here on the next read. Nothing in this module names a family.

**EVERY EDGE HAS A BASIS, AND THE THREE ARE NEVER MERGED.**

    claim     families.json: a family contains a subfamily or a member, and a
              repository claimed by two families is a member of each
    declared  ci/interop-registry.yaml: a repository implements a surface
              another publishes
    measured  a member's own manifests name another estate repository by its
              URL on the host

A measured edge never places a repository. Family membership is a claim a
person made (`records/DRAFT-a-family-is-bordered-by-what-it-drives.md` §1), and a
dependency graph that moved a member would be the measurement asserting it.

**A REPOSITORY IN TWO FAMILIES IS DRAWN ONCE.** Schema 2 made membership a
relation, not a function, so drawing a shared member inside one family's
outline would have the picture assert what the document no longer says. On the
index it sits outside both outlines, with a `member_of` edge to each; on a
family's own graph it sits inside that family, with a `member_of` edge to a
marker for each other family that claims it.

**A PRIVATE MEMBER IS COUNTED AND NEVER NAMED.** The corpus refers to one as
`private-NN`; this draws it as "a private member" with nothing to open.

**THE WHOLE CORPUS IS THE INDEX WITH EACH PROJECT'S CODE IN IT.** Its code is
the code map the corpus's own show document for it holds
(`docs/show/project/<name>/show.json`, written by `codecarto show export`), read
as data: nothing is parsed or fetched to draw it, and a project with no such
document is drawn alone and counted in the caveat.

**AN ABSENCE IS A SENTENCE.** A corpus with no `families.json`, or one at a
schema this window does not read, is a `reason`, never an empty estate. A
roster, an inventory or a registry that is missing is a note in the metadata:
the graph still draws, and says what it could not see.

WHAT THIS CANNOT SEE. Whether a claim is true. It reads that a person placed a
repository in a family and draws that; it cannot tell whether the repository
drives what the family drives. And a measured edge is only as current as the
clone it was read from, which this window does not fetch.
"""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from codecarto.services import clones
from codecarto.services import corpus as corpus_root

FAMILIES_FILE = Path("families.json")
ROSTER_FILE = Path("ci") / "workspace.yaml"
INVENTORY_FILE = Path("status") / "inventory.yaml"
INTEROP_FILE = Path("ci") / "interop-registry.yaml"
PALETTE_FILE = Path("ci") / "palette.py"
SHOW_DOCS = Path("docs") / "show"

KNOWN_SCHEMAS = (1, 2)
"""The `families.json` schemas this window draws. Schema 1 is flat; schema 2
adds `within`, `subfamilies` and `all_members`."""

PRIVATE = re.compile(r"^private-\d+$")

CLAIM, DECLARED, MEASURED = "claim", "declared", "measured"
# A project's code, as its show document's code map holds it: no claim, no
# seam, and nothing measured between repositories.
PARSED = "parsed"

# How each basis is drawn. The renderer reads `style`, `color` and `size` off an
# edge's metadata, so the legend can say what each look means.
LOOK = {
    CLAIM: {"style": "solid", "color": "#8a93a6", "size": 1.5},
    DECLARED: {"style": "solid", "color": "#e0a526", "size": 2.5},
    MEASURED: {"style": "dashed", "color": "#4fb3ad", "size": 1.5},
    PARSED: {"style": "solid", "color": "#56688f", "size": 0.75},
}

# Files a member's own dependencies are measured from, read at the clone's
# default branch rather than its working tree.
MANIFESTS = (".gitmodules", "pyproject.toml", "package.json", "Cargo.toml")

# The corpus is vendored by every governed project; drawing it as an edge would
# add one spoke per member and say nothing the governed mark does not.
CORPUS_NAME = "qm"

# This project, as the corpus names it: its pin is `project/codecartographer`
# (`.gitmodules`), so a listing of the corpus's project branches without that
# one was not fetched in full.
THIS_PROJECT = "codecartographer"

VIEWS = ("estate", "code", "system")


@dataclass
class Family:
    name: str
    drives: str
    within: str | None = None
    subfamilies: list[str] = field(default_factory=list)
    members: list[str] = field(default_factory=list)
    all_members: list[str] = field(default_factory=list)


@dataclass
class Reading:
    """The corpus as this window read it, or why it could not."""

    source: str = ""
    reason: str = ""
    root: Path | None = None
    schema: int | None = None
    commit: str | None = None
    generated_at: str = ""
    families: dict[str, Family] = field(default_factory=dict)
    unstated: list[str] = field(default_factory=list)
    roster: dict[str, dict[str, Any]] = field(default_factory=dict)
    inventory: dict[str, dict[str, Any]] = field(default_factory=dict)
    surfaces: list[dict[str, Any]] = field(default_factory=list)
    governed: set[str] | None = None
    hues: dict[str, tuple[str, str]] = field(default_factory=dict)
    org: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.reason

    def claimed_by(self, repo: str) -> list[str]:
        """The families that name `repo` as their own member, in file order."""
        return [f.name for f in self.families.values() if repo in f.members]


def _rows(value: Any) -> list[Any]:
    """The list a document holds where a list belongs, or none.

    A number or a mapping there is read as nothing rather than iterated.
    """
    return value if isinstance(value, list) else []


def _yaml(path: Path, notes: list[str], what: str) -> dict[str, Any]:
    """A mapping the corpus keeps, or `{}` with a note saying why not."""
    import yaml

    where = corpus_root.shown(path)
    if not path.is_file():
        notes.append(f"no {what} at {where}")
        return {}
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        notes.append(f"{where} is not UTF-8, so no {what} was read")
        return {}
    except yaml.YAMLError as error:
        notes.append(f"{where} did not parse: {error}")
        return {}
    if value is not None and not isinstance(value, dict):
        notes.append(f"{where} is not a mapping, so no {what} was read")
        return {}
    return value or {}


def _hues(path: Path, notes: list[str]) -> dict[str, tuple[str, str]]:
    """`FAMILY` from the corpus's palette, read as a literal and never executed."""
    where = corpus_root.shown(path)
    if not path.is_file():
        notes.append(f"no palette at {where}; families draw uncoloured")
        return {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        notes.append(f"{where} is not UTF-8; families draw uncoloured")
        return {}
    except SyntaxError as error:
        notes.append(f"{where} did not parse: {error}")
        return {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "FAMILY"):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                break
            if not isinstance(value, dict):
                break
            return {str(k): (str(v[0]), str(v[1])) for k, v in value.items()
                    if isinstance(v, (tuple, list)) and len(v) == 2}
    notes.append(f"{where} declares no FAMILY mapping literal; families "
                 f"draw uncoloured")
    return {}


def _governed(root: Path, roster: dict[str, dict[str, Any]],
              notes: list[str]) -> set[str] | None:
    """Repositories governance reaches: a `project/<name>` branch, or the corpus.

    The same reading `ci/cookbook.py`'s `adopted_names` makes. `None` when that
    is unknown, which is never drawn as "not adopted": git could not answer, or
    its answer is short. A checkout of the pin's commit alone, as CI's
    `--depth 1` makes, lists no project branch and git exits 0; a single-branch
    clone lists one at most. Either lacks `project/<THIS_PROJECT>`, the branch
    this project's own pin is on, and so says nothing about anyone else's.
    """
    out = corpus_root.git(root, "for-each-ref", "--format=%(refname)",
                          "refs/remotes/origin/project", "refs/heads/project")
    if out is None:
        notes.append("git could not list the corpus's project branches, so "
                     "whether a member is governed is unknown")
        return None
    names = {line.rsplit("project/", 1)[-1] for line in out.splitlines() if line}
    if THIS_PROJECT not in names:
        notes.append(f"the corpus checkout has no project/{THIS_PROJECT} branch, "
                     f"this project's own, so it holds few project branches or "
                     f"none (a shallow or single-branch checkout) and whether a "
                     f"member is governed is unknown")
        return None
    names |= {name for name, row in roster.items() if row.get("role") == "corpus"}
    return names


def read(corpus: Path | str | None = None) -> Reading:
    """Everything the showgraphs are drawn from. **Runs nothing but read-only git.**"""
    root = Path(corpus) if corpus else corpus_root.root()
    path = root / FAMILIES_FILE
    where = corpus_root.shown(path)
    reading = Reading(source=where, root=root)
    if not path.is_file():
        reading.reason = (f"no families document at {where}. The "
                          f"governance pin may predate it.")
        return reading
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        reading.reason = f"{where} is not UTF-8"
        return reading
    except json.JSONDecodeError as error:
        reading.reason = f"{where} did not parse: {error}"
        return reading
    if not isinstance(document, dict):
        reading.reason = f"{where} is not a JSON object"
        return reading

    schema = document.get("schema")
    reading.schema = schema if isinstance(schema, int) else None
    if reading.schema not in KNOWN_SCHEMAS:
        reading.reason = (f"{where} is at schema {schema!r}; this window "
                          f"draws schemas {', '.join(map(str, KNOWN_SCHEMAS))}")
        return reading
    if document.get("families") is not None and not isinstance(document["families"], list):
        reading.reason = f"{where}: `families` is not a list"
        return reading

    for entry in _rows(document.get("families")):
        if not isinstance(entry, dict) or not entry.get("name"):
            continue
        members = [str(m) for m in _rows(entry.get("members"))]
        within = entry.get("within")
        reading.families[str(entry["name"])] = Family(
            name=str(entry["name"]),
            drives=str(entry.get("drives") or ""),
            within=within if isinstance(within, str) and within else None,
            subfamilies=[str(s) for s in _rows(entry.get("subfamilies"))],
            members=members,
            all_members=[str(m) for m in _rows(entry.get("all_members")) or members],
        )
    reading.unstated = [str(u) for u in _rows(document.get("unstated"))]
    reading.generated_at = str(document.get("generated_at") or "")
    reading.commit = corpus_root.commit(root)

    notes = reading.notes
    roster = _yaml(root / ROSTER_FILE, notes, "roster")
    for row in _rows(roster.get("repositories")):
        if isinstance(row, dict) and (row.get("name") or row.get("ref")):
            reading.roster[str(row.get("name") or row.get("ref"))] = row

    inventory = _yaml(root / INVENTORY_FILE, notes, "inventory")
    generator = inventory.get("generator")
    org = generator.get("org") if isinstance(generator, dict) else None
    reading.org = org if isinstance(org, str) and org else None
    for row in _rows(inventory.get("repositories")):
        if isinstance(row, dict) and row.get("name") and not row.get("private"):
            reading.inventory[str(row["name"])] = row
    if not reading.org:
        notes.append(f"no organisation is known ({INVENTORY_FILE.as_posix()}'s "
                     f"generator.org), so nothing is measured: a manifest names a "
                     f"repository by its URL on the host, and a URL is matched by "
                     f"the organisation")

    interop = _yaml(root / INTEROP_FILE, notes, "interop registry")
    reading.surfaces = [s for s in _rows(interop.get("surfaces"))
                        if isinstance(s, dict) and s.get("id")]

    reading.hues = _hues(root / PALETTE_FILE, notes)
    reading.governed = _governed(root, reading.roster, notes)
    return reading


# --- what can be shown ------------------------------------------------------

def projects(reading: Reading) -> list[str]:
    """Every public repository a family or the roster names, in first-seen order."""
    seen: dict[str, None] = {}
    for family in reading.families.values():
        for member in family.members:
            seen.setdefault(member, None)
    for name in reading.roster:
        seen.setdefault(name, None)
    return [name for name in seen if not PRIVATE.match(name)]


def private_members(reading: Reading) -> list[str]:
    """Every private member a family names, once each, in first-seen order.

    A private member two families claim is one member, as a public one is.
    """
    return list(dict.fromkeys(m for f in reading.families.values()
                              for m in f.members if PRIVATE.match(m)))


def subjects(reading: Reading) -> dict[str, Any]:
    """The index of what can be drawn, as a panel lists it."""
    return {
        "families": [{
            "name": f.name,
            "drives": f.drives,
            "within": f.within,
            "subfamilies": f.subfamilies,
            "members": len(f.members),
            "all_members": len(f.all_members),
            "hue": _hue(reading, f.name),
        } for f in reading.families.values()],
        "projects": [{
            "name": name,
            "families": reading.claimed_by(name),
            "governed": _is_governed(reading, name),
            "phase": str((reading.roster.get(name) or {}).get("phase") or ""),
            "description": str((reading.inventory.get(name) or {}).get("description") or ""),
            "views": list(VIEWS),
        } for name in projects(reading)],
        "unstated": len(reading.unstated),
        "private": len(private_members(reading)),
    }


# --- drawing ----------------------------------------------------------------

def _hue(reading: Reading, family: str | None, scheme: int = 1) -> str | None:
    """A family's hue for the canvas. Scheme 1 is the dark theme the window opens in."""
    pair = reading.hues.get(family or "")
    return pair[scheme] if pair else None


def _is_governed(reading: Reading, name: str) -> bool | None:
    return None if reading.governed is None else name in reading.governed


def _governance_word(reading: Reading, name: str) -> str:
    governed = _is_governed(reading, name)
    return {True: "governed", False: "not adopted", None: "governance unknown"}[governed]


def _family_node(graph, reading: Reading, name: str, *, depth: int | None,
                 elsewhere: bool = False) -> str:
    node_id = f"family::{name}"
    if node_id in graph:
        return node_id
    family = reading.families.get(name)
    drives = family.drives if family else "a family this corpus does not declare"
    attrs: dict[str, Any] = {
        "label": f"{name} ↗" if elsewhere else name,
        "kind": "family",
        "family": name,
        "drives": drives,
        "elsewhere": elsewhere,
        "shape": "hexagon",
        "hover": f"{name} — drives {drives}",
        "click": (f"<p>The <b>{name}</b> family drives {drives}.</p>"
                  + (f"<p>Within <b>{family.within}</b>.</p>" if family and family.within else "")
                  + (f"<p>{len(family.all_members)} member(s) in all.</p>" if family else "")),
        "show": f"family:{name}",
    }
    hue = _hue(reading, name)
    if hue:
        attrs["color"] = hue
    if depth is not None:
        attrs["depth"] = depth
    graph.add_node(node_id, **attrs)
    return node_id


def _repo_node(graph, reading: Reading, name: str, *, depth: int | None,
               hue_of: str | None = None, also_in: list[str] = (),
               elsewhere: bool = False) -> str:
    node_id = f"repo::{name}"
    if node_id in graph:
        return node_id
    attrs: dict[str, Any]
    if PRIVATE.match(name):
        attrs = {"label": "a private member", "kind": "private",
                 "hover": "a private member, counted and not named",
                 "click": "<p>A private member. The corpus counts it and does not name it.</p>"}
    else:
        row = reading.roster.get(name) or {}
        host = reading.inventory.get(name) or {}
        governed = _governance_word(reading, name)
        phase = str(row.get("phase") or "no phase stated")
        attention = str(row.get("attention") or "unstated")
        recency = str(host.get("recency") or "unknown")
        description = str(host.get("description") or "")
        attrs = {
            "label": f"{name} ↗" if elsewhere else name,
            "kind": "project" if governed == "governed" else "repository",
            "governed": _is_governed(reading, name),
            "phase": phase,
            "attention": attention,
            "recency": recency,
            "elsewhere": elsewhere,
            "also_in": list(also_in),
            "hover": f"{name} — {phase} · {governed}"
                     + (f" · also in {', '.join(also_in)}" if also_in else ""),
            "click": (f"<p><b>{name}</b>{' — ' + description if description else ''}</p>"
                      f"<p>{governed}. Phase <b>{phase}</b> "
                      f"({row.get('phase_source') or 'unstated'}); attention "
                      f"<b>{attention}</b> (claims) beside recency <b>{recency}</b> "
                      f"(measured).</p>"
                      + (f"<p>Also in {', '.join(also_in)}.</p>" if also_in else "")),
            "show": f"project:{name}",
        }
        attrs["shape"] = "square" if governed == "governed" else "circle"
    hue = _hue(reading, hue_of)
    if hue:
        attrs["color"] = hue
    if depth is not None:
        attrs["depth"] = depth
    graph.add_node(node_id, **attrs)
    return node_id


def _edge(graph, source: str, target: str, basis: str, kind: str, label: str,
          hover: str = "", **extra: Any) -> None:
    graph.add_edge(source, target, kind=kind, label=label, basis=basis,
                   stated=basis != MEASURED, hover=hover or f"{label} ({basis})",
                   **LOOK[basis], **extra)


def _end(value: Any) -> str:
    """The repository at one end of a surface, `{repo: ...}`, or none."""
    return str(value.get("repo") or "") if isinstance(value, dict) else ""


def _declared(graph, reading: Reading, drawn: set[str]) -> int:
    """Every surface with an end among `drawn`, as implementation -> publisher."""
    count = 0
    for surface in reading.surfaces:
        publisher = _end(surface.get("publisher"))
        protocol = str(surface.get("protocol") or surface["id"])
        for implementation in _rows(surface.get("implementations")):
            implementer = _end(implementation)
            if not publisher or not implementer:
                continue
            if publisher not in drawn and implementer not in drawn:
                continue
            for name in (publisher, implementer):
                if name not in drawn:
                    _repo_node(graph, reading, name, depth=None, elsewhere=True,
                               hue_of=next(iter(reading.claimed_by(name)), None))
            _edge(graph, f"repo::{implementer}", f"repo::{publisher}", DECLARED,
                  "seam", protocol,
                  hover=f"{implementer} implements {surface['id']}, published by "
                        f"{publisher} (declared in ci/interop-registry.yaml)")
            count += 1
    return count


_MANIFESTS_READ: dict[tuple[str, str], dict[str, str]] = {}


def _manifests(clone: Path) -> dict[str, str] | None:
    """Every manifest at the clone's default branch, by name, in one git call.

    Kept per commit, so a second drawing reads nothing and a clone that moved
    is read again: the key is the commit the default branch is at, not the
    clone's path. `None` when git could not read the clone, which is kept for
    nothing: the next drawing asks again.
    """
    commit = clones.default_commit(clone)
    if commit is None:
        return {}
    key = (str(clone), commit)
    if key in _MANIFESTS_READ:
        return _MANIFESTS_READ[key]
    import subprocess

    request = "".join(f"{commit}:{name}\n" for name in MANIFESTS)
    try:
        done = subprocess.run(["git", "-C", str(clone), "cat-file", "--batch"],
                              input=request.encode("utf-8"), capture_output=True,
                              timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        # Raises nothing, and its empty answer is not "no manifests".
        return None
    found: dict[str, str] = {}
    data, at = done.stdout, 0
    for name in MANIFESTS:
        end = data.find(b"\n", at)
        if end < 0:
            break
        header = data[at:end].decode("utf-8", "replace").split()
        at = end + 1
        if len(header) == 3 and header[1] == "blob":
            size = int(header[2])
            found[name] = data[at:at + size].decode("utf-8", "replace")
            at += size + 1
    _MANIFESTS_READ[key] = found
    return found


def measured_links(reading: Reading, repos: list[str],
                   among: list[Path] | None = None) -> tuple[list[dict[str, str]], list[str]]:
    """Each estate repository a member's manifests name by its host URL.

    Returns the links and the members nothing was measured for: each with no
    clone, or one git could not read, or every one when no organisation is
    known. Only a URL on the host naming this organisation resolves; a package
    that merely shares a repository's name is not a link, because drawing a
    guess would be the measurement asserting a claim.
    """
    estate = set(projects(reading))
    if not reading.org:
        return [], [r for r in repos if not PRIVATE.match(r)]
    # A name ends at anything a name cannot hold: a quote, `/`, `#`, a tag's
    # `@` or a query's `?`. The host and the organisation match in any case,
    # as the host reads them.
    url = re.compile(rf"(?i:github\.com[/:]{re.escape(reading.org)})/"
                     rf"([A-Za-z0-9._-]+?)(?:\.git)?(?=[^A-Za-z0-9._-]|$)",
                     re.MULTILINE)
    links: list[dict[str, str]] = []
    unread: list[str] = []
    for repo in repos:
        if PRIVATE.match(repo):
            continue
        clone = clones.find(repo, among)
        manifests = None if clone is None else _manifests(clone)
        if manifests is None:
            unread.append(repo)
            continue
        seen: set[str] = set()
        for manifest, text in manifests.items():
            for target in url.findall(text):
                if target in estate and target not in (repo, CORPUS_NAME) and target not in seen:
                    seen.add(target)
                    links.append({"source": repo, "target": target, "file": manifest})
    return links, unread


def _measured(graph, reading: Reading, drawn: set[str],
              among: list[Path] | None = None) -> tuple[int, list[str]]:
    links, unread = measured_links(reading, sorted(drawn), among)
    for link in links:
        if link["target"] not in drawn:
            _repo_node(graph, reading, link["target"], depth=None, elsewhere=True,
                       hue_of=next(iter(reading.claimed_by(link["target"])), None))
        _edge(graph, f"repo::{link['source']}", f"repo::{link['target']}", MEASURED,
              "depends_on", f"measured from {link['file']}",
              hover=f"{link['source']}'s {link['file']} names {link['target']}")
    return len(links), unread


def _undeclared(graph, reading: Reading) -> list[dict[str, str]]:
    """Measured links no surface declares: seams somebody has not stated.

    One direction only. A declared seam with no measured link is the ordinary
    case -- MIDI and OSC appear in no manifest -- and is not reported.
    """
    declared = {(u, v) for u, v, d in graph.edges(data=True) if d.get("basis") == DECLARED}
    declared |= {(v, u) for u, v in declared}
    return [{"source": u.split("::", 1)[1], "target": v.split("::", 1)[1]}
            for u, v, d in graph.edges(data=True)
            if d.get("kind") == "depends_on" and (u, v) not in declared]


def family_graph(reading: Reading, name: str, among: list[Path] | None = None):
    """One family: its subfamilies, its members, and every seam touching them."""
    import networkx as nx

    family = reading.families[name]
    graph = nx.MultiDiGraph(kind="show", subject=f"family:{name}")
    root = _family_node(graph, reading, name, depth=0)
    inner = set(family.subfamilies)
    drawn: set[str] = set()

    def place(member: str, parent: str, depth: int, hue_of: str) -> None:
        if member in drawn:
            # Claimed twice within this family: one outline holds it, and the
            # second claim is an edge rather than a second home.
            _edge(graph, f"repo::{member}", parent, CLAIM, "member_of", "also in")
            return
        elsewhere = [f for f in reading.claimed_by(member) if f != hue_of
                     and f not in inner and f != name]
        node = _repo_node(graph, reading, member, depth=depth, hue_of=hue_of,
                          also_in=elsewhere)
        _edge(graph, parent, node, CLAIM, "contains", "member")
        drawn.add(member)
        for other in elsewhere:
            marker = _family_node(graph, reading, other, depth=None, elsewhere=True)
            _edge(graph, node, marker, CLAIM, "member_of", "also in")

    for sub in family.subfamilies:
        if sub not in reading.families:
            continue
        sub_node = _family_node(graph, reading, sub, depth=1)
        _edge(graph, root, sub_node, CLAIM, "contains", "within")
        for member in reading.families[sub].members:
            place(member, sub_node, 2, sub)
    for member in family.members:
        place(member, root, 1, name)

    if family.within:
        outer = _family_node(graph, reading, family.within, depth=None, elsewhere=True)
        _edge(graph, root, outer, CLAIM, "within", "within")

    declared = _declared(graph, reading, drawn)
    measured, unread = _measured(graph, reading, drawn, among)
    graph.graph.update(declared=declared, measured=measured, unread=unread,
                       undeclared=_undeclared(graph, reading))
    return graph


def index_graph(reading: Reading, among: list[Path] | None = None):
    """Every family, its nesting, and each member drawn once."""
    import networkx as nx

    graph = nx.MultiDiGraph(kind="show", subject="index")
    depth_of: dict[str, int] = {}

    def family_depth(name: str, seen: frozenset = frozenset()) -> int:
        family = reading.families.get(name)
        if not family or not family.within or family.within in seen:
            return 0
        return family_depth(family.within, seen | {name}) + 1

    for name in reading.families:
        depth_of[name] = family_depth(name)
        _family_node(graph, reading, name, depth=depth_of[name])
    for family in reading.families.values():
        if family.within in reading.families:
            _edge(graph, f"family::{family.within}", f"family::{family.name}",
                  CLAIM, "contains", "within")

    drawn: set[str] = set()
    for member in projects(reading) + private_members(reading):
        claimed = reading.claimed_by(member)
        if not claimed:
            continue
        drawn.add(member)
        if len(claimed) == 1:
            node = _repo_node(graph, reading, member, hue_of=claimed[0],
                              depth=depth_of[claimed[0]] + 1)
            _edge(graph, f"family::{claimed[0]}", node, CLAIM, "contains", "member")
        else:
            # Outside every outline, so the picture asserts no single home.
            node = _repo_node(graph, reading, member, depth=None, also_in=claimed)
            for name in claimed:
                _edge(graph, node, f"family::{name}", CLAIM, "member_of", "member of")

    declared = _declared(graph, reading, drawn)
    measured, unread = _measured(graph, reading, drawn, among)
    graph.graph.update(declared=declared, measured=measured, unread=unread,
                       undeclared=_undeclared(graph, reading))
    return graph


def _code_map(reading: Reading, name: str) -> dict[str, Any] | None:
    """`name`'s code map as the corpus's show document for it holds it, and
    the commit it was drawn from, or None when there is none to read."""
    # An export reads the code maps it has just written, wherever it writes them.
    docs = os.environ.get("CODECARTO_SHOW_DOCS")
    if docs:
        path = Path(docs) / "project" / name / "show.json"
    elif reading.root is not None:
        path = reading.root / SHOW_DOCS / "project" / name / "show.json"
    else:
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict):
        return None
    code = ((document.get("views") or {}).get("code") or {})
    graph = code.get("graph") if isinstance(code, dict) else None
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), dict):
        return None
    source = (document.get("provenance") or {}).get("source") or {}
    return {"nodes": graph["nodes"], "edges": [e for e in _rows(graph.get("edges")) if isinstance(e, dict)],
            "commit": source.get("commit") if isinstance(source, dict) else None}


def corpus_graph(reading: Reading, among: list[Path] | None = None):
    """Every family, each member drawn once, and inside each project its code:
    the index (`index_graph`) with its projects' code (`_with_code`)."""
    graph = index_graph(reading, among)
    graph.graph["subject"] = "corpus"
    _with_code(graph, reading)
    return graph


def family_code_graph(reading: Reading, name: str, among: list[Path] | None = None):
    """One family with each of its projects' code inside it, its subfamilies'
    too: the family's code view, the part of the whole corpus that is this
    family's (`family_graph`, `_with_code`).

    **ONE PER FAMILY, NOT ONE FOR THE CORPUS.** Every project's code map drawn
    to its symbols is some thirty thousand nodes, a picture several times the
    size the whole corpus's was; a family's is a fraction of that, and the
    family is the grouping its projects are read in already."""
    graph = family_graph(reading, name, among)
    _with_code(graph, reading)
    return graph


def _with_code(graph, reading: Reading) -> None:
    """Each project `graph` draws, with its code map from the corpus's show
    document for it inside it.

    A code node is `code::<project>::<id>`, one depth below its project for
    each depth it had in the map, marked `code` so the layout packs it as a
    disc round the project. A private member has no document and is drawn as
    the estate draws it. Sets `code_drawn` (each project drawn with its code,
    and the commit its map was drawn from) and `code_missing`.
    """
    drawn: dict[str, str | None] = {}
    missing: list[str] = []
    for repo, attrs in list(graph.nodes(data=True)):
        if not repo.startswith("repo::") or attrs.get("kind") == "private":
            continue
        name = repo.removeprefix("repo::")
        code = _code_map(reading, name)
        if code is None:
            missing.append(name)
            continue
        # A member two families claim has no depth, so no outline holds it,
        # and its code none either: given one, the canvas, finding no parent
        # at the depth above, set each node in the nearest outline instead.
        shared = not isinstance(attrs.get("depth"), int)
        base = 0 if shared else attrs["depth"] + 1
        ids = {}
        for node_id, node in code["nodes"].items():
            if not isinstance(node, dict):
                continue
            depth = node.get("depth") if isinstance(node.get("depth"), int) else 1
            ids[node_id] = f"code::{name}::{node_id}"
            path = str(node_id).split("::", 1)[-1]
            graph.add_node(ids[node_id], label=str(node.get("label") or path.rsplit("/", 1)[-1]),
                           kind=str(node.get("kind") or "file"), code=True, hover=f"{name}: {path}",
                           **({} if shared else {"depth": base + depth}))
        held = set()
        for edge in code["edges"]:
            kind = (edge.get("metadata") or {}).get("kind") or edge.get("kind")
            source, target = ids.get(edge.get("source")), ids.get(edge.get("target"))
            if kind == "contains" and source and target:
                _edge(graph, source, target, PARSED, "contains", "holds")
                held.add(target)
        for code_id in ids.values():
            if code_id not in held:
                _edge(graph, repo, code_id, PARSED, "contains", "its code")
        drawn[name] = code["commit"]
    graph.graph.update(code_drawn=drawn, code_missing=missing)


def _records(root: Path, name: str) -> list[dict[str, str]] | None:
    """The records on `project/<name>`: each one's title and status, or `None`."""
    for ref in (f"refs/remotes/origin/project/{name}", f"refs/heads/project/{name}"):
        if corpus_root.git(root, "rev-parse", "--verify", "--quiet", ref) is None:
            continue
        out = corpus_root.git(root, "grep", "-I", "-E", r"^# |^\| \*\*Status\*\*",
                              ref, "--", "adr/*.md")
        if out is None:
            return []
        found: dict[str, dict[str, str]] = {}
        for line in out.splitlines():
            # `<ref>:<path>:<text>`
            _, _, rest = line.partition(":")
            path, _, text = rest.partition(":")
            if path.endswith(("README.md", "TEMPLATE.md")):
                continue
            row = found.setdefault(path, {"path": path, "title": Path(path).stem,
                                          "status": "unstated"})
            if text.startswith("# ") and row["title"] == Path(path).stem:
                row["title"] = text[2:].strip()
            elif "**Status**" in text:
                # `| **Status** | Proposed |`; a line with no cell after it
                # states nothing.
                cells = text.split("|")
                status = cells[2].strip().strip("*") if len(cells) > 2 else ""
                row["status"] = status or "unstated"
        return list(found.values())
    return None


def project_graph(reading: Reading, name: str, corpus: Path | str | None = None):
    """One repository's place in the estate: its claims, its records, its seams."""
    import networkx as nx

    from codecarto.services import capability_service

    graph = nx.MultiDiGraph(kind="show", subject=f"project:{name}")
    families = reading.claimed_by(name)
    node = _repo_node(graph, reading, name, depth=None,
                      hue_of=next(iter(families), None), also_in=families[1:])
    for family in families:
        marker = _family_node(graph, reading, family, depth=None)
        _edge(graph, node, marker, CLAIM, "member_of", "member of")

    row = reading.roster.get(name) or {}
    for key, basis, label in (("phase", CLAIM, "phase"), ("attention", CLAIM, "attention")):
        value = str(row.get(key) or "unstated")
        fact = f"{key}::{value}"
        graph.add_node(fact, label=f"{label}: {value}", kind="claim",
                       hover=f"{label} {value}, a claim in ci/workspace.yaml")
        _edge(graph, node, fact, basis, "claims", label)
    host = reading.inventory.get(name) or {}
    recency = str(host.get("recency") or "unknown")
    graph.add_node(f"recency::{recency}", label=f"recency: {recency}", kind="measurement",
                   hover=f"recency {recency}, measured from the default branch's last commit")
    _edge(graph, node, f"recency::{recency}", MEASURED, "measured", "recency")

    root = Path(corpus) if corpus else corpus_root.root()
    records = _records(root, name)
    if records is not None:
        branch = f"branch::project/{name}"
        graph.add_node(branch, label=f"project/{name}", kind="branch", depth=0,
                       hover=f"project/{name}: this project's records in the corpus")
        _edge(graph, node, branch, MEASURED, "governed_by", "records on")
        for record in records:
            record_id = f"record::{record['path']}"
            graph.add_node(record_id, label=record["title"], kind="record", depth=1,
                           status=record["status"],
                           hover=f"{record['title']} — {record['status']}")
            _edge(graph, branch, record_id, MEASURED, "contains", record["status"])

    capabilities = capability_service.read(root)
    for entry in capabilities.capabilities if capabilities.ok else []:
        if str(entry.get("repo") or "").split("/")[-1] != name:
            continue
        cap_id = f"capability::{entry['id']}"
        graph.add_node(cap_id, label=str(entry.get("title") or entry["id"]),
                       kind="capability", phase=str(entry.get("phase") or "unknown"),
                       hover=f"{entry.get('title')} — claims {entry.get('phase')}")
        _edge(graph, cap_id, node, DECLARED, "lives_in", f"claims {entry.get('phase')}")

    _declared(graph, reading, {name})
    measured, unread = _measured(graph, reading, {name})
    graph.graph.update(measured=measured, unread=unread,
                       records=None if records is None else len(records),
                       undeclared=_undeclared(graph, reading))
    return graph


# --- what travels with a graph ----------------------------------------------

def provenance(reading: Reading) -> dict[str, Any]:
    """Where the graph was read from, which commit, and whether it was the pin."""
    return {
        "source": reading.source,
        "commit": reading.commit,
        "schema": reading.schema,
        "generated_at": reading.generated_at,
        "overridden": corpus_root.overridden(),
    }


def caveat(reading: Reading, graph) -> str:
    """The sentences a reader needs before believing the shape."""
    parts = ["Membership is a claim a person made in the roster; this draws it "
             "and cannot tell whether a repository drives what its family "
             "drives. Solid grey edges are claims, gold edges are seams "
             "declared in the interop registry, and dashed edges are measured "
             "from a member's own manifests and never place it."]
    unread = graph.graph.get("unread") or []
    if unread and not reading.org:
        # Every member is unread then, clone or no clone, and the clone is
        # not the reason.
        parts.append(f"No organisation is known, so nothing was measured for "
                     f"{len(unread)} member(s): {', '.join(unread)}. A manifest "
                     f"names a repository by its URL on the host, and a URL is "
                     f"matched by the inventory's organisation.")
    elif unread:
        parts.append(f"{len(unread)} member(s) had no clone beside this one, or "
                     f"one git could not read, so nothing was measured for them: "
                     f"{', '.join(unread)}.")
    if "code_drawn" in graph.graph:
        drawn = graph.graph.get("code_drawn") or {}
        missing = graph.graph.get("code_missing") or []
        parts.append(f"Each project's code is the code map its show document in "
                     f"the corpus holds, drawn from its default branch: "
                     f"{len(drawn)} project(s)"
                     + (f"; {len(missing)} with no code map drawn yet are drawn "
                        f"alone: {', '.join(missing)}." if missing else "."))
    undeclared = graph.graph.get("undeclared") or []
    if undeclared:
        parts.append(f"{len(undeclared)} measured link(s) have no declared seam: "
                     + ", ".join(f"{u['source']} → {u['target']}" for u in undeclared)
                     + ". Each is a seam nobody has stated, not a fault.")
    return " ".join(parts)


def metadata(reading: Reading, graph, options: Any = None) -> dict[str, Any]:
    """Graph-level facts the canvas, the provenance strip and any client read."""
    return {
        "kind": "show",
        "subject": graph.graph.get("subject"),
        "source": reading.source,
        "generated_at": reading.generated_at,
        "commit": reading.commit,
        "provenance": provenance(reading),
        "layout": getattr(options, "layout", "Kamada Kawai"),
        "type": getattr(options, "type", None),
        "palette_id": getattr(options, "palette_id", "0"),
        "bases": {basis: dict(LOOK[basis]) for basis in (CLAIM, DECLARED, MEASURED)
                  + ((PARSED,) if "code_drawn" in graph.graph else ())},
        "declared": graph.graph.get("declared"),
        "measured": graph.graph.get("measured"),
        "unread": graph.graph.get("unread") or [],
        "undeclared": graph.graph.get("undeclared") or [],
        "unstated": len(reading.unstated),
        "notes": list(reading.notes),
        # The whole corpus, or a family's code view: each project whose code
        # is drawn, and the commit of its default branch its map was drawn from.
        **({"code": graph.graph.get("code_drawn") or {}} if "code_drawn" in graph.graph else {}),
        "caveat": caveat(reading, graph),
    }


def as_gjgf(graph, options: Any = None) -> dict[str, Any]:
    """The graph in this project's format, laid out by its layouts."""
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    from codecarto.services import show_layout
    from codecarto.services.position_service import layout_key

    chosen = options or PlotOptions(layout="Kamada Kawai")
    drawn = GraphSerializer.serialize_to_gjgf(graph, chosen)
    # The compound layout is the one a showgraph opens in. It spaces groups
    # for a code graph's symbols, so a showgraph's groups are re-placed as
    # rings packed in rows; any other layout the reader picks is theirs.
    if layout_key(chosen.layout) == "compound_layout":
        show_layout.pack(drawn, str(graph.graph.get("subject") or ""))
    return drawn
