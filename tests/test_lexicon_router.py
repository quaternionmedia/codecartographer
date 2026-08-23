"""
Tests for codecarto.routers.lexicon_router.

Written alongside fixing a real inconsistency: these endpoints returned raw
dicts instead of the generate_return() envelope every other router in this
app uses (RequestHandler.handleResponse on the frontend unconditionally
expects responseData.status/results - calling these endpoints through the
normal frontend path would have thrown). Fixed before any frontend code
called them; these tests guard the envelope shape going forward.
"""

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app


@pytest.fixture()
def client():
    return TestClient(app)


class TestLexiconRouterEnvelope:
    def test_list_languages_envelope(self, client):
        resp = client.get("/lexicon/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == 200
        assert "c" in body["results"]["languages"]
        assert "python" in body["results"]["languages"]

    def test_get_lexicon_envelope(self, client):
        resp = client.get("/lexicon/c")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == 200
        assert body["results"]["language"] == "c"

    def test_get_lexicon_graph_is_gjgf_shaped(self, client):
        """Must be {graph: {nodes, edges}, metadata} - what
        D3GraphRenderer.canHandle actually requires - not the plain
        node-link {nodes, links} LexiconService.to_json() produces, which
        the frontend doesn't recognize as valid graph data at all."""
        resp = client.get("/lexicon/c/graph")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == 200
        results = body["results"]
        assert "graph" in results and "metadata" in results
        assert "nodes" in results["graph"] and "edges" in results["graph"]
        assert results["metadata"]["nodeCount"] == len(results["graph"]["nodes"])

    def test_get_lexicon_graph_nodes_have_layout_positions(self, client):
        """Confirms the real GraphSerializer pipeline ran (layout/size),
        not just a raw structural dump."""
        resp = client.get("/lexicon/python/graph")
        body = resp.json()
        sample = next(iter(body["results"]["graph"]["nodes"].values()))
        meta = sample.get("metadata", sample)
        assert "x" in meta and "y" in meta and "size" in meta

    def test_get_lexicon_index_envelope(self, client):
        resp = client.get("/lexicon/python/index")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == 200
        assert "class" in body["results"]

    def test_unknown_language_404(self, client):
        resp = client.get("/lexicon/cobol")
        assert resp.status_code == 404
