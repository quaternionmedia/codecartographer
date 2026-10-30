"""What `codecarto show measure` counts, and the budgets it holds an export to.

- **A picture is counted by what its elements draw.** Marks, links, outlines
  and labels, and the labels a reader sees: not hidden, and at least
  `LEGIBLE_PX` high once every enclosing scale and the picture's own viewBox
  are applied.
- **What a picture carries beyond what it shows is counted apart:** the
  window's `data-*`, a `style` repeating presentation attributes beside it,
  and decimals past the first.
- **A page is what opens with it.** Its eager pictures are its cost on
  opening; its lazy ones count only toward its whole.
- **A report names nothing on this machine,** folds in Chromium's timings
  when given them, and says what exceeds a budget and what changed.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from codecarto.cli import cli
from codecarto.services import show_measure

# The viewBox is twice the width, and the outer group halves again: a label's
# font-size is drawn at a quarter of itself.
PICTURE = """<svg width="{width}" height="100" viewBox="0 0 400 200" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(10,10) scale(0.5)">
 <g class="compound-backgrounds"><g class="compound-group depth-0"><circle r="5"/><text font-size="40">core</text></g></g>
 <g class="links"><line class="stream-edge" data-from="a" data-to="b" x1="0.123456"/></g>
 <g class="nodes">
  <g class="graph-node" data-node-id="a"><path d="M 0 0" fill="#fff" style="fill:rgb(255,255,255)"/><title>a</title></g>
  <g class="graph-node" data-node-id="b"><path d="M 0 0"/></g>
 </g>
 <g class="labels"><text font-size="20">small</text><text font-size="40" visibility="hidden">hidden</text><text style="font-size:48px">styled</text></g>
