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


# A commit name: SHA-1, or SHA-256 in a repository that uses it.
COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


def _git_dirs(clone: Path) -> tuple[Path, Path] | None:
    """The clone's git directory and its common directory (a worktree's differ)."""
    dot = clone / ".git"
    if dot.is_dir():
        return dot, dot
    if not dot.is_file():
        return None
    text = dot.read_text(encoding="utf-8", errors="replace").strip()
    if not text.startswith("gitdir:"):
        return None
    own = Path(text[len("gitdir:"):].strip())
    own = own if own.is_absolute() else (clone / own).resolve()
    common = own
    pointer = own / "commondir"
    if pointer.is_file():
        named = Path(pointer.read_text(encoding="utf-8").strip())
        common = named if named.is_absolute() else (own / named).resolve()
    return own, common


def _resolve(own: Path, common: Path, ref: str, hops: int = 0) -> str | None:
    if hops > 5:
        return None
    for base in (own,) if ref == "HEAD" else (own, common):
        path = base / ref
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if text.startswith("ref:"):
                return _resolve(own, common, text[len("ref:"):].strip(), hops + 1)
            return text if COMMIT.fullmatch(text) else None
    packed = common / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
            sha, _, name = line.partition(" ")
            if name == ref and COMMIT.fullmatch(sha):
                return sha
    return None


def default_commit(clone: Path) -> str | None:
    """The commit the clone's default branch is at: `origin/HEAD`, else `HEAD`.

    Read from the ref files, loose or packed, rather than by starting git: the
    index measures every member's clone, and a `git rev-parse` per clone was
    most of the two seconds the index took to answer when nothing had moved.
    Anything the files do not settle -- a ref store this does not read, a
    symbolic ref more than five deep -- is asked of git, so the answer is
    git's either way.
    """
    dirs = _git_dirs(clone)
    if dirs is not None:
        for ref in ("refs/remotes/origin/HEAD", "HEAD"):
            found = _resolve(*dirs, ref)
            if found:
                return found
    import subprocess

    for ref in ("origin/HEAD", "HEAD"):
        try:
            done = subprocess.run(["git", "-C", str(clone), "rev-parse", "--verify", "--quiet", ref],
                                  capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if done.returncode == 0 and done.stdout.strip():
            return done.stdout.strip()
    return None
