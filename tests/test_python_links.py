"""The links between a Python file's functions and variables (`python_links`, `PythonLanguageParser`).

A function's calls, the values that flow from one variable to another, and the
names a function reads without holding them. Each test is over a small source
written here, through `links` and through the parser.
"""

from __future__ import annotations

from codecarto.models.source_data import File
from codecarto.services.parsers.python_language_parser import PythonLanguageParser
from codecarto.services.parsers.python_links import links

SOURCE = '''\
LIMIT = 3


class Counter:
    def bump(self, step):
        total = step + LIMIT
        self.show(total)

    def show(self, value):
        shown = value
        return shown


def run(n):
    count = Counter()
    for item in range(n):
        current = item
    with open("f") as handle:
        text = handle
    done = helper(count)
    done += current
    return done


def helper(thing):
    return thing
'''


def test_a_function_calls_what_it_calls_in_its_module():
    # Mutation: read no calls -- and this fails.
    found = {(s, t) for s, t, kind in links(SOURCE, "m") if kind == "calls"}
    assert ("m.run", "m.helper") in found
    assert ("m.run", "m.Counter") in found, "a class called is a call"
    assert ("m.bump", "m.show") in found, "self.show() is a call to the class's method"
    assert ("m.helper", "m.run") not in found


def test_a_value_flows_from_each_variable_it_is_computed_from():
    # Mutation: read no flows from a for or a with -- and this fails.
    found = {(s, t) for s, t, kind in links(SOURCE, "m") if kind == "flows"}
    assert {("m.step", "m.total"), ("m.LIMIT", "m.total"), ("m.value", "m.shown")} <= found
    assert ("m.item", "m.current") in found and ("m.handle", "m.text") in found
    assert ("m.n", "m.item") in found, "a for loop's variable flows from what it iterates"
    assert ("m.count", "m.done") in found and ("m.current", "m.done") in found, "y += x flows x to y"


def test_a_source_that_does_not_parse_states_no_links():
    assert links("def broken(:\n", "m") == set()


def _parsed(depth: int = 3):
    return PythonLanguageParser().parse_files([File(url="", name="m.py", size=0, raw=SOURCE)], depth=depth)


def _kinds(graph, source, target):
    return graph.edges[source, target]["kind"] if graph.has_edge(source, target) else None


def test_a_module_s_variable_is_its_file_s_and_used_by_the_functions_that_read_it():
    # The walker joined every function reading LIMIT to it as holding it. Its
    # file holds it now -- nothing in the file's parse does -- and a function
    # reading it uses it. Mutation: hold every name its readers hold -- and this fails.
    graph = _parsed()
    holds = [s for s, t, kind in graph.edges(data="kind") if t == "m.LIMIT" and kind == "contains"]
    assert holds == [], f"LIMIT is held by {holds}, not by its file"
    assert _kinds(graph, "m.bump", "m.LIMIT") == "uses"


def test_a_variable_two_functions_share_is_held_by_one_and_used_by_the_other():
    # The parser names a variable once per module. Mutation: hold it from
    # every function -- it has two holders, and this fails.
    graph = _parsed()
    holders = {s for s, t, kind in graph.edges(data="kind") if kind == "contains" and t in graph}
    targets = [t for s, t, kind in graph.edges(data="kind") if kind == "contains"]
    twice = {t for t in targets if targets.count(t) > 1}
    assert not twice, f"held twice: {sorted(twice)}"
    assert holders


def test_a_node_two_files_hold_is_held_by_one_and_used_by_the_other(tmp_path):
    # The parser names an import by the module it is from, so two files that
    # import one name each hold the same node, and the canvas drew each file's
    # outline round it wherever it lay -- across the map. Mutation: merge each
    # file's holds as they come (`_one_holder`) -- the shared names have two
    # holders, and this fails.
    from codecarto.services.local_repo_service import get_local_repo
    from codecarto.services.unified_parser_service import UnifiedParserService

    shared = "import typing\nfrom typing import ClassVar\n\n\nclass {name}:\n    kinds: ClassVar[int] = 1\n"
    for name in ("One", "Two", "Three"):
        (tmp_path / f"{name.lower()}.py").write_text(shared.format(name=name), encoding="utf-8")
    graph = UnifiedParserService.build_graph(get_local_repo(str(tmp_path)), 3, None)
    holders: dict[str, set[str]] = {}
    for source, target, kind in graph.edges(data="kind"):
        if kind in ("contains", "field_of"):
            holders.setdefault(target, set()).add(source)
    twice = {node: sorted(by) for node, by in holders.items() if len(by) > 1}
    assert twice == {}, f"held twice: {twice}"
    used = [s for s, t, kind in graph.edges(data="kind") if t == "typing.ClassVar" and kind == "uses"]
    assert len(used) >= 2, "the other files use what one holds"


def test_the_parser_draws_the_calls_and_the_flows_and_none_below_its_depth():
    graph = _parsed()
    assert _kinds(graph, "m.run", "m.helper") == "calls"
    assert _kinds(graph, "m.step", "m.total") == "flows"
    # At depth 2 a function's variables are not parsed, and neither are their flows.
    shallow = _parsed(depth=2)
    assert _kinds(shallow, "m.run", "m.helper") == "calls"
    assert not [1 for _, _, kind in shallow.edges(data="kind") if kind == "flows"]
