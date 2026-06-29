"""
Tests for codecarto.services.c_parser_service.CParserService

These tests focus on the service layer: path validation, error wrapping,
and graceful handling of missing libclang. The libclang integration itself
requires system-level LLVM libraries and is exercised in manual / CI tests.
"""

import importlib.util

import pytest
from codecarto.util.exceptions import CodeCartoException

_HAS_LIBCLANG = importlib.util.find_spec("clang") is not None
requires_libclang = pytest.mark.skipif(
    not _HAS_LIBCLANG,
    reason="libclang not installed — install with: uv sync --extra c-parsing",
)


class TestCParserServicePathValidation:
    """parse_file and parse_directory should raise CodeCartoException for bad paths."""

    def test_parse_file_missing_raises(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        with pytest.raises(CodeCartoException) as exc_info:
            CParserService.parse_file(str(tmp_path / "nonexistent.c"))

        exc = exc_info.value
        assert exc.status_code == 404
        assert "not found" in exc.message.lower()

    def test_parse_directory_missing_raises(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        missing = tmp_path / "no_such_dir"
        with pytest.raises(CodeCartoException) as exc_info:
            CParserService.parse_directory(str(missing))

        exc = exc_info.value
        assert exc.status_code == 404

    def test_parse_directory_empty_dir_raises(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        with pytest.raises(CodeCartoException) as exc_info:
            CParserService.parse_directory(str(tmp_path))

        exc = exc_info.value
        # "No .c or .h files found"
        assert exc.status_code == 404

    def test_parse_compile_commands_missing_raises(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        with pytest.raises(CodeCartoException) as exc_info:
            CParserService.parse_directory(
                str(tmp_path),
                compile_commands=str(tmp_path / "missing_cc.json"),
            )

        exc = exc_info.value
        assert exc.status_code == 404


class TestCParserServiceImportError:
    """Without libclang installed, CParserService should raise CodeCartoException
    wrapping the ImportError — not propagate a raw ImportError."""

    def test_parse_file_wraps_import_error_when_libclang_missing(self, tmp_path, monkeypatch):
        from codecarto.services.c_parser_service import CParserService

        # Create a real C file so path validation passes
        c_file = tmp_path / "hello.c"
        c_file.write_text("int main() { return 0; }\n")

        # Simulate libclang not being installed
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "clang.cindex" or name == "clang":
                raise ImportError("No module named 'clang'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        # Also reset the cached index so lazy-init runs again
        import codecarto.services.parsers.c_parser as c_parser_mod
        original_idx = c_parser_mod._clang_idx
        c_parser_mod._clang_idx = None

        try:
            with pytest.raises(CodeCartoException) as exc_info:
                CParserService.parse_file(str(c_file))
            assert "libclang" in exc_info.value.message.lower() or "clang" in exc_info.value.message.lower()
        finally:
            c_parser_mod._clang_idx = original_idx


class TestIsPlatformSpecificPath:
    """Pure path-matching logic — no libclang needed."""

    @pytest.mark.parametrize(
        "path",
        [
            "compat/apple-only.c",
            "compat/darwin/foo.c",
            "compat/mingw.c",
            "win32/console.c",
            "WIN32/Console.C",  # case-insensitive
            "compat\\solaris\\foo.c",  # backslash path separator
            "vendor/aix-stub.h",
        ],
    )
    def test_flags_platform_specific_paths(self, path):
        from codecarto.services.parsers.c_parser import is_platform_specific_path

        assert is_platform_specific_path(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "src/main.c",
            "builtin/commit.c",
            "include/git-compat-util.h",
        ],
    )
    def test_does_not_flag_normal_paths(self, path):
        from codecarto.services.parsers.c_parser import is_platform_specific_path

        assert is_platform_specific_path(path) is False


class TestDefaultParseArgs:
    """Pure arg-building logic — no libclang needed."""

    def test_includes_stub_header_isystem_and_std(self):
        from codecarto.services.parsers.c_parser import default_parse_args, _STUB_DIR

        args = default_parse_args()

        assert "-std=c11" in args
        assert "-isystem" in args
        assert str(_STUB_DIR) in args

    def test_includes_platform_defines(self):
        from codecarto.services.parsers.c_parser import default_parse_args

        args = default_parse_args()

        assert "-D__linux__" in args

    def test_project_root_adds_include_path(self, tmp_path):
        from codecarto.services.parsers.c_parser import default_parse_args

        args = default_parse_args(project_root=tmp_path)

        assert f"-I{tmp_path}" in args

    def test_no_project_root_omits_include_path(self):
        from codecarto.services.parsers.c_parser import default_parse_args

        args = default_parse_args()

        assert not any(a.startswith("-I") for a in args)


@requires_libclang
class TestParseDirectorySkipsPlatformSpecificFiles:
    def test_skips_platform_specific_files_and_reports_them(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        (tmp_path / "main.c").write_text("int main(void) { return 0; }\n")
        compat = tmp_path / "compat"
        compat.mkdir()
        (compat / "apple-only.c").write_text("void apple_only(void) {}\n")

        result = CParserService.parse_directory(str(tmp_path))

        skipped = result["meta"]["skipped_files"]
        assert any("apple-only.c" in s for s in skipped)
        assert not any("main.c" in s for s in skipped)
        assert "main.c" in result["meta"]["files"]

    def test_all_files_platform_specific_raises_no_files_left(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        compat = tmp_path / "compat"
        compat.mkdir()
        (compat / "apple-only.c").write_text("void apple_only(void) {}\n")

        # Directory has a .c file so the "no files found" check passes, but
        # every file is platform-specific and gets filtered before parsing.
        result = CParserService.parse_directory(str(tmp_path))

        assert result["meta"]["node_count"] == 0
        assert any("apple-only.c" in s for s in result["meta"]["skipped_files"])


@requires_libclang
class TestParseDirectoryDiagnostics:
    def test_stub_headers_resolve_common_posix_includes_without_warnings(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        (tmp_path / "main.c").write_text(
            "#include <unistd.h>\n"
            "#include <pthread.h>\n"
            "#include <stdint.h>\n"
            "int add(int a, int b) { return a + b; }\n"
            "int main(void) { pthread_t t; uint32_t x = add(2, 3); sleep(0); return (int)x; }\n"
        )

        result = CParserService.parse_directory(str(tmp_path))

        diag = result["meta"]["diagnostics"]
        assert diag["missing_header"] == 0
        assert diag["unknown_type"] == 0
        assert diag["files_with_warnings"] == 0

    def test_genuinely_missing_header_is_classified_and_flagged(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        (tmp_path / "broken.c").write_text(
            '#include "totally_missing_header_xyz.h"\n'
            "int main(void) { return 0; }\n"
        )

        result = CParserService.parse_directory(str(tmp_path))

        diag = result["meta"]["diagnostics"]
        assert diag["missing_header"] >= 1
        assert diag["files_with_warnings"] >= 1
        assert diag["worst_files"]

    def test_node_from_file_with_warning_is_flagged_for_frontend(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        (tmp_path / "broken.c").write_text(
            '#include "totally_missing_header_xyz.h"\n'
            "int broken_fn(void) { return 0; }\n"
        )

        result = CParserService.parse_directory(str(tmp_path))

        broken_nodes = [n for n in result["nodes"] if n.get("file") == "broken"]
        assert broken_nodes, "expected at least one node parsed from broken.c despite the error"
        assert any(n.get("has_parse_warning") is True for n in broken_nodes)


@requires_libclang
class TestParseFilesOnFileParsedCallback:
    """CParser.parse_files(on_file_parsed=...) — the hook the streaming
    endpoint uses to push nodes out as each file finishes, instead of
    waiting for the whole multi-file parse to return."""

    def test_callback_fires_once_per_file_with_that_files_nodes(self, tmp_path):
        from codecarto.services.parsers.c_parser import CParser

        (tmp_path / "a.c").write_text("int fn_a(void) { return 1; }\n")
        (tmp_path / "b.c").write_text("int fn_b(void) { return 2; }\n")

        calls: list[tuple[str, list]] = []
        result = CParser().parse_files(
            [tmp_path / "a.c", tmp_path / "b.c"],
            on_file_parsed=lambda name, nodes: calls.append((name, nodes)),
        )

        assert [c[0] for c in calls] == ["a.c", "b.c"]
        a_names = {n["name"] for n in calls[0][1]}
        b_names = {n["name"] for n in calls[1][1]}
        assert "fn_a" in a_names
        assert "fn_b" in b_names
        # The callback's nodes are a subset of (not a copy diverging from)
        # the final result — same dicts, so has_parse_warning etc. line up.
        assert sum(len(c[1]) for c in calls) == len(result["nodes"])

    def test_callback_nodes_flagged_with_has_parse_warning_for_that_file(self, tmp_path):
        from codecarto.services.parsers.c_parser import CParser

        (tmp_path / "broken.c").write_text(
            '#include "totally_missing_header_xyz.h"\n'
            "int broken_fn(void) { return 0; }\n"
        )

        calls: list[tuple[str, list]] = []
        CParser().parse_files(
            [tmp_path / "broken.c"],
            on_file_parsed=lambda name, nodes: calls.append((name, nodes)),
        )

        assert calls and calls[0][1], "expected at least one node from broken.c"
        assert all(n.get("has_parse_warning") is True for n in calls[0][1])

    def test_no_callback_is_backward_compatible(self, tmp_path):
        from codecarto.services.parsers.c_parser import CParser

        (tmp_path / "a.c").write_text("int fn_a(void) { return 1; }\n")

        result = CParser().parse_files([tmp_path / "a.c"])

        assert any(n["name"] == "fn_a" for n in result["nodes"])


@requires_libclang
class TestParseDirectoryOnProgressCallback:
    """CParserService.parse_directory(on_progress=...) — drives the SSE
    streaming endpoint. event_type is 'meta' (once) then 'nodes' (per file)."""

    def test_meta_event_precedes_nodes_and_reports_file_counts(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        (tmp_path / "main.c").write_text("int main(void) { return 0; }\n")
        compat = tmp_path / "compat"
        compat.mkdir()
        (compat / "apple-only.c").write_text("void apple_only(void) {}\n")

        events: list[tuple[str, dict]] = []
        CParserService.parse_directory(
            str(tmp_path), on_progress=lambda et, payload: events.append((et, payload))
        )

        assert events[0][0] == "meta"
        assert events[0][1]["total_files"] == 1  # apple-only.c was skipped
        assert any("apple-only.c" in s for s in events[0][1]["skipped_files"])
        assert all(et == "nodes" for et, _ in events[1:])

    def test_nodes_events_cover_every_target_file(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        (tmp_path / "a.c").write_text("int fn_a(void) { return 1; }\n")
        (tmp_path / "b.c").write_text("int fn_b(void) { return 2; }\n")

        events: list[tuple[str, dict]] = []
        CParserService.parse_directory(
            str(tmp_path), on_progress=lambda et, payload: events.append((et, payload))
        )

        node_events = [p for et, p in events if et == "nodes"]
        assert {e["file"] for e in node_events} == {"a.c", "b.c"}

    def test_no_callback_is_backward_compatible(self, tmp_path):
        from codecarto.services.c_parser_service import CParserService

        (tmp_path / "main.c").write_text("int main(void) { return 0; }\n")

        result = CParserService.parse_directory(str(tmp_path))

        assert result["meta"]["node_count"] >= 1


class TestParseGithubOnProgressCallback:
    """CParserService.parse_github(on_progress=...) cache-hit path — exercised
    without network by pre-seeding the repo cache directory directly."""

    def test_cache_hit_emits_fetching_then_forwards_to_parse_directory(self, tmp_path, monkeypatch):
        import time
        import json as jsonlib
        from codecarto.services import c_parser_service as svc

        cache_root = tmp_path / "cache"
        repo_cache = cache_root / "octocat-hello"
        src_dir = repo_cache / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "main.c").write_text("int main(void) { return 0; }\n")
        (repo_cache / "metadata.json").write_text(
            jsonlib.dumps({"owner": "octocat", "repo": "hello", "ts": time.time()})
        )
        monkeypatch.setattr(svc, "_REPO_CACHE_DIR", cache_root)

        events: list[tuple[str, dict]] = []

        def fake_parse_directory(path, max_files=None, on_progress=None, **_):
            if on_progress:
                on_progress("fetching", {"message": "should not double-fire"})
            return {"nodes": [], "edges": [], "meta": {}}

        monkeypatch.setattr(svc.CParserService, "parse_directory", staticmethod(fake_parse_directory))

        svc.CParserService.parse_github(
            "https://github.com/octocat/hello",
            on_progress=lambda et, payload: events.append((et, payload)),
        )

        assert events[0] == ("fetching", {"message": "Using cached clone of octocat/hello"})


class TestRepoCacheListingAndEviction:
    """CParserService.list_cached_repos/evict_repo_cache — eviction parity
    with CacheService's GET /parse/cache + DELETE /parse/cache/{key}."""

    def _seed_repo_cache(self, cache_root, owner, repo, ts=None):
        import time
        import json as jsonlib

        entry_dir = cache_root / f"{owner}-{repo}"
        src_dir = entry_dir / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "main.c").write_text("int main(void) { return 0; }\n")
        (entry_dir / "metadata.json").write_text(jsonlib.dumps({
            "owner": owner, "repo": repo,
            "url": f"https://github.com/{owner}/{repo}",
            "ts": ts if ts is not None else time.time(),
        }))
        return entry_dir

    def test_list_cached_repos_empty_when_no_cache_dir(self, tmp_path, monkeypatch):
        from codecarto.services import c_parser_service as svc

        monkeypatch.setattr(svc, "_REPO_CACHE_DIR", tmp_path / "does_not_exist")

        assert svc.CParserService.list_cached_repos() == []

    def test_list_cached_repos_returns_entries_newest_first(self, tmp_path, monkeypatch):
        from codecarto.services import c_parser_service as svc

        monkeypatch.setattr(svc, "_REPO_CACHE_DIR", tmp_path)
        self._seed_repo_cache(tmp_path, "octocat", "old", ts=1000.0)
        self._seed_repo_cache(tmp_path, "octocat", "new", ts=2000.0)

        entries = svc.CParserService.list_cached_repos()

        assert [e["key"] for e in entries] == ["octocat-new", "octocat-old"]
        assert entries[0]["owner"] == "octocat"
        assert entries[0]["repo"] == "new"
        assert entries[0]["size_bytes"] > 0

    def test_evict_repo_cache_removes_directory(self, tmp_path, monkeypatch):
        from codecarto.services import c_parser_service as svc

        monkeypatch.setattr(svc, "_REPO_CACHE_DIR", tmp_path)
        entry_dir = self._seed_repo_cache(tmp_path, "octocat", "hello")

        deleted = svc.CParserService.evict_repo_cache("octocat-hello")

        assert deleted is True
        assert not entry_dir.exists()

    def test_evict_repo_cache_missing_key_returns_false(self, tmp_path, monkeypatch):
        from codecarto.services import c_parser_service as svc

        monkeypatch.setattr(svc, "_REPO_CACHE_DIR", tmp_path)

        assert svc.CParserService.evict_repo_cache("nobody-nothing") is False

    @pytest.mark.parametrize("bad_key", ["../escape", "a/b", "a\\b", ".."])
    def test_evict_repo_cache_rejects_path_traversal(self, tmp_path, monkeypatch, bad_key):
        from codecarto.services import c_parser_service as svc

        monkeypatch.setattr(svc, "_REPO_CACHE_DIR", tmp_path)
        # A real sibling directory outside tmp_path that traversal *would*
        # reach if the guard were broken — assert it survives untouched.
        sibling = tmp_path.parent / "should_not_be_touched_by_test"
        sibling.mkdir(exist_ok=True)

        assert svc.CParserService.evict_repo_cache(bad_key) is False
        assert sibling.exists()
        sibling.rmdir()


@requires_libclang
class TestCLanguageParserUnsavedFiles:
    """CLangaugeParser (the unified-pipeline C adapter) parsing content that
    only exists in memory — e.g. fetched from GitHub, never written to disk.
    Before unsaved_files support this silently returned an empty graph for
    EVERY GitHub-sourced repo's C/H files, regardless of endpoint."""

    def test_parses_file_with_raw_content_and_no_real_path(self):
        from codecarto.services.parsers.c_language_parser import CLangaugeParser
        from codecarto.models.source_data import File

        f = File(
            url="https://raw.githubusercontent.com/x/y/HEAD/main.c",
            name="main.c", size=10,
            raw="int add(int a, int b) { return a + b; }\n",
        )

        g = CLangaugeParser().parse_files([f], depth=2)

        names = {d["label"] for _, d in g.nodes(data=True)}
        assert "add" in names

    def test_cross_file_calls_resolve_via_shared_virtual_header(self):
        from codecarto.services.parsers.c_language_parser import CLangaugeParser
        from codecarto.models.source_data import File

        header = File(
            url="https://raw.githubusercontent.com/x/y/HEAD/helper.h",
            name="helper.h", size=10, raw="int helper_fn(int x);",
        )
        main_c = File(
            url="https://raw.githubusercontent.com/x/y/HEAD/main.c",
            name="main.c", size=10,
            raw='#include "helper.h"\nint main(void) { return helper_fn(5); }',
        )
        helper_c = File(
            url="https://raw.githubusercontent.com/x/y/HEAD/helper.c",
            name="helper.c", size=10,
            raw='#include "helper.h"\nint helper_fn(int x) { return x * 2; }',
        )

        g = CLangaugeParser().parse_files([header, main_c, helper_c], depth=2)

        assert g.number_of_edges() >= 1
        edge_kinds = {d.get("kind") for _, _, d in g.edges(data=True)}
        assert "calls" in edge_kinds

    def test_has_parse_warning_is_top_level_not_nested_in_meta(self):
        from codecarto.services.parsers.c_language_parser import CLangaugeParser
        from codecarto.models.source_data import File

        f = File(
            url="https://raw.githubusercontent.com/x/y/HEAD/broken.c",
            name="broken.c", size=10,
            raw='#include "totally_missing_header_xyz.h"\nint broken_fn(void) { return 0; }',
        )

        g = CLangaugeParser().parse_files([f], depth=2)

        broken_nodes = [d for _, d in g.nodes(data=True) if d.get("label") == "broken_fn"]
        assert broken_nodes
        assert broken_nodes[0]["has_parse_warning"] is True
        assert "has_parse_warning" not in broken_nodes[0]["meta"]

    def test_real_disk_path_still_preferred_over_raw_content(self, tmp_path):
        """When a real file exists on disk, parse it directly rather than
        going through the virtual/unsaved_files path — keeps real project
        structure (and therefore real #include resolution) intact."""
        from codecarto.services.parsers.c_language_parser import CLangaugeParser
        from codecarto.models.source_data import File

        real_file = tmp_path / "real.c"
        real_file.write_text("int from_disk(void) { return 1; }\n")

        f = File(url=str(real_file), name="real.c", size=10, raw="garbage that should be ignored")

        g = CLangaugeParser().parse_files([f], depth=2)

        names = {d["label"] for _, d in g.nodes(data=True)}
        assert "from_disk" in names
