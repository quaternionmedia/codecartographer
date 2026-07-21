"""
Tests for UnifiedParserService.

Covers:
  - Directory/file skeleton is always emitted (depth 0 + 1 nodes)
  - Depth control: depth=0 → dirs only, depth=1 → dirs+files, depth=2 → +symbols
  - Extension filtering: only allowed extensions appear as file nodes
  - All nodes carry the unified schema (depth, language, kind, label)
  - expand_node: sub-graph rooted at a file node
  - expand_node with unknown node_id → empty result
  - Output is a valid gJGF dict (graph/metadata keys present)
  - Multiple files in same folder all appear
  - Nested folders produce correctly linked nodes
"""

import json

import pytest
import networkx as nx

from codecarto.models.source_data import Directory, File, Folder, RepoInfo
from codecarto.services.unified_parser_service import UnifiedParserService


# ── Factories ─────────────────────────────────────────────────────────────────

def _info(name: str = "myrepo") -> RepoInfo:
    return RepoInfo(owner="test", name=name, url="")


def _file(name: str, raw: str = "") -> File:
    return File(name=name, size=len(raw), raw=raw)


def _dir(root: Folder, name: str = "myrepo") -> Directory:
    return Directory(info=_info(name), size=0, root=root)


def _simple_dir(files: list[File], name: str = "myrepo") -> Directory:
    """Directory with a single flat root folder."""
    root = Folder(name=name, size=len(files), files=files, folders=[])
    return _dir(root, name)


# ── Depth=0: directories only ─────────────────────────────────────────────────

class TestDepthZero:
    def test_dir_node_present(self):
        d = _simple_dir([_file("main.py", "def f(): pass")])
        result = UnifiedParserService.parse(d, depth=0)

        # gJGF shape
        assert "graph" in result
        assert "metadata" in result

        nodes = result["graph"]["nodes"]
        assert any("dir::" in nid for nid in nodes)

    def test_no_file_nodes_at_depth0(self):
        d = _simple_dir([_file("main.py", "class A: pass")])
        result = UnifiedParserService.parse(d, depth=0)

        nodes = result["graph"]["nodes"]
        assert not any(nid.startswith("file::") for nid in nodes)

    def test_no_symbol_nodes_at_depth0(self):
        d = _simple_dir([_file("main.py", "class A: pass")])
        result = UnifiedParserService.parse(d, depth=0)

        # No depth-2 nodes (classes/functions)
        for nid, node_data in result["graph"]["nodes"].items():
            meta = node_data.get("metadata", {})
            assert meta.get("depth", 0) == 0, f"unexpected node at depth>0: {nid}"


# ── Depth=1: directories + files ──────────────────────────────────────────────

class TestDepthOne:
    def test_file_nodes_present(self):
        d = _simple_dir([_file("utils.py", "x=1")])
        result = UnifiedParserService.parse(d, depth=1)

        nodes = result["graph"]["nodes"]
        assert any(nid.startswith("file::") for nid in nodes)

    def test_no_symbol_nodes_at_depth1(self):
        d = _simple_dir([_file("utils.py", "class Foo: pass")])
        result = UnifiedParserService.parse(d, depth=1)

        for nid, node_data in result["graph"]["nodes"].items():
            meta = node_data.get("metadata", {})
            assert meta.get("depth", 0) <= 1, f"symbol leaked at depth=1: {nid}"

    def test_file_node_kind(self):
        d = _simple_dir([_file("app.py", "")])
        result = UnifiedParserService.parse(d, depth=1)

        nodes = result["graph"]["nodes"]
        file_nodes = {nid: nd for nid, nd in nodes.items() if nid.startswith("file::")}
        assert file_nodes, "expected at least one file node"
        for nid, nd in file_nodes.items():
            assert nd["metadata"]["kind"] == "file", f"wrong kind on {nid}"


# ── Depth=2: directories + files + symbols ────────────────────────────────────

class TestDepthTwo:
    def test_class_and_function_appear(self):
        code = "class MyClass:\n    def my_method(self): pass\n"
        d = _simple_dir([_file("mod.py", code)])
        result = UnifiedParserService.parse(d, depth=2)

        nodes = result["graph"]["nodes"]
        kinds = {nd["metadata"]["kind"] for nd in nodes.values()}
        assert "class" in kinds
        assert "function" in kinds

    def test_all_nodes_have_unified_schema_fields(self):
        code = "def standalone(): pass\n"
        d = _simple_dir([_file("x.py", code)])
        result = UnifiedParserService.parse(d, depth=2)

        # gravis promotes 'label' to the node top-level in gJGF;
        # the remaining unified schema fields live inside 'metadata'.
        required_in_meta = {"depth", "kind", "language"}
        for nid, nd in result["graph"]["nodes"].items():
            meta = nd.get("metadata", {})
            missing = required_in_meta - meta.keys()
            assert not missing, f"node {nid!r} missing schema fields: {missing}"
            # label is either in metadata OR promoted to the node top-level
            has_label = "label" in meta or "label" in nd
            assert has_label, f"node {nid!r} has no label anywhere in gJGF node"

    def test_depth2_nodes_language_is_python(self):
        code = "class Z: pass\n"
        d = _simple_dir([_file("z.py", code)])
        result = UnifiedParserService.parse(d, depth=2)

        for nid, nd in result["graph"]["nodes"].items():
            meta = nd["metadata"]
            if meta.get("depth", -1) == 2:
                assert meta["language"] == "python", (
                    f"depth-2 node {nid!r} has language={meta['language']!r}"
                )

    def test_edges_connect_dir_to_file_to_symbols(self):
        code = "class A: pass\n"
        d = _simple_dir([_file("a.py", code)])
        result = UnifiedParserService.parse(d, depth=2)

        edges = result["graph"]["edges"]
        # At least a dir→file edge and a file→symbol edge must exist
        assert len(edges) >= 2, "expected at least 2 edges"


