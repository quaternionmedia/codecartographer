"""Every seam this window reads, and whether each one is there to read.

**A SEAM IS A SOURCE THIS WINDOW DRAWS AND DOES NOT OWN.** The harness's
topologies, the corpus's capability registry, dossier's overview, the prose
reader's archive listing -- each is produced by another repository and reaches
this one over HTTP or through a pinned file. `topology_service`,
`capability_service` and `overview_service` already share one shape: read a
document or a reason, build a `networkx` graph, hand it to the serializer, carry
a caveat in the metadata. This module names that shape and adds the one thing
none of them answers alone: **is the thing behind this seam there at all, and is
it the thing this window thinks it is.**

**IDENTITY, NOT REACHABILITY.** A port answering proves that something listens.
On this workstation several servers run at once, and one of them once spent an
afternoon being measured as another (`governance/qm/handbook/async-contract.md`
§4). So a seam is *identified* by asking the far side for a document whose shape
this window knows -- the harness's `/v1/topology/encoding` with its `schema`, the
registry file with its `capabilities` list -- and a 200 carrying something else
is reported as *something answered and it was not the harness*, which is a
different sentence from *down*.

**ABSENCE IS A SENTENCE, NEVER A GREEN ROW.** Every probe returns an `Identity`
that says what it found or why it found nothing, with the command that would
change the answer. A liveness table that showed a seam as absent by leaving its
row out would be a table of what happened to be up, which is not what anybody
asked.

**THE PROBES RUN NOTHING.** A probe reads one small document or stats one file.
It does not start a server, parse a repository or index an archive; the remedies
name the commands that do.

WHAT THIS CANNOT DO. Say that a seam's *content* is right. The harness can
identify itself and serve a topology whose weights are wrong; the registry can be
present and stale. Those are the caveats each service carries in its own
metadata, and this module reports only that there was something to carry them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from codecarto.services import capability_service, overview_service, qmcp_client

# Where the prose reader answers. Root two, the fourth constant in
# `governance/qm/ci/dashboard.py`'s allocation -- a memory aid and not a claim,
# overridable like every other address here.
PROSE_DEFAULT_BASE = "http://127.0.0.1:1414"
PROSE_START_COMMAND = "uv run qm dashboard --start prose"


def prose_base_url() -> str:
    return (os.environ.get("LOOKSATWORDS_URL") or PROSE_DEFAULT_BASE).rstrip("/")


@dataclass
class Identity:
    """What one probe found, or why it found nothing."""

    ok: bool
    where: str
    """The address or path that was asked."""

    schema: int | None = None
    """The schema the far side declared, when it declared one."""

    detail: str = ""
    """One sentence in the far side's own words -- a caption, a count of
    entries, a scope -- so a reader can tell two answering servers apart."""

    problem: str = ""
    remedy: str = ""


@dataclass
class Seam:
    """One source this window reads."""

    name: str
    role: str
    probe: Callable[[], Identity]
    routes: tuple[str, ...] = field(default_factory=tuple)
    """The routes this window serves from it, so a reader of the table can go
    from a live seam to the thing that draws it."""

    panel: str = ""
    """The panel that draws it, by registry id, or empty when nothing does yet.
    Stated rather than inferred: a seam with routes and no panel is exactly the
    gap the table is for."""


def probe_harness() -> Identity:
    """The harness, identified by its encoding document.

    `/v1/topology/encoding` is served wherever the harness is bound and names
    nobody, so it is safe to ask from any window. Its `schema` and `encoding`
    keys are what make a 200 count as the harness rather than as a port.
    """
    reach = qmcp_client.fetch("/v1/topology/encoding")
    if not reach.ok:
        return Identity(False, reach.where, problem=reach.problem, remedy=reach.remedy)
    document = reach.document
    schema = document.get("schema")
    encoding = document.get("encoding")
    if not isinstance(schema, int) or not isinstance(encoding, list):
        return Identity(
            False, reach.where,
            problem=("something answered at the harness's address and it did "
                     "not describe a topology encoding"),
            remedy=("check what is bound there -- `uv run qm dashboard` prints "
                    "the allocation and what holds each port"))
    return Identity(True, reach.where, schema=schema,
                    detail=f"{len(encoding)} encoding channel(s) declared")


def probe_corpus(corpus: Path | str | None = None) -> Identity:
    """The capability registry, at the pinned governance path."""
    reading = capability_service.read(corpus)
    if not reading.ok:
        return Identity(False, reading.source, problem=reading.reason,
                        remedy=("a propagation moves this project's governance "
                                "pin: `propagate/<name>-<date>` in the corpus, "
                                "merged into `project/<name>`, then the "
                                "submodule moved to that tip"))
    return Identity(True, reading.source, schema=1,
                    detail=f"{len(reading.capabilities)} capability declaration(s)")


def probe_overview(seam: Path | str | None = None) -> Identity:
    """dossier's overview seam, where a caller or the environment placed it."""
    reading = overview_service.read(seam)
    if not reading.ok:
        return Identity(False, reading.source, problem=reading.reason,
                        remedy=("the producer writes it with `dossier overview "
                                f"--json`; point this window at it with "
                                f"{overview_service.SEAM_ENV}"))
    return Identity(True, reading.source, schema=overview_service.KNOWN_SCHEMA,
                    detail=(f"scope {reading.scope or 'unstated'}, "
                            f"{len(reading.sections)} section(s)"))


