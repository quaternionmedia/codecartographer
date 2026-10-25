"""What `.github/workflows/web.yml` runs, and on which pull requests.

**THE WORKFLOW IS READ, NOT TRUSTED.** Its header says it runs on every pull
request that can change what the frontend's suites test. That is a claim about
every path the browser suite and the backend it starts read, and it was false
the day it was written: the filter named `web/`, `codecarto/` and the Python
manifests, while the Cargo specs read `tests/fixtures/cargo/workspace`, the
project selector opens `examples/rust-firmware`, the estate panels read the
`governance/qm` corpus, and the Cargo panel's not-a-workspace case reads
`docs`. A pull request changing any of them ran no browser.

**READ FROM THE TREE, NOT FROM A LIST HERE.** The paths come from what the
specs type into the window, from the backend's own constants for the examples
and the corpus, from the seam `playwright.config.ts` hands the backend, and
`.gitmodules` from the job that fetches the corpus. A list in this file would
be one more copy to go stale.

**A SKIP ON A RUNNER IS A TEST THAT CANNOT FAIL THERE.** The moat replay test
skips when no `moat` clone sits beside the backend, and a runner never has
one, so the run reported it as skipped among the passes on every pull request.
A browser test that can skip is left out of the run by name, where the
workflow says why, so the summary counts only tests that ran.

Seen red before trusted: against the filter this branch had, the path test
failed naming `docs`, `examples`, `governance/qm` and `tests/fixtures/...`;
with each entry since added dropped in turn, it fails naming that one. The
skip test failed on the run step this branch had, which excluded nothing.

WHAT THIS CANNOT SEE. A path a spec reaches some other way than these, such as
a route that reads a file nothing here names; and a skip in a test the specs
spell some other way than `test.skip(` in its own body.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "web.yml"
E2E = ROOT / "web" / "tests" / "e2e"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _pull_request_paths() -> list[str]:
    doc = _workflow()
    # YAML 1.1, which PyYAML reads, takes the bare key `on` for True.
    triggers = doc.get("on", doc.get(True))
    return triggers["pull_request"]["paths"]


def _glob(pattern: str) -> re.Pattern[str]:
    """A GitHub path filter as a regex: `**` crosses `/`; `*` and `?` do not."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def _starts_the_workflow(path: str, patterns: list[str]) -> bool:
    """Whether a change to `path` matches the filter. The last pattern that
    matches decides, and a `!` pattern excludes, as GitHub reads them."""
    included = False
    for pattern in patterns:
        if pattern.startswith("!"):
            if _glob(pattern[1:]).match(path):
                included = False
        elif _glob(pattern).match(path):
            included = True
    return included


def _gitlinks() -> set[str]:
    text = (ROOT / ".gitmodules").read_text(encoding="utf-8")
    return set(re.findall(r"^\s*path\s*=\s*(\S+)\s*$", text, re.MULTILINE))


def _typed_by_the_specs() -> set[str]:
    """Every repository path a spec types into the window."""
    found = set()
    for spec in sorted(E2E.glob("*.ts")):
        text = spec.read_text(encoding="utf-8")
        constants = dict(re.findall(r"^const (\w+) = '([^']*)';", text, re.MULTILINE))
        for argument in re.findall(r"\.fill\(\s*('[^']*'|\w+)\s*\)", text):
            value = argument.strip("'") if argument.startswith("'") else constants.get(argument)
            if value and not value.startswith("/") and (ROOT / value).exists():
                found.add(value)
    return found


def _read_by_the_backend() -> set[str]:
    """What the backend reads outside its own package for the browser suite."""
    from codecarto.services import capability_service, examples_service

    found = {
        examples_service.ROOT.relative_to(ROOT).as_posix(),
        capability_service.CORPUS.as_posix(),
    }
    config = (ROOT / "web" / "playwright.config.ts").read_text(encoding="utf-8")
    found.update(re.findall(r"DOSSIER_OVERVIEW_SEAM:\s*'([^']+)'", config))
    return found


def _changes_to(path: str) -> list[str]:
    """The paths a pull request changing `path` would list."""
    if path in _gitlinks() or (ROOT / path).is_file():
        return [path]
    return [f"{path}/added", f"{path}/a/b/added"]


def _browser_tests() -> dict[str, bool]:
    """Every browser test's title, and whether its body calls `test.skip(`."""
    found = {}
    for spec in sorted(E2E.glob("*.spec.ts")):
        text = spec.read_text(encoding="utf-8")
        heads = list(re.finditer(r"\btest\(\s*(['\"`])(.+?)\1", text))
        for here, after in zip(heads, [*heads[1:], None]):
            body = text[here.end():after.start() if after else len(text)]
            found[here.group(2)] = "test.skip(" in body
    return found


def _browser_run() -> str:
    """The one step of the e2e job that runs the browser suite."""
    runs = [str(step["run"]) for step in _workflow()["jobs"]["e2e"]["steps"]
            if "test:e2e" in str(step.get("run", ""))]
    assert len(runs) == 1, f"the e2e job should run test:e2e once, not {runs}"
    return runs[0]


def test_the_matcher_reads_a_filter_as_github_does():
    assert _starts_the_workflow("web/src/a.ts", ["web/**"])
    assert not _starts_the_workflow("webx/a.ts", ["web/**"])
    assert not _starts_the_workflow("tests/fixtures/a/b", ["tests/*"])
    assert _starts_the_workflow("governance/qm", ["governance/qm"])
    assert not _starts_the_workflow("governance/qm/x", ["governance/qm"])
    assert not _starts_the_workflow("web/a.md", ["web/**", "!web/*.md"])


def test_every_path_the_browser_suite_reads_starts_the_workflow():
    read = _typed_by_the_specs() | _read_by_the_backend()
    # The job that fetches the corpus reads where to fetch it from.
    if any("git submodule" in str(step.get("run", ""))
           for step in _workflow()["jobs"]["e2e"]["steps"]):
        read.add(".gitmodules")
    # The premise: what the review found missing is found here. If one of these
    # stops being read, this list is what to change, not the filter.
    assert {"tests/fixtures/cargo/workspace", "examples", "governance/qm"} <= read, read
    patterns = _pull_request_paths()
    missing = sorted(change for path in read for change in _changes_to(path)
                     if not _starts_the_workflow(change, patterns))
    assert not missing, (
        f"web.yml's pull_request paths leave out what the browser suite reads, "
        f"so a change to these runs no browser: {missing}")


def test_a_browser_test_that_can_skip_is_left_out_by_name_not_counted_as_a_skip():
    tests = _browser_tests()
    skipping = sorted(title for title, skips in tests.items() if skips)
    # The premise: the test the review found skipping on every runner.
    assert "moat is derived from its clone and replays real history" in skipping, skipping
    inverted = [quoted[1:-1] for quoted in
                re.findall(r"--grep-invert[= ](\"[^\"]*\"|'[^']*')", _browser_run())]
    left_out = sorted(title for title in tests
                      if any(re.search(pattern, title) for pattern in inverted))
    assert left_out == skipping, (
        f"the e2e run should leave out by name exactly the browser tests that "
        f"can skip, {skipping}, and leaves out {left_out}")
