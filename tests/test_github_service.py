"""
Tests for codecarto.services.github_service:
  - handle_status_code: must surface the REAL status code and response body
    instead of collapsing everything into a generic "GitHub API returned 500"
    (this masked an invalid GITHUB_TOKEN/GH_TOKEN — a 401 — as an opaque 500).
  - fetch_tree_fast: short-TTL in-memory memoization to avoid burning the
    60/hour unauthenticated api.github.com budget on repeat requests for the
    same repo.
  - get_raw_from_repo: persistent tree cache (CacheService.get_tree/set_tree)
    so reopening a repo doesn't repull GitHub, plus the three size-tier
    fetch behaviors (small=content, medium=structure-only, huge=shallow).
"""

import httpx
import pytest

from codecarto.services import cache_service as cache_svc
from codecarto.services import github_service as svc
from codecarto.util.exceptions import (
    Github403Error,
    Github404Error,
    GithubAPIError,
    GithubError,
    GithubNoDataError,
    GithubRateLimitError,
)


def _isolate_cache(monkeypatch, tmp_path):
    """Point the cache at a tmp dir so these tests never touch ~/.codecarto."""
    cache_dir = tmp_path / "cache"
    repos_dir = cache_dir / "repos"
    monkeypatch.setattr(cache_svc, "_CACHE_DIR", cache_dir)
    monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
    monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")


def _response(status_code: int, text: str = "", headers: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        text=text,
        headers=headers or {},
        request=httpx.Request("GET", "https://api.github.com/repos/octocat/hello"),
    )


class TestHandleStatusCode:
    def test_404_returns_no_data_error(self):
        exc = svc.handle_status_code(_response(404, "Not Found"), "url")
        assert isinstance(exc, GithubNoDataError)
        assert exc.status_code == 404
        assert "404" in exc.message

    def test_401_reports_invalid_credentials_not_generic_500(self):
        exc = svc.handle_status_code(_response(401, "Bad credentials"), "url")
        assert isinstance(exc, GithubAPIError)
        # The whole point of this fix: a 401 must never read as "returned 500".
        assert "500" not in exc.message
        assert "401" in exc.message
        assert "GITHUB_TOKEN" in exc.message or "GH_TOKEN" in exc.message
        assert "Bad credentials" in exc.message

    def test_429_returns_rate_limit_error(self):
        exc = svc.handle_status_code(_response(429, "Too Many Requests"), "url")
        assert isinstance(exc, GithubRateLimitError)
        assert exc.status_code == 429
        assert "429" in exc.message

    def test_403_with_rate_limit_body_returns_rate_limit_error(self):
        exc = svc.handle_status_code(
            _response(403, '{"message": "API rate limit exceeded for 1.2.3.4."}'), "url"
        )
        assert isinstance(exc, GithubRateLimitError)

    def test_403_with_secondary_abuse_body_returns_rate_limit_error(self):
        exc = svc.handle_status_code(
            _response(403, '{"message": "You have exceeded a secondary rate limit. Please retry... abuse detection"}'),
            "url",
        )
        assert isinstance(exc, GithubRateLimitError)

    def test_403_without_rate_limit_wording_returns_403_error(self):
        exc = svc.handle_status_code(_response(403, "Repository access blocked"), "url")
        assert isinstance(exc, Github403Error)
        assert not isinstance(exc, GithubRateLimitError)

    def test_429_surfaces_retry_after_header(self):
        exc = svc.handle_status_code(
            _response(429, "Too Many Requests", headers={"retry-after": "30"}), "url"
        )
        assert "30" in exc.message

    def test_unmapped_status_preserves_real_code_not_generic_500(self):
        exc = svc.handle_status_code(_response(502, "Bad Gateway upstream"), "url")
        assert isinstance(exc, GithubError)
        assert exc.status_code == 502
        assert "502" in exc.message
        assert "Bad Gateway upstream" in exc.message

    def test_long_body_is_truncated(self):
        exc = svc.handle_status_code(_response(502, "x" * 10_000), "url")
        assert len(exc.message) < 1000


