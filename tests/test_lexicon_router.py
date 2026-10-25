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

    @pytest.mark.parametrize("language", ["c", "python", "rust"])
    def test_every_layered_node_carries_the_colour_the_canvas_draws(self, client, language):
        """"Color By: Abstraction Layer" paints `layer_color` and the key names
        a layer from `meta.lexicon_layers`; the lexicon graph sent only
        `layer_ordinal`, so choosing it on a lexicon changed no pixel and the
        key showed every layer as one steelblue "Layer N". Mutation: stop
        stamping `layer_color` in `LexiconService.to_graph` -- this fails."""
        from codecarto.services.construct_service import layer_color

        nodes = client.get(f"/lexicon/{language}/graph").json()["results"]["graph"]["nodes"]
        layered = [n.get("metadata", n) for n in nodes.values()
                   if n.get("metadata", n).get("layer_ordinal", -1) >= 0]
        assert layered
        for node in layered:
            ordinal = node["layer_ordinal"]
            assert node.get("layer_color") == layer_color(ordinal), node
            assert node.get("language") == language
            names = {c["layer_name"] for c in (node.get("meta") or {}).get("lexicon_layers", [])
                     if c["layer_ordinal"] == ordinal}
            assert len(names) == 1, node

    def test_get_lexicon_index_envelope(self, client):
        resp = client.get("/lexicon/python/index")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == 200
        assert "class" in body["results"]

    def test_unknown_language_404(self, client):
        resp = client.get("/lexicon/cobol")
        assert resp.status_code == 404


class TestChrestomathyRoutes:
    """The construct vocabulary and the chrestomathy, under `/lexicon`."""

    def test_constructs_is_not_read_as_a_language(self, client):
        """Registered before `/{language}`. Mutation: take `/constructs` off the
        router, so the catch-all answers -- this fails with a 404 for a lexicon
        named `constructs`."""
        body = client.get("/lexicon/constructs").json()
        assert body["status"] == 200
        ids = {c["id"] for c in body["results"]["constructs"]}
        assert {"type.product", "type.sum", "layout.section"} <= ids

    def test_one_construct_across_languages(self, client):
        rows = client.get("/lexicon/chrestomathy/type.product").json()["results"]["languages"]
        assert {r["language"] for r in rows} >= {"c", "rust", "python"}

    def test_the_graph_rides_the_serializer(self, client):
        results = client.get("/lexicon/chrestomathy/type.product/gjgf").json()["results"]
        assert results["metadata"]["kind"] == "chrestomathy"
        sample = next(iter(results["graph"]["nodes"].values()))
        assert "x" in sample.get("metadata", sample)

    def test_an_unknown_construct_is_a_sentence(self, client):
        results = client.get("/lexicon/chrestomathy/no.such/gjgf").json()["results"]
        assert results["unreadable"] is True and "type.product" in results["remedy"]
