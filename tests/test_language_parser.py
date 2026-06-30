"""
Tests for the unified parser foundations:
  - language_parser.py  (LanguageParser Protocol, ParserRegistry, helpers)
  - python_language_parser.py (PythonLanguageParser adapter)
  - c_language_parser.py (CLangaugeParser adapter)

These tests do NOT require libclang or any optional system dependency.
"""

import pytest
import networkx as nx

from codecarto.models.source_data import File
from codecarto.services.parsers.language_parser import (
    ParserRegistry,
    make_node,
    make_edge,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _py_file(name: str, code: str) -> File:
    return File(name=name, size=len(code), raw=code)


# ── ParserRegistry ────────────────────────────────────────────────────────────

class TestParserRegistry:
    """ParserRegistry must map extensions to parser instances."""

    def test_python_registered(self):
        # Importing the adapter registers it
        import codecarto.services.parsers.python_language_parser  # noqa: F401
        parser = ParserRegistry.get(".py")
        assert parser is not None
        assert parser.language == "python"

    def test_c_registered(self):
        import codecarto.services.parsers.c_language_parser  # noqa: F401
        parser_c = ParserRegistry.get(".c")
        parser_h = ParserRegistry.get(".h")
        assert parser_c is not None
        assert parser_h is not None
        assert parser_c.language == "c"
        assert parser_h.language == "c"

    def test_unknown_extension_returns_none(self):
        result = ParserRegistry.get(".xyz_unknown_ext")
        assert result is None

    def test_case_insensitive_lookup(self):
        import codecarto.services.parsers.python_language_parser  # noqa: F401
        upper = ParserRegistry.get(".PY")
        lower = ParserRegistry.get(".py")
        assert upper is lower

    def test_all_extensions_includes_registered(self):
        import codecarto.services.parsers.python_language_parser  # noqa: F401
        import codecarto.services.parsers.c_language_parser  # noqa: F401
        exts = ParserRegistry.all_extensions()
        assert ".py" in exts
        assert ".c" in exts
        assert ".h" in exts

    def test_all_parsers_deduped(self):
        """all_parsers() should not contain duplicate instances."""
        import codecarto.services.parsers.python_language_parser  # noqa: F401
        import codecarto.services.parsers.c_language_parser  # noqa: F401
        parsers = ParserRegistry.all_parsers()
        ids = [id(p) for p in parsers]
        assert len(ids) == len(set(ids)), "Duplicate parser instances found"


# ── make_node / make_edge ─────────────────────────────────────────────────────

class TestMakeHelpers:
    """make_node and make_edge should produce correctly shaped dicts."""

    def test_make_node_required_fields(self):
        attrs = make_node(
            "my_id",
            depth=2,
            language="python",
            kind="function",
            label="foo",
        )
        assert attrs["depth"] == 2
        assert attrs["language"] == "python"
        assert attrs["kind"] == "function"
        assert attrs["label"] == "foo"
        assert attrs["file"] == ""
        assert attrs["line"] == 0
        assert attrs["meta"] == {}

    def test_make_node_optional_fields(self):
        attrs = make_node(
            "x",
            depth=1,
            language="c",
            kind="file",
            label="main.c",
            file="src/main.c",
            line=1,
            meta={"foo": "bar"},
        )
        assert attrs["file"] == "src/main.c"
        assert attrs["line"] == 1
        assert attrs["meta"] == {"foo": "bar"}

    def test_make_edge_defaults(self):
        e = make_edge("contains")
        assert e["kind"] == "contains"
        assert e["weight"] == 1.0

    def test_make_edge_custom_weight(self):
        e = make_edge("calls", weight=0.5)
        assert e["weight"] == 0.5


# ── PythonLanguageParser ──────────────────────────────────────────────────────

class TestPythonLanguageParser:
    """PythonLanguageParser must convert PythonCustomAST output to unified schema."""

    def test_class_and_function_depth2(self):
        code = "class Foo:\n    def bar(self): pass\n"
        f = _py_file("mymod.py", code)

        from codecarto.services.parsers.python_language_parser import PythonLanguageParser
        g = PythonLanguageParser().parse_files([f], depth=2)

        assert isinstance(g, nx.DiGraph)
        assert g.number_of_nodes() > 0

        kinds = {d["kind"] for _, d in g.nodes(data=True)}
        assert "class" in kinds
        assert "function" in kinds

    def test_all_nodes_have_unified_schema(self):
        code = "def standalone(): pass\n"
        f = _py_file("mod.py", code)

        from codecarto.services.parsers.python_language_parser import PythonLanguageParser
        g = PythonLanguageParser().parse_files([f], depth=2)

        for nid, data in g.nodes(data=True):
            assert "depth" in data,    f"node {nid!r} missing 'depth'"
            assert "language" in data, f"node {nid!r} missing 'language'"
            assert "kind" in data,     f"node {nid!r} missing 'kind'"
            assert "label" in data,    f"node {nid!r} missing 'label'"
            assert data["language"] == "python"

    def test_depth1_excludes_depth2_nodes(self):
        code = "class Foo:\n    def bar(self): pass\n"
        f = _py_file("mymod.py", code)

        from codecarto.services.parsers.python_language_parser import PythonLanguageParser
        g = PythonLanguageParser().parse_files([f], depth=1)

        # At depth=1 we expect only Module-level nodes (depth==1)
        for _, data in g.nodes(data=True):
            assert data["depth"] <= 1, (
                f"depth-2 node leaked through at max_depth=1: {data}"
            )

    def test_empty_file_returns_graph(self):
        f = _py_file("empty.py", "")
        from codecarto.services.parsers.python_language_parser import PythonLanguageParser
        g = PythonLanguageParser().parse_files([f], depth=2)
        assert isinstance(g, nx.DiGraph)

    def test_multiple_files_merged(self):
        f1 = _py_file("a.py", "class A: pass\n")
        f2 = _py_file("b.py", "class B: pass\n")

        from codecarto.services.parsers.python_language_parser import PythonLanguageParser
        g = PythonLanguageParser().parse_files([f1, f2], depth=2)

        labels = {d["label"] for _, d in g.nodes(data=True)}
        assert "A" in labels
        assert "B" in labels


class TestExtractPythonImports:
    """extract_python_imports — used by unified_parser_service.py's
    _add_python_dependency_edges to resolve real file-to-file dependency
    edges, independent of PythonCustomAST's own (per-file, last-write-wins)
    import bookkeeping."""

    def _imports(self, code: str) -> list[str]:
        from codecarto.services.parsers.python_language_parser import extract_python_imports
        return extract_python_imports(code)

    def test_plain_import(self):
        assert self._imports("import os\n") == ["os"]

    def test_plain_import_with_alias(self):
        assert self._imports("import numpy as np\n") == ["numpy"]

    def test_dotted_import(self):
        assert self._imports("import os.path\n") == ["os.path"]

    def test_from_import(self):
        assert self._imports("from os import path\n") == ["os"]

    def test_relative_import_skipped(self):
        """No absolute dotted name to resolve without full package context."""
        assert self._imports("from . import sibling\n") == []
        assert self._imports("from .pkg import thing\n") == []

    def test_multiple_imports(self):
        code = "import os\nimport sys\nfrom json import loads\n"
        assert self._imports(code) == ["os", "sys", "json"]

    def test_no_imports(self):
        assert self._imports("x = 1\n") == []

    def test_syntax_error_returns_empty(self):
        assert self._imports("def f(:\n") == []

    def test_empty_string_returns_empty(self):
        assert self._imports("") == []


# ── CLangaugeParser ────────────────────────────────────────────────────────────

class TestCLanguageParser:
    """CLangaugeParser must fall back gracefully when libclang is unavailable."""

    def test_returns_empty_graph_when_file_has_no_path_and_no_content(self):
        """A File with no url, no real filesystem path, and no raw content
        has nothing to parse from disk OR from memory -> empty graph."""
        from codecarto.services.parsers.c_language_parser import CLangaugeParser
        f = File(name="ghost.c", size=0, raw="", url="")
        g = CLangaugeParser().parse_files([f], depth=2)
        assert isinstance(g, nx.DiGraph)
        assert g.number_of_nodes() == 0

    # NOTE: a File with no real url but WITH raw content (e.g. fetched from
    # GitHub, never written to disk) now parses via libclang's unsaved_files
    # mechanism instead of returning empty — see
    # TestCLanguageParserUnsavedFiles in test_c_parser_service.py (requires
    # libclang, so it lives in the libclang-gated test file, not here).

    def test_language_and_extension_attributes(self):
        from codecarto.services.parsers.c_language_parser import CLangaugeParser
        p = CLangaugeParser()
        assert p.language == "c"
        assert ".c" in p.extensions
        assert ".h" in p.extensions

    def test_convert_mock_c_graph(self):
        """_convert() should produce a valid unified graph from a synthetic dict."""
        from codecarto.services.parsers.c_language_parser import CLangaugeParser

        raw = {
            "nodes": [
                {
                    "id": "myfile::my_func",
                    "kind": "function",
                    "name": "my_func",
                    "file": "myfile",
                    "line": 10,
                    "qualifiers": [],
                    "type_str": "void",
                    "param_count": 1,
                    "is_definition": True,
                },
                {
                    "id": "myfile::MyStruct",
                    "kind": "struct",
                    "name": "MyStruct",
                    "file": "myfile",
                    "line": 3,
                    "qualifiers": [],
                    "type_str": "struct MyStruct",
                    "field_count": 2,
                },
                {
                    "id": "myfile::field_x",
                    "kind": "field",
                    "name": "field_x",
                    "file": "myfile",
                    "line": 4,
                    "qualifiers": [],
                    "type_str": "int",
                },
            ],
            "edges": [
                {"src": "myfile::MyStruct", "dst": "myfile::field_x", "kind": "FIELD_OF", "weight": 1.0},
            ],
            "meta": {"files": ["myfile"], "node_count": 3, "edge_count": 1, "kind_counts": {}, "edge_kinds": {}},
        }

        p = CLangaugeParser()
        g = p._convert(raw, max_depth=3)

        assert isinstance(g, nx.DiGraph)
        assert g.has_node("myfile::my_func")
        assert g.has_node("myfile::MyStruct")
        assert g.has_node("myfile::field_x")

        func_data = g.nodes["myfile::my_func"]
        assert func_data["depth"] == 2
        assert func_data["language"] == "c"
        assert func_data["kind"] == "function"
        assert func_data["meta"]["param_count"] == 1

        field_data = g.nodes["myfile::field_x"]
        assert field_data["depth"] == 3
        assert field_data["kind"] == "field"

        assert g.has_edge("myfile::MyStruct", "myfile::field_x")
        edge_kind = g.edges["myfile::MyStruct", "myfile::field_x"]["kind"]
        assert edge_kind == "field_of"

    def test_convert_respects_max_depth(self):
        """Nodes deeper than max_depth should be excluded."""
        from codecarto.services.parsers.c_language_parser import CLangaugeParser

        raw = {
            "nodes": [
                {"id": "f::func", "kind": "function", "name": "func",
                 "file": "f", "line": 1, "qualifiers": [], "type_str": ""},
                {"id": "f::field1", "kind": "field", "name": "field1",
                 "file": "f", "line": 2, "qualifiers": [], "type_str": "int"},
            ],
            "edges": [],
            "meta": {},
        }

        p = CLangaugeParser()
        g = p._convert(raw, max_depth=2)  # depth=3 field should be excluded

        assert g.has_node("f::func")
        assert not g.has_node("f::field1"), "depth-3 node should be excluded when max_depth=2"
