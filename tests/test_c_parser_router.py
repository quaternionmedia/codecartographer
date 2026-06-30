"""
Tests for codecarto.routers.c_parser_router's /c-parser/stream-github SSE endpoint.

CParserService.parse_github is monkeypatched so these tests exercise the
router's queue-draining/threading/SSE-formatting logic deterministically,
without needing real libclang or network access. The real parse pipeline
(stub headers, diagnostics, on_progress plumbing) is covered separately in
test_c_parser_service.py.
"""

import json

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app
from codecarto.routers.c_parser_router import _stream_cached_c_graph, _c_cache_key
from codecarto.services.c_parser_service import CParserService
from codecarto.services.cache_service import CacheService


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch, tmp_path):
    """Redirect the graph cache to a per-test tmp dir so write-back from one
    test can't cause a cache hit in the next."""
    import codecarto.services.cache_service as cache_svc
    repos_dir = tmp_path / "repos"
    monkeypatch.setattr(cache_svc, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
    monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")
    monkeypatch.setattr(cache_svc, "_mongo_collection", None)


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type, data = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_type = line[len("event: "):].strip()
            elif line.startswith("data: "):
                import json
                data = json.loads(line[len("data: "):].strip())
        if event_type:
            events.append((event_type, data))
    return events


class TestStreamCGithubHappyPath:
    def test_emits_fetching_meta_node_edge_done_in_order(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            on_progress("fetching", {"message": "Downloading octocat/hello…"})
            on_progress("meta", {"total_files": 1, "skipped_files": []})
            on_progress("nodes", {"file": "main.c", "nodes": [
                {"id": "main::fn_a", "kind": "function", "name": "fn_a", "file": "main"},
            ]})
            return {
                "nodes": [{"id": "main::fn_a", "kind": "function", "name": "fn_a", "file": "main"}],
                "edges": [{"src": "main::fn_a", "dst": "main::fn_a", "kind": "CALLS", "weight": 1.0}],
                "meta": {"diagnostics": {"missing_header": 0}, "skipped_files": []},
            }

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post(
            "/c-parser/stream-github",
            json={"url": "https://github.com/octocat/hello", "max_files": 200},
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        events = _parse_sse(resp.text)
        types = [e[0] for e in events]
        assert types == ["fetching", "meta", "node", "reposition", "edge", "done"]

    def test_meta_event_reports_file_and_skip_counts(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            on_progress("meta", {"total_files": 5, "skipped_files": ["compat/apple.c"]})
            return {"nodes": [], "edges": [], "meta": {}}

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post(
            "/c-parser/stream-github", json={"url": "https://github.com/octocat/hello"}
        )

        events = dict(_parse_sse(resp.text))
        assert events["meta"] == {"fileCount": 5, "skippedCount": 1}

    def test_node_event_carries_language_and_depth(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            on_progress("nodes", {"file": "main.c", "nodes": [
                {"id": "main::fn_a", "kind": "function", "name": "fn_a", "file": "main"},
            ]})
            return {
                "nodes": [{"id": "main::fn_a", "kind": "function", "name": "fn_a", "file": "main"}],
                "edges": [],
                "meta": {},
            }

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post(
            "/c-parser/stream-github", json={"url": "https://github.com/octocat/hello"}
        )

        node_events = [p for et, p in _parse_sse(resp.text) if et == "node"]
        assert len(node_events) == 1
        node = node_events[0]
        assert {k: v for k, v in node.items() if k not in ("x", "y")} == {
            "id": "main::fn_a", "kind": "function", "name": "fn_a", "file": "main",
            "language": "c", "depth": 2,
        }
        assert isinstance(node["x"], (int, float))
        assert isinstance(node["y"], (int, float))

    def test_edge_remaps_src_dst_to_source_target(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            return {
                "nodes": [{"id": "a"}, {"id": "b"}],
                "edges": [{"src": "a", "dst": "b", "kind": "CALLS", "weight": 2.0}],
                "meta": {},
            }

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post(
            "/c-parser/stream-github", json={"url": "https://github.com/octocat/hello"}
        )

        edge_events = [p for et, p in _parse_sse(resp.text) if et == "edge"]
        assert edge_events == [{"source": "a", "target": "b", "label": "CALLS", "weight": 2.0}]

    def test_reposition_event_precedes_edges_with_real_layout(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            return {
                "nodes": [{"id": "a"}, {"id": "b"}],
                "edges": [{"src": "a", "dst": "b", "kind": "CALLS", "weight": 1.0}],
                "meta": {},
            }

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post(
            "/c-parser/stream-github",
            json={"url": "https://github.com/octocat/hello", "layout": "Spring"},
        )

        events = _parse_sse(resp.text)
        types = [e[0] for e in events]
        assert types.index("reposition") < types.index("edge")

        reposition = dict(events)["reposition"]
        assert set(reposition.keys()) == {"a", "b"}
        for pos in reposition.values():
            assert isinstance(pos["x"], (int, float))
            assert isinstance(pos["y"], (int, float))

    def test_no_nodes_skips_reposition_event(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            return {"nodes": [], "edges": [], "meta": {}}

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post(
            "/c-parser/stream-github", json={"url": "https://github.com/octocat/hello"}
        )

        types = [et for et, _ in _parse_sse(resp.text)]
        assert "reposition" not in types

    def test_edge_referencing_unknown_node_is_filtered(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            return {
                "nodes": [{"id": "a"}],
                "edges": [{"src": "a", "dst": "ghost", "kind": "FIELD_OF", "weight": 1.0}],
                "meta": {},
            }

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post(
            "/c-parser/stream-github", json={"url": "https://github.com/octocat/hello"}
        )

        edge_events = [p for et, p in _parse_sse(resp.text) if et == "edge"]
        assert edge_events == []

    def test_done_event_reports_counts_and_diagnostics(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            return {
                "nodes": [{"id": "a"}, {"id": "b"}],
                "edges": [{"src": "a", "dst": "b", "kind": "CALLS", "weight": 1.0}],
                "meta": {"diagnostics": {"missing_header": 3}, "skipped_files": ["x.c"]},
            }

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post(
            "/c-parser/stream-github", json={"url": "https://github.com/octocat/hello"}
        )

        events = dict(_parse_sse(resp.text))
        done = events["done"]
        assert done["node_count"] == 2
        assert done["edge_count"] == 1
        assert done["diagnostics"] == {"missing_header": 3}
        assert done["skipped_files"] == ["x.c"]
        assert isinstance(done["elapsed_ms"], int)


class TestStreamCGithubErrorPath:
    def test_exception_in_worker_emits_error_event_not_done(self, client, monkeypatch):
        def failing_parse_github(url, max_files=200, on_progress=None):
            raise ValueError("invalid GitHub URL")

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(failing_parse_github))

        resp = client.post(
            "/c-parser/stream-github", json={"url": "not-a-real-url"}
        )

        events = _parse_sse(resp.text)
        types = [e[0] for e in events]
        assert types == ["error"]
        assert "invalid GitHub URL" in dict(events)["error"]["message"]

    def test_exception_after_partial_progress_still_emits_error(self, client, monkeypatch):
        def failing_parse_github(url, max_files=200, on_progress=None):
            on_progress("meta", {"total_files": 1, "skipped_files": []})
            on_progress("nodes", {"file": "a.c", "nodes": [{"id": "a", "kind": "function"}]})
            raise RuntimeError("parse exploded")

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(failing_parse_github))

        resp = client.post(
            "/c-parser/stream-github", json={"url": "https://github.com/octocat/hello"}
        )

        events = _parse_sse(resp.text)
        types = [e[0] for e in events]
        assert types == ["meta", "node", "error"]
        assert "parse exploded" in dict(events)["error"]["message"]


class TestRepoCacheEndpoints:
    def test_list_cache_returns_entries(self, client, monkeypatch):
        monkeypatch.setattr(
            CParserService, "list_cached_repos",
            staticmethod(lambda: [{"key": "octocat-hello", "owner": "octocat"}]),
        )

        resp = client.get("/c-parser/cache")

        assert resp.status_code == 200
        assert resp.json()["results"]["entries"] == [{"key": "octocat-hello", "owner": "octocat"}]

    def test_evict_cache_found_returns_200(self, client, monkeypatch):
        monkeypatch.setattr(CParserService, "evict_repo_cache", staticmethod(lambda key: True))

        resp = client.delete("/c-parser/cache/octocat-hello")

        assert resp.status_code == 200
        assert resp.json()["status"] == 200

    def test_evict_cache_missing_returns_404_envelope(self, client, monkeypatch):
        monkeypatch.setattr(CParserService, "evict_repo_cache", staticmethod(lambda key: False))

        resp = client.delete("/c-parser/cache/nobody-nothing")

        assert resp.status_code == 200  # generate_return doesn't raise, unlike proc_exception
        assert resp.json()["status"] == 404


class TestStreamCGithubNodePositions:
    """Regression coverage: streamed nodes MUST carry x/y, or every node
    falls back to the exact center of the canvas in StreamingGraphRenderer
    (renders as nothing visible — thousands of nodes stacked on one pixel)."""

    def test_every_node_gets_numeric_x_and_y(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            on_progress("meta", {"total_files": 2, "skipped_files": []})
            on_progress("nodes", {"file": "a.c", "nodes": [
                {"id": "a::fn1", "kind": "function", "name": "fn1", "file": "a"},
                {"id": "a::fn2", "kind": "function", "name": "fn2", "file": "a"},
            ]})
            on_progress("nodes", {"file": "b.c", "nodes": [
                {"id": "b::fn1", "kind": "function", "name": "fn1", "file": "b"},
            ]})
            return {"nodes": [], "edges": [], "meta": {}}

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post("/c-parser/stream-github", json={"url": "https://github.com/o/r"})

        node_events = [p for et, p in _parse_sse(resp.text) if et == "node"]
        assert len(node_events) == 3
        for node in node_events:
            assert isinstance(node["x"], (int, float))
            assert isinstance(node["y"], (int, float))

    def test_different_files_get_different_cluster_centers(self, client, monkeypatch):
        """Symbols from different files must NOT collapse onto the same
        point — otherwise every file's nodes overlap visually."""
        def fake_parse_github(url, max_files=200, on_progress=None):
            on_progress("meta", {"total_files": 2, "skipped_files": []})
            on_progress("nodes", {"file": "a.c", "nodes": [
                {"id": "a::fn1", "kind": "function", "name": "fn1", "file": "a"},
            ]})
            on_progress("nodes", {"file": "b.c", "nodes": [
                {"id": "b::fn1", "kind": "function", "name": "fn1", "file": "b"},
            ]})
            return {"nodes": [], "edges": [], "meta": {}}

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post("/c-parser/stream-github", json={"url": "https://github.com/o/r"})

        node_events = [p for et, p in _parse_sse(resp.text) if et == "node"]
        positions = {(n["x"], n["y"]) for n in node_events}
        assert len(positions) == len(node_events), "nodes from different files collapsed onto the same point"

    def test_symbols_within_same_file_dont_all_collapse_onto_one_point(self, client, monkeypatch):
        def fake_parse_github(url, max_files=200, on_progress=None):
            on_progress("nodes", {"file": "a.c", "nodes": [
                {"id": "a::fn1", "kind": "function", "name": "fn1", "file": "a"},
                {"id": "a::fn2", "kind": "function", "name": "fn2", "file": "a"},
                {"id": "a::fn3", "kind": "function", "name": "fn3", "file": "a"},
            ]})
            return {"nodes": [], "edges": [], "meta": {}}

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        resp = client.post("/c-parser/stream-github", json={"url": "https://github.com/o/r"})

        node_events = [p for et, p in _parse_sse(resp.text) if et == "node"]
        positions = {(n["x"], n["y"]) for n in node_events}
        assert len(positions) == len(node_events)


def _parse_cached_sse(text: str) -> list[tuple[str, dict]]:
    """Re-use _parse_sse logic for the async-generator tests."""
    return _parse_sse(text)


async def _collect_c_cached(cached: dict) -> list[tuple[str, dict]]:
    events = []
    async for chunk in _stream_cached_c_graph(cached):
        event_type, data = None, None
        for line in chunk.strip().split("\n"):
            if line.startswith("event: "):
                event_type = line[len("event: "):].strip()
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):].strip())
        if event_type:
            events.append((event_type, data))
    return events


class TestStreamCachedCGraph:
    @pytest.mark.asyncio
    async def test_event_order_meta_nodes_reposition_edges_done(self):
        cached = {
            "nodes": [{"id": "a", "kind": "function", "file": "f"}],
            "edges": [{"src": "a", "dst": "a", "kind": "CALLS"}],
            "positions": {"a": {"x": 1.0, "y": 2.0}},
            "layout": "Spring",
            "meta": {"total_files": 1},
        }
        events = await _collect_c_cached(cached)
        types = [t for t, _ in events]
        assert types == ["meta", "node", "reposition", "edge", "done"]

    @pytest.mark.asyncio
    async def test_positions_baked_into_node_events(self):
        cached = {
            "nodes": [{"id": "a", "kind": "function"}],
            "edges": [],
            "positions": {"a": {"x": 42.0, "y": -7.5}},
            "layout": "Spring",
            "meta": {},
        }
        events = await _collect_c_cached(cached)
        node = next(d for t, d in events if t == "node")
        assert node["x"] == 42.0
        assert node["y"] == -7.5

    @pytest.mark.asyncio
    async def test_from_cache_flags_in_meta_and_done(self):
        cached = {"nodes": [], "edges": [], "positions": {}, "layout": "Spring", "meta": {}}
        events = await _collect_c_cached(cached)
        meta = next(d for t, d in events if t == "meta")
        done = next(d for t, d in events if t == "done")
        assert meta["from_cache"] is True
        assert done["from_cache"] is True

    @pytest.mark.asyncio
    async def test_edges_outside_node_set_filtered(self):
        cached = {
            "nodes": [{"id": "a", "kind": "function"}],
            "edges": [
                {"src": "a", "dst": "ghost", "kind": "CALLS"},
                {"src": "ghost", "dst": "a", "kind": "CALLS"},
            ],
            "positions": {},
            "layout": "Spring",
            "meta": {},
        }
        events = await _collect_c_cached(cached)
        edge_events = [d for t, d in events if t == "edge"]
        assert edge_events == []

    @pytest.mark.asyncio
    async def test_no_positions_skips_reposition_event(self):
        cached = {
            "nodes": [{"id": "a"}],
            "edges": [],
            "positions": {},
            "layout": "Spring",
            "meta": {},
        }
        events = await _collect_c_cached(cached)
        types = [t for t, _ in events]
        assert "reposition" not in types


class TestCCacheKey:
    def test_uses_c_mode_to_avoid_collision(self):
        url = "https://github.com/test/repo"
        key_c = _c_cache_key(url, "Spring")
        key_unified = CacheService.cache_key(url=url, mode="2", layout="Spring", extensions=[])
        assert key_c != key_unified

    def test_same_url_and_layout_produces_same_key(self):
        url = "https://github.com/test/repo"
        assert _c_cache_key(url, "Spring") == _c_cache_key(url, "Spring")

    def test_different_layout_produces_different_key(self):
        url = "https://github.com/test/repo"
        assert _c_cache_key(url, "Spring") != _c_cache_key(url, "Spectral")


class TestStreamCGithubCacheWriteback:
    """After a live stream, the result should be persisted to CacheService
    so the next request for the same URL+layout is an instant cache replay."""

    def test_cache_hit_after_first_stream(self, client, monkeypatch, tmp_path):
        import codecarto.services.cache_service as cache_svc
        repos_dir = tmp_path / "repos"
        monkeypatch.setattr(cache_svc, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
        monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")

        def fake_parse_github(url, max_files=200, on_progress=None):
            return {
                "nodes": [{"id": "a", "kind": "function"}],
                "edges": [],
                "meta": {},
            }

        monkeypatch.setattr(CParserService, "parse_github", staticmethod(fake_parse_github))

        url = "https://github.com/test/cache-writeback"
        client.post("/c-parser/stream-github", json={"url": url, "layout": "Spring"})

        key = _c_cache_key(url, "Spring")
        cached = CacheService.get(key)
        assert cached is not None
        assert len(cached["nodes"]) == 1
