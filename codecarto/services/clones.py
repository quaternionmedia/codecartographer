"""Where sibling clones live, and how a repository name becomes one.

Both the derived system monitor and the show seam read a repository's own
files from a clone beside this one. One lookup serves both, so "which
repositories can this window read" has one answer.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ENV = "CODECARTO_REPO_ROOTS"

# One path segment, nothing hidden, nothing traversal-shaped.
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def roots() -> list[Path]:
    """Where sibling clones live: beside this repository, and one level up.

    `CODECARTO_REPO_ROOTS` (os.pathsep-separated directories) overrides the
    convention entirely when set. It exists because a git worktree is not
    beside anything — its parents are wherever the worktree was made — and a
    session working from one would otherwise find no repositories at all.
    An override that *adds* roots was considered and rejected: two sources of
    truth for "which repositories can this read" is how an allowlist stops
    being one.
    """
    override = os.environ.get(ENV, "")
    if override.strip():
        return [Path(part) for part in override.split(os.pathsep)
                if part.strip()]
    here = Path(__file__).resolve().parents[2]
    return [here.parent, here.parent.parent]


def find(name: str, among: list[Path] | None = None) -> Path | None:
    """The clone named `name` under one of the roots, or `None`."""
    if not NAME.match(name) or name.startswith("."):
        return None
    for root in among if among is not None else roots():
        candidate = root / name
        if (candidate / ".git").exists():
            return candidate
    return None
