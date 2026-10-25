"""The CLI's exit status and output streams.

A command that prints a failure exits 1, as `docs/cli.md`'s exit-code table
says, so a script or a CI step can tell. With `-o json`, stdout is the JSON
and nothing else, so it pipes into `jq`; the status lines go to stderr.
"""

import json
import subprocess

import pytest
from click.testing import CliRunner

from codecarto.cli import cli


@pytest.fixture()
def runner():
    return CliRunner()


def _package(tmp_path):
    (tmp_path / "a.py").write_text("import b\nclass Foo:\n    def bar(self): pass\n")
    (tmp_path / "b.py").write_text("x = 1\n")
    return tmp_path


def _broken_reader(*args, **kwargs):
    raise OSError("unreadable")


# ── -o json ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("args", [
    ["repo", "scan", "{path}", "-o", "json"],
    ["repo", "graph", "{path}", "-o", "json"],
    ["parse", "{path}/a.py", "-o", "json"],
])
def test_json_output_is_the_whole_of_stdout(runner, tmp_path, args):
    _package(tmp_path)
    result = runner.invoke(cli, [a.format(path=tmp_path) for a in args])
    assert result.exit_code == 0, result.output
    json.loads(result.stdout)
    assert "Scanning" in result.stderr or "Generating" in result.stderr \
        or "Parsing" in result.stderr


def test_graph_nodes_carry_kind_in_lower_case(runner, tmp_path):
    """`docs/cli.md`'s jq recipe selects on `.kind == "function"`."""
    _package(tmp_path)
    result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-o", "json"])
    kinds = {n.get("kind") for n in json.loads(result.stdout)["nodes"]}
    assert "function" in kinds, kinds


# ── Failures exit 1 ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("command", [["repo", "scan"], ["repo", "tree"], ["repo", "graph"]])
def test_a_repo_command_that_fails_exits_1(runner, tmp_path, monkeypatch, command):
    monkeypatch.setattr("codecarto.services.local_repo_service.get_local_repo",
                        _broken_reader)
    result = runner.invoke(cli, [*command, str(tmp_path)])
    assert result.exit_code == 1, result.output
    assert "✗" in result.stderr


def test_a_parse_that_fails_exits_1(runner, tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("def (:\n")
    result = runner.invoke(cli, ["parse", str(broken)])
    assert result.exit_code == 1, result.output
    assert "Parse error" in result.stderr


def test_lint_without_ruff_exits_1_and_says_how_to_get_it(runner, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = runner.invoke(cli, ["lint"])
    assert result.exit_code == 1, result.output
    assert "uv sync --locked --extra dev --extra c-parsing" in result.stderr


def test_lint_that_finds_issues_exits_1(runner, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "ruff")
    monkeypatch.setattr("subprocess.run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1))
    result = runner.invoke(cli, ["lint"])
    assert result.exit_code == 1, result.output


def test_lint_that_finds_nothing_exits_0(runner, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "ruff")
    monkeypatch.setattr("subprocess.run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0))
    result = runner.invoke(cli, ["lint"])
    assert result.exit_code == 0, result.output


def _without(monkeypatch, missing: str):
    """`import <missing>` fails, as it does where the package is not installed."""
    import builtins

    real = builtins.__import__

    def importer(name, *args, **kwargs):
        if name == missing:
            raise ImportError(f"No module named {name!r}")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", importer)


def test_info_with_a_dependency_missing_exits_1(runner, monkeypatch):
    """Every package `info` lists is one of the project's own dependencies,
    so one it cannot import is a broken install, and its ✗ a failure."""
    _without(monkeypatch, "gravis")
    result = runner.invoke(cli, ["info"])
    assert result.exit_code == 1, result.output
    assert "✗ gravis: not found" in result.stdout
    assert "gravis" in result.stderr


def test_info_with_every_dependency_exits_0(runner):
    result = runner.invoke(cli, ["info"])
    assert result.exit_code == 0, result.output
    assert "✗" not in result.output


@pytest.mark.parametrize("command", ["docker", "docker-down"])
def test_docker_without_compose_exits_1(runner, monkeypatch, command):
    def missing(cmd, **kw):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr("subprocess.run", missing)
    result = runner.invoke(cli, [command])
    assert result.exit_code == 1, result.output
    assert "docker-compose not found" in result.stderr


def test_ruff_is_in_the_dev_extra():
    """`codecarto lint` runs ruff, so the extra that has the CLI's tools has it."""
    from pathlib import Path

    try:
        import tomllib
    except ImportError:  # Python 3.10
        import tomli as tomllib

    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    dev = pyproject["project"]["optional-dependencies"]["dev"]
    assert any(req.split(">")[0].split("=")[0].strip() == "ruff" for req in dev), dev
