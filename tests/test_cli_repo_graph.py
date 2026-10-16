"""
Tests for `codecarto repo graph` (cli.py's repo_graph command).

All three graph types go through UnifiedParserService.build_graph(), the
pipeline every other repository uses. "ast" and "dependency" produce the same
depth-2 graph (symbols and resolved dependency edges together -- see
_add_python_dependency_edges); "directory" is depth 1.
"""

import json

import pytest
from click.testing import CliRunner

from codecarto.cli import cli


@pytest.fixture()
def runner():
    return CliRunner()


def _make_pkg(tmp_path):
    (tmp_path / "a.py").write_text("import b\nclass Foo:\n    def bar(self): pass\n")
    (tmp_path / "b.py").write_text("x = 1\n")
    return tmp_path


def _parse_json_output(output: str) -> dict:
    """stdout is the JSON alone; the status line goes to stderr."""
    return json.loads(output)


class TestRepoGraphAstMode:
    def test_exits_zero(self, runner, tmp_path):
        _make_pkg(tmp_path)
        result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-t", "ast", "-o", "json"])
        assert result.exit_code == 0, result.output

    def test_json_output_has_symbol_and_dependency_nodes(self, runner, tmp_path):
        _make_pkg(tmp_path)
        result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-t", "ast", "-o", "json"])
        data = _parse_json_output(result.stdout)

        kinds = {n.get("kind") for n in data["nodes"]}
        assert "class" in kinds or "function" in kinds

    def test_json_output_has_depends_on_edge(self, runner, tmp_path):
        _make_pkg(tmp_path)
        result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-t", "ast", "-o", "json"])
        data = _parse_json_output(result.stdout)

        edge_kinds = {e.get("kind") for e in data["edges"]}
        assert "depends_on" in edge_kinds


class TestRepoGraphDependencyMode:
    def test_exits_zero(self, runner, tmp_path):
        _make_pkg(tmp_path)
        result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-t", "dependency", "-o", "json"])
        assert result.exit_code == 0, result.output

    def test_same_node_count_as_ast_mode(self, runner, tmp_path):
        _make_pkg(tmp_path)
        ast_result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-t", "ast", "-o", "json"])
        dep_result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-t", "dependency", "-o", "json"])

        ast_data = _parse_json_output(ast_result.stdout)
        dep_data = _parse_json_output(dep_result.stdout)
        assert len(ast_data["nodes"]) == len(dep_data["nodes"])


class TestRepoGraphDirectoryMode:
    def test_exits_zero(self, runner, tmp_path):
        _make_pkg(tmp_path)
        result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-t", "directory", "-o", "json"])
        assert result.exit_code == 0, result.output

    def test_no_symbol_nodes(self, runner, tmp_path):
        _make_pkg(tmp_path)
        result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-t", "directory", "-o", "json"])
        data = _parse_json_output(result.stdout)

        kinds = {n.get("kind") for n in data["nodes"]}
        assert "class" not in kinds
        assert "function" not in kinds

    def test_text_output_does_not_crash(self, runner, tmp_path):
        """Default -o text path exercises the node-kind breakdown branch
        (cli.py reads each node's 'kind')."""
        _make_pkg(tmp_path)
        result = runner.invoke(cli, ["repo", "graph", str(tmp_path), "-t", "directory"])
        assert result.exit_code == 0, result.output
        assert "Node types:" in result.output