# ── Extension filtering ───────────────────────────────────────────────────────

class TestExtensionFilter:
    def test_only_py_files_when_extension_filtered(self):
        files = [
            _file("main.py", "def f(): pass"),
            _file("readme.md", "# Hello"),
        ]
        d = _simple_dir(files)
        result = UnifiedParserService.parse(d, depth=1, extensions=[".py"])

        nodes = result["graph"]["nodes"]
        file_nodes = [nid for nid in nodes if nid.startswith("file::")]
        # Only the .py file should appear
        assert all(".py" in nid for nid in file_nodes), (
            f"non-py file node slipped through: {file_nodes}"
        )

    def test_unknown_extension_produces_no_file_nodes(self):
        files = [_file("data.csv", "a,b,c")]
        d = _simple_dir(files)
        result = UnifiedParserService.parse(d, depth=1)

        nodes = result["graph"]["nodes"]
        file_nodes = [nid for nid in nodes if nid.startswith("file::")]
        # .csv is not a registered extension → should be filtered
        assert len(file_nodes) == 0


# ── Multiple files ────────────────────────────────────────────────────────────

class TestMultipleFiles:
    def test_all_files_appear(self):
        files = [
            _file("a.py", "class A: pass"),
            _file("b.py", "class B: pass"),
        ]
        d = _simple_dir(files)
        result = UnifiedParserService.parse(d, depth=2)

        nodes = result["graph"]["nodes"]
        # gravis may promote 'label' to node top-level or keep it in metadata
        def _label(nd: dict) -> str:
            return nd.get("label") or nd.get("metadata", {}).get("label", "")

        labels = {_label(nd) for nd in nodes.values()}
        assert "A" in labels
        assert "B" in labels


# ── Nested folders ────────────────────────────────────────────────────────────

class TestNestedFolders:
    def test_subfolder_dir_node_created(self):
        sub = Folder(
            name="pkg",
            size=0,
            files=[_file("helpers.py", "def h(): pass")],
            folders=[],
        )
        root = Folder(name="myrepo", size=0, files=[], folders=[sub])
        d = _dir(root)
        result = UnifiedParserService.parse(d, depth=1)

        nodes = result["graph"]["nodes"]
        dir_ids = [nid for nid in nodes if nid.startswith("dir::")]
        assert any("pkg" in nid for nid in dir_ids), (
            f"subfolder dir node not found in {dir_ids}"
        )

    def test_subfolder_file_appears(self):
        sub = Folder(
            name="pkg",
            size=0,
            files=[_file("helpers.py", "def h(): pass")],
            folders=[],
        )
        root = Folder(name="myrepo", size=0, files=[], folders=[sub])
        d = _dir(root)
        result = UnifiedParserService.parse(d, depth=1)

        nodes = result["graph"]["nodes"]
        file_ids = [nid for nid in nodes if nid.startswith("file::")]
        assert any("helpers.py" in nid for nid in file_ids)


# ── expand_node ───────────────────────────────────────────────────────────────

class TestExpandNode:
    def _make_dir(self) -> Directory:
        files = [
            _file("mod.py", "class Foo:\n    def bar(self): pass\n"),
        ]
        return _simple_dir(files)

    def test_expand_node_returns_subgraph(self):
        d = self._make_dir()

        # First, do a depth-1 parse to learn the file node id
        depth1 = UnifiedParserService.parse(d, depth=1)
        file_nodes = [
            nid for nid in depth1["graph"]["nodes"] if nid.startswith("file::")
        ]
        assert file_nodes, "need at least one file node"
        file_nid = file_nodes[0]

        # Now expand that file node to depth=2
        result = UnifiedParserService.expand_node(d, node_id=file_nid, depth=2)

        assert "graph" in result
        assert "metadata" in result
        nodes = result["graph"]["nodes"]
        assert len(nodes) > 0, "expand_node returned empty sub-graph"

    def test_expand_node_includes_symbols(self):
        d = self._make_dir()
        depth1 = UnifiedParserService.parse(d, depth=1)
        file_nid = next(
            nid for nid in depth1["graph"]["nodes"] if nid.startswith("file::")
        )

        result = UnifiedParserService.expand_node(d, node_id=file_nid, depth=2)
        nodes = result["graph"]["nodes"]
        kinds = {nd["metadata"]["kind"] for nd in nodes.values()}
        # The sub-graph should include the file node itself and at least one symbol
        assert "class" in kinds or "function" in kinds, (
            f"no symbol kinds found after expand; got kinds={kinds}"
        )

    def test_expand_node_unknown_id_returns_empty(self):
        d = self._make_dir()
        result = UnifiedParserService.expand_node(
            d, node_id="file::does_not_exist.py", depth=2
        )
        assert result["graph"] == {}
        assert result["metadata"]["nodeCount"] == 0


