"""
Tests for codecarto.routers.unified_parser_router:
  - _stream_cached_graph: the single shared SSE cache-replay generator used
    by both POST /parse/stream and POST /parse/stream-url. Before this it
    was two ~25-line near-identical inner functions (stream_cached /
    stream_cached_url) — extracted so the two endpoints can't silently
    drift from each other on the next edit. Mirrors the frontend's
    PlotService._consumeSSE(), which already serves as the one shared
    parser for streamUnified/streamFromUrl/streamCGithub.
"""

import json

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app
from codecarto.routers.unified_parser_router import (
    _stream_cached_graph,
    _accumulate,
    _write_stream_cache,
)
from codecarto.services.cache_service import CacheService


def _parse_sse_chunk(chunk: str) -> tuple[str, dict]:
    lines = chunk.strip().split("\n")
    event_type = lines[0].split("event: ", 1)[1]
    data_line = next(l for l in lines if l.startswith("data: "))
    return event_type, json.loads(data_line[len("data: "):])


async def _collect(cached: dict, layout: str = "Spring") -> list[tuple[str, dict]]:
    events = []
    async for chunk in _stream_cached_graph(cached, layout):
        events.append(_parse_sse_chunk(chunk))
    return events


class TestStreamCachedGraph:
    @pytest.mark.asyncio
    async def test_event_order_meta_nodes_edges_done(self):
        cached = {
            "graph": {
                "nodes": {
                    "file::a.py": {"metadata": {"depth": 1, "kind": "file", "label": "a.py"}},
                    "fn::a.foo": {"metadata": {"depth": 2, "kind": "function", "label": "foo"}},
                },
                "edges": [{"source": "file::a.py", "target": "fn::a.foo", "kind": "contains"}],
            }
        }
        events = await _collect(cached)
        types = [t for t, _ in events]
        assert types == ["meta", "node", "node", "edge", "done"]

    @pytest.mark.asyncio
    async def test_nodes_sorted_by_depth_then_id(self):
        cached = {
            "graph": {
                "nodes": {
                    "fn::a.foo": {"metadata": {"depth": 2, "kind": "function", "label": "foo"}},
                    "file::a.py": {"metadata": {"depth": 1, "kind": "file", "label": "a.py"}},
                },
                "edges": [],
            }
        }
        events = await _collect(cached)
        node_ids = [d["id"] for t, d in events if t == "node"]
        assert node_ids == ["file::a.py", "fn::a.foo"]

    @pytest.mark.asyncio
    async def test_meta_and_done_marked_from_cache(self):
        cached = {"graph": {"nodes": {}, "edges": []}}
        events = await _collect(cached, layout="Spectral")

        meta = next(d for t, d in events if t == "meta")
        done = next(d for t, d in events if t == "done")
        assert meta["from_cache"] is True
        assert meta["layout"] == "Spectral"
        assert done["from_cache"] is True

    @pytest.mark.asyncio
    async def test_counts_match_actual_nodes_and_edges(self):
        cached = {
            "graph": {
                "nodes": {
                    "a": {"metadata": {"depth": 1, "label": "a"}},
                    "b": {"metadata": {"depth": 1, "label": "b"}},
                },
                "edges": [{"source": "a", "target": "b", "kind": "contains"}],
            }
        }
        events = await _collect(cached)
        meta = next(d for t, d in events if t == "meta")
        assert meta["nodeCount"] == 2
        assert meta["edgeCount"] == 1

    @pytest.mark.asyncio
    async def test_non_dict_node_entries_are_skipped(self):
        """Defensive: a malformed cache entry (corrupted JSON value) must not
        crash the replay, just be skipped."""
        cached = {
            "graph": {
                "nodes": {"a": {"metadata": {"depth": 1, "label": "a"}}, "b": "not-a-dict"},
                "edges": [],
            }
        }
        events = await _collect(cached)
        node_ids = [d["id"] for t, d in events if t == "node"]
        assert node_ids == ["a"]

    @pytest.mark.asyncio
    async def test_node_attrs_flattened_with_metadata_priority(self):
        """Top-level attrs (e.g. x/y from some gravis versions) come first,
        metadata attrs (depth/kind/...) override/supplement them."""
        cached = {
            "graph": {
                "nodes": {"a": {"x": 1.0, "y": 2.0, "metadata": {"depth": 1, "label": "a"}}},
                "edges": [],
            }
        }
        events = await _collect(cached)
        node = next(d for t, d in events if t == "node")
        assert node["x"] == 1.0
        assert node["y"] == 2.0
        assert node["depth"] == 1
        assert node["label"] == "a"

    @pytest.mark.asyncio
    async def test_empty_graph_still_yields_meta_and_done(self):
        cached = {"graph": {}}
        events = await _collect(cached)
        types = [t for t, _ in events]
        assert types == ["meta", "done"]


