"""A Showcase draws a parse's code, not its imports, and a folder of prose as one dot.

`showcase_graph` leaves a Showcase's import nodes out, and every link to or
from one, and folds a directory holding nothing but markdown to one node as
large as the lines its pages hold. These hold it to that over graphs made
here, over a stream as `/parse/stream-url` sends one, and through the route
itself over a repository on this disk.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app
from codecarto.services import cache_service
from codecarto.services.show_layout import lines_scale
from codecarto.services.showcase_graph import thinned, without_imports
from codecarto.services.stream_floor import floored

SHOWCASE = "Showcase(dot=2,gap=0.5,nest=true,sized=true)"


def _node(nid: str, kind: str, depth: int, label: str | None = None) -> dict:
    return {"id": nid, "kind": kind, "depth": depth, "label": label or nid.rsplit("/", 1)[-1]}


def _edge(source: str, target: str, kind: str = "contains") -> dict:
    return {"source": source, "target": target, "metadata": {"kind": kind}}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _events(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) == 2 and lines[0].startswith("event: "):
            out.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return out


def _parse() -> tuple[list[dict], list[dict]]:
    """A repository: a module importing two names, one from its sibling, and a
    prose folder of pages two deep beside a folder of a page and a module."""
    nodes = [
        _node("dir::r", "directory", 0),
        _node("file::r/a.py", "file", 1), _node("file::r/b.py", "file", 1),
        _node("a.Sequence", "import", 2, "Sequence"), _node("a.h", "import", 2, "h"),
        _node("a.f", "function", 2, "f"), _node("b.h", "function", 2, "h"),
        _node("dir::r/prose", "directory", 0), _node("file::r/prose/guide.md", "file", 1),
        _node("dir::r/prose/deep", "directory", 0), _node("file::r/prose/deep/notes.md", "file", 1),
        _node("dir::r/mixed", "directory", 0), _node("file::r/mixed/readme.md", "file", 1),
        _node("file::r/mixed/c.py", "file", 1),
    ]
    edges = [
        _edge("dir::r", "file::r/a.py"), _edge("dir::r", "file::r/b.py"),
        _edge("file::r/a.py", "a.Sequence"), _edge("file::r/a.py", "a.h"),
        _edge("file::r/a.py", "a.f"), _edge("file::r/b.py", "b.h"),
        _edge("a.f", "a.h", "imports"), _edge("a.h", "b.h", "uses"),
        _edge("file::r/a.py", "file::r/b.py", "depends_on"),
        _edge("dir::r", "dir::r/prose"), _edge("dir::r/prose", "file::r/prose/guide.md"),
        _edge("dir::r/prose", "dir::r/prose/deep"), _edge("dir::r/prose/deep", "file::r/prose/deep/notes.md"),
        _edge("dir::r", "dir::r/mixed"), _edge("dir::r/mixed", "file::r/mixed/readme.md"),
        _edge("dir::r/mixed", "file::r/mixed/c.py"),
    ]
    return nodes, edges


LINES = {"file::r/prose/guide.md": 400, "file::r/prose/deep/notes.md": 600, "file::r/mixed/readme.md": 9}


def test_a_showcase_draws_no_import_and_keeps_a_file_importing_another_as_a_link():
    # Mutation: keep the import nodes -- Sequence and h are drawn, with the
    # links to and from them, and this fails.
    nodes, edges = thinned(*_parse(), LINES)
    ids = {n["id"] for n in nodes}
    assert not {"a.Sequence", "a.h"} & ids
    assert not [e for e in edges if {e["source"], e["target"]} & {"a.Sequence", "a.h"}]
    assert {(e["source"], e["target"]) for e in edges if e["metadata"]["kind"] == "depends_on"} == {
        ("file::r/a.py", "file::r/b.py")}, "a file importing another lost its link"
    assert {"a.f", "b.h", "file::r/a.py"} <= ids


def test_a_folder_of_nothing_but_markdown_is_one_node_as_large_as_its_pages_lines():
    # The outermost folder of prose is the one dot, its pages and its folder
    # of pages gone; a folder holding a module beside its page is not prose.
    # Mutation: fold a folder by its own pages alone -- prose/deep is folded on
    # its own and prose keeps it, and this fails.
    nodes, edges = thinned(*_parse(), LINES)
    by_id = {n["id"]: n for n in nodes}
    assert by_id["dir::r/prose"]["meta"] == {"lines": 1000, "pages": 2}
    assert not {"file::r/prose/guide.md", "dir::r/prose/deep", "file::r/prose/deep/notes.md"} & set(by_id)
    assert not [e for e in edges if e["source"].startswith("dir::r/prose/") or "prose/" in e["target"]]
    assert ("dir::r", "dir::r/prose") in {(e["source"], e["target"]) for e in edges}
    # Mutation: fold a folder holding any markdown -- mixed is folded, and this fails.
    assert "meta" not in by_id["dir::r/mixed"] and "file::r/mixed/readme.md" in by_id


def test_a_folder_of_prose_is_sized_by_its_lines():
    # A directory's two dots up to a hundred lines, one more for each ten
    # times as many, at most six. Mutation: size it as any directory -- and
    # this fails.
    assert lines_scale(0) == lines_scale(100) == 2.0
    assert lines_scale(1000) == pytest.approx(3.0) and lines_scale(10 ** 9) == 6.0


def test_a_floored_showcase_folds_its_prose_by_the_lines_the_stream_measured():
    # As `/parse/stream-url` sends a repository: its tree, then each page's
    # lines as it is read, then its code. Mutation: drop the stream's `lines`
    # events -- the folder of prose is folded with no lines, and this fails.
    nodes, edges = _parse()
    async def stream():
        for node in nodes:
            if node["depth"] <= 1:
                yield _sse("node", node)
        for edge in edges:
            if edge["metadata"]["kind"] == "contains" and not edge["target"].startswith(("a.", "b.")):
                yield _sse("edge", edge)
        yield _sse("phase", {"phase": "symbols"})
        for page, count in LINES.items():
            yield _sse("lines", {"id": page, "lines": count})
        for node in nodes:
            if node["depth"] == 2:
                yield _sse("node", node)
        for edge in edges:
            if edge["source"].startswith(("a.", "b.", "file::r/a.py", "file::r/b.py")):
                yield _sse("edge", edge)
        yield _sse("done", {"elapsed_ms": 1})

    async def collect():
        return "".join([chunk async for chunk in floored(stream(), 1, SHOWCASE)])
    events = _events(asyncio.run(collect()))
    drawn = {e["id"]: e for kind, e in events if kind == "node"}
    assert drawn["dir::r/prose"]["meta"]["lines"] == 1000
    assert "a.Sequence" not in drawn and "file::r/prose/guide.md" not in drawn
    assert drawn["dir::r/prose"]["dot_scale"] == pytest.approx(3.0)
    assert events[-1][0] == "done" and events[-1][1]["nodes"] == len(drawn)


def test_a_showcase_laid_out_as_it_arrives_is_streamed_without_its_imports():
    # Mutation: let the stream through as it came -- the import and its link
    # are sent, and this fails.
    async def stream():
        yield _sse("node", _node("a.f", "function", 2))
        yield _sse("node", _node("a.h", "import", 2))
        yield _sse("edge", _edge("a.f", "a.h", "imports"))
        yield _sse("edge", _edge("file::r/a.py", "a.f"))

    async def collect():
        return "".join([chunk async for chunk in without_imports(stream())])
    events = _events(asyncio.run(collect()))
    assert [(kind, e.get("id") or e["target"]) for kind, e in events] == [("node", "a.f"), ("edge", "a.f")]


def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_service, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(cache_service, "_REPOS_DIR", tmp_path / "cache" / "repos")
    monkeypatch.setattr(cache_service, "_INDEX_FILE", tmp_path / "cache" / "repos" / "index.json")


def _repository(where: Path) -> Path:
    where.mkdir()
    (where / "a.py").write_text("import os\nfrom b import h\n\n\ndef f():\n    return h(os.sep)\n", encoding="utf-8")
    (where / "b.py").write_text("def h(x):\n    return x\n", encoding="utf-8")
    (where / "prose" / "deep").mkdir(parents=True)
    (where / "prose" / "guide.md").write_text("# Guide\n" + "line\n" * 399, encoding="utf-8")
    (where / "prose" / "deep" / "notes.md").write_text("# Notes\n" + "line\n" * 599, encoding="utf-8")
    return where


def test_a_local_folder_drawn_as_a_showcase_has_no_import_and_its_prose_folded(tmp_path, monkeypatch):
    # Through the route, a folder on this disk read whole. Mutation: lay a
    # local folder out as a Showcase unthinned -- its imports and its pages
    # are drawn, and this fails.
    _isolated_cache(tmp_path, monkeypatch)
    repo = _repository(tmp_path / "r")
    body = TestClient(app).post("/parse/stream-url", json={"url": str(repo), "depth": 3, "layout": SHOWCASE}).text
    drawn = {e["id"]: e for kind, e in _events(body) if kind == "node"}
    assert not [n for n in drawn.values() if n.get("kind") == "import"], "an import was drawn"
    prose = drawn["dir::r/prose"]
    assert prose["meta"]["lines"] == 1000 and prose["meta"]["pages"] == 2
    assert not [key for key in drawn if key.startswith(("file::r/prose/", "dir::r/prose/"))]
    assert prose["dot_scale"] == pytest.approx(3.0)
    # The Map draws the same folder as it was: its imports and its pages.
    mapped = {e["id"] for kind, e in _events(TestClient(app).post(
        "/parse/stream-url", json={"url": str(repo), "depth": 3, "layout": "Map"}).text) if kind == "node"}
    assert "file::r/prose/guide.md" in mapped


def test_a_showgraph_replayed_from_the_cache_says_the_depth_it_was_drawn_to(tmp_path, monkeypatch):
    # Mutation: replay a floored graph's end as any other's -- it says no
    # depth, the window takes the depth it asked for, and this fails.
    _isolated_cache(tmp_path, monkeypatch)
    url = str(tmp_path / "not-read")
    graph = {"graph": {"nodes": {
        "dir::r": {"metadata": {"depth": 0, "kind": "directory"}},
        "file::r/a.py": {"metadata": {"depth": 1, "kind": "file"}},
        "a.f": {"metadata": {"depth": 2, "kind": "function"}}}, "edges": []}, "metadata": {}}
    key = cache_service.CacheService.cache_key(url=url, mode="3/floor100", layout=SHOWCASE, extensions=[])
    cache_service.CacheService.set(key, graph, label="r", url=url, mode="3/floor100", layout=SHOWCASE)
    body = TestClient(app).post("/parse/stream-url",
                                json={"url": url, "depth": 3, "floor": 100, "layout": SHOWCASE}).text
    kind, done = _events(body)[-1]
    assert kind == "done" and done["from_cache"] is True
    assert (done["depth"], done["floor"], done["nodes"]) == (2, 100, 3)


def test_a_showcase_cached_before_it_was_thinned_is_parsed_again(tmp_path, monkeypatch):
    # At 11 a Showcase holds no import and no page of a folder of prose; one
    # cached at 10 holds both. Mutation: leave GRAPH_SCHEMA_VERSION at 10 --
    # the Showcase cached at 10 is served, and this fails.
    import hashlib

    _isolated_cache(tmp_path, monkeypatch)
    url = str(_repository(tmp_path / "r"))
    at_10 = hashlib.sha256(f"v10::{url}::3::{SHOWCASE}::{sorted([])}".encode()).hexdigest()[:16]
    old = {"graph": {"nodes": {"CACHED_AT_10": {"metadata": {"depth": 2, "kind": "import"}}}, "edges": []},
           "metadata": {}}
    cache_service.CacheService.set(f"{cache_service._repo_key_from_url(url)}::{at_10}", old, label="r",
                                   url=url, mode="3", layout=SHOWCASE)
    body = TestClient(app).post("/parse/stream-url", json={"url": url, "depth": 3, "layout": SHOWCASE}).text
    assert "CACHED_AT_10" not in body and "dir::r/prose" in body


@pytest.mark.asyncio
async def test_the_github_stream_says_each_markdown_pages_lines(monkeypatch):
    # Read as the host serves it: a page's lines, sent as the page is read,
    # are what a floored Showcase folds a folder of prose by. Mutation: send
    # no `lines` event -- and this fails.
    import codecarto.services.github_service as gh_svc
    from codecarto.services.unified_parser_service import UnifiedParserService

    pages = {"https://raw.example/r/prose/guide.md": "# Guide\n" + "line\n" * 41,
             "https://raw.example/r/m.py": "def f():\n    pass\n"}
    items = [("prose/guide.md", "blob", "https://raw.example/r/prose/guide.md"),
             ("m.py", "blob", "https://raw.example/r/m.py")]

    async def fake_fetch_tree_fast(owner, repo, headers, url):
        return items, "main", 1, False

    async def fake_get_raw_from_url(dl_url):
        return pages[dl_url]

    monkeypatch.setattr(gh_svc, "fetch_tree_fast", fake_fetch_tree_fast)
    monkeypatch.setattr(gh_svc, "get_raw_from_url", fake_get_raw_from_url)
    chunks = [c async for c in UnifiedParserService.stream_parse_url("https://github.com/test/r", depth=2)]
    measured = [data for kind, data in _events("".join(chunks)) if kind == "lines"]
    assert len(measured) == 1 and measured[0]["lines"] == 42
    assert measured[0]["id"].endswith("prose/guide.md")
    drawn = {data["id"] for kind, data in _events("".join(chunks)) if kind == "node"}
    assert measured[0]["id"] in drawn, "the lines name a page the stream drew under another id"


def test_a_repository_parsed_whole_as_a_showcase_has_no_import_and_its_prose_folded(tmp_path, monkeypatch):
    # `/parse/unified`, a repository's files sent with it: the one-shot parse
    # thins a Showcase as the stream does. Mutation: lay it out unthinned --
    # its import and its page are drawn, and this fails.
    _isolated_cache(tmp_path, monkeypatch)
    body = {
        "directory": {
            "info": {"url": "https://github.com/test/whole", "owner": "test", "name": "whole"},
            "size": 0,
            "root": {"name": "r", "size": 0, "files": [
                {"name": "a.py", "size": 0, "raw": "import os\n\n\ndef f():\n    return os.sep\n"}],
                "folders": [{"name": "prose", "size": 0, "folders": [],
                             "files": [{"name": "guide.md", "size": 0, "raw": "# Guide\n" + "line\n" * 999}]}]},
            "is_partial": False,
        },
        "depth": 3,
        "layout": SHOWCASE,
    }
    nodes = TestClient(app).post("/parse/unified", json=body).json()["results"]["graph"]["nodes"]
    kinds = {key: (node.get("metadata") or node).get("kind") for key, node in nodes.items()}
    assert "import" not in kinds.values() and "file::r/prose/guide.md" not in kinds
    assert (nodes["dir::r/prose"].get("metadata") or nodes["dir::r/prose"])["meta"]["lines"] == 1000
