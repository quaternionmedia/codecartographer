"""A clone's default commit, read from its ref files, is the one git names.

`clones.default_commit` reads `origin/HEAD`, else `HEAD`, from the files git
keeps them in rather than starting git, because the show index measures every
member's clone. Each test builds a repository in the shape git leaves one in
and compares the answer with `git rev-parse`'s.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from codecarto.services import clones


def _git(where: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(where), "-c", "user.name=t", "-c", "user.email=t@t",
                           "-c", "commit.gpgsign=false", *args],
                          check=True, capture_output=True, text=True)
    return done.stdout.strip()


def _repo(where: Path, commits: int = 1) -> Path:
    where.mkdir(parents=True)
    _git(where, "init", "-q", "-b", "main")
    for i in range(commits):
        (where / "f.txt").write_text(str(i), encoding="utf-8")
        _git(where, "add", "-A")
        _git(where, "commit", "-q", "-m", f"c{i}")
    return where


def _rev(where: Path, ref: str) -> str:
    return _git(where, "rev-parse", ref)


def _from_files(clone: Path, monkeypatch) -> str | None:
    """The answer with git forbidden, so it can only have come from the files."""
    def no_git(*args, **kwargs):
        raise AssertionError("git was started where the ref files should have answered")
    monkeypatch.setattr(subprocess, "run", no_git)
    try:
        return clones.default_commit(clone)
    finally:
        monkeypatch.undo()


def test_a_branch_checked_out_is_read_from_its_loose_ref(tmp_path, monkeypatch):
    repo = _repo(tmp_path / "r")
    assert _from_files(repo, monkeypatch) == _rev(repo, "HEAD")


def test_a_packed_ref_is_read_from_packed_refs(tmp_path, monkeypatch):
    repo = _repo(tmp_path / "r", commits=2)
    _git(repo, "pack-refs", "--all")
    assert not (repo / ".git" / "refs" / "heads" / "main").exists()
    assert _from_files(repo, monkeypatch) == _rev(repo, "HEAD")


def test_origin_head_wins_over_a_checkout_elsewhere(tmp_path, monkeypatch):
    upstream = _repo(tmp_path / "up", commits=2)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(upstream), str(clone)], check=True)
    _git(clone, "checkout", "-q", "-b", "topic", "HEAD~1")
    assert _rev(clone, "HEAD") != _rev(clone, "origin/HEAD")
    assert _from_files(clone, monkeypatch) == _rev(clone, "origin/HEAD")


def test_a_detached_head_is_its_commit(tmp_path, monkeypatch):
    repo = _repo(tmp_path / "r", commits=2)
    _git(repo, "checkout", "-q", "--detach", "HEAD~1")
    assert _from_files(repo, monkeypatch) == _rev(repo, "HEAD")


def test_a_worktree_reads_its_own_head_and_the_shared_refs(tmp_path, monkeypatch):
    repo = _repo(tmp_path / "r", commits=2)
    tree = tmp_path / "tree"
    # On a branch, so its HEAD names a ref that lives in the shared directory.
    _git(repo, "worktree", "add", "-q", "-b", "wt", str(tree), "HEAD~1")
    assert (tree / ".git").is_file()
    assert _from_files(tree, monkeypatch) == _rev(tree, "HEAD")


def test_what_the_files_do_not_settle_is_asked_of_git(tmp_path, monkeypatch):
    repo = _repo(tmp_path / "r")
    monkeypatch.setattr(clones, "_git_dirs", lambda clone: None)
    assert clones.default_commit(repo) == _rev(repo, "HEAD")


def test_a_directory_that_is_no_clone_has_no_commit(tmp_path):
    (tmp_path / "plain").mkdir()
    assert clones.default_commit(tmp_path / "plain") is None


@pytest.mark.parametrize("text", ["ref: refs/heads/nowhere", "not a commit"])
def test_a_head_that_names_nothing_is_not_a_commit(tmp_path, text):
    repo = _repo(tmp_path / "r")
    (repo / ".git" / "HEAD").write_text(text + "\n", encoding="utf-8")
    assert clones._resolve(repo / ".git", repo / ".git", "HEAD") is None
