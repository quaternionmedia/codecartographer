"""The governance workflows are the seed's own, at the pinned submodule.

**A PIN BUMP DOES NOT RE-COPY A FILE.** `.github/workflows/` holds copies of
`governance/qm/project-seed/ci/`, and moving the submodule's pin moves the seed
without touching the copies. They drifted that way: at the pin of
2026-10-13 all five copies differed from the seed they named, and the lint,
slot and leak workflows still carried this project's own departure, checking
out the governance submodule alone, after the seed had taken it up.
`handbook/propagation-runbook.md` Part B says to re-copy what changed; this is
what says it was done.

**EVERY SEED WORKFLOW IS COPIED OR NAMED AS NOT.** A workflow the seed gains is
a decision to make here, not one to miss. The three not copied check out every
submodule, and `graphbase` is one the runner cannot fetch, so their checkout
fails before they run. When the seed changes that, the last test fails, saying
to copy them.

WHERE THIS RUNS. `pytest.yml` checks out no submodule, on purpose (see
`test_capability_router.py`), so on a runner these skip. They run in the local
suite and in `run_workflows_locally.py`, which is where a pin is bumped.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "governance" / "qm" / "project-seed" / "ci"
WORKFLOWS = ROOT / ".github" / "workflows"

COPIED = ("adr-lint.yml", "leak-check.yml", "one-pr-check.yml", "reuse-lint.yml", "submodule-check.yml")
NOT_COPIED = ("signature-check.yml", "tag-claims.yml", "timeless-check.yml")

pytestmark = pytest.mark.skipif(
    not SEED.is_dir(),
    reason="the governance submodule is not checked out (pytest.yml fetches no submodule)",
)


def _text(path: Path) -> str:
    # A Windows checkout may write CRLF; the comparison is of what is committed.
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.mark.parametrize("name", COPIED)
def test_each_governance_workflow_is_the_seeds_byte_for_byte(name: str) -> None:
    assert _text(WORKFLOWS / name) == _text(SEED / name), (
        f".github/workflows/{name} is not the seed's copy at the pinned submodule; "
        f"copy governance/qm/project-seed/ci/{name} over it"
    )


def test_every_seed_workflow_is_copied_or_named_as_not() -> None:
    seed = {p.name for p in SEED.glob("*.yml")}
    assert seed == set(COPIED) | set(NOT_COPIED), (
        f"the seed's workflows are {sorted(seed)}; each is to be copied or named here as not"
    )


@pytest.mark.parametrize("name", NOT_COPIED)
def test_a_workflow_not_copied_still_fetches_every_submodule(name: str) -> None:
    assert "submodules: true" in _text(SEED / name), (
        f"the seed's {name} no longer checks out every submodule; copy it, and move it to COPIED"
    )