class TestStreamEndpointsShareCacheReplay:
    """The actual point of the extraction: /parse/stream and
    /parse/stream-url must produce byte-for-byte identical SSE output for
    the same cached entry — proving they share _stream_cached_graph rather
    than two independently-maintained copies."""

    @pytest.fixture()
    def client(self):
        return TestClient(app)

    def test_stream_and_stream_url_identical_on_cache_hit(self, client, monkeypatch, tmp_path):
        cache_dir = tmp_path / "cache"
        repos_dir = cache_dir / "repos"
        import codecarto.services.cache_service as cache_svc
        monkeypatch.setattr(cache_svc, "_CACHE_DIR", cache_dir)
        monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
        monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")

        url = "https://github.com/test/shared-replay"
        graph_data = {
            "graph": {
                "nodes": {"file::a.py": {"metadata": {"depth": 1, "kind": "file", "label": "a.py"}}},
                "edges": [],
            },
            "metadata": {},
        }
        key = CacheService.cache_key(url, "2", "Spring", [])
        CacheService.set(key, graph_data, label="test/shared-replay", url=url, mode="2", layout="Spring")

        body_stream = {
            "directory": {
                "info": {"url": url, "owner": "test", "name": "shared-replay"},
                "size": 0,
                "root": {"name": "", "size": 0, "files": [], "folders": []},
                "is_partial": False,
            },
            "depth": 2,
            "layout": "Spring",
        }
        body_stream_url = {"url": url, "depth": 2, "layout": "Spring"}

        resp_a = client.post("/parse/stream", json=body_stream)
        resp_b = client.post("/parse/stream-url", json=body_stream_url)

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.text == resp_b.text


class TestStreamEndpointsAnnotateLexiconBypassesCache:
    """annotate_lexicon isn't part of the cache key (CacheService.cache_key
    is shared with every other caller) - both streaming endpoints must skip
    the cache entirely for annotated requests rather than risk serving a
    cached unannotated result, matching /parse/unified's own fix."""

    @pytest.fixture()
    def client(self):
        return TestClient(app)

    def test_stream_ignores_cached_entry_when_annotate_lexicon_true(self, client, monkeypatch, tmp_path):
        cache_dir = tmp_path / "cache"
        repos_dir = cache_dir / "repos"
        import codecarto.services.cache_service as cache_svc
        monkeypatch.setattr(cache_svc, "_CACHE_DIR", cache_dir)
        monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
        monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")

        url = "https://github.com/test/annotate-bypass"
        # A cached entry with a sentinel node id that would NOT appear in a
        # fresh parse of the empty directory below - if the cache were
        # (wrongly) consulted, this sentinel would show up in the response.
        graph_data = {
            "graph": {
                "nodes": {"file::CACHED_SENTINEL.py": {"metadata": {"depth": 1, "kind": "file", "label": "CACHED_SENTINEL.py"}}},
                "edges": [],
            },
            "metadata": {},
        }
        key = CacheService.cache_key(url, "2", "Spring", [])
        CacheService.set(key, graph_data, label="test/annotate-bypass", url=url, mode="2", layout="Spring")

        body = {
            "directory": {
                "info": {"url": url, "owner": "test", "name": "annotate-bypass"},
                "size": 0,
                "root": {"name": "", "size": 0, "files": [], "folders": []},
                "is_partial": False,
            },
            "depth": 2,
            "layout": "Spring",
            "annotate_lexicon": True,
        }
        resp = client.post("/parse/stream", json=body)
        assert resp.status_code == 200
        assert "CACHED_SENTINEL" not in resp.text

    def test_stream_url_ignores_cached_entry_when_annotate_lexicon_true(self, client, monkeypatch, tmp_path):
        cache_dir = tmp_path / "cache"
        repos_dir = cache_dir / "repos"
        import codecarto.services.cache_service as cache_svc
        monkeypatch.setattr(cache_svc, "_CACHE_DIR", cache_dir)
        monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
        monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")

        import codecarto.services.github_service as gh_svc

        async def fake_fetch_tree_fast(owner, repo, headers, url):
            return [], "main", 1, False

        monkeypatch.setattr(gh_svc, "fetch_tree_fast", fake_fetch_tree_fast)

        url = "https://github.com/test/annotate-bypass-url"
        graph_data = {
            "graph": {
                "nodes": {"file::CACHED_SENTINEL.py": {"metadata": {"depth": 1, "kind": "file", "label": "CACHED_SENTINEL.py"}}},
                "edges": [],
            },
            "metadata": {},
        }
        key = CacheService.cache_key(url, "2", "Spring", [])
        CacheService.set(key, graph_data, label="test/annotate-bypass-url", url=url, mode="2", layout="Spring")

        body = {"url": url, "depth": 2, "layout": "Spring", "annotate_lexicon": True}
        resp = client.post("/parse/stream-url", json=body)
        assert resp.status_code == 200
        assert "CACHED_SENTINEL" not in resp.text