# ── gJGF output shape ─────────────────────────────────────────────────────────

class TestGjgfOutputShape:
    def test_graph_key_present(self):
        d = _simple_dir([_file("x.py", "x=1")])
        result = UnifiedParserService.parse(d, depth=1)
        assert "graph" in result

    def test_metadata_key_present(self):
        d = _simple_dir([_file("x.py", "x=1")])
        result = UnifiedParserService.parse(d, depth=1)
        assert "metadata" in result

    def test_metadata_has_node_count(self):
        d = _simple_dir([_file("x.py", "x=1")])
        result = UnifiedParserService.parse(d, depth=1)
        meta = result["metadata"]
        assert "nodeCount" in meta
        assert meta["nodeCount"] >= 1  # at least the dir node

    def test_graph_has_nodes_and_edges_keys(self):
        d = _simple_dir([_file("x.py", "x=1")])
        result = UnifiedParserService.parse(d, depth=1)
        graph = result["graph"]
        assert "nodes" in graph
        assert "edges" in graph


# ── depth parameter ───────────────────────────────────────────────────────────

class TestDepthParameter:
    """Tests for the depth parameter controlling graph detail level.

    depth=1 → directory + file nodes only (no symbols)
    depth=2 → full combined graph: dirs, files, symbols, and dependencies

    The UI always uses depth=2 to produce the unified graph; depth=1 is
    available for lightweight structure-only views.
    """

    def test_depth1_produces_no_symbols(self):
        """depth=1 should produce no symbol nodes, even for a .py file with real content."""
        code = "class Foo:\n    def bar(self): pass\n"
        d = _simple_dir([_file("foo.py", code)])
        result = UnifiedParserService.parse(d, depth=1)

        for nid, nd in result["graph"]["nodes"].items():
            meta = nd.get("metadata", {})
            assert meta.get("depth", 0) <= 1, (
                f"depth-2+ node {nid!r} appeared in depth=1 parse"
            )

    def test_depth2_produces_symbols(self):
        """depth=2 (unified graph) should produce symbol nodes for a .py file."""
        code = "class Foo:\n    def bar(self): pass\n"
        d = _simple_dir([_file("foo.py", code)])
        result = UnifiedParserService.parse(d, depth=2)

        depth2_nodes = [
            nid for nid, nd in result["graph"]["nodes"].items()
            if nd.get("metadata", {}).get("depth", 0) == 2
        ]
        assert len(depth2_nodes) > 0, "depth=2 produced no symbol nodes"

    def test_depth_controls_symbol_presence(self):
        """depth=1 → no symbol nodes; depth=2 → symbol nodes."""
        code = "def standalone(): pass\n"
        d = _simple_dir([_file("x.py", code)])

        result_d1 = UnifiedParserService.parse(d, depth=1)
        result_d2 = UnifiedParserService.parse(d, depth=2)

        has_symbols_d1 = any(
            nd.get("metadata", {}).get("depth", 0) >= 2
            for nd in result_d1["graph"]["nodes"].values()
        )
        has_symbols_d2 = any(
            nd.get("metadata", {}).get("depth", 0) >= 2
            for nd in result_d2["graph"]["nodes"].values()
        )

        assert not has_symbols_d1, "depth=1 should produce no symbols"
        assert has_symbols_d2,     "depth=2 should produce symbols"


# ── Partial/shallow directory (empty raw) ─────────────────────────────────────

class TestPartialDirectory:
    """Graceful handling of files with raw='' (shallow / large repo mode)."""

    def test_shallow_dir_directory_mode(self):
        """.c and .py files with raw='' at depth=1 both appear as file nodes."""
        files = [
            _file("main.c", ""),
            _file("util.py", ""),
        ]
        d = _simple_dir(files)
        result = UnifiedParserService.parse(d, depth=1)

        file_nodes = [nid for nid in result["graph"]["nodes"] if nid.startswith("file::")]
        names = [nid.split("/")[-1] for nid in file_nodes]
        assert "main.c" in names,  "main.c should appear as a file node at depth=1"
        assert "util.py" in names, "util.py should appear as a file node at depth=1"

    def test_shallow_dir_ast_graceful(self):
        """raw='' at depth=2 → file nodes present, zero symbol nodes (no crash)."""
        files = [
            _file("app.py", ""),
            _file("core.c", ""),
        ]
        d = _simple_dir(files)
        result = UnifiedParserService.parse(d, depth=2)

        nodes = result["graph"]["nodes"]
        assert nodes, "should have at least some nodes"

        depth2_nodes = [
            nid for nid, nd in nodes.items()
            if nd.get("metadata", {}).get("depth", 0) >= 2
        ]
        assert len(depth2_nodes) == 0, (
            f"empty-raw files produced symbol nodes: {depth2_nodes}"
        )

    def test_c_extension_included(self):
        """.c files at depth=1 produce a file:: node (not filtered out)."""
        d = _simple_dir([_file("parser.c", "")])
        result = UnifiedParserService.parse(d, depth=1)

        file_nodes = [nid for nid in result["graph"]["nodes"] if nid.startswith("file::")]
        assert any("parser.c" in nid for nid in file_nodes), (
            f".c file not found in file nodes: {file_nodes}"
        )


