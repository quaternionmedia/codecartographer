"""Any graph on the canvas can be read as a chrestomathy.

The chrestomathy began as a panel that set one chosen construct beside itself
across languages. What makes it foundational is that every graph can be read
that way: whatever a panel or a parse draws says what each of its nodes *is*,
in the same vocabulary, and the census turns the graph into the constructs it
holds and the languages that write them.

So the vocabulary is applied where every graph passes -- the serializer, and
the cache's replay -- and the decision is made in one function, `stamp`, which
the census also calls; the client never decides a construct.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from codecarto.models.plot_data import PlotOptions
from codecarto.services import cargo_service, construct_service
from codecarto.services.graph_serializer import GraphSerializer

VOCABULARY = construct_service.load()
WORKSPACE = Path(__file__).parent / "fixtures" / "cargo" / "workspace"
requires_libclang = pytest.mark.skipif(importlib.util.find_spec("clang") is None,
                                       reason="libclang not installed — install with: uv sync --extra c-parsing")


def nodes_of(gjgf: dict) -> dict[str, dict]:
    return {nid: {**nd, **nd.get("metadata", {})} for nid, nd in gjgf["nodes"].items()}


# ── Where every graph passes ──────────────────────────────────────────────────


def test_the_serializer_stamps_what_reaches_it():
    """A graph no parser stamped -- a producer that never heard of the
    vocabulary -- still reaches the canvas saying what its nodes are.
    Mutation: drop the serializer's `annotate` -- this fails."""
    graph = nx.DiGraph()
    graph.add_node("f", language="rust", kind="function", label="delay")
    graph.add_node("s", language="c", kind="struct", label="config", color="#123456")
    found = nodes_of(GraphSerializer.serialize_to_gjgf(graph, PlotOptions(layout="Spring", type="d3")))
    assert (found["f"]["construct"], found["f"]["construct_name"]) == ("callable.function", "Function")
    assert found["s"]["construct"] == "type.product"
    # A parser's own colour stays; the construct's colour rides beside it.
    assert found["s"]["color"] == "#123456"
    assert found["s"]["construct_color"] == VOCABULARY.get("type.product").look.color


@pytest.mark.asyncio
async def test_a_cached_graph_is_stamped_as_it_is_replayed():
    """A graph cached before a construct existed says what it is on replay.
    Mutation: replay without stamping -- this fails."""
    import json

    from codecarto.routers.unified_parser_router import _stream_cached_graph

    cached = {"graph": {"nodes": {"fn": {"metadata": {"depth": 2, "language": "rust", "kind": "function"}}},
                        "edges": []}}
    nodes = [json.loads(chunk.split("data: ", 1)[1]) async for chunk in _stream_cached_graph(cached, "Spring")
             if chunk.startswith("event: node")]
    assert nodes[0]["construct"] == "callable.function"


