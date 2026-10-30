"""What a show export costs, measured: the numbers a redraw is held to.

**A PICTURE'S COST IS ITS ELEMENTS, NOT ITS BYTES.** GitHub Pages sends each
picture gzipped -- a 22.5 MB code map arrives as 2 MB -- but the browser
parses and paints every element whatever the wire carried. `picture` counts
them by what they draw (marks, links, labels, outlines), and the labels a
reader could see at the picture's own size.

**WHAT A PICTURE CARRIES BEYOND WHAT IT SHOWS IS COUNTED APART.** Elements: the
labels the window hides, and each mark's `<title>`, which a page showing the
picture as an image never shows (opened on its own, a browser shows it on
hover). Bytes: the window's interaction data (`data-*`), a colour stated
twice (a `style` beside the presentation attributes it repeats), and
decimals past the first. A lean writer drops these with nothing on the page
changing, so they bound what one is worth before it is written.

**A PAGE IS WHAT OPENS WITH IT.** `page` sums the pictures a built page embeds,
the eager ones (fetched as the page opens) apart from the lazy (fetched as
they scroll into view).

**NOTHING HERE TIMES ANYTHING.** Elements and bytes are the same on every
machine; how long a browser takes to draw them is not. `web/scripts/
measure-draw.mjs` times each picture and page in Chromium, and `measure`
folds its answer in when given one, with the machine it ran on.

`measure` gathers all of it over an export folder, and a built site when one
is given. `compare` sets one report against another, and `over_budget` names
what exceeds `BUDGETS` (docs/scale.md says where each comes from).
"""

from __future__ import annotations

import gzip
import io
import json
import re
import statistics
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = 1

# The smallest label a reader can read, in screen pixels at the picture's own
# size. Pages draw a picture no larger than that, so a label under it is
# unreadable everywhere it is shown.
LEGIBLE_PX = 8.0

# What one page or picture may cost. docs/scale.md derives each.
BUDGETS = {
    "picture_elements": 15_000,
    "page_open_elements": 15_000,
    "page_elements": 75_000,
    "unseen_labels": 0,
}

PRESENTATION = ("fill", "stroke", "stroke-width", "fill-opacity", "stroke-opacity",
                "font-size", "opacity", "stroke-dasharray")
SCALE = re.compile(r"scale\(\s*([-\d.eE+]+)")
NUMBER = re.compile(r"[-\d.eE+]+")
EXCESS = re.compile(r"\d\.(\d{2,})")
FONT_PX = re.compile(r"font-size:\s*([\d.]+)px")
IMG = re.compile(r"<img\b[^>]*>")
SRC = re.compile(r'\bsrc="([^"]+)"')
LEVELS = ("index", "family", "project")


def _scale(element: ET.Element) -> float:
    """How much this element enlarges what it holds: its transform's scales,
    and an `<svg>`'s width over its viewBox's."""
    factor = 1.0
    for match in SCALE.findall(element.get("transform", "")):
        factor *= abs(float(match))
    if element.tag.rpartition("}")[2] == "svg" and element.get("viewBox") and element.get("width"):
        box = NUMBER.findall(element.get("viewBox", ""))
        width = NUMBER.findall(element.get("width", ""))
        if len(box) == 4 and width and float(box[2]):
            factor *= float(width[0]) / float(box[2])
    return factor


def _font_px(element: ET.Element, inherited: float) -> float:
    stated = element.get("font-size")
    if stated and NUMBER.match(stated):
        return float(NUMBER.match(stated).group(0))
    style = FONT_PX.search(element.get("style", ""))
    return float(style.group(1)) if style else inherited


def _hidden(element: ET.Element) -> bool:
    style = element.get("style", "").replace(" ", "")
    return (element.get("visibility") == "hidden" or element.get("display") == "none"
            or "visibility:hidden" in style or "display:none" in style)