# ── Python dependency edges (depends_on) ──────────────────────────────────────
# unified-pipeline counterpart to the old standalone DependencyParser: at
# depth>=2, Python imports are resolved to real file-to-file 'depends_on'
# edges (internal) or a synthetic 'external_module' node (stdlib/third-party).

class TestPythonDependencyEdges:
    def _edge_kind(self, e: dict) -> str:
        return e.get("metadata", e).get("kind")

    def test_internal_import_creates_depends_on_edge(self):
        a = _file("a.py", "import b\n")
        b = _file("b.py", "x = 1\n")
        d = _simple_dir([a, b])
        result = UnifiedParserService.parse(d, depth=2)

        edges = result["graph"]["edges"]
        depends_on = [e for e in edges if self._edge_kind(e) == "depends_on"]
        assert any(
            "a.py" in e["source"] and "b.py" in e["target"] for e in depends_on
        ), f"expected a.py -> b.py depends_on edge, got: {depends_on}"

    def test_from_import_creates_depends_on_edge(self):
        a = _file("a.py", "from b import x\n")
        b = _file("b.py", "x = 1\n")
        d = _simple_dir([a, b])
        result = UnifiedParserService.parse(d, depth=2)

        edges = result["graph"]["edges"]
        depends_on = [e for e in edges if self._edge_kind(e) == "depends_on"]
        assert any(
            "a.py" in e["source"] and "b.py" in e["target"] for e in depends_on
        )

    def test_stdlib_import_creates_external_node(self):
        a = _file("a.py", "import os\n")
        d = _simple_dir([a])
        result = UnifiedParserService.parse(d, depth=2)

        nodes = result["graph"]["nodes"]
        assert "external::os" in nodes, f"expected external::os node, got: {list(nodes)}"

        edges = result["graph"]["edges"]
        depends_on = [e for e in edges if self._edge_kind(e) == "depends_on"]
        assert any(
            "a.py" in e["source"] and e["target"] == "external::os" for e in depends_on
        )

    def test_submodule_import_groups_under_top_level_external_node(self):
        a = _file("a.py", "import os.path\n")
        d = _simple_dir([a])
        result = UnifiedParserService.parse(d, depth=2)

        nodes = result["graph"]["nodes"]
        assert "external::os" in nodes
        assert "external::os.path" not in nodes

    def test_no_self_loop_for_self_import(self):
        """A file that imports a stdlib module sharing no name collisions
        with itself should never get a depends_on edge to itself."""
        a = _file("a.py", "import a\n")  # pathological but shouldn't crash/self-loop
        d = _simple_dir([a])
        result = UnifiedParserService.parse(d, depth=2)

        edges = result["graph"]["edges"]
        depends_on = [e for e in edges if self._edge_kind(e) == "depends_on"]
        assert not any(e["source"] == e["target"] for e in depends_on)

    def test_no_depends_on_edges_at_depth1(self):
        a = _file("a.py", "import b\n")
        b = _file("b.py", "x = 1\n")
        d = _simple_dir([a, b])
        result = UnifiedParserService.parse(d, depth=1)

        edges = result["graph"]["edges"]
        assert not any(self._edge_kind(e) == "depends_on" for e in edges)

    def test_unrelated_files_get_no_depends_on_edge(self):
        a = _file("a.py", "x = 1\n")
        b = _file("b.py", "y = 2\n")
        d = _simple_dir([a, b])
        result = UnifiedParserService.parse(d, depth=2)

        edges = result["graph"]["edges"]
        assert not any(self._edge_kind(e) == "depends_on" for e in edges)


# ── Python dependency edges via stream_parse_url (GitHub-streaming path) ──────
# Extends the same _resolve_python_dependencies resolution used by
# _add_python_dependency_edges to the two-phase GitHub-streaming pipeline.
# Dependency edges can't be resolved per-file (an earlier-completing file's
# import target might not have arrived yet), so they're emitted as a final
# batch of edge/node SSE events after every file has been fetched+parsed —
# the same deferred-until-complete approach C's cross-file 'calls' edges
# already use in the batch_whole_tree path.

def _parse_sse_chunk(chunk: str) -> tuple[str, dict]:
    lines = chunk.strip().split("\n")
    event_type = lines[0].split("event: ", 1)[1]
    data_line = next(l for l in lines if l.startswith("data: "))
    return event_type, json.loads(data_line[len("data: "):])


