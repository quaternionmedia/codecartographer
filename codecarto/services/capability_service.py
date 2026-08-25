"""The estate's capabilities as a graph this project already knows how to draw.

**THE VOCABULARY IS THE CORPUS'S AND THIS ADDS NONE OF ITS OWN.** The four rungs
-- design, deployment, execution, monitoring -- and what each declines to claim
are `governance/qm/records/DRAFT-a-capability-has-four-phases.md`. The claims are
`governance/qm/ci/capability-registry.yaml`. `dossier` is the other window onto
the same file; a rung that meant something different here would give two readings
of one estate with nothing able to say which is right.

**EVERY EDGE IS DECLARED, AND NOTHING IS ADDED TO MAKE THE PICTURE CONNECTED.**
That is the whole design constraint. A ladder of four rungs is a table, and
forcing it into a graph would draw relations nobody stated. What the registry
*does* declare is genuinely relational, and only these:

    capability  --claims-->      the one rung a human stated
    capability  --lives-in-->    the repository it belongs to
    capability  --design-->      the record that decided it
    capability  --deployment-->  the command that reaches it
    capability  --execution-->   the address its evidence points at
    capability  --monitoring-->  the document that watches it

**WHERE THE CONVERGENCE ACTUALLY IS, MEASURED RATHER THAN HOPED FOR.** Against
the registry as it stands, the repo and rung nodes are what several capabilities
point at -- two per repository, three claiming `execution`. **No artifact is
cited by more than one capability yet**, so the shared-record convergence this
shape allows has not happened with four declarations. That is a fact about the
registry rather than about the drawing, and it is stated here so nobody reads
the picture as denser than it is.

An unclaimed rung is drawn with no edges rather than omitted. That two rungs
have nothing at them is one of the more useful things this view can show, and a
node that appears only once somebody claims it would hide exactly that.

**AN `unknown` RUNG DRAWS NOTHING.** No node, no edge, no placeholder. A rung
nobody has established must not render as an edge to a box labelled "nothing" --
that is an absence drawn as a thing, and the corpus's rule is that a thing nobody
could measure must not render like a thing measured and found wanting. The count
of them travels in the metadata instead, so a reader knows how much of the
picture is missing without the picture inventing it.

**THE CLAIM IS ONE EDGE, NOT FOUR.** A capability at `execution` has reached
`design` and `deployment` too, but the registry declares one phase and the
ordering is what implies the rest. Drawing an edge to each reached rung would
turn one stated fact into three drawn ones.

WHAT THIS CANNOT SEE. Whether any pointer is true. It reads that a pointer was
written down; nothing here runs the command or resolves the address. A capability
claiming `deployment` and naming a command nobody can run draws exactly like one
that works -- which is the defect the record was written about, so the limit
rides in the metadata as a caveat rather than being left for a reader to assume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Where the corpus is mounted in this project. The same submodule path
# `governance/qm` every QM project uses.
CORPUS = Path("governance/qm")
REGISTRY = Path("ci") / "capability-registry.yaml"

RUNGS = ("design", "deployment", "execution", "monitoring")
"""Ordered, and the corpus's. If these disagree with `ci/capabilities.py` in the
corpus, that file is right and this is the copy to repair."""

UNKNOWN = "unknown"

# What each node is, so a palette can colour by kind without this module
# choosing a colour. The renderer decides how a kind looks; this decides what
# kind a thing is.
CAPABILITY, RUNG, REPO, ARTIFACT = "capability", "rung", "repo", "artifact"


@dataclass
class Reading:
    """The registry as this window read it, or why it could not."""

    capabilities: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    source: str = ""

    @property
    def ok(self) -> bool:
        return not self.reason


def read(corpus: Path | str | None = None) -> Reading:
    """Every capability the corpus declares. **Runs nothing.**

    An absent registry is a reason rather than an empty list: a submodule pinned
    before the file existed is not an estate that declares no capabilities, and
    the two must not render alike.
    """
    import yaml

    root = Path(corpus) if corpus else CORPUS
    path = root / REGISTRY
    if not path.is_file():
        return Reading(source=str(path), reason=(
            f"no capability registry at {path.as_posix()}. The governance pin "
            f"may predate it."))
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        return Reading(source=str(path),
                       reason=f"{path.as_posix()} did not parse: {error}")

    declared = data.get("capabilities")
    if not isinstance(declared, list):
        return Reading(source=str(path),
                       reason=f"{path.as_posix()}: `capabilities` is not a list")
    # A row that cannot be named cannot be matched to itself next time, which is
    # the rule every addressed row in this estate follows.
    return Reading(source=str(path),
                   capabilities=[entry for entry in declared
                                 if isinstance(entry, dict) and entry.get("id")])


def pointer(entry: dict[str, Any], rung: str) -> str:
    """The evidence pointer for one rung, or `unknown`.

    A missing key and an explicit `null` read the same. Neither says the rung
    was checked and found wanting.
    """
    value = (entry.get("evidence") or {}).get(rung)
    return str(value) if value else UNKNOWN


def unmeasured(reading: Reading) -> int:
    """How many rungs across the estate name no evidence at all.

    **The number the picture cannot show**, because those rungs draw nothing.
    Carried in the metadata so a reader can tell a sparse estate from a
    sparsely drawn one.
    """
    return sum(1 for entry in reading.capabilities for rung in RUNGS
               if pointer(entry, rung) == UNKNOWN)


def as_graph(reading: Reading):
    """The registry as a `networkx` graph this project's serializer accepts.

    Imported inside the function so that reading the registry does not require
    a graph library -- a window that cannot render should still be able to say
    what it was given. The same choice `topology_service.as_graph` makes.
    """
    import networkx as nx

    graph = nx.MultiDiGraph(kind="capabilities", source=reading.source,
                            unmeasured=unmeasured(reading))

    for rung in RUNGS:
        graph.add_node(rung, label=rung, kind=RUNG,
                       hover=f"rung: {rung}",
                       click=f"<p>The <b>{rung}</b> rung.</p>")

    for entry in reading.capabilities:
        name = str(entry["id"])
        title = str(entry.get("title", name))
        graph.add_node(
            name, label=title, kind=CAPABILITY,
            phase=str(entry.get("phase", UNKNOWN)),
            hover=f"{title} -- claims {entry.get('phase', UNKNOWN)}",
            click=_click_for(entry))

        repo = str(entry.get("repo") or "").strip()
        if repo:
            graph.add_node(repo, label=repo, kind=REPO, hover=repo,
                           click=f"<p>Repository <b>{repo}</b></p>")
            graph.add_edge(name, repo, label="lives-in", stated=True)

        phase = str(entry.get("phase", ""))
        if phase in RUNGS:
            # One edge, to the rung a human stated. The rungs below it are
            # implied by the ordering and are not drawn as separate facts.
            graph.add_edge(name, phase, label="claims", stated=True)

        for rung in RUNGS:
            where = pointer(entry, rung)
            if where == UNKNOWN:
                # Draws nothing. An absence must not become a box.
                continue
            graph.add_node(where, label=where, kind=ARTIFACT, hover=where,
                           click=f"<p><code>{where}</code></p>")
            graph.add_edge(name, where, label=rung, stated=True)

    return graph


def _click_for(entry: dict[str, Any]) -> str:
    """What a renderer shows when somebody opens a capability.

    Includes `cannot_see` deliberately: the limit a capability states about
    itself is the part a reader of a picture is least likely to have."""
    rows = "".join(
        f"<li><b>{rung}</b>: {pointer(entry, rung)}</li>" for rung in RUNGS)
    return (f"<p><b>{entry.get('title', entry['id'])}</b></p>"
            f"<p>{entry.get('what', '')}</p>"
            f"<p>Claims <b>{entry.get('phase', UNKNOWN)}</b>, stated by "
            f"{entry.get('stated_by', 'nobody')} on "
            f"{entry.get('stated_on', 'no date')}.</p>"
            f"<ul>{rows}</ul>"
            f"<p><i>Cannot see: {entry.get('cannot_see', '')}</i></p>")


def caveat(reading: Reading) -> str:
    """The sentence a reader needs before believing the shape."""
    missing = unmeasured(reading)
    return (
        "Every edge here was declared in the registry; nothing was added to "
        "make the graph connected. A pointer is where to look, never what was "
        "found -- this window runs no command and resolves no address, so a "
        "capability naming a command that does not exist draws like one that "
        f"works. {missing} rung(s) name no evidence and draw nothing at all."
    )


def metadata(reading: Reading, options: Any = None) -> dict[str, Any]:
    """Graph-level facts the canvas and any other client both read."""
    chosen = options
    return {
        "kind": "capabilities",
        "source": reading.source,
        "layout": getattr(chosen, "layout", "Kamada Kawai"),
        "type": getattr(chosen, "type", None),
        "palette_id": getattr(chosen, "palette_id", "0"),
        "capabilities": len(reading.capabilities),
        "rungs": list(RUNGS),
        "unmeasured": unmeasured(reading),
        "caveat": caveat(reading),
    }


def as_gjgf(reading: Reading, options: Any = None) -> dict[str, Any]:
    """The reading in this project's graph format, laid out by its layouts.

    Everything after this call is the path every other graph in codecarto
    takes. A capability view that rendered itself would reimplement all of it
    and drift from it the first time either changed.
    """
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    chosen = options or PlotOptions(layout="Kamada Kawai")
    return GraphSerializer.serialize_to_gjgf(as_graph(reading), chosen)