def picture(path: Path) -> dict[str, Any]:
    """One SVG picture's weight, what its elements draw, and what it carries
    beyond what it shows. A label is shown when nothing hides it and it is at
    least `LEGIBLE_PX` high at the picture's own size; the window keeps the
    labels it hides (`visibility: hidden`), which a picture parses and never
    shows."""
    raw = path.read_bytes()
    counts = dict.fromkeys(("elements", "hidden_elements", "marks", "links", "outlines", "titles", "labels",
                            "shown_labels", "hidden_labels", "small_labels"), 0)
    carried = dict.fromkeys(("interaction", "doubled", "precision"), 0)
    scales: list[float] = []
    fonts: list[float] = []
    hiding: list[bool] = []
    for event, element in ET.iterparse(io.BytesIO(raw), events=("start", "end")):
        if event == "end":
            scales.pop()
            fonts.pop()
            hiding.pop()
            element.clear()
            continue
        scale = (scales[-1] if scales else 1.0) * _scale(element)
        font = _font_px(element, fonts[-1] if fonts else 16.0)
        hidden = (hiding[-1] if hiding else False) or _hidden(element)
        scales.append(scale)
        fonts.append(font)
        hiding.append(hidden)
        tag = element.tag.rpartition("}")[2]
        classes = element.get("class", "").split()
        counts["elements"] += 1
        counts["hidden_elements"] += hidden
        if tag == "g" and "graph-node" in classes:
            counts["marks"] += 1
        elif tag == "g" and "compound-group" in classes:
            counts["outlines"] += 1
        elif tag == "line":
            counts["links"] += 1
        elif tag == "title":
            counts["titles"] += 1
        elif tag == "text":
            counts["labels"] += 1
            if hidden:
                counts["hidden_labels"] += 1
            elif font * scale < LEGIBLE_PX:
                counts["small_labels"] += 1
            else:
                counts["shown_labels"] += 1
        for key, value in element.attrib.items():
            size = len(key) + len(value) + 4  # ` key="value"`
            if key.startswith("data-"):
                carried["interaction"] += size
            elif key == "style" and any(p in element.attrib for p in PRESENTATION):
                carried["doubled"] += size
            else:
                carried["precision"] += sum(len(d) - 1 for d in EXCESS.findall(value))
    return {"bytes": len(raw), "gzip": len(gzip.compress(raw, 6)), **counts,
            "unseen_labels": counts["hidden_labels"] + counts["small_labels"],
            "carried": carried, "carried_bytes": sum(carried.values())}


def document(path: Path) -> dict[str, Any]:
    """A show document's size, and each view it stores a graph of: its nodes,
    its edges and its nodes at each depth. A family's code view names its
    projects' graphs rather than storing them, and is left out."""
    data = json.loads(path.read_text(encoding="utf-8"))
    views = {}
    for view, drawn in (data.get("views") or {}).items():
        graph = (drawn or {}).get("graph")
        nodes = graph.get("nodes") if isinstance(graph, dict) else None
        if not nodes:
            continue
        depths: dict[str, int] = {}
        for node in (nodes.values() if isinstance(nodes, dict) else nodes):
            key = str(node.get("depth", 0))
            depths[key] = depths.get(key, 0) + 1
        views[view] = {"nodes": len(nodes), "edges": len(graph.get("edges") or []),
                       "by_depth": dict(sorted(depths.items()))}
    return {"bytes": path.stat().st_size, "views": views}


def page(html: str, here: Path, pictures: dict[str, dict]) -> dict[str, Any] | None:
    """What a built page fetches of the export: each picture it embeds, eager
    and lazy. `here` is the page's folder; a picture is named as `pictures`
    names it, relative to the export folder the site copies as `show/`. None
    for a page that embeds none."""
    eager: list[str] = []
    lazy: list[str] = []
    for tag in IMG.findall(html):
        src = SRC.search(tag)
        if not src or "/show/" not in "/" + src.group(1):
            continue
        name = "show/" + src.group(1).rpartition("show/")[2]
        target = (here / src.group(1)).resolve()
        key = name.partition("/")[2]
        if key not in pictures:
            if not target.is_file() or target.suffix != ".svg":
                continue
            pictures[key] = picture(target)
        (lazy if 'loading="lazy"' in tag else eager).append(key)
    if not eager and not lazy:
        return None

    def total(keys: list[str], field: str) -> int:
        return sum(pictures[k][field] for k in keys)

    return {"pictures": len(eager) + len(lazy), "eager": eager, "lazy": lazy,
            "open_bytes": total(eager, "bytes"), "open_gzip": total(eager, "gzip"),
            "open_elements": total(eager, "elements"),
            "bytes": total(eager + lazy, "bytes"), "gzip": total(eager + lazy, "gzip"),
            "elements": total(eager + lazy, "elements")}