class TestStreamParseUrlDependencyEdges:
    @staticmethod
    def _patch_github_fetch(monkeypatch, items, contents: dict[str, str]):
        import codecarto.services.github_service as gh_svc

        async def fake_fetch_tree_fast(owner, repo, headers, url):
            return items, "main", 1, False

        async def fake_get_raw_from_url(dl_url):
            return contents[dl_url]

        monkeypatch.setattr(gh_svc, "fetch_tree_fast", fake_fetch_tree_fast)
        monkeypatch.setattr(gh_svc, "get_raw_from_url", fake_get_raw_from_url)

    async def _collect_events(self, url: str, depth: int = 2) -> list[tuple[str, dict]]:
        events = []
        async for chunk in UnifiedParserService.stream_parse_url(url, depth=depth):
            events.append(_parse_sse_chunk(chunk))
        return events

    @pytest.mark.asyncio
    async def test_internal_import_creates_depends_on_edge(self, monkeypatch):
        items = [
            ("a.py", "blob", "https://raw.example/streamdeps/a.py"),
            ("b.py", "blob", "https://raw.example/streamdeps/b.py"),
        ]
        contents = {
            "https://raw.example/streamdeps/a.py": "import b\n",
            "https://raw.example/streamdeps/b.py": "x = 1\n",
        }
        self._patch_github_fetch(monkeypatch, items, contents)

        events = await self._collect_events("https://github.com/test/streamdeps-internal")

        depends_on = [d for t, d in events if t == "edge" and d.get("kind") == "depends_on"]
        assert any(
            "a.py" in e["source"] and "b.py" in e["target"] for e in depends_on
        ), f"expected a.py -> b.py depends_on edge, got: {depends_on}"

    @pytest.mark.asyncio
    async def test_stdlib_import_creates_external_node_and_edge(self, monkeypatch):
        items = [("a.py", "blob", "https://raw.example/streamdeps/a.py")]
        contents = {"https://raw.example/streamdeps/a.py": "import os\n"}
        self._patch_github_fetch(monkeypatch, items, contents)

        events = await self._collect_events("https://github.com/test/streamdeps-external")

        node_ids = {d.get("id") for t, d in events if t == "node"}
        assert "external::os" in node_ids

        depends_on = [d for t, d in events if t == "edge" and d.get("kind") == "depends_on"]
        assert any(
            "a.py" in e["source"] and e["target"] == "external::os" for e in depends_on
        )

    @pytest.mark.asyncio
    async def test_no_duplicate_edge_for_repeated_import(self, monkeypatch):
        """A file importing the same module via two statements (or two
        submodules of the same package) must not produce duplicate
        depends_on edges — SSE events have no has_edge() backing store to
        dedupe against, unlike the in-memory path."""
        items = [("a.py", "blob", "https://raw.example/streamdeps/a.py")]
        contents = {"https://raw.example/streamdeps/a.py": "import os\nimport os.path\n"}
        self._patch_github_fetch(monkeypatch, items, contents)

        events = await self._collect_events("https://github.com/test/streamdeps-dedup")

        depends_on = [d for t, d in events if t == "edge" and d.get("kind") == "depends_on"]
        external_edges = [e for e in depends_on if e["target"] == "external::os"]
        assert len(external_edges) == 1, f"expected exactly one deduped edge, got: {external_edges}"

        node_events = [d for t, d in events if t == "node" and d.get("id") == "external::os"]
        assert len(node_events) == 1, "external node should only be emitted once"

    @pytest.mark.asyncio
    async def test_no_depends_on_edges_at_depth1(self, monkeypatch):
        items = [
            ("a.py", "blob", "https://raw.example/streamdeps/a.py"),
            ("b.py", "blob", "https://raw.example/streamdeps/b.py"),
        ]
        contents = {
            "https://raw.example/streamdeps/a.py": "import b\n",
            "https://raw.example/streamdeps/b.py": "x = 1\n",
        }
        self._patch_github_fetch(monkeypatch, items, contents)

        events = await self._collect_events("https://github.com/test/streamdeps-depth1", depth=1)

        assert not any(t == "edge" and d.get("kind") == "depends_on" for t, d in events)


# ── _split_by_batch_mode: pure grouping helper, shared by both dispatch sites ──
# Extracted so the GitHub-streaming path (stream_parse_url) and the
# local-directory path (_walk_folder) don't each reimplement "group by
# whether this item's parser wants batch_whole_tree" independently. Tested
# directly here since it's pure (no I/O, no closures) — the end-to-end
# behavior it enables is covered separately by TestCBatchWholeTree below.

class TestSplitByBatchMode:
    def _ext_of_name(self, item: str) -> str:
        return "." + item.rsplit(".", 1)[-1].lower()

    def test_python_files_go_to_per_item(self):
        import codecarto.services.parsers.python_language_parser  # noqa: F401 (registers .py)
        from codecarto.services.unified_parser_service import _split_by_batch_mode

        per_item, batched = _split_by_batch_mode(["a.py", "b.py"], self._ext_of_name)

        assert batched == {}
        assert {item for item, _ in per_item} == {"a.py", "b.py"}

    def test_c_files_go_to_batched_grouped_by_parser_identity(self):
        # No libclang needed here — CLangaugeParser registers itself with
        # ParserRegistry at import time regardless of whether libclang is
        # installed; only parse_files() itself lazily needs it.
        import codecarto.services.parsers.c_language_parser as clp
        from codecarto.services.unified_parser_service import _split_by_batch_mode

        per_item, batched = _split_by_batch_mode(["a.c", "b.h"], self._ext_of_name)

        assert per_item == []
        assert len(batched) == 1
        parser, items = next(iter(batched.values()))
        assert isinstance(parser, clp.CLangaugeParser)
        assert set(items) == {"a.c", "b.h"}

    def test_unregistered_extension_is_dropped(self):
        from codecarto.services.unified_parser_service import _split_by_batch_mode

        per_item, batched = _split_by_batch_mode(["data.csv"], self._ext_of_name)

        assert per_item == []
        assert batched == {}

    def test_mixed_extensions_split_correctly(self):
        import codecarto.services.parsers.python_language_parser  # noqa: F401
        import codecarto.services.parsers.c_language_parser  # noqa: F401
        from codecarto.services.unified_parser_service import _split_by_batch_mode

        per_item, batched = _split_by_batch_mode(
            ["a.py", "b.c", "c.py", "d.h"], self._ext_of_name
        )

        assert {item for item, _ in per_item} == {"a.py", "c.py"}
        assert len(batched) == 1
        _, items = next(iter(batched.values()))
        assert set(items) == {"b.c", "d.h"}

    def test_same_parser_instance_across_calls_groups_together(self):
        """.c and .h are different extensions but the SAME CLangaugeParser
        instance — must land in one batch group, not two (matches the
        existing batch_whole_tree id(parser)-keying convention)."""
        import codecarto.services.parsers.c_language_parser  # noqa: F401
        from codecarto.services.unified_parser_service import _split_by_batch_mode

        _, batched = _split_by_batch_mode(["x.c", "y.h", "z.c"], self._ext_of_name)

        assert len(batched) == 1


