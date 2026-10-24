"""Where this window reads the governance corpus from, and which commit it read.

**ONE PLACE RESOLVES IT.** The capability registry was read from a relative
`governance/qm` with no way to point it elsewhere, and the families test read a
sibling clone by a path of its own. Two readers with two ideas of where the
corpus is would draw two estates and say nothing about which was which. Every
reader asks `root()`.

**THE PIN IS THE DEFAULT, AND THE OVERRIDE REPLACES IT.** The submodule is the
state this project adopted, so it is what a window reads unless somebody says
otherwise. `CODECARTO_CORPUS` names another checkout -- the sibling `qm` clone
when the pin is behind what a reader wants to see. It replaces the default
rather than adding a second place to look, the same choice
`CODECARTO_REPO_ROOTS` makes and for the same reason.

**A READING SAYS WHICH COMMIT IT WAS.** `commit()` asks git, read-only. A
corpus that is not a git checkout answers `None`, which is unknown and is never
printed as a commit.

WHAT THIS CANNOT SEE. Whether the checkout is current. A clone nobody has
fetched in a month reads exactly like one fetched a minute ago; the commit it
names is the only way a reader can tell.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ENV = "CODECARTO_CORPUS"

# Where every QM project mounts the corpus.
SUBMODULE = Path("governance/qm")


def root(default: Path | str | None = None) -> Path:
    """The corpus checkout this window reads: the override, or the default.

    `SUBMODULE` is read when this is called, not when it is defined, so a test
    that moves the default moves it for every reader at once.
    """
    override = os.environ.get(ENV, "").strip()
    if override:
        return Path(override)
    return Path(default if default is not None else SUBMODULE)


def overridden() -> bool:
    """Whether a person pointed this window at a corpus other than the pin."""
    return bool(os.environ.get(ENV, "").strip())


def git(corpus: Path, *args: str) -> str | None:
    """One read-only git command in the corpus, or `None` when it cannot run."""
    try:
        done = subprocess.run(["git", "-C", str(corpus), *args],
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def commit(corpus: Path) -> str | None:
    """The commit the checkout is at, or `None` when that is unknown."""
    out = git(corpus, "rev-parse", "--short", "HEAD")
    return (out.strip() or None) if out is not None else None
