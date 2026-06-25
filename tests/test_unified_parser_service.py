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