# ── batch_whole_tree: C files parsed together, not one-at-a-time ──────────────
# Before this, _walk_folder dispatched parser.parse_files([file], depth) one
# file at a time for every language. Fine for Python; structurally wrong for
# C, whose CALLS edges need the whole file set in one CParser call to
# resolve cross-file references. CLangaugeParser.batch_whole_tree=True opts
# into a second pass (_parse_pending_batches) that collects every C/H file
# across the WHOLE tree (not just one folder) before parsing.

import importlib.util
requires_libclang = pytest.mark.skipif(
    importlib.util.find_spec("clang") is None,
    reason="libclang not installed — install with: uv sync --extra c-parsing",
)


@requires_libclang
class TestCBatchWholeTree:
    def _c_file(self, name: str, raw: str) -> File:
        return File(name=name, size=len(raw), raw=raw, url="")

    def test_cross_file_calls_resolve_through_full_parse(self):
        import codecarto.services.parsers.c_language_parser  # noqa: F401  (registers .c/.h)

        header = self._c_file("helper.h", "int helper_fn(int x);")
        main_c = self._c_file("main.c", '#include "helper.h"\nint main(void) { return helper_fn(5); }')
        helper_c = self._c_file("helper.c", '#include "helper.h"\nint helper_fn(int x) { return x * 2; }')

        d = _simple_dir([header, main_c, helper_c])
        result = UnifiedParserService.parse(d, depth=2)

        edges = result["graph"]["edges"]
        call_edges = [
            e for e in edges
            if e.get("metadata", e).get("kind") == "calls"
        ]
        assert any(
            "main" in e["source"] and "helper_fn" in e["target"]
            for e in call_edges
        ), f"expected a cross-file calls edge main -> helper_fn, got: {call_edges}"

    def test_files_split_across_subfolders_still_batch_together(self):
        """The whole point of batch_whole_tree: files in DIFFERENT folders
        must still land in the same CParser call (same-folder batching
        alone would not resolve this cross-folder call)."""
        import codecarto.services.parsers.c_language_parser  # noqa: F401

        header = self._c_file("helper.h", "int helper_fn(int x);")
        helper_sub = Folder(name="lib", size=0, files=[header], folders=[])
        main_c = self._c_file("main.c", '#include "helper.h"\nint main(void) { return helper_fn(5); }')
        helper_c = self._c_file("helper.c", '#include "helper.h"\nint helper_fn(int x) { return x * 2; }')
        root = Folder(name="repo", size=0, files=[main_c, helper_c], folders=[helper_sub])
        d = _dir(root, "repo")

        result = UnifiedParserService.parse(d, depth=2)

        call_edges = [
            e for e in result["graph"]["edges"]
            if e.get("metadata", e).get("kind") == "calls"
        ]
        assert call_edges, "cross-folder cross-file call did not resolve"

    def test_c_and_h_extensions_batch_into_one_call_not_two(self):
        """.c and .h are different extensions but the SAME parser instance —
        regression test for a bug where pending was keyed by extension,
        splitting a .h declaration and its .c definition into separate
        CParser calls and breaking #include resolution between them."""
        import codecarto.services.parsers.c_language_parser as clp

        calls: list[list[str]] = []
        orig = clp.CLangaugeParser.parse_files

        def traced(self, files, depth=2):
            calls.append([f.name for f in files])
            return orig(self, files, depth)

        clp.CLangaugeParser.parse_files = traced
        try:
            header = self._c_file("helper.h", "int helper_fn(int x);")
            main_c = self._c_file("main.c", '#include "helper.h"\nint main(void) { return helper_fn(5); }')
            d = _simple_dir([header, main_c])

            UnifiedParserService.parse(d, depth=2)
        finally:
            clp.CLangaugeParser.parse_files = orig

        assert len(calls) == 1, f"expected one batched call, got {len(calls)}: {calls}"
        assert set(calls[0]) == {"helper.h", "main.c"}

    def test_depth2_node_gets_contains_edge_from_correct_file(self):
        import codecarto.services.parsers.c_language_parser  # noqa: F401

        a_c = self._c_file("a.c", "int fn_a(void) { return 1; }")
        b_c = self._c_file("b.c", "int fn_b(void) { return 2; }")
        d = _simple_dir([a_c, b_c])

        result = UnifiedParserService.parse(d, depth=2)
        edges = result["graph"]["edges"]

        def contains_target(source_substr, target_substr):
            return any(
                source_substr in e["source"] and target_substr in e["target"]
                for e in edges
            )

        assert contains_target("a.c", "fn_a")
        assert contains_target("b.c", "fn_b")
        assert not contains_target("a.c", "fn_b")
        assert not contains_target("b.c", "fn_a")

    def test_python_files_unaffected_by_batching(self):
        """Python has no batch_whole_tree flag — must still dispatch one
        file at a time, unchanged."""
        f1 = _file("a.py", "class A: pass\n")
        f2 = _file("b.py", "class B: pass\n")
        d = _simple_dir([f1, f2])

        result = UnifiedParserService.parse(d, depth=2)

        labels = {nd["label"] for nd in result["graph"]["nodes"].values()}
        assert "A" in labels
        assert "B" in labels