def probe_prose() -> Identity:
    """The prose reader, identified by its own health document.

    It answers `/health` with a `status` and a `message` naming itself. A 200
    without those is some other server on that port.
    """
    reach = qmcp_client.fetch(
        "/health", base=prose_base_url(),
        remedy_404="this build of the reader does not answer /health")
    if not reach.ok:
        remedy = reach.remedy
        if reach.status is None and "nothing is answering" in reach.problem:
            remedy = f"start it with `{PROSE_START_COMMAND}`"
        return Identity(False, reach.where, problem=reach.problem, remedy=remedy)
    document = reach.document
    if not isinstance(document, dict) or "status" not in document:
        return Identity(
            False, reach.where,
            problem=("something answered at the prose reader's address and it "
                     "did not describe itself"),
            remedy="check what is bound there -- `uv run qm dashboard` prints it")
    return Identity(True, reach.where, detail=str(document.get("message") or
                                                 document.get("status") or ""))


SEAMS: tuple[Seam, ...] = (
    Seam("harness", "the work, and the only source of it", probe_harness,
         routes=("/topology/gjgf", "/topology/available", "/topology/data"),
         panel="topology-panel"),
    Seam("corpus", "what each named thing this estate can do has reached",
         probe_corpus,
         routes=("/capabilities/gjgf", "/capabilities/data"),
         panel="capabilities-panel"),
    Seam("overview", "dossier's reading of the estate, drawn here", probe_overview,
         routes=("/overview/gjgf", "/overview/data"),
         panel="overview-panel"),
    Seam("prose", "the archive's conversations, read as topics", probe_prose,
         routes=(), panel=""),
)

BY_NAME = {s.name: s for s in SEAMS}


def unknown_layout(error: ValueError, where: str) -> dict[str, Any]:
    """A layout nobody registered, as the envelope every estate route answers in.

    **STATUS 200, AND THE PROBLEM IN `results`**, the rule every estate router
    follows: the route worked, the seam answered, and the caller asked for a
    layout this window cannot compute. `Positions.get_layout_params` already
    raises a `ValueError` naming what *is* registered; this carries that
    sentence to the browser instead of letting it become a 500 with no detail,
    which is what `compound_layout` -- the name the front end's own menu is
    keyed by -- produced until the serializer normalised spellings.
    """
    from codecarto.services.position_service import Positions

    known = sorted(str(layout["name"]) for layout in
                   Positions(include_networkx=True, include_custom=True)._layouts)
    return {
        "unreadable": True,
        "problem": str(error),
        "remedy": ("choose one of the registered layouts: " + ", ".join(known)
                   + ". `/topology/available` lists them in the form the menu "
                   "uses"),
        "where": where,
    }


def survey(seams: tuple[Seam, ...] = SEAMS) -> list[dict[str, Any]]:
    """Every seam, probed once, as rows a table or a panel can render.

    **EVERY SEAM GETS A ROW**, live or not. The order is the declaration order,
    which is the order a reader starting the estate from nothing would bring
    them up.
    """
    rows = []
    for seam in seams:
        found = seam.probe()
        rows.append({
            "name": seam.name,
            "role": seam.role,
            "ok": found.ok,
            "where": found.where,
            "schema": found.schema,
            "detail": found.detail,
            "problem": found.problem,
            "remedy": found.remedy,
            "routes": list(seam.routes),
            "panel": seam.panel,
        })
    return rows


def caveat(rows: list[dict[str, Any]]) -> str:
    """The sentence a reader needs before believing the table."""
    live = sum(1 for r in rows if r["ok"])
    if not rows:
        return "no seams are declared"
    if live == len(rows):
        return ("every seam identified itself. That says each source is there "
                "and is what this window expects; it says nothing about "
                "whether what it holds is current")
    if live == 0:
        return ("no seam identified itself. Each row names what would change "
                "that; an estate with nothing up is the state a fresh "
                "workstation starts in, not a fault in this window")
    return (f"{live} of {len(rows)} seam(s) identified itself; the rest say "
            f"what would bring them up")