class TestFetchTreeFastCaching:
    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        svc._tree_cache.clear()
        yield
        svc._tree_cache.clear()

    async def _run(self, monkeypatch, call_counter):
        class FakeResponse:
            def __init__(self, payload):
                self.status_code = 200
                self._payload = payload

            def json(self):
                return self._payload

        async def fake_get(self, url, headers=None, **kwargs):
            call_counter.append(url)
            if "/git/trees/" in url:
                return FakeResponse({"tree": [{"path": "main.c", "type": "blob"}]})
            return FakeResponse({"default_branch": "main"})

        monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    @pytest.mark.asyncio
    async def test_second_call_within_ttl_skips_network(self, monkeypatch):
        calls: list[str] = []
        await self._run(monkeypatch, calls)

        items1, branch1, size1, truncated1 = await svc.fetch_tree_fast("octocat", "hello", {}, "url")
        first_call_count = len(calls)
        assert first_call_count == 2  # repo metadata + tree

        items2, branch2, size2, truncated2 = await svc.fetch_tree_fast("octocat", "hello", {}, "url")

        assert len(calls) == first_call_count, "second call should be served from cache, no new requests"
        assert items2 == items1
        assert branch2 == branch1
        assert size2 == size1
        assert truncated2 == truncated1

    @pytest.mark.asyncio
    async def test_different_repo_is_not_cached_together(self, monkeypatch):
        calls: list[str] = []
        await self._run(monkeypatch, calls)

        await svc.fetch_tree_fast("octocat", "hello", {}, "url")
        count_after_first = len(calls)
        await svc.fetch_tree_fast("octocat", "other-repo", {}, "url")

        assert len(calls) == count_after_first + 2, "a different repo must trigger fresh requests"

    @pytest.mark.asyncio
    async def test_expired_ttl_triggers_fresh_fetch(self, monkeypatch):
        import time

        calls: list[str] = []
        await self._run(monkeypatch, calls)

        await svc.fetch_tree_fast("octocat", "hello", {}, "url")
        count_after_first = len(calls)

        # Simulate TTL expiry by backdating the cached entry.
        ts, items, branch, size_kb, truncated = svc._tree_cache["octocat/hello"]
        svc._tree_cache["octocat/hello"] = (ts - svc._TREE_CACHE_TTL - 1, items, branch, size_kb, truncated)

        await svc.fetch_tree_fast("octocat", "hello", {}, "url")

        assert len(calls) == count_after_first + 2, "expired entry must trigger fresh requests"


class TestGetRawFromRepo:
    @pytest.fixture(autouse=True)
    def _isolate(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)

    @pytest.mark.asyncio
    async def test_cache_hit_skips_network_entirely(self, monkeypatch):
        from codecarto.services.cache_service import CacheService

        url = "https://github.com/octocat/hello"
        CacheService.set_tree(url, {
            "info": {"owner": "octocat", "name": "hello", "url": url},
            "size": 1,
            "root": {"name": "octocat/hello", "size": 0, "files": [], "folders": []},
            "is_partial": False,
        })

        async def fail_if_called(*args, **kwargs):
            raise AssertionError("fetch_tree_fast should not be called on a cache hit")

        monkeypatch.setattr(svc, "fetch_tree_fast", fail_if_called)

        directory = await svc.get_raw_from_repo(url)
        assert directory.root.name == "octocat/hello"

    @pytest.mark.asyncio
    async def test_small_repo_fetches_content_and_caches_tree(self, monkeypatch):
        from codecarto.services.cache_service import CacheService

        url = "https://github.com/octocat/hello"

        async def fake_fetch_tree_fast(owner, repo, headers, u):
            return (
                [("main.py", "blob", "https://raw.githubusercontent.com/octocat/hello/main/main.py")],
                "main", 10, False,
            )

        async def fake_get_raw_from_url(dl_url):
            return "x = 1\n"

        monkeypatch.setattr(svc, "fetch_tree_fast", fake_fetch_tree_fast)
        monkeypatch.setattr(svc, "get_raw_from_url", fake_get_raw_from_url)

        directory = await svc.get_raw_from_repo(url)

        assert directory.is_partial is False
        assert directory.root.files[0].raw == "x = 1\n"

        cached = CacheService.get_tree(url)
        assert cached is not None
        assert cached["root"]["files"][0]["raw"] == "x = 1\n"

    @pytest.mark.asyncio
    async def test_medium_repo_skips_content_fetch(self, monkeypatch):
        url = "https://github.com/octocat/hello"

        async def fake_fetch_tree_fast(owner, repo, headers, u):
            return (
                [("main.py", "blob", "https://raw.githubusercontent.com/octocat/hello/main/main.py")],
                "main", 10_000, False,
            )

        async def fail_if_called(dl_url):
            raise AssertionError("medium repos must not download file content")

        monkeypatch.setattr(svc, "fetch_tree_fast", fake_fetch_tree_fast)
        monkeypatch.setattr(svc, "get_raw_from_url", fail_if_called)

        directory = await svc.get_raw_from_repo(url)

        assert directory.is_partial is False
        assert directory.root.files[0].raw == ""

    @pytest.mark.asyncio
    async def test_huge_repo_falls_back_to_shallow_root(self, monkeypatch):
        from codecarto.models.source_data import Folder

        url = "https://github.com/octocat/hello"

        async def fake_fetch_tree_fast(owner, repo, headers, u):
            return [], "main", 100_000, False

        async def fake_get_shallow_root(owner, repo, u, headers):
            return Folder(name="", size=0, files=[], folders=[])

        monkeypatch.setattr(svc, "fetch_tree_fast", fake_fetch_tree_fast)
        monkeypatch.setattr(svc, "get_shallow_root", fake_get_shallow_root)

        directory = await svc.get_raw_from_repo(url)

        assert directory.is_partial is True

    @pytest.mark.asyncio
    async def test_truncated_tree_falls_back_to_shallow_root(self, monkeypatch):
        from codecarto.models.source_data import Folder

        url = "https://github.com/octocat/hello"

        async def fake_fetch_tree_fast(owner, repo, headers, u):
            return [], "main", 10, True  # small size_kb but truncated by GitHub

        async def fake_get_shallow_root(owner, repo, u, headers):
            return Folder(name="", size=0, files=[], folders=[])

        monkeypatch.setattr(svc, "fetch_tree_fast", fake_fetch_tree_fast)
        monkeypatch.setattr(svc, "get_shallow_root", fake_get_shallow_root)

        directory = await svc.get_raw_from_repo(url)

        assert directory.is_partial is True