# ── Lexicon annotation (Option B) ──────────────────────────────────────────
# annotate_lexicon=True stamps layer_ordinal/meta['lexicon_layers'] onto
# nodes whose kind or (for C) qualifiers match a keyword/operator in that
# language's Lexicon. See codecarto/services/lexicon_bridge.py's module
# docstring for why this isn't a kind.lower() heuristic - Python's own
# "Function" node kind maps to unified kind "function", not the keyword
# "def", proving casing alone isn't reliable even within one language.

class TestLexiconAnnotation:
    def test_default_is_unannotated(self):
        """annotate_lexicon defaults to False - existing callers see no
        behavior change."""
        d = _simple_dir([_file("mod.py", "class A: pass\n")])
        result = UnifiedParserService.parse(d, depth=2)
        for nd in result["graph"]["nodes"].values():
            assert "layer_ordinal" not in nd.get("metadata", {})

    def test_python_class_gets_structure_layer(self):
        code = "class Greeter:\n    def hello(self):\n        pass\n"
        d = _simple_dir([_file("greet.py", code)])
        graph = UnifiedParserService.build_graph(
            d, depth=2, extensions=None, annotate_lexicon=True
        )

        class_nodes = [
            (n, data) for n, data in graph.nodes(data=True)
            if data.get("kind") == "class"
        ]
        assert class_nodes, "expected a class node"
        for _, data in class_nodes:
            assert data["layer_ordinal"] == 1  # Structure & definition
            assert data["meta"]["lexicon_layers"][0]["group"] == "definition"

    def test_python_function_maps_to_def_keyword_not_the_word_function(self):
        """Regression guard for the exact bug this design was built to
        avoid: 'function'.lower() is not a real Python keyword, 'def' is -
        the kind->token map must translate explicitly, not assume casing."""
        code = "def standalone(): pass\n"
        d = _simple_dir([_file("x.py", code)])
        graph = UnifiedParserService.build_graph(
            d, depth=2, extensions=None, annotate_lexicon=True
        )

        func_nodes = [
            data for _, data in graph.nodes(data=True)
            if data.get("kind") == "function"
        ]
        assert func_nodes
        for data in func_nodes:
            assert data["layer_ordinal"] == 1
            tokens = {m.get("group") for m in data["meta"]["lexicon_layers"]}
            assert "definition" in tokens  # reached via the "def" mapping

    def test_non_matching_python_nodes_are_left_untouched(self):
        """Module/Call/Name/Constant nodes have no lexicon-token equivalent
        - they must not gain a layer_ordinal key at all (absent, not null),
        matching how shape/color are absent rather than null when unset."""
        code = "def f():\n    print('hi')\n"
        d = _simple_dir([_file("x.py", code)])
        graph = UnifiedParserService.build_graph(
            d, depth=3, extensions=None, annotate_lexicon=True
        )

        non_keyword_kinds = {"module", "call", "name", "constant", "argument"}
        for _, data in graph.nodes(data=True):
            if data.get("kind") in non_keyword_kinds:
                assert "layer_ordinal" not in data, (
                    f"{data.get('kind')} node unexpectedly annotated: {data}"
                )

    @requires_libclang
    def test_c_struct_gets_aggregate_layer(self):
        import codecarto.services.parsers.c_language_parser  # noqa: F401

        code = "struct Point { int x; int y; };\n"
        d = _simple_dir([File(name="shapes.c", size=len(code), raw=code, url="")])
        graph = UnifiedParserService.build_graph(
            d, depth=3, extensions=None, annotate_lexicon=True
        )

        struct_nodes = [
            data for _, data in graph.nodes(data=True)
            if data.get("kind") == "struct"
        ]
        assert struct_nodes
        for data in struct_nodes:
            assert data["layer_ordinal"] == 2  # Aggregate & user-defined types
            groups = {m["group"] for m in data["meta"]["lexicon_layers"]}
            assert "aggregate" in groups

    @requires_libclang
    def test_c_qualifier_reaches_a_different_layer_than_kind_would(self):
        """static is Layer 0 (Storage & memory placement); the function
        kind itself has no direct keyword match - this only works because
        meta['qualifiers'] is checked independently of kind."""
        import codecarto.services.parsers.c_language_parser  # noqa: F401

        code = "static int add(int a, int b) { return a + b; }\n"
        d = _simple_dir([File(name="math.c", size=len(code), raw=code, url="")])
        graph = UnifiedParserService.build_graph(
            d, depth=3, extensions=None, annotate_lexicon=True
        )

        fn_nodes = [
            data for _, data in graph.nodes(data=True)
            if data.get("kind") == "function"
        ]
        assert fn_nodes
        for data in fn_nodes:
            assert data["layer_ordinal"] == 0  # Storage & memory placement
            groups = {m["group"] for m in data["meta"]["lexicon_layers"]}
            assert "storage class" in groups

    @requires_libclang
    def test_c_fields_unmatched_by_kind_or_qualifiers_are_untouched(self):
        import codecarto.services.parsers.c_language_parser  # noqa: F401

        code = "struct Point { int x; };\n"
        d = _simple_dir([File(name="shapes.c", size=len(code), raw=code, url="")])
        graph = UnifiedParserService.build_graph(
            d, depth=3, extensions=None, annotate_lexicon=True
        )

        field_nodes = [
            data for _, data in graph.nodes(data=True)
            if data.get("kind") == "field"
        ]
        assert field_nodes
        for data in field_nodes:
            assert "layer_ordinal" not in data

    @requires_libclang
    def test_mixed_language_graph_annotates_each_language_independently(self):
        """A single build_graph call can span multiple languages (a real
        repo isn't mono-language) - annotation must handle every language
        present, not assume one for the whole graph."""
        import codecarto.services.parsers.c_language_parser  # noqa: F401

        py = _file("greet.py", "class Greeter: pass\n")
        c = File(name="shapes.c", size=30, raw="struct Point { int x; };\n", url="")
        d = _simple_dir([py, c])
        graph = UnifiedParserService.build_graph(
            d, depth=3, extensions=None, annotate_lexicon=True
        )

        by_kind = {}
        for _, data in graph.nodes(data=True):
            if data.get("kind") in ("class", "struct"):
                by_kind[data["kind"]] = data

        assert by_kind["class"]["layer_ordinal"] == 1  # python: Structure & definition
        assert by_kind["struct"]["layer_ordinal"] == 2  # c: Aggregate & user-defined types

    @pytest.mark.asyncio
    async def test_stream_parse_emits_layer_ordinal_in_sse_node_events(self):
        """The non-streaming path (above) reads the final graph directly;
        this confirms annotation actually reaches the wire format real
        clients receive - SSE node event JSON, not just the in-memory
        graph."""
        code = "class Greeter:\n    def hello(self): pass\n"
        d = _simple_dir([_file("greet.py", code)])

        node_events = []
        async for chunk in UnifiedParserService.stream_parse(
            d, depth=2, annotate_lexicon=True
        ):
            event_type, data = _parse_sse_chunk(chunk)
            if event_type == "node":
                node_events.append(data)

        annotated = [n for n in node_events if "layer_ordinal" in n]
        assert annotated, f"expected at least one annotated node, got: {node_events}"
        assert all(n["layer_ordinal"] == 1 for n in annotated)

    @pytest.mark.asyncio
    async def test_stream_parse_url_per_file_dispatch_annotates(self, monkeypatch):
        """stream_parse_url's per-file dispatch (fetch_and_parse_file)
        parses each file into its own small subgraph, separate from
        build_graph's single accumulated graph - annotation has to happen
        on that subgraph specifically (see the annotate_graph_with_lexicon
        calls added directly in fetch_and_parse_file/fetch_and_parse_batch)
        or nothing downstream of the per-file path would ever see a
        layer_ordinal, no matter what build_graph itself does."""
        import codecarto.services.github_service as gh_svc

        items = [("greet.py", "blob", "https://raw.example/lexstream/greet.py")]
        contents = {
            "https://raw.example/lexstream/greet.py": "class Greeter:\n    def hello(self): pass\n"
        }

        async def fake_fetch_tree_fast(owner, repo, headers, url):
            return items, "main", 1, False

        async def fake_get_raw_from_url(dl_url):
            return contents[dl_url]

        monkeypatch.setattr(gh_svc, "fetch_tree_fast", fake_fetch_tree_fast)
        monkeypatch.setattr(gh_svc, "get_raw_from_url", fake_get_raw_from_url)

        node_events = []
        async for chunk in UnifiedParserService.stream_parse_url(
            "https://github.com/test/lexstream", depth=2, annotate_lexicon=True
        ):
            event_type, data = _parse_sse_chunk(chunk)
            if event_type == "node":
                node_events.append(data)

        annotated = [n for n in node_events if "layer_ordinal" in n]
        assert annotated, f"expected at least one annotated node, got: {node_events}"
        assert all(n["layer_ordinal"] == 1 for n in annotated)

    @pytest.mark.asyncio
    async def test_stream_parse_url_default_is_unannotated(self, monkeypatch):
        import codecarto.services.github_service as gh_svc

        items = [("greet.py", "blob", "https://raw.example/lexstream2/greet.py")]
        contents = {"https://raw.example/lexstream2/greet.py": "class Greeter: pass\n"}

        async def fake_fetch_tree_fast(owner, repo, headers, url):
            return items, "main", 1, False

        async def fake_get_raw_from_url(dl_url):
            return contents[dl_url]

        monkeypatch.setattr(gh_svc, "fetch_tree_fast", fake_fetch_tree_fast)
        monkeypatch.setattr(gh_svc, "get_raw_from_url", fake_get_raw_from_url)

        async for chunk in UnifiedParserService.stream_parse_url(
            "https://github.com/test/lexstream2", depth=2
        ):
            event_type, data = _parse_sse_chunk(chunk)
            if event_type == "node":
                assert "layer_ordinal" not in data
