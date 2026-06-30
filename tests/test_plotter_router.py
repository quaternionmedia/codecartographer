"""
Tests for POST /demo (plotter_router.py).

/demo used to route through a standalone legacy stack (ParserService ->
DirectoryParser/PythonCustomAST/DependencyParser) duplicating what
UnifiedParserService already does for every other repo. It now parses the
codecarto/ source tree itself through get_local_repo() +
UnifiedParserService.parse() — same pipeline, same output shape (gJGF
dict), no separate code path to keep in sync.
"""

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def _post_demo(client, parse_by: str = "directory", layout: str = "Spring"):
    return client.post(
        "/plotter/demo",
        json={"options": {"palette_id": "0", "layout": layout, "type": "d3", "parse_by": parse_by}},
    )


class TestDemoDirectoryMode:
    def test_returns_200(self, client):
        resp = _post_demo(client, "directory")
        assert resp.status_code == 200

    def test_has_graph_and_metadata(self, client):
        resp = _post_demo(client, "directory")
        results = resp.json()["results"]
        assert "graph" in results
        assert "metadata" in results

    def test_no_symbol_nodes(self, client):
        """directory mode is depth=1 — dirs/files only, no class/function nodes."""
        resp = _post_demo(client, "directory")
        nodes = resp.json()["results"]["graph"]["nodes"]
        for nid, nd in nodes.items():
            depth = nd.get("metadata", nd).get("depth", 0)
            assert depth <= 1, f"unexpected symbol-depth node {nid!r} in directory mode"

    def test_dir_and_file_nodes_present(self, client):
        resp = _post_demo(client, "directory")
        nodes = resp.json()["results"]["graph"]["nodes"]
        assert any(nid.startswith("dir::") for nid in nodes)
        assert any(nid.startswith("file::") for nid in nodes)


class TestDemoAstMode:
    def test_returns_200(self, client):
        resp = _post_demo(client, "ast")
        assert resp.status_code == 200

    def test_symbol_nodes_present(self, client):
        """ast mode is depth=2 — real Python source should yield class/function nodes."""
        resp = _post_demo(client, "ast")
        nodes = resp.json()["results"]["graph"]["nodes"]
        kinds = {nd.get("metadata", nd).get("kind") for nd in nodes.values()}
        assert "class" in kinds or "function" in kinds, f"no symbol kinds found: {kinds}"

    def test_dependency_edges_present(self):
        """codecarto/ has real internal imports — depends_on edges should
        appear for the same depth=2 parse, not just symbol nodes."""
        from pathlib import Path
        from codecarto.services.local_repo_service import get_local_repo
        from codecarto.services.unified_parser_service import UnifiedParserService

        codecarto_dir = Path(__file__).parent.parent / "codecarto"
        directory = get_local_repo(str(codecarto_dir), extensions=[".py"])
        result = UnifiedParserService.parse(directory, depth=2, extensions=[".py"])

        edges = result["graph"]["edges"]

        def kind(e):
            return e.get("metadata", e).get("kind")

        assert any(kind(e) == "depends_on" for e in edges), (
            "expected at least one depends_on edge parsing codecarto/ itself"
        )


class TestDemoDependenciesMode:
    def test_returns_200(self, client):
        resp = _post_demo(client, "dependencies")
        assert resp.status_code == 200

    def test_same_shape_as_ast_mode(self, client):
        """dependencies mode has no separate code path anymore — both
        resolve to depth=2 through the same pipeline."""
        ast_resp = _post_demo(client, "ast")
        dep_resp = _post_demo(client, "dependencies")
        assert (
            ast_resp.json()["results"]["metadata"]["nodeCount"]
            == dep_resp.json()["results"]["metadata"]["nodeCount"]
        )