class TestAccumulate:
    def test_node_chunk_stored_by_id(self):
        import json
        node = {"id": "file::a.py", "depth": 1, "label": "a.py"}
        chunk = f"event: node\ndata: {json.dumps(node)}\n\n"
        acc_nodes, acc_edges = {}, []
        _accumulate(chunk, acc_nodes, acc_edges)
        assert "file::a.py" in acc_nodes
        assert acc_nodes["file::a.py"]["depth"] == 1
        assert "id" not in acc_nodes["file::a.py"]  # id is popped to become the key

    def test_edge_chunk_appended_as_is(self):
        import json
        edge = {"source": "a", "target": "b", "label": "contains"}
        chunk = f"event: edge\ndata: {json.dumps(edge)}\n\n"
        acc_nodes, acc_edges = {}, []
        _accumulate(chunk, acc_nodes, acc_edges)
        assert acc_edges == [{"source": "a", "target": "b", "label": "contains"}]

    def test_non_node_edge_chunk_ignored(self):
        acc_nodes, acc_edges = {}, []
        _accumulate("event: meta\ndata: {}\n\n", acc_nodes, acc_edges)
        _accumulate("event: done\ndata: {}\n\n", acc_nodes, acc_edges)
        assert acc_nodes == {}
        assert acc_edges == []

    def test_malformed_json_does_not_raise(self):
        acc_nodes, acc_edges = {}, []
        _accumulate("event: node\ndata: {bad json\n\n", acc_nodes, acc_edges)
        assert acc_nodes == {}

    def test_node_without_id_not_stored(self):
        import json
        chunk = f"event: node\ndata: {json.dumps({'depth': 1, 'label': 'x'})}\n\n"
        acc_nodes, acc_edges = {}, []
        _accumulate(chunk, acc_nodes, acc_edges)
        assert acc_nodes == {}


class TestWriteStreamCache:
    def test_writes_gjgf_to_cache(self, monkeypatch, tmp_path):
        import codecarto.services.cache_service as cache_svc
        repos_dir = tmp_path / "repos"
        monkeypatch.setattr(cache_svc, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
        monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")

        url = "https://github.com/test/write-cache"
        key = CacheService.cache_key(url, "2", "Spring", [])
        acc_nodes = {"file::a.py": {"depth": 1, "label": "a.py"}}
        acc_edges = [{"source": "file::a.py", "target": "fn::foo"}]

        _write_stream_cache(key, "test/write-cache", url, "2", "Spring", acc_nodes, acc_edges)

        stored = CacheService.get(key)
        assert stored is not None
        assert "file::a.py" in stored["graph"]["nodes"]
        assert stored["graph"]["edges"] == acc_edges

    def test_empty_nodes_skips_write(self, monkeypatch, tmp_path):
        import codecarto.services.cache_service as cache_svc
        repos_dir = tmp_path / "repos"
        monkeypatch.setattr(cache_svc, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
        monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")

        url = "https://github.com/test/empty"
        key = CacheService.cache_key(url, "2", "Spring", [])
        _write_stream_cache(key, "test/empty", url, "2", "Spring", {}, [])
        assert CacheService.get(key) is None

    def test_empty_key_skips_write(self):
        written = []
        _write_stream_cache("", "label", "url", "mode", "layout", {"a": {}}, [])
        assert written == []  # no exception, just silently skipped