</g>
</svg>"""


def _picture(tmp_path: Path, name: str = "code.svg", width: int = 200) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PICTURE.format(width=width), encoding="utf-8")
    return path


def _export(tmp_path: Path) -> Path:
    show = tmp_path / "show"
    _picture(show, "family/core/code.svg")
    _picture(show, "project/qm/code.svg")
    (show / "family/core/show.json").write_text(json.dumps({
        "provenance": {"drawn_by": {"graph": "codecartographer@abc1234"}, "claims": {"commit": "def5678"},
                       "drawn_at": "2026-10-29T00:00:00Z"},
        "views": {"code": {"graph": "each project's code view's"}}}), encoding="utf-8")
    (show / "project/qm/show.json").write_text(json.dumps({"views": {"code": {"graph": {
        "nodes": {"d": {"depth": 0}, "f": {"depth": 1}, "s": {"depth": 2}, "t": {"depth": 2}},
        "edges": [{"source": "f", "target": "s"}]}}}}), encoding="utf-8")
    return show


def _site(tmp_path: Path) -> Path:
    page = tmp_path / "site" / "families" / "core" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text('<img alt="a" src="../../show/family/core/code.svg">'
                    '<img alt="b" src="../../show/project/qm/code.svg" loading="lazy">'
                    '<img alt="logo" src="../../assets/logo.svg">', encoding="utf-8")
    _picture(tmp_path / "site", "assets/logo.svg")  # a picture, but not the export's
    (tmp_path / "site" / "about.html").write_text("<p>No pictures.</p>", encoding="utf-8")
    return tmp_path / "site"


def test_a_picture_is_counted_by_what_its_elements_draw(tmp_path: Path) -> None:
    measured = show_measure.picture(_picture(tmp_path))
    assert (measured["marks"], measured["links"], measured["outlines"], measured["labels"]) == (2, 1, 1, 4)
    assert measured["titles"] == 1
    assert measured["elements"] == 18
    assert measured["hidden_elements"] == 1


def test_a_label_is_shown_when_nothing_hides_it_and_it_is_legible_at_the_pictures_size(tmp_path: Path) -> None:
    # core is 40 at a quarter: 10px. styled is 48: 12px. small is 20: 5px.
    measured = show_measure.picture(_picture(tmp_path))
    assert (measured["shown_labels"], measured["hidden_labels"], measured["small_labels"]) == (2, 1, 1)
    assert measured["unseen_labels"] == 2
    # Drawn at the viewBox's own width, small is 10px and shown; hidden stays hidden.
    wide = show_measure.picture(_picture(tmp_path, "wide.svg", width=400))
    assert (wide["shown_labels"], wide["hidden_labels"], wide["small_labels"]) == (3, 1, 0)


def test_what_a_picture_carries_beyond_what_it_shows_is_counted_apart(tmp_path: Path) -> None:
    carried = show_measure.picture(_picture(tmp_path))["carried"]
    # ` data-from="a"` 14, ` data-to="b"` 12, ` data-node-id="a"` and `="b"` 17 each.
    assert carried["interaction"] == 14 + 12 + 17 + 17
    # ` style="fill:rgb(255,255,255)"` beside the fill it repeats; the outer
    # group's and the styled label's style repeat nothing.
    assert carried["doubled"] == len(' style="fill:rgb(255,255,255)"')
    # x1="0.123456" keeps one decimal of six.
    assert carried["precision"] == 5


def test_a_document_counts_each_stored_graph_by_depth_and_leaves_out_a_named_one(tmp_path: Path) -> None:
    show = _export(tmp_path)
    project = show_measure.document(show / "project/qm/show.json")
    assert project["views"] == {"code": {"nodes": 4, "edges": 1, "by_depth": {"0": 1, "1": 1, "2": 2}}}
    assert show_measure.document(show / "family/core/show.json")["views"] == {}


def test_a_page_opens_with_its_eager_pictures_and_counts_its_lazy_ones_toward_its_whole(tmp_path: Path) -> None:
    show, site = _export(tmp_path), _site(tmp_path)
    pictures = {"family/core/code.svg": show_measure.picture(show / "family/core/code.svg"),
                "project/qm/code.svg": show_measure.picture(show / "project/qm/code.svg")}
    one = pictures["family/core/code.svg"]
    page = site / "families/core/index.html"
    weight = show_measure.page(page.read_text(encoding="utf-8"), page.parent, pictures)
    assert (weight["eager"], weight["lazy"]) == (["family/core/code.svg"], ["project/qm/code.svg"])
    assert (weight["open_elements"], weight["open_gzip"]) == (one["elements"], one["gzip"])
    assert weight["elements"] == 2 * one["elements"]
    assert show_measure.page("<p>No pictures.</p>", site, pictures) is None


def test_a_report_sums_each_level_and_names_nothing_on_this_machine(tmp_path: Path) -> None:
    report = show_measure.measure(_export(tmp_path), _site(tmp_path))
    assert report["of"] == {"drawn_by": "codecartographer@abc1234", "corpus": "def5678",
                            "drawn_at": "2026-10-29T00:00:00Z"}
    assert {level: s["count"] for level, s in report["levels"].items()} == {"index": 0, "family": 1, "project": 1}
    assert report["levels"]["family"]["elements"]["max_at"] == "family/core/code.svg"
    assert list(report["pages"]) == ["families/core/index.html"]
    assert report["totals"]["pictures"] == 2 and report["totals"]["documents"] == 2
    text = json.dumps(report)
    assert str(tmp_path) not in text and str(tmp_path).replace("\\", "/") not in text


def test_chromiums_timings_are_folded_in_by_name(tmp_path: Path) -> None:
    times = {"machine": {"cpu": "a cpu"}, "pictures": {"family/core/code.svg": 120, "elsewhere.svg": 9},
             "pages": {"families/core/index.html": 340}}
    report = show_measure.measure(_export(tmp_path), _site(tmp_path), times)
    assert report["pictures"]["family/core/code.svg"]["draw_ms"] == 120
    assert "draw_ms" not in report["pictures"]["project/qm/code.svg"]
    assert "elsewhere.svg" not in report["pictures"]
    assert report["pages"]["families/core/index.html"]["open_ms"] == 340
    assert report["machine"] == {"cpu": "a cpu"}
    assert report["levels"]["family"]["draw_ms"]["max"] == 120


def test_over_budget_names_each_budget_exceeded_and_nothing_within_one(tmp_path: Path) -> None:
    report = show_measure.measure(_export(tmp_path), _site(tmp_path))
    elements = report["pictures"]["family/core/code.svg"]["elements"]
    tight = {"picture_elements": elements - 1, "page_open_elements": elements - 1,
             "page_elements": 2 * elements - 1, "unseen_labels": 2}
    assert sorted({f[0] for f in show_measure.over_budget(report, tight)}) == [
        "page_elements", "page_open_elements", "picture_elements"]
    loose = {"picture_elements": elements, "page_open_elements": elements,
             "page_elements": 2 * elements, "unseen_labels": 2}
    assert show_measure.over_budget(report, loose) == []


def test_a_comparison_names_each_number_that_changed_with_its_ratio(tmp_path: Path) -> None:
    show = _export(tmp_path)
    before = show_measure.measure(show)
    _picture(show, "project/qm/code.svg", width=400)  # its small label now shown
    (show / "project/carlos").mkdir()
    _picture(show, "project/carlos/code.svg")
    after = show_measure.measure(show)
    changed = {what: (a, b) for what, a, b in show_measure.compare(before, after) if a != b}
    assert changed["total pictures"] == (2.0, 3.0)
    assert changed["project total elements"] == (18.0, 36.0)
    assert "family max elements" not in changed
    lines = show_measure.comparison(before, after)
    assert any("total pictures" in line and "x1.50" in line for line in lines)
    assert show_measure.comparison(before, before) == ["Against the earlier report:", "  nothing changed"]


def test_the_command_prints_the_summary_writes_the_report_and_checks_the_budgets(tmp_path: Path) -> None:
    show, site = _export(tmp_path), _site(tmp_path)
    out = tmp_path / "report.json"
    result = CliRunner().invoke(cli, ["show", "measure", str(show), "--site", str(site), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "family/core/code.svg" in result.output and "Over budget: 2" in result.output
    assert json.loads(out.read_text(encoding="utf-8"))["totals"]["pictures"] == 2
    # Each picture's two unseen labels exceed the budget of none.
    checked = CliRunner().invoke(cli, ["show", "measure", str(show), "--against", str(out), "--check"])
    assert checked.exit_code == 1
    assert "nothing changed" not in checked.output  # this one has no site, so its pages differ
