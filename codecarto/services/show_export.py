"""The triplet's graph leg, exported: one show document and its pictures per subject.

**THE PICTURES COME FROM THE WINDOW, NOT FROM HERE.** There is one drawing
path, the web renderer, and `web/tests/export/` runs it headlessly with the
harness the browser suite already has: it opens each subject's address, waits
for the drawing to settle, and writes the picture and the graph it drew. This
module decides which subjects there are, what a document says about where its
claims came from, and what must never be written, and checks what the harness
left.

**A SUBJECT'S CLAIMS DIGEST COVERS ITS OWN ROWS ONLY** -- a project's families,
their nesting and its roster entry; a family's own row and its nesting; every
family for the index -- so an edit elsewhere in the roster leaves the other
subjects' documents current.

**NOTHING MACHINE-SCOPED IS WRITTEN.** A document names the corpus by its host
repository and commit. The backend names what it read by where it sits on this
disk (`~/repos/qm/qm/families.json`), which is right for a window and wrong
for a committed file, so `scrub` refuses any home or drive path anywhere in a
document.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from codecarto.services import show_service

SCHEMA = 1

# The window's address grammar (`web/src/features/show/show_address.ts`).
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# A home folder or a drive, at the start of a value or after a space, quote or
# bracket: `~/`, `C:\` or `c:/`, `/home/`, `/Users/`.
MACHINE = re.compile(r"(?:^|[\s\"'(])(?:~[/\\]|[A-Za-z]:[\\/]|/home/|/Users/)")
# The window's words for the machine it runs on, true where it runs and of no
# other reader: a clone "beside this one" or "beside this checkout", "this disk".
MACHINE_WORDS = re.compile(r"\bbeside this (?:one|checkout)\b|\bthis disk\b|\bthis machine\b", re.I)


@dataclass(frozen=True)
class Subject:
    kind: str
    name: str = ""

    @property
    def address(self) -> str:
        """The window's `?show=` value for it."""
        return "index" if self.kind == "index" else f"{self.kind}:{self.name}"

    @property
    def folder(self) -> str:
        """Where its document and pictures go, under the export's folder."""
        return "index" if self.kind == "index" else f"{self.kind}/{self.name}"

    @property
    def views(self) -> tuple[str, ...]:
        return ("estate", "code", "system") if self.kind == "project" else ("estate",)


def parse_subject(text: str) -> Subject:
    """`index`, `family:<name>` or `project:<name>`, by a name the address takes."""
    if text == "index":
        return Subject("index")
    kind, _, name = text.partition(":")
    if kind not in ("family", "project") or not NAME.match(name):
        raise ValueError(f"{text!r} is not index, family:<name> or project:<name>")
    if show_service.PRIVATE.match(name):
        raise ValueError(f"{name} is a private member: counted on its family's graph, never drawn by name")
    return Subject(kind, name)


def subjects(reading: show_service.Reading, which: str) -> list[Subject]:
    """`all`: the index, then every family, then every public project, each by name.

    With an inventory, a public project is one the host lists: the site has a
    page for each of those, and a project's showgraph sits on its page. A name
    a family claims and the host does not list has no page to sit on.
    """
    if which != "all":
        return [parse_subject(part) for part in which.split(",") if part]
    families = [Subject("family", name) for name in sorted(reading.families)]
    named = [name for name in show_service.projects(reading)
             if not reading.inventory or name in reading.inventory]
    projects = [Subject("project", name) for name in sorted(named, key=str.lower)]
    return [Subject("index"), *families, *projects]


def _family_row(family: show_service.Family) -> dict[str, Any]:
    return {"name": family.name, "drives": family.drives, "within": family.within,
            "subfamilies": list(family.subfamilies), "members": list(family.members)}


def _nesting(reading: show_service.Reading, name: str) -> list[dict[str, Any]]:
    """The family `name` and each family it sits within, outward."""
    rows, seen = [], set()
    while name and name in reading.families and name not in seen:
        seen.add(name)
        rows.append(_family_row(reading.families[name]))
        name = reading.families[name].within or ""
    return rows


