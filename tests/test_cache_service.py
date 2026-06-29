"""
Tests for codecarto.services.cache_service.CacheService.

Covers the repo-keyed unification: the graph cache (final parsed gJGF,
keyed by url+mode+layout+extensions) and the new repo source-tree cache
now live under the same ~/.codecarto/cache/repos/{repo_key}/ directory
instead of two unrelated flat caches, so evicting/inspecting a repo's
cache touches both. Each test points _CACHE_DIR/_REPOS_DIR/_INDEX_FILE at
a tmp_path so nothing touches the real ~/.codecarto cache.
"""

from codecarto.services import cache_service as svc
from codecarto.services.cache_service import CacheService


def _isolate_cache(monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    repos_dir = cache_dir / "repos"
    monkeypatch.setattr(svc, "_CACHE_DIR", cache_dir)
    monkeypatch.setattr(svc, "_REPOS_DIR", repos_dir)
    monkeypatch.setattr(svc, "_INDEX_FILE", repos_dir / "index.json")


class TestRepoKeyFromUrl:
    def test_github_url_uses_owner_dash_repo(self):
        assert svc._repo_key_from_url("https://github.com/octocat/Hello-World") == "octocat-Hello-World"

    def test_non_github_url_hashes(self):
        key = svc._repo_key_from_url("/some/local/path")
        assert len(key) == 16
        assert key == svc._repo_key_from_url("/some/local/path")  # stable
        assert key != svc._repo_key_from_url("/other/local/path")


class TestGraphCache:
    def test_set_then_get_round_trips(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        key = CacheService.cache_key("https://github.com/a/b", "2", "Spring", [])
        CacheService.set(key, {"graph": {"nodes": {}, "edges": []}}, label="a/b", url="https://github.com/a/b", mode="2", layout="Spring")

        assert CacheService.get(key) == {"graph": {"nodes": {}, "edges": []}}

    def test_get_miss_returns_none(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        key = CacheService.cache_key("https://github.com/a/b", "2", "Spring", [])
        assert CacheService.get(key) is None

    def test_different_repos_get_different_keys(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        key_a = CacheService.cache_key("https://github.com/a/b", "2", "Spring", [])
        key_b = CacheService.cache_key("https://github.com/c/d", "2", "Spring", [])
        assert key_a != key_b
        assert key_a.split("::")[0] == "a-b"
        assert key_b.split("::")[0] == "c-d"

    def test_list_cached_includes_age_seconds(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        key = CacheService.cache_key("https://github.com/a/b", "2", "Spring", [])
        CacheService.set(key, {"graph": {}}, label="a/b", url="https://github.com/a/b", mode="2", layout="Spring")

        entries = CacheService.list_cached()
        assert len(entries) == 1
        assert entries[0]["key"] == key
        assert "age_seconds" in entries[0]

    def test_evict_removes_entry_and_blob(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        key = CacheService.cache_key("https://github.com/a/b", "2", "Spring", [])
        CacheService.set(key, {"graph": {}}, label="a/b", url="https://github.com/a/b", mode="2", layout="Spring")

        assert CacheService.evict(key) is True
        assert CacheService.get(key) is None
        assert CacheService.list_cached() == []

    def test_evict_missing_key_returns_false(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        assert CacheService.evict("nope-repo::deadbeef") is False


class TestTreeCache:
    def test_set_then_get_round_trips(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        url = "https://github.com/a/b"
        CacheService.set_tree(url, {"info": {"owner": "a", "name": "b"}, "size": 10})

        assert CacheService.get_tree(url) == {"info": {"owner": "a", "name": "b"}, "size": 10}

    def test_get_miss_returns_none(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        assert CacheService.get_tree("https://github.com/a/b") is None

    def test_expired_tree_returns_none(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        monkeypatch.setattr(svc, "_TTL_SECONDS", 1)
        url = "https://github.com/a/b"
        CacheService.set_tree(url, {"size": 1})

        path = svc._repo_dir(svc._repo_key_from_url(url)) / "tree.json"
        import os, time
        old = time.time() - 10
        os.utime(path, (old, old))

        assert CacheService.get_tree(url) is None


class TestEvictRepo:
    def test_evict_repo_removes_tree_and_graphs(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        url = "https://github.com/a/b"
        CacheService.set_tree(url, {"size": 1})
        key = CacheService.cache_key(url, "2", "Spring", [])
        CacheService.set(key, {"graph": {}}, label="a/b", url=url, mode="2", layout="Spring")

        assert CacheService.evict_repo(url) is True
        assert CacheService.get_tree(url) is None
        assert CacheService.get(key) is None
        assert CacheService.list_cached() == []

    def test_evict_repo_does_not_touch_other_repos(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        url_a = "https://github.com/a/b"
        url_c = "https://github.com/c/d"
        CacheService.set_tree(url_a, {"size": 1})
        CacheService.set_tree(url_c, {"size": 2})

        CacheService.evict_repo(url_a)

        assert CacheService.get_tree(url_a) is None
        assert CacheService.get_tree(url_c) == {"size": 2}

    def test_evict_repo_missing_returns_false(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)
        assert CacheService.evict_repo("https://github.com/nope/nope") is False
