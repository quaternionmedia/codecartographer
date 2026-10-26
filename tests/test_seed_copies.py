"""What this repository copies from the governance seed is the seed's own, at the pin.

**A PIN BUMP DOES NOT RE-COPY A FILE.** `.github/workflows/` and `.vscode/`
hold copies of `governance/qm/project-seed/ci/` and `project-seed/ide/`, and
moving the submodule's pin moves the seed without touching the copies. They
drifted that way: at the pin of 2026-10-13 all five governance workflows
differed from the seed they named, and the lint, slot and leak workflows still
carried this project's own departure, checking out the governance submodule
alone, after the seed had taken it up. `handbook/propagation-runbook.md` Part
B says to re-copy what changed; this is what says it was done.

**EVERY SEED WORKFLOW IS COPIED OR NAMED AS NOT.** A workflow the seed gains is
a decision to make here, not one to miss. The three not copied check out every
submodule, and `graphbase` is one the runner cannot fetch, so their checkout
fails before they run. When the seed changes that, a test fails, saying to
copy them.

**THE POINTER FILES ARE SYMLINKS, AS THE SEED'S ARE.** `CLAUDE.md` and
`.github/copilot-instructions.md` point at `AGENTS.md`; a copy that dereferenced
them would be a second `AGENTS.md` to go stale. Read from git's index, which is
what is committed, rather than from a Windows checkout's file, which may be a
one-line text file holding the target.

NOT HELD HERE. `AGENTS.md` itself: its governance section is this project's own
wording of an earlier seed, and bringing it to the seed's is a change of its own.

WHERE THIS RUNS. `pytest.yml` checks out no submodule, on purpose (see
`test_capability_router.py`), so on a runner these skip. They run in the local
suite and in `run_workflows_locally.py`, which is where a pin is bumped.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "governance" / "qm" / "project-seed"
WORKFLOWS = ROOT / ".github" / "workflows"

COPIED = ("adr-lint.yml", "leak-check.yml", "one-pr-check.yml", "reuse-lint.yml", "submodule-check.yml")
NOT_COPIED = ("signature-check.yml", "tag-claims.yml", "timeless-check.yml")
EDITOR = (".vscode/settings.json", ".vscode/extensions.json")
POINTERS = ("CLAUDE.md", ".github/copilot-instructions.md")

pytestmark = pytest.mark.skipif(
    not (SEED / "ci").is_dir(),
    reason="the governance submodule is not checked out (pytest.yml fetches no submodule)",
)


def _text(path: Path) -> str:
    # A Windows checkout may write CRLF; the comparison is of what is committed.
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _committed(repo: Path, path: str) -> tuple[str, str]:
    """The mode and the content git's index holds for `path` in `repo`: what is, or will be, committed."""
    entry = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-s", "--", path],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert entry, f"{path} is not tracked in {repo}"
    mode, blob = entry[:2]
    content = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-p", blob], capture_output=True, text=True, check=True,
    ).stdout
    return mode, content


@pytest.mark.parametrize("name", COPIED)
def test_each_governance_workflow_is_the_seeds_byte_for_byte(name: str) -> None:
    assert _text(WORKFLOWS / name) == _text(SEED / "ci" / name), (
        f".github/workflows/{name} is not the seed's copy at the pinned submodule; "
        f"copy governance/qm/project-seed/ci/{name} over it"
    )


def test_every_seed_workflow_is_copied_or_named_as_not() -> None:
    seed = {p.name for p in (SEED / "ci").glob("*.yml")}
    assert seed == set(COPIED) | set(NOT_COPIED), (
        f"the seed's workflows are {sorted(seed)}; each is to be copied or named here as not"
    )


@pytest.mark.parametrize("name", NOT_COPIED)
def test_a_workflow_not_copied_still_fetches_every_submodule(name: str) -> None:
    assert "submodules: true" in _text(SEED / "ci" / name), (
        f"the seed's {name} no longer checks out every submodule; copy it, and move it to COPIED"
    )


@pytest.mark.parametrize("path", EDITOR)
def test_each_editor_setting_is_the_seeds_byte_for_byte(path: str) -> None:
    assert _text(ROOT / path) == _text(SEED / "ide" / path), (
        f"{path} is not the seed's copy at the pinned submodule; copy governance/qm/project-seed/ide/{path} over it"
    )


@pytest.mark.parametrize("path", POINTERS)
def test_each_pointer_file_is_the_seeds_symlink(path: str) -> None:
    ours = _committed(ROOT, path)
    seeds = _committed(SEED.parent, f"project-seed/ide/{path}")
    assert ours[0] == "120000", f"{path} is committed as mode {ours[0]}, not as a symlink"
    assert ours == seeds, f"{path} points at {ours[1]!r}; the seed's points at {seeds[1]!r}"