def claims(reading: show_service.Reading, subject: Subject) -> dict[str, Any]:
    """The rows of the corpus this subject's showgraph is drawn from."""
    if subject.kind == "index":
        return {"families": [_family_row(reading.families[n]) for n in sorted(reading.families)],
                "unstated": sorted(reading.unstated)}
    if subject.kind == "family":
        return {"families": _nesting(reading, subject.name)}
    claimed = sorted(f.name for f in reading.families.values() if subject.name in f.members)
    return {"families": [row for name in claimed for row in _nesting(reading, name)],
            "roster": reading.roster.get(subject.name)}


def claims_digest(reading: show_service.Reading, subject: Subject) -> str:
    """sha256 of the subject's own claim rows, as canonical JSON."""
    text = json.dumps(claims(reading, subject), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def scrub(document: Any, where: str = "") -> None:
    """Refuse a home or drive path, or the window's words for this machine,
    anywhere in `document`, naming where it is."""
    if isinstance(document, dict):
        for key, value in document.items():
            scrub(value, f"{where}.{key}" if where else str(key))
    elif isinstance(document, list):
        for i, value in enumerate(document):
            scrub(value, f"{where}[{i}]")
    elif isinstance(document, str) and (MACHINE.search(document) or MACHINE_WORDS.search(document)):
        raise ValueError(f"{where} names a place on this machine: {document!r}")


HOST_REPO = re.compile(r"github\.com[:/]+([A-Za-z0-9][\w.-]*)/([\w.-]+?)(?:\.git)?/?$")


def repo_of(url: str) -> str:
    """`owner/name` of a GitHub remote, in any of the forms git writes it."""
    found = HOST_REPO.search(url.strip())
    if not found:
        raise ValueError(f"{url!r} is not a GitHub repository")
    return f"{found.group(1)}/{found.group(2)}"


def _git(where: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(where), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def corpus_identity(corpus: Path) -> dict[str, str]:
    """The corpus as a document names it: its host repository, and the commit checked out."""
    return {"repo": repo_of(_git(corpus, "remote", "get-url", "origin")),
            "commit": _git(corpus, "rev-parse", "HEAD")}


def drawn_by(root: Path) -> str:
    """`codecartographer@<commit>` of the checkout drawing, marked when it has uncommitted changes."""
    commit = _git(root, "rev-parse", "HEAD")
    changed = bool(_git(root, "status", "--porcelain", "--untracked-files=no"))
    return f"codecartographer@{commit}{'+changes' if changed else ''}"


def default_branch_head(org: str, name: str) -> str | None:
    """The commit at the head of `org/name`'s default branch on the host, or None when it does not answer."""
    try:
        out = subprocess.run(["git", "ls-remote", f"https://github.com/{org}/{name}", "HEAD"],
                             capture_output=True, text=True, timeout=60, check=True).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    return out.split()[0] if out.split() else None


def manifest(reading: show_service.Reading, chosen: list[Subject], out: Path,
             corpus: dict[str, str], drawer: str,
             sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """What the browser harness draws, and what each document says about where it came from."""
    return {
        "out": str(out),
        "corpus": corpus,
        "drawn_by": {"graph": drawer},
        "drawn_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": sources,
        "subjects": [{"kind": s.kind, "name": s.name, "address": s.address, "folder": s.folder,
                      "views": list(s.views), "digest": claims_digest(reading, s)} for s in chosen],
    }


def missing(out: Path, chosen: list[Subject]) -> list[str]:
    """Each subject's document, and each file a document names, that is not there."""
    absent: list[str] = []
    for subject in chosen:
        folder = out / subject.folder
        document = folder / "show.json"
        if not document.is_file():
            absent.append(f"{subject.folder}/show.json")
            continue
        files = json.loads(document.read_text(encoding="utf-8")).get("files", {})
        absent += [f"{subject.folder}/{name}" for name in files.values() if not (folder / name).is_file()]
    return absent
