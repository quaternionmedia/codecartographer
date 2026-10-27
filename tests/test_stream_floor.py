"""A showgraph's code view is held to a floor of nodes: drawn deeper where a project is small.

`stream_floor.floored` reads a parse's stream drawn to its deepest and lets
through the shallowest depth holding the floor's nodes. These hold it to that
over streams made here, shaped as `/parse/stream-url` sends them, and through
the route itself over a repository on this disk.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient

from codecarto.main import app
from codecarto.services.stream_floor import CODE_FLOOR, floored


def _node(nid: str, depth: int) -> str:
    return f"event: node\ndata: {json.dumps({'id': nid, 'depth': depth})}\n\n"


def _edge(source: str, target: str) -> str:
    return f"event: edge\ndata: {json.dumps({'source': source, 'target': target, 'kind': 'contains'})}\n\n"


def _events(chunks: list[str]) -> list[tuple[str, dict]]:
    out = []
    for chunk in chunks:
        lines = chunk.strip().split("\n")
        out.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return out


def _run(stream, floor: int) -> list[tuple[str, dict]]:
    async def collect():
        return [chunk async for chunk in floored(stream, floor)]
    return _events(asyncio.run(collect()))


def _repository(files: int, symbols: int, members: int, fetched: list[str], phase: bool = True):
    """A stream as `/parse/stream-url` sends one: its directory and files, a
    `phase` event, then a symbol per file in turn with its members, and `done`.
    `fetched` records each file whose symbols were asked for."""
    async def stream():
        yield 'event: meta\ndata: {"nodeCount": 0}\n\n'
        yield _node("dir::root", 0)
        for i in range(files):
            yield _node(f"file::root/f{i}.py", 1)
            yield _edge("dir::root", f"file::root/f{i}.py")
        if phase:
            yield 'event: phase\ndata: {"phase": "symbols"}\n\n'
        for i in range(symbols):
            fetched.append(f"f{i % files}.py")
            yield _node(f"sym{i}", 2)
            yield _edge(f"file::root/f{i % files}.py", f"sym{i}")
        for i in range(members):
            yield _node(f"member{i}", 3)
            yield _edge(f"sym{i % max(symbols, 1)}", f"member{i}")
        yield 'event: done\ndata: {"elapsed_ms": 7}\n\n'
    return stream()


def test_a_project_whose_files_reach_the_floor_is_drawn_to_them_and_no_file_is_fetched():
    # Mutation: let the stream run on past the files -- its symbols are
    # fetched and drawn, and this fails.
    fetched: list[str] = []
    events = _run(_repository(files=120, symbols=40, members=40, fetched=fetched), floor=100)
    nodes = [e for kind, e in events if kind == "node"]
    assert len(nodes) == 121 and all(n["depth"] <= 1 for n in nodes)
    assert fetched == [], "a file was fetched for its symbols past the floor"
    assert events[-1] == ("done", {"elapsed_ms": events[-1][1]["elapsed_ms"], "depth": 1, "floor": 100, "nodes": 121})


def test_a_small_project_is_drawn_to_its_symbols_and_its_members_are_left_out_once_they_reach_it():
    # Ten files and ninety-five symbols reach a hundred: the members are left
    # out, and their edges with them. Mutation: let the members through
    # always -- and this fails.
    events = _run(_repository(files=10, symbols=95, members=30, fetched=[]), floor=100)
    nodes = [e for kind, e in events if kind == "node"]
    edges = [e for kind, e in events if kind == "edge"]
    assert {n["depth"] for n in nodes} == {0, 1, 2}
    assert not [e for e in edges if e["target"].startswith("member")], "an edge to a member left out was drawn"
    assert events[-1][1]["depth"] == 2 and events[-1][1]["nodes"] == 106


def test_a_project_whose_symbols_fall_short_is_drawn_to_its_members_too():
    # Mutation: never let the members through -- the project is drawn with
    # fifty-one nodes, and this fails.
    events = _run(_repository(files=10, symbols=40, members=60, fetched=[]), floor=100)
    nodes = [e for kind, e in events if kind == "node"]
    edges = [e for kind, e in events if kind == "edge"]
    assert len(nodes) == 111 and max(n["depth"] for n in nodes) == 3
    assert len([e for e in edges if e["target"].startswith("member")]) == 60
    # Each member arrives with its edge, never an edge before its node.
    seen: set[str] = set()
    for kind, e in events:
        if kind == "node":
            seen.add(e["id"])
        elif kind == "edge" and e["target"].startswith("member"):
            assert e["target"] in seen, "a member's edge arrived before the member"
    assert events[-1][1]["depth"] == 3 and events[-1][1]["nodes"] == 111


def test_a_deepened_project_is_laid_out_whole_and_nothing_is_drawn_over_anything():
    # The stream places each file's symbols in a ring round the file as it
    # arrives, where they pile on their neighbours'. Mutation: send a deepened
    # project as it was placed -- its symbols are drawn over each other and
    # over the files, and this fails.
    from codecarto.services.show_layout import _drawn_r

    async def stream():
        yield 'event: meta\ndata: {"nodeCount": 9}\n\n'
        yield f"event: node\ndata: {json.dumps({'id': 'dir::root', 'depth': 0, 'x': 0, 'y': 0})}\n\n"
        for f in range(8):
            yield f"event: node\ndata: {json.dumps({'id': f'file::root/f{f}.py', 'depth': 1, 'x': 30 * f, 'y': 0})}\n\n"
            yield ("event: edge\ndata: " + json.dumps({"source": "dir::root", "target": f"file::root/f{f}.py",
                                                      "metadata": {"kind": "contains"}}) + "\n\n")
        yield 'event: phase\ndata: {"phase": "symbols"}\n\n'
        for f in range(8):
            for s in range(6):
                # As the stream places a symbol: 25 units round its file.
                yield (f"event: node\ndata: {json.dumps({'id': f's{f}.{s}', 'depth': 2, 'x': 30 * f + 25, 'y': s})}"
                       "\n\n")
                yield _edge(f"file::root/f{f}.py", f"s{f}.{s}")
        # A module the files import from elsewhere: held by nothing in the repository.
        yield _node("external::os", 1)
        yield ("event: edge\ndata: " + json.dumps({"source": "file::root/f0.py", "target": "external::os",
                                                  "kind": "depends_on"}) + "\n\n")
        yield 'event: done\ndata: {"elapsed_ms": 3}\n\n'

    events = _run(stream(), floor=100)
    nodes = [e for kind, e in events if kind == "node"]
    # Mutation: keep what nothing in the repository holds -- the imported
    # module is drawn, and this fails.
    assert "external::os" not in {n["id"] for n in nodes}
    assert len(nodes) == 57 and events[-1][1]["depth"] == 2
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            apart = ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5
            assert apart >= _drawn_r(a["depth"]) + _drawn_r(b["depth"]) - 1e-6, \
                f"{a['id']} and {b['id']} were drawn over each other"


def test_a_node_a_parser_sent_twice_is_drawn_once_as_its_shallower_copy():
    # Python's parser names a class and a member alike (`qlab.QLab`), and the
    # canvas drew both: the export counted 374 nodes and found 376. Mutation:
    # keep every copy -- the id is sent twice, and this fails.
    async def stream():
        yield _node("dir::root", 0)
        yield _node("file::root/a.py", 1)
        yield _edge("dir::root", "file::root/a.py")
        yield 'event: phase\ndata: {"phase": "symbols"}\n\n'
        yield _node("pkg.Thing", 2)
        yield _edge("file::root/a.py", "pkg.Thing")
        yield _node("pkg.Thing", 3)
        yield _node("pkg.other", 3)
        yield _node("pkg.other", 3)
        yield _edge("pkg.Thing", "pkg.other")
        yield 'event: done\ndata: {"elapsed_ms": 1}\n\n'

    nodes = [e for kind, e in _run(stream(), floor=100) if kind == "node"]
    assert sorted(n["id"] for n in nodes) == ["dir::root", "file::root/a.py", "pkg.Thing", "pkg.other"]
    assert next(n for n in nodes if n["id"] == "pkg.Thing")["depth"] == 2


def test_a_repository_with_less_than_the_floor_at_every_depth_is_drawn_whole():
    events = _run(_repository(files=2, symbols=3, members=4, fetched=[]), floor=100)
    assert len([e for kind, e in events if kind == "node"]) == 10
    assert events[-1][1]["depth"] == 3


def test_a_stream_with_no_phase_event_is_held_to_the_floor_by_its_first_symbol():
    # The local path sends every node sorted by depth, and no phase event.
    # Mutation: count only at a phase event -- the symbols are drawn, and this fails.
    fetched: list[str] = []
    events = _run(_repository(files=150, symbols=20, members=0, fetched=fetched, phase=False), floor=100)
    assert max(e["depth"] for kind, e in events if kind == "node") == 1
    assert events[-1][1]["depth"] == 1


def test_the_show_views_name_the_floor_the_code_view_is_held_to(tmp_path, monkeypatch):
    from codecarto.routers import show_router
    from codecarto.services import show_service

    class Reading:
        ok, org, inventory, source = True, "example", {"alpha"}, "families.json"
    monkeypatch.setattr(show_service, "read", lambda *a, **k: Reading())
    monkeypatch.setattr(show_service, "projects", lambda reading: ["alpha"])
    monkeypatch.setattr(show_router.clones, "find", lambda name: None)
    code = TestClient(app).get("/show/project/alpha/views").json()["results"]["code"]
    assert code["depth"] == 3 and code["floor"] == CODE_FLOOR


def _local_repository(where: Path) -> Path:
    """Two Python files: a class of three methods and two functions, and two more functions."""
    where.mkdir()
    (where / "a.py").write_text(
        "class A:\n    def one(self):\n        pass\n\n    def two(self):\n        pass\n\n"
        "    def three(self):\n        pass\n\n\ndef f():\n    pass\n\n\ndef g():\n    pass\n",
        encoding="utf-8")
    (where / "b.py").write_text("def h():\n    pass\n\n\ndef k():\n    pass\n", encoding="utf-8")
    return where


def _streamed(client: TestClient, url: str, floor: int) -> list[tuple[str, dict]]:
    body = client.post("/parse/stream-url", json={"url": url, "depth": 3, "floor": floor, "layout": "Spring"}).text
    return _events([block + "\n\n" for block in body.split("\n\n") if block.startswith("event: ")])


def test_the_stream_route_holds_a_parse_to_the_floor_it_is_asked_for(tmp_path, monkeypatch):
    # Through the route: a floor its files and symbols reach draws no members;
    # one they do not draws its members too. Mutation: leave the route's
    # stream unheld -- every member is drawn whatever the floor, and this fails.
    import codecarto.services.cache_service as cache_svc
    monkeypatch.setattr(cache_svc, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(cache_svc, "_REPOS_DIR", tmp_path / "cache" / "repos")
    monkeypatch.setattr(cache_svc, "_INDEX_FILE", tmp_path / "cache" / "repos" / "index.json")
    repo = str(_local_repository(tmp_path / "repo"))
    client = TestClient(app)

    whole = _streamed(client, repo, floor=1000)
    depths = [e["depth"] for kind, e in whole if kind == "node"]
    assert 3 in depths, f"the parse drew no members to hold back: {sorted(set(depths))}"
    to_symbols = sum(1 for d in depths if d <= 2)

    held = _streamed(client, repo, floor=to_symbols)
    assert max(e["depth"] for kind, e in held if kind == "node") == 2
    assert held[-1][0] == "done" and held[-1][1]["depth"] == 2
    assert whole[-1][1]["depth"] == 3
