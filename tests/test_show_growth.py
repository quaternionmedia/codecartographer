"""What `codecarto show growth` reads of the corpus's history.

- **A month's size is what the parser reads at its end,** turned into nodes at
  the rate the project's code map holds them at the commit it was drawn from.
- **Commits are counted to the drawn commit,** not past it.
- **A rate is a doubling time** fitted through log2 of the months, and none
  for a series that is not growing.
- **A project that cannot be read is named,** never counted as empty.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from codecarto.cli import cli
from codecarto.services import show_growth

READS = {".py", ".md"}


def _commit(repo: Path, when: str, files: dict[str, str]) -> str:
    for name, text in files.items():
        (repo / name).write_text(text, encoding="utf-8")
    env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when,
           "GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@example.invalid",
           "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@example.invalid"}
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit", "-qm", "c"], check=True, env=env)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True,
                          text=True).stdout.strip()


def _corpus(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    """carlos: 10 bytes of Python in January, 40 in March, then a commit in
    April past the one its map was drawn from; its map holds 8 nodes. dossier
    starts in March with 20 bytes of markdown, and its map holds 4."""
    clones, show = tmp_path / "clones", tmp_path / "show"
    repo, later = clones / "carlos", clones / "dossier"
    for each in (repo, later):
        each.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(each)], check=True)
    _commit(repo, "2026-01-15T12:00:00Z", {"a.py": "x" * 10, "notes.txt": "y" * 1000})
    drawn = _commit(repo, "2026-03-15T12:00:00Z", {"a.py": "x" * 40})
    _commit(repo, "2026-04-15T12:00:00Z", {"b.py": "z" * 500})
    begun = _commit(later, "2026-03-20T12:00:00Z", {"d.md": "d" * 20})
    for name, commit, held in (("carlos", drawn, 8), ("dossier", begun, 4), ("stomp", "0" * 40, 0),
                               ("ira", None, 0)):
        folder = show / "project" / name
        folder.mkdir(parents=True)
        source = {"source": {"commit": commit}} if commit else {}
        nodes = {str(i): {"depth": 2} for i in range(held)}
        folder.joinpath("show.json").write_text(json.dumps(
            {"provenance": source, "views": {"code": {"graph": {"nodes": nodes, "edges": []}}}}), encoding="utf-8")
    return clones, show, {"drawn": drawn}


def test_a_month_is_what_the_parser_reads_at_its_end_in_nodes_at_todays_rate(tmp_path: Path) -> None:
    clones, show, _ = _corpus(tmp_path)
    report = show_growth.growth(clones, show, READS)
    by_month = {r["month"]: r for r in report["months"]}
    assert list(by_month) == ["2026-01", "2026-02", "2026-03"]
    # notes.txt is not read. carlos's 8 nodes over 40 bytes is a node per 5,
    # dossier's 4 over 20 the same; dossier counts from March, its first month.
    assert [by_month[m]["source_bytes"] for m in by_month] == [10, 10, 60]
    assert [by_month[m]["est_nodes"] for m in by_month] == [2, 2, 12]
    assert [by_month[m]["projects"] for m in by_month] == [1, 1, 2]


def test_commits_are_counted_up_to_the_drawn_commit(tmp_path: Path) -> None:
    clones, show, _ = _corpus(tmp_path)
    report = show_growth.growth(clones, show, READS)
    assert [r["commits"] for r in report["months"]] == [1, 0, 2]
    assert report["through"] == "2026-03"


def test_a_project_that_cannot_be_read_is_named(tmp_path: Path) -> None:
    clones, show, ids = _corpus(tmp_path)
    report = show_growth.growth(clones, show, READS)
    assert list(report["projects"]) == ["carlos", "dossier"]
    assert report["projects"]["carlos"]["commit"] == ids["drawn"]
    assert report["left_out"] == {"ira": "its document names no source commit", "stomp": "no clone"}
    (clones / "stomp").mkdir()
    subprocess.run(["git", "init", "-q", str(clones / "stomp")], check=True)
    _commit(clones / "stomp", "2026-01-01T00:00:00Z", {"s.py": "s"})
    assert show_growth.growth(clones, show, READS)["left_out"]["stomp"] == "its clone lacks 0000000"


def test_a_rate_is_a_doubling_time_and_none_for_a_series_that_does_not_grow() -> None:
    assert show_growth.doubling([1, 2, 4, 8, 16], 6) == 1.0
    # Fourfold every second month is a doubling a month, steps and all.
    assert abs(show_growth.doubling([1, 1, 4, 4, 16, 16, 64], 24) - 1.0) < 0.2
    assert show_growth.doubling([5, 5, 5, 5], 6) is None
    assert show_growth.doubling([8, 4, 2], 6) is None
    assert show_growth.doubling([0, 0, 2, 4], 6) is None  # two months above zero
    # Only the last span is fitted: an old jump is past it.
    assert show_growth.doubling([1, 1000, 1000, 2000, 4000], 3) == 1.0


def test_months_run_across_a_year_and_each_ends_at_the_next_ones_start() -> None:
    assert show_growth.months("2025-11", "2026-02") == ["2025-11", "2025-12", "2026-01", "2026-02"]
    assert show_growth.month_end("2025-12") == "2026-01-01T00:00:00Z"
    assert show_growth.month_end("2026-03") == "2026-04-01T00:00:00Z"


def test_the_command_prints_the_months_and_writes_the_report(tmp_path: Path, monkeypatch) -> None:
    clones, show, _ = _corpus(tmp_path)
    monkeypatch.setattr(show_growth, "parser_reads", lambda: READS)
    out = tmp_path / "growth.json"
    result = CliRunner().invoke(cli, ["show", "growth", str(clones), str(show), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "2026-03" in result.output and "left out: ira" in result.output
    assert json.loads(out.read_text(encoding="utf-8"))["through"] == "2026-03"


def test_the_parser_reads_python_and_markdown() -> None:
    reads = show_growth.parser_reads()
    assert {".py", ".md", ".ts"} <= reads and ".txt" not in reads