class TestExpandAllSaysWhatItLeftUnlisted:
    """Expand All's tree is partial wherever a folder in it was not listed.

    A folder below `max_depth`, or one GitHub refused, came back as an empty
    folder in a tree marked `is_partial=False`, and the Files panel draws an
    empty folder in a complete tree as empty, with no `…` and no click: the
    reader could not tell it from an empty folder, or open it. The route says
    the tree is partial, so the panel offers each such folder its read.
    """

    @pytest.fixture(autouse=True)
    def _isolate(self, monkeypatch, tmp_path):
        _isolate_cache(monkeypatch, tmp_path)

    URL = "https://github.com/octocat/hello"

    @staticmethod
    def _listing(*entries):
        return [
            {"type": kind, "name": path.split("/")[-1], "path": path,
             "download_url": f"https://raw.githubusercontent.com/octocat/hello/main/{path}" if kind == "file" else None,
             "size": 1}
            for kind, path in entries
        ]

    def _serve(self, monkeypatch, listings: dict, refused: set = frozenset()):
        """Answer the contents API from `listings` by path; 403 for `refused`."""
        import json

        base = "https://api.github.com/repos/octocat/hello/contents/"

        async def fake_api_get(client, url, headers):
            path = url[len(base):]
            if path in refused:
                return _response(403, '{"message": "API rate limit exceeded"}')
            return _response(200, json.dumps(listings[path]))

        monkeypatch.setattr(svc, "_api_get", fake_api_get)

    def _tree(self):
        return {
            "": self._listing(("file", "README.md"), ("dir", "src"), ("dir", "vendor")),
            "src": self._listing(("file", "src/main.py"), ("dir", "src/lib")),
            "src/lib": self._listing(("file", "src/lib/util.py")),
            "vendor": self._listing(("file", "vendor/x.c")),
        }

    async def _expand(self, max_depth):
        from codecarto.routers import repo_router

        answer = await repo_router.expand_all_repo(self.URL, max_depth)
        assert answer["status"] == 200, answer
        return answer["results"]

    async def test_every_folder_listed_is_a_complete_tree(self, monkeypatch):
        self._serve(monkeypatch, self._tree())
        tree = await self._expand(3)
        assert tree["is_partial"] is False
        src = next(f for f in tree["root"]["folders"] if f["name"] == "src")
        assert [f["name"] for f in src["folders"][0]["files"]] == ["util.py"]

    async def test_a_folder_below_the_depth_is_unlisted_and_the_tree_says_so(self, monkeypatch):
        """Mutation: build the Directory with `is_partial=False` again -- this fails."""
        self._serve(monkeypatch, self._tree())
        tree = await self._expand(2)
        src = next(f for f in tree["root"]["folders"] if f["name"] == "src")
        assert src["folders"][0] == {"name": "lib", "size": 0, "files": [], "folders": []}
        assert tree["is_partial"] is True

    async def test_a_folder_github_refused_is_unlisted_and_the_tree_says_so(self, monkeypatch):
        self._serve(monkeypatch, self._tree(), refused={"vendor"})
        tree = await self._expand(3)
        vendor = next(f for f in tree["root"]["folders"] if f["name"] == "vendor")
        assert vendor["files"] == [] and vendor["folders"] == []
        assert tree["is_partial"] is True

    async def test_a_refused_root_is_an_error_and_not_an_empty_tree(self, monkeypatch):
        """An empty tree would replace the one the reader has, and the panel hides an empty tree."""
        from fastapi import HTTPException

        self._serve(monkeypatch, self._tree(), refused={""})
        with pytest.raises(HTTPException) as refused:
            await self._expand(3)
        assert refused.value.status_code == 429
