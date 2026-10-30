"""How fast the corpus grows, read from its projects' histories: the rate a
show export's budgets have to outlast.

For each project an export drew a code map of, the clone of its repository
under a folder of clones is read up to the commit that map was drawn from.
Each month gives three numbers: the commits made, the bytes of the files the
parser reads at the month's end, and those bytes turned into code-map nodes
at the rate the project's map holds them today. The last is an estimate, not
a parse: it assumes a project's nodes per byte have not changed, which is the
assumption a projection forward makes anyway.

**A RATE IS A DOUBLING TIME**, fitted by least squares through log2 of the
last 6, 12 and 24 months. Growth that compounds is a straight line there, and
its slope's inverse is the months it takes to double.
"""

from __future__ import annotations

import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

SPANS = (6, 12, 24)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def parser_reads() -> set[str]:
    """Every extension the parser registry reads."""
    import codecarto.services.unified_parser_service  # noqa: F401 -- registers the parsers
    from codecarto.services.parsers.language_parser import ParserRegistry

    return {e.lower() for e in ParserRegistry.all_extensions()}


def months(first: str, last: str) -> list[str]:
    """Every `YYYY-MM` from `first` to `last`, both kept."""
    out, (year, number) = [], map(int, first.split("-"))
    while f"{year:04d}-{number:02d}" <= last:
        out.append(f"{year:04d}-{number:02d}")
        year, number = (year + 1, 1) if number == 12 else (year, number + 1)
    return out


def month_end(month: str) -> str:
    """The instant a month ends: the first of the next, at midnight UTC."""
    year, number = map(int, month.split("-"))
    year, number = (year + 1, 1) if number == 12 else (year, number + 1)
    return f"{year:04d}-{number:02d}-01T00:00:00Z"


def source_bytes(repo: Path, rev: str, reads: set[str]) -> int:
    """The bytes of the files at `rev` whose extension the parser reads."""
    total = 0
    for line in _git(repo, "ls-tree", "-r", "-l", rev).splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) == 4 and parts[1] == "blob" and parts[3].isdigit() and Path(path).suffix.lower() in reads:
            total += int(parts[3])
    return total


def doubling(values: Iterable[float], span: int) -> float | None:
    """Months for a monthly series to double, from its last `span` months
    above zero; None when it is not growing or has under three."""
    points = [(i, math.log2(v)) for i, v in enumerate(list(values)[-span:]) if v > 0]
    if len(points) < 3:
        return None
    mx = sum(x for x, _ in points) / len(points)
    my = sum(y for _, y in points) / len(points)
    spread = sum((x - mx) ** 2 for x, _ in points)
    slope = sum((x - mx) * (y - my) for x, y in points) / spread if spread else 0.0
    return 1 / slope if slope > 0 else None


def growth(clones: Path, show: Path, reads: set[str] | None = None) -> dict[str, Any]:
    """The month-by-month report: each project read, each month's totals and
    each series' doubling time. A project whose clone is missing, or lacks
    the commit its map was drawn from, is named and left out."""
    reads = reads if reads is not None else parser_reads()
    projects: dict[str, dict[str, Any]] = {}
    left_out: dict[str, str] = {}
    for document in sorted((show / "project").glob("*/show.json")):
        name = document.parent.name
        data = json.loads(document.read_text(encoding="utf-8"))
        commit = ((data.get("provenance") or {}).get("source") or {}).get("commit")
        graph = ((data.get("views") or {}).get("code") or {}).get("graph")
        nodes = len(graph.get("nodes") or {}) if isinstance(graph, dict) else 0
        repo = next((p for p in (clones / f"{name}.git", clones / name) if p.is_dir()), None)
        if not commit:
            left_out[name] = "its document names no source commit"
        elif repo is None:
            left_out[name] = "no clone"
        elif not _git(repo, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}").strip():
            left_out[name] = f"its clone lacks {commit[:7]}"
        else:
            made = Counter(stamp[:7] for stamp in _git(repo, "log", "--format=%aI", commit).split())
            size = source_bytes(repo, commit, reads)
            projects[name] = {"repo": repo, "commit": commit, "nodes": nodes, "bytes": size,
                              "per_byte": nodes / size if size else 0.0, "made": made,
                              "first": min(made) if made else None}

    rows: list[dict[str, Any]] = []
    started = [p["first"] for p in projects.values() if p["first"]]
    if started:
        last = max(m for p in projects.values() for m in p["made"])
        for month in months(min(started), last):
            row = {"month": month, "projects": 0, "commits": 0, "source_bytes": 0, "est_nodes": 0.0}
            for p in projects.values():
                row["commits"] += p["made"].get(month, 0)
                if not p["first"] or p["first"] > month:
                    continue
                row["projects"] += 1
                rev = _git(p["repo"], "rev-list", "-1", "--first-parent", f"--before={month_end(month)}",
                           p["commit"]).strip()
                if rev:
                    size = source_bytes(p["repo"], rev, reads)
                    row["source_bytes"] += size
                    row["est_nodes"] += size * p["per_byte"]
            row["est_nodes"] = round(row["est_nodes"])
            rows.append(row)

    series = ("projects", "commits", "source_bytes", "est_nodes")
    return {
        "through": rows[-1]["month"] if rows else None,
        "projects": {n: {k: p[k] for k in ("commit", "nodes", "bytes", "first")} for n, p in projects.items()},
        "left_out": left_out,
        "months": rows,
        "doubling_months": {s: {str(span): doubling([r[s] for r in rows], span) for span in SPANS}
                            for s in series},
    }


def summary(report: dict[str, Any], recent: int = 12) -> list[str]:
    """The last months, and how long each series takes to double."""
    lines = [f"{len(report['projects'])} projects read through {report['through']}"
             + (f"; left out: {', '.join(f'{n} ({why})' for n, why in report['left_out'].items())}"
                if report["left_out"] else "."), ""]
    for row in report["months"][-recent:]:
        lines.append(f"{row['month']}  {row['projects']:4d} projects  {row['commits']:6,d} commits  "
                     f"{row['source_bytes'] / 2 ** 20:8.1f} MB read  {row['est_nodes']:9,d} nodes (est.)")
    lines += ["", "Months to double, fitted over the last " + ", ".join(str(s) for s in SPANS) + " months:"]
    for name, spans in report["doubling_months"].items():
        said = ", ".join("not growing" if v is None else f"{v:.1f}" for v in spans.values())
        lines.append(f"  {name:14s} {said}")
    return lines
