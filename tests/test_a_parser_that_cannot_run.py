"""A parser that cannot run over files the graph still draws says so.

C is read by libclang, an optional extra. Without it, every C file was drawn
as a file with nothing in it and nothing said why: the batch that would have
parsed them failed inside a `try` that only continued. The same was true of
the GitHub stream. A file drawn empty reads as a file with nothing to draw, so
the reason now travels beside the graph -- a `note` event in each stream, a
`notes` list in the one-shot parse -- and a stream that carried one is not
cached, since a replay would arrive without it.

libclang's import is made to fail as it does where it is not installed,
rather than uninstalling anything, so these run wherever the suite does -- and
everything between that import and the graph is the code that runs there, so
a failure swallowed anywhere on the way, the C adapter included, is seen.
"""

from __future__ import annotations

import json
import sys

import pytest
from fastapi.testclient import TestClient

from codecarto.services.local_repo_service import get_local_repo
from codecarto.services.unified_parser_service import UnifiedParserService

MISSING = ("libclang is not installed, so C and C++ declarations cannot be read. "
           "Install it with: uv sync --extra c-parsing")


@pytest.fixture
def without_libclang(monkeypatch):
    """`import clang.cindex` fails, and no index is left from an earlier parse."""
    from codecarto.services.parsers import c_parser

    monkeypatch.setitem(sys.modules, "clang", None)
    monkeypatch.setitem(sys.modules, "clang.cindex", None)
    monkeypatch.setattr(c_parser, "_clang", None)
    monkeypatch.setattr(c_parser, "_clang_idx", None)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "main.c").write_text("int main(void) { return 0; }\n")
    (tmp_path / "util.c").write_text("int util(void) { return 1; }\n")
    (tmp_path / "tool.py").write_text("def tool():\n    return 1\n")
    return tmp_path


def events(chunks: list[str]) -> list[tuple[str, dict]]:
    found = []
    for chunk in chunks:
        lines = chunk.strip().split("\n")
        found.append((lines[0].removeprefix("event: "),
                      json.loads(next(l for l in lines if l.startswith("data: "))[6:])))
    return found


def test_the_graph_says_which_files_it_could_not_read(repo, without_libclang):
    """Mutation: swallow the batch's exception again, or catch the ImportError
    in the C adapter and return an empty graph -- no note, and this fails."""
    graph = UnifiedParserService.build_graph(get_local_repo(str(repo)), 2, None)
    assert graph.graph["notes"] == [f"2 c file(s) drawn without their contents: {MISSING}"]
    labels = {d.get("label") for _, d in graph.nodes(data=True)}
    assert {"main.c", "util.c", "tool.py"} <= labels  # the files are still drawn


def test_a_c_backend_that_cannot_be_loaded_is_said_too(repo, monkeypatch):
    """The adapter imported its backend inside `except ImportError: return
    nx.DiGraph()`, so a backend that could not be loaded drew every C file
    empty and said nothing. Mutation: put that `except` back -- no note."""
    monkeypatch.setitem(sys.modules, "codecarto.services.parsers.c_parser", None)
    graph = UnifiedParserService.build_graph(get_local_repo(str(repo)), 2, None)
    notes = graph.graph.get("notes", [])
    assert len(notes) == 1 and notes[0].startswith("2 c file(s) drawn without their contents: ")
    assert "codecarto.services.parsers.c_parser" in notes[0]


@pytest.mark.asyncio
async def test_the_directory_stream_carries_it_after_meta(repo, without_libclang):
    chunks = [c async for c in UnifiedParserService.stream_parse(get_local_repo(str(repo)), depth=2)]
    found = events(chunks)
    assert found[0][0] == "meta"
    assert found[1] == ("note", {"message": f"2 c file(s) drawn without their contents: {MISSING}"})


@pytest.mark.asyncio
async def test_the_github_stream_carries_it_too(monkeypatch, without_libclang):
    """Mutation: return no events from a failed batch -- this fails."""
    import codecarto.services.github_service as gh_svc

    items = [("main.c", "blob", "https://raw.example/noted/main.c")]

    async def fake_fetch_tree_fast(owner, repo, headers, url):
        return items, "main", 1, False

    async def fake_get_raw_from_url(dl_url):
        return "int main(void) { return 0; }\n"

    monkeypatch.setattr(gh_svc, "fetch_tree_fast", fake_fetch_tree_fast)
    monkeypatch.setattr(gh_svc, "get_raw_from_url", fake_get_raw_from_url)
    chunks = [c async for c in UnifiedParserService.stream_parse_url("https://github.com/test/noted", depth=2)]
    notes = [data for kind, data in events(chunks) if kind == "note"]
    assert notes == [{"message": f"1 c file(s) drawn without their contents: {MISSING}"}]


def test_a_stream_that_carried_a_note_is_not_cached(monkeypatch):
    """Mutation: write the cache regardless -- the replay would serve this
    graph again without saying what it lacks, and this fails."""
    import codecarto.routers.unified_parser_router as router
    from codecarto.main import app

    async def fake_stream(**kwargs):
        yield 'event: meta\ndata: {"nodeCount": 0, "edgeCount": 0, "layout": "Spring"}\n\n'
        yield f"event: note\ndata: {json.dumps({'message': MISSING})}\n\n"
        yield 'event: done\ndata: {"elapsed_ms": 0}\n\n'

    written = []
    monkeypatch.setattr(UnifiedParserService, "stream_parse_url", staticmethod(fake_stream))
    monkeypatch.setattr(router, "_write_stream_cache", lambda *a, **k: written.append(a))
    resp = TestClient(app).post("/parse/stream-url",
                                json={"url": "https://github.com/test/noted-uncached", "depth": 2})
    assert resp.status_code == 200 and "event: note" in resp.text
    assert written == []