def _cache_in(monkeypatch, tmp_path):
    import codecarto.services.cache_service as cache_svc

    repos_dir = tmp_path / "cache" / "repos"
    monkeypatch.setattr(cache_svc, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
    monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")


def _unified_body(url: str) -> dict:
    return {"directory": {"info": {"url": url, "owner": "test", "name": url.rsplit("/", 1)[-1]},
                          "size": 0, "is_partial": False,
                          "root": {"name": "r", "size": 0, "folders": [],
                                   "files": [{"name": "a.py", "size": 19, "raw": "class A:\n    pass\n"}]}},
            "depth": 2, "layout": "Spring"}


def test_a_graph_cached_before_nodes_carried_their_constructs_colour_is_parsed_again(monkeypatch, tmp_path):
    """At 8 a placed node carries `construct_color` and `construct_name`; a
    graph cached at 7 carries neither, and Color By: Construct had nothing
    to paint it with. Mutation: leave GRAPH_SCHEMA_VERSION at 7 -- the graph
    cached at 7 is served."""
    import hashlib

    from codecarto.main import app
    from codecarto.services.cache_service import CacheService

    _cache_in(monkeypatch, tmp_path)
    url = "https://github.com/test/before-construct-colours"
    at_7 = hashlib.sha256(f"v7::{url}::2::Spring::{sorted([])}".encode()).hexdigest()[:16]
    old = {"graph": {"nodes": {"CACHED_AT_7": {"metadata": {"depth": 2, "kind": "class"}}}, "edges": []},
           "metadata": {}}
    CacheService.set(f"test-before-construct-colours::{at_7}", old, label="test/before-construct-colours",
                     url=url, mode="2", layout="Spring")
    results = TestClient(app).post("/parse/unified", json=_unified_body(url)).json()["results"]
    assert not results.get("from_cache")
    assert "CACHED_AT_7" not in results["graph"]["nodes"]
    assert results["graph"]["nodes"]["a.A"]["metadata"]["construct_color"]


def test_a_cached_graph_is_stamped_as_unified_serves_it(monkeypatch, tmp_path):
    """docs/api.md: a cached graph is stamped again -- which the stream's
    replay did and `/parse/unified`'s cache hit did not, returning the
    cached nodes as they were stored. Mutation: return the hit without
    `_stamp_cached` -- the node has no construct."""
    from codecarto.main import app
    from codecarto.services.cache_service import CacheService

    _cache_in(monkeypatch, tmp_path)
    url = "https://github.com/test/stamped-on-a-hit"
    key = CacheService.cache_key(url=url, mode="2", layout="Spring", extensions=[])
    cached = {"graph": {"nodes": {"fn": {"label": "delay",
                                         "metadata": {"depth": 2, "language": "rust", "kind": "function"}}},
                        "edges": []}, "metadata": {}}
    CacheService.set(key, cached, label="test/stamped-on-a-hit", url=url, mode="2", layout="Spring")
    results = TestClient(app).post("/parse/unified", json=_unified_body(url)).json()["results"]
    assert results["from_cache"] is True
    node = results["graph"]["nodes"]["fn"]["metadata"]
    assert (node.get("construct"), node.get("construct_name")) == ("callable.function", "Function")
    assert node["construct_color"] == VOCABULARY.get("callable.function").look.color


def test_the_crate_graph_says_a_crate_is_a_package():
    """The Cargo panel's graph is read as `cargo`, and a crate there is the
    construct a C library and a Python distribution are."""
    from codecarto.main import app

    found = TestClient(app).get("/cargo/gjgf", params={"path": str(WORKSPACE)}).json()["results"]["graph"]
    crates = {nid: nd for nid, nd in nodes_of(found).items() if nd.get("kind") in ("crate", "external_crate")}
    assert crates and all(nd["construct"] == "namespace.package" for nd in crates.values())


def test_every_cargo_kind_the_vocabulary_maps_is_one_the_crate_graph_draws():
    """The `cargo` graph maps the kinds `cargo_service` draws -- a mapping
    for a kind it never emits is a construct nothing could be."""
    graph = cargo_service.as_graph(cargo_service.read(WORKSPACE), features=True, transitive=True)
    drawn = {d.get("kind") for _, d in graph.nodes(data=True)}
    assert set(VOCABULARY.graphs["cargo"].kinds) <= drawn
    assert {d.get("language") for _, d in graph.nodes(data=True)} == {"cargo"}


def test_the_crate_graph_is_placed_and_is_no_row_of_any_chrestomathy():
    """Cargo is a graph a service draws, not a language anything is written
    in: listed under `languages:`, every construct's chrestomathy gained a row
    saying constructs.yaml records no Cargo manifest spelling of it. Under
    `graphs:` its nodes are still stamped and the census places them.
    Mutations: list `cargo` under `languages:` again -- the row check fails;
    drop `graphs` from `Vocabulary.mapping` -- the census places nothing."""
    assert "cargo" not in VOCABULARY.languages
    assert not set(VOCABULARY.languages) & set(VOCABULARY.graphs)
    rows = {(c.id, row["language"]) for c in VOCABULARY.constructs
            for row in construct_service.reading(c.id)["languages"]}
    assert not {r for r in rows if r[1] in VOCABULARY.graphs}, "a graph is a chrestomathy row"

    graph = cargo_service.as_graph(cargo_service.read(WORKSPACE))
    found = construct_service.census(
        [{"id": n, **{k: d.get(k) for k in ("language", "kind")}} for n, d in graph.nodes(data=True)])
    package = next(r for r in found["constructs"] if r["id"] == "namespace.package")
    crates = [n for n, d in graph.nodes(data=True) if d.get("kind") in ("crate", "external_crate")]
    assert sorted(package["ids"]) == sorted(crates)
    assert [l["language"] for l in package["languages"]] == ["cargo"]
    assert found["outside"] == []


@requires_libclang
def test_a_c_local_is_automatic_and_a_static_one_claims_no_linkage(tmp_path):
    """Read from a local repository, as the Repository panel reads one: C's
    locals were stamped as static storage, which they are not, and a static
    local is static storage with no linkage -- `static` inside a body is how
    long it lives, not who can name it. Mutations: drop the C refinement --
    `n` is static storage; drop `no_linkage` from `_block_scope_facts` --
    `calls` claims `linkage.internal`."""
    from codecarto.services.local_repo_service import get_local_repo
    from codecarto.services.unified_parser_service import UnifiedParserService

    (tmp_path / "unit.c").write_text(
        "int shared;\n"
        "static int hidden;\n"
        "int count(void) { static int calls; int n = 0; calls++; return n + hidden; }\n")
    graph = UnifiedParserService.build_graph(get_local_repo(str(tmp_path)), 3, None)
    seen = {d.get("label"): (d.get("construct"), (d.get("meta") or {}).get("facets") or [])
            for _, d in graph.nodes(data=True) if d.get("kind") == "variable"}
    assert seen == {
        "shared": ("storage.static", []),
        "hidden": ("storage.static", ["linkage.internal"]),
        "calls": ("storage.static", []),
        "n": ("storage.automatic", []),
    }


# ── The census ────────────────────────────────────────────────────────────────

MIXED = [
    {"id": "r1", "language": "rust", "kind": "function", "construct": "callable.function"},
    {"id": "r2", "language": "rust", "kind": "function",
     "construct": "callable.function", "meta": {"facets": ["memory.unsafe"]}},
    {"id": "c1", "language": "c", "kind": "function"},              # arrived unstamped
    {"id": "c2", "language": "c", "kind": "struct"},
    {"id": "p1", "language": "python", "kind": "class"},
    {"id": "r3", "language": "rust", "kind": "doc_comment"},        # a kind nothing maps
    {"id": "j1", "language": "javascript", "kind": "function"},     # a language nothing lists
    {"id": "d1", "kind": "directory"},                              # no language at all
]


def test_the_census_reads_a_graph_as_its_constructs_and_their_languages():
    """Mutation: skip stamping an unstamped node -- the C function goes
    uncounted and this fails."""
    found = construct_service.census(MIXED)
    rows = {r["id"]: r for r in found["constructs"]}
    function = rows["callable.function"]
    assert function["count"] == 3 and sorted(function["ids"]) == ["c1", "r1", "r2"]
    assert {(l["language"], l["count"]) for l in function["languages"]} == {("rust", 2), ("c", 1)}
    assert rows["type.product"]["ids"] == ["c2"] and rows["type.class"]["ids"] == ["p1"]
    # In the vocabulary's order, not the order nodes arrived.
    order = [c.id for c in VOCABULARY.constructs]
    assert [r["id"] for r in found["constructs"]] == sorted(rows, key=order.index)
    assert [(f["id"], f["ids"]) for f in found["facets"]] == [("memory.unsafe", ["r2"])]


def test_what_the_census_cannot_place_it_says():
    found = construct_service.census(MIXED)
    assert found["unplaced"] == [{"language": "rust", "display_name": "Rust", "kind": "doc_comment", "count": 1}]
    assert found["outside"] == [{"language": "javascript", "count": 1}]
    assert found["unlabelled"] == 1 and found["nodes"] == len(MIXED)
    assert found["caveat"]


def test_the_census_changes_nothing_it_was_sent():
    sent = [{"id": "c1", "language": "c", "kind": "function", "meta": {}}]
    construct_service.census(sent)
    assert sent == [{"id": "c1", "language": "c", "kind": "function", "meta": {}}]


def test_the_census_route():
    from codecarto.main import app

    resp = TestClient(app).post("/lexicon/chrestomathy/census", json={"nodes": MIXED})
    assert resp.status_code == 200
    assert {r["id"] for r in resp.json()["results"]["constructs"]} >= {"callable.function", "type.product"}