def _level(key: str) -> str:
    return key.split("/", 1)[0]


def _summary(rows: dict[str, dict], fields: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {"count": len(rows)}
    for field in fields:
        values = sorted(r[field] for r in rows.values() if field in r)
        if values:
            top = max((k for k in rows if field in rows[k]), key=lambda k: rows[k][field])
            out[field] = {"median": statistics.median(values), "max": values[-1], "max_at": top,
                          "total": sum(values)}
    return out


def measure(show: Path, site: Path | None = None, times: dict | None = None) -> dict[str, Any]:
    """The whole report: every picture and document under `show`, every page
    of `site` that embeds one, a summary by level and the folder's totals.
    Every name in it is relative to `show` or `site`."""
    pictures = {p.relative_to(show).as_posix(): picture(p) for p in sorted(show.rglob("*.svg"))}
    documents = {p.parent.relative_to(show).as_posix(): document(p) for p in sorted(show.rglob("show.json"))}
    files = [p for p in show.rglob("*") if p.is_file()]
    pages: dict[str, dict] = {}
    if site:
        for html in sorted(site.rglob("*.html")):
            weight = page(html.read_text(encoding="utf-8", errors="replace"), html.parent, pictures)
            if weight:
                pages[html.relative_to(site).as_posix()] = weight
    if times:
        for key, timed in (times.get("pictures") or {}).items():
            if key in pictures:
                pictures[key]["draw_ms"] = timed
        for key, timed in (times.get("pages") or {}).items():
            if key in pages:
                pages[key]["open_ms"] = timed

    provenance = next((json.loads((show / d / "show.json").read_text(encoding="utf-8")).get("provenance")
                       for d in documents), {}) or {}
    fields = ("bytes", "gzip", "elements", "marks", "links", "titles", "labels", "unseen_labels", "hidden_elements",
              "carried_bytes", "draw_ms")
    report = {
        "schema": SCHEMA,
        "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "of": {"drawn_by": (provenance.get("drawn_by") or {}).get("graph"),
               "corpus": (provenance.get("claims") or {}).get("commit"),
               "drawn_at": provenance.get("drawn_at")},
        "legible_px": LEGIBLE_PX,
        "budgets": BUDGETS,
        "machine": (times or {}).get("machine"),
        "totals": {"files": len(files), "bytes": sum(p.stat().st_size for p in files),
                   "pictures": len(pictures), "picture_bytes": sum(p["bytes"] for p in pictures.values()),
                   "picture_gzip": sum(p["gzip"] for p in pictures.values()),
                   "documents": len(documents), "document_bytes": sum(d["bytes"] for d in documents.values())},
        "levels": {level: _summary({k: v for k, v in pictures.items() if _level(k) == level}, fields)
                   for level in LEVELS},
        "pages_summary": _summary(pages, ("open_elements", "open_bytes", "open_gzip", "elements", "bytes",
                                          "gzip", "open_ms")),
        "pictures": pictures,
        "documents": documents,
        "pages": pages,
    }
    return report


def over_budget(report: dict[str, Any], budgets: dict[str, int] = BUDGETS) -> list[tuple[str, str, int, int]]:
    """Each (budget, what, value, limit) the report exceeds, worst first."""
    found = []
    for key, p in report["pictures"].items():
        if p["elements"] > budgets["picture_elements"]:
            found.append(("picture_elements", key, p["elements"], budgets["picture_elements"]))
        if p["unseen_labels"] > budgets["unseen_labels"]:
            found.append(("unseen_labels", key, p["unseen_labels"], budgets["unseen_labels"]))
    for key, p in report["pages"].items():
        if p["open_elements"] > budgets["page_open_elements"]:
            found.append(("page_open_elements", key, p["open_elements"], budgets["page_open_elements"]))
        if p["elements"] > budgets["page_elements"]:
            found.append(("page_elements", key, p["elements"], budgets["page_elements"]))
    return sorted(found, key=lambda f: (f[0], -f[2] / max(f[3], 1)))


