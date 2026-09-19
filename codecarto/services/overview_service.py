"""`dossier`'s org overview, read as a seam and drawn on this canvas.

**THE OTHER WINDOW PRODUCES THIS ONE CONSUMES.** `dossier` assembles the org
overview -- masthead figures and a table per facet -- and can emit it as a data
seam (`dossier overview --json`). This service reads that seam and turns it into
a graph the canvas already knows how to draw. It is the mirror of
`capability_service`, which reads a file *both* windows share; here the file is
one window's reading of the estate, and this window renders it at the canvas's
resolution instead of the terminal's nine cells.

**REDACTION IS INHERITED, NEVER REPEATED.** The producer redacted every private
repository before it wrote the seam, so a name here is whatever `dossier` chose
to publish -- `private/<id>` or a real public name. This service adds no
privacy policy of its own and invents no name: it draws the bytes it was handed.
A seam that leaked a private name would be a defect in the producer, and this
window would faithfully draw the leak rather than paper over it.

**THE ONE INTERPRETIVE CHOICE, MADE OUT LOUD.** A section is a table, and a
table is not inherently a graph. What the overview *does* relate is which
subjects appear under which reading: the first column of a facet row is its
subject -- a repository, a branch's repository, a delta's repository. So the
graph drawn is exactly that and no more:

    scope    --has-->      each section the overview carried
    section  --lists-->    each distinct first-column subject in its rows

No edge is added to make the picture connected, and the masthead figures draw
nothing -- a count is a fact about the estate, not a relation between two things,
so it rides in the metadata rather than becoming a node with no edge.

**AN UNKNOWN SCHEMA DRAWS NOTHING.** A seam whose `schema` this window does not
know is answered with a reason, not a guess -- the same shape a governance pin
older than the capability registry takes. Reading a field whose meaning may have
changed is how two windows quietly start disagreeing about one estate.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The seam version this window knows how to read. `dossier.overview.as_dict`
# stamps the producer's; a number this does not recognise is declined rather
# than guessed.
KNOWN_SCHEMA = 1

# Where the seam is looked for when a caller names no path. An env var first,
# for a producer that writes it somewhere deliberate; then the working
# directory, the way `families.json` sits beside the clone that reads it.
SEAM_ENV = "DOSSIER_OVERVIEW_SEAM"
DEFAULT_SEAM = Path("overview.json")

# What each node is, so a palette colours by kind without this module choosing a
# colour. The renderer decides how a kind looks; this decides what a thing is.
SCOPE, SECTION, SUBJECT = "scope", "section", "subject"


@dataclass
class Reading:
    """A parse of the overview seam, or a reason it could not be drawn."""

    source: str
    scope: str = ""
    generated_from: str = ""
    masthead: list[dict[str, Any]] = field(default_factory=list)
    sections: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""

    @property
    def ok(self) -> bool:
        return not self.reason


def _seam_path(seam: Path | str | None) -> Path:
    if seam is not None:
        return Path(seam)
    return Path(os.environ.get(SEAM_ENV) or DEFAULT_SEAM)


def read(seam: Path | str | None = None) -> Reading:
    """Read the overview seam, declining rather than guessing on trouble."""
    path = _seam_path(seam)
    if not path.exists():
        return Reading(source=str(path), reason=(
            f"no overview seam at {path}. The producer writes it with "
            "`dossier overview --json`; point this window at it with "
            f"{SEAM_ENV} or place it in the working directory."))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return Reading(source=str(path), reason=f"the seam at {path} did not parse: {exc}")

    if not isinstance(data, dict):
        return Reading(source=str(path), reason=f"the seam at {path} is not an object")

    schema = data.get("schema")
    if schema != KNOWN_SCHEMA:
        return Reading(source=str(path), reason=(
            f"the seam declares schema {schema!r}; this window reads "
            f"{KNOWN_SCHEMA}. A field's meaning may have changed, so it is "
            "declined rather than read on the old assumption."))

    return Reading(
        source=str(path),
        scope=str(data.get("scope", "")),
        generated_from=str(data.get("generated_from", "")),
        masthead=list(data.get("masthead", [])),
        sections=list(data.get("sections", [])),
    )


def _subject(row: Any) -> str:
    """A row's subject: its first column, however the seam packed the row."""
    if isinstance(row, (list, tuple)) and row:
        return str(row[0]).strip()
    return ""


def as_graph(reading: Reading):
    """The overview as a `networkx` graph this project's serializer accepts.

    Imported inside the function so reading the seam does not require a graph
    library -- a window that cannot render should still be able to say what it
    was given, the choice every `as_graph` here makes.
    """
    import networkx as nx

    graph = nx.MultiDiGraph(kind="overview", source=reading.source,
                            scope=reading.scope, generated_from=reading.generated_from)

    scope = reading.scope or "the estate"
    graph.add_node(scope, label=scope, kind=SCOPE, hover=scope,
                   click=f"<p><b>{scope}</b></p>")

    for section in reading.sections:
        title = str(section.get("title", "")).strip()
        if not title:
            continue
        rows = section.get("rows", []) or []
        graph.add_node(title, label=title, kind=SECTION,
                       rows=len(rows), hover=f"{title} -- {len(rows)} row(s)",
                       click=f"<p><b>{title}</b><br/>{len(rows)} row(s)</p>")
        graph.add_edge(scope, title, label="has", stated=True)

        # Distinct first-column subjects, drawn once and linked to the section
        # they appear under. A blank first column adds nothing.
        for name in dict.fromkeys(_subject(r) for r in rows):
            if not name:
                continue
            graph.add_node(name, label=name, kind=SUBJECT, hover=name,
                           click=f"<p><code>{name}</code></p>")
            graph.add_edge(title, name, label="lists", stated=True)

    return graph


def caveat(reading: Reading) -> str:
    """The sentence a reader needs before believing the shape."""
    return (
        "This is dossier's reading, drawn here rather than recomputed -- every "
        "name is whatever the producer published, already redacted, and this "
        "window adds no name of its own. The only relation drawn is that a "
        "section lists a subject; the masthead figures are estate facts, not "
        "relations, and ride in the metadata rather than as unconnected nodes."
    )


def metadata(reading: Reading, options: Any = None) -> dict[str, Any]:
    """Graph-level facts the canvas and any other client both read."""
    return {
        "kind": "overview",
        "source": reading.source,
        "scope": reading.scope,
        "generated_from": reading.generated_from,
        "layout": getattr(options, "layout", "Kamada Kawai"),
        "type": getattr(options, "type", None),
        "palette_id": getattr(options, "palette_id", "0"),
        "sections": len(reading.sections),
        "masthead": reading.masthead,
        "caveat": caveat(reading),
    }


def as_gjgf(reading: Reading, options: Any = None) -> dict[str, Any]:
    """The reading in this project's graph format, laid out by its layouts.

    Everything after this call is the path every other graph in codecarto
    takes -- the same serializer, layouts and palettes -- so this view cannot
    drift from the canvas the way a bespoke renderer would.
    """
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    chosen = options or PlotOptions(layout="Kamada Kawai")
    return GraphSerializer.serialize_to_gjgf(as_graph(reading), chosen)