def compare(before: dict[str, Any], after: dict[str, Any]) -> list[tuple[str, float, float]]:
    """The headline numbers of two reports, side by side: (what, before, after)."""
    def headline(report: dict[str, Any]) -> dict[str, float]:
        out = {f"total {k}": float(v) for k, v in report["totals"].items()}
        for level, summary in report["levels"].items():
            for field in ("elements", "bytes", "gzip", "unseen_labels", "hidden_elements"):
                if field in summary:
                    out[f"{level} max {field}"] = float(summary[field]["max"])
                    out[f"{level} total {field}"] = float(summary[field]["total"])
        for field in ("open_elements", "elements", "gzip"):
            if field in report["pages_summary"]:
                out[f"page max {field}"] = float(report["pages_summary"][field]["max"])
        return out

    a, b = headline(before), headline(after)
    return [(k, a.get(k, 0.0), b.get(k, 0.0)) for k in sorted(set(a) | set(b))]


def _size(count: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if count < 1024 or unit == "GB":
            return f"{count:.0f} {unit}" if unit == "B" else f"{count:.1f} {unit}"
        count /= 1024
    return ""


def summary(report: dict[str, Any], heaviest: int = 5) -> list[str]:
    """The report as a reader takes it in: what was measured, each level's
    heaviest picture, the heaviest pages and what exceeds a budget."""
    of, totals = report["of"], report["totals"]
    lines = [f"Drawn by {of.get('drawn_by') or 'an unnamed codecarto'} from the corpus at "
             f"{str(of.get('corpus') or '?')[:7]}, on {str(of.get('drawn_at') or '?')[:10]}.",
             f"{totals['pictures']} pictures, {_size(totals['picture_bytes'])} "
             f"({_size(totals['picture_gzip'])} gzipped); {totals['documents']} documents, "
             f"{_size(totals['document_bytes'])}; {totals['files']} files, {_size(totals['bytes'])} in all.", ""]
    timed = any("draw_ms" in p for p in report["pictures"].values())
    lines.append(f"{'level':8s} {'pictures':>8s} {'heaviest':32s} {'elements':>9s} {'gzipped':>9s}"
                 f"{' drawn in' if timed else ''}")
    for level, s in report["levels"].items():
        if not s["count"]:
            continue
        at = s["elements"]["max_at"]
        p = report["pictures"][at]
        lines.append(f"{level:8s} {s['count']:8d} {at:32s} {p['elements']:9,d} {_size(p['gzip']):>9s}"
                     + (f" {p['draw_ms']:6,d} ms" if "draw_ms" in p else ""))
    pages = sorted(report["pages"].items(), key=lambda kv: -kv[1]["open_elements"])[:heaviest]
    if pages:
        lines += ["", "Heaviest pages, by the elements they fetch as they open:"]
        for key, p in pages:
            opened = f", open in {p['open_ms']:,d} ms" if "open_ms" in p else ""
            lines.append(f"  {key:44s} {p['open_elements']:9,d} elements, {_size(p['open_gzip'])} gzipped"
                         f"{opened}; {p['elements']:,d} with its lazy pictures")
    found = over_budget(report)
    lines += ["", f"Over budget: {len(found)}"]
    for budget, key, value, limit in found:
        lines.append(f"  {budget:20s} {key:44s} {value:9,d} > {limit:,d}")
    return lines


def comparison(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Each headline number that changed between two reports, with its ratio."""
    lines = []
    for what, a, b in compare(before, after):
        if a != b:
            ratio = f"x{b / a:.2f}" if a else "new"
            lines.append(f"  {what:36s} {a:14,.0f} -> {b:14,.0f}  {ratio}")
    return ["Against the earlier report:", *(lines or ["  nothing changed"])]
