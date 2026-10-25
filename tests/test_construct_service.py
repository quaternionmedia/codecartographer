"""The construct vocabulary, held to everything that depends on it.

`constructs.yaml` is joined to three other sources: the lexicons (by token),
the parsers (by kind) and C's reference design (by look). Each join has a test
here, because each one drifts silently -- a token renamed in a lexicon, a kind
added to a parser, a colour changed in one place -- and the picture still
draws.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import networkx as nx
import pytest

from codecarto.services import construct_service
from codecarto.services.lexicon_service import LexiconService
from codecarto.services.parsers import c_language_parser, linker_script_parser, rust_language_parser

VOCABULARY = construct_service.load()
IDS = {c.id for c in VOCABULARY.constructs}


def test_ids_are_unique_and_dotted():
    ids = [c.id for c in VOCABULARY.constructs]
    assert len(ids) == len(set(ids))
    assert all("." in i for i in ids)


def test_every_mapping_names_a_construct_that_exists():
    for language, mapping in VOCABULARY.languages.items():
        targets = [*mapping.kinds.values(), *(r.target for r in mapping.refine),
                   *mapping.qualifiers.values(), *mapping.attributes.values(),
                   *mapping.meta.values(), *mapping.macros.values()]
        missing = [t for t in targets if t not in IDS]
        assert not missing, (language, missing)


def test_a_kind_maps_to_something_a_node_can_be():
    """A facet has no look; a node's construct must have one."""
    for language, mapping in VOCABULARY.languages.items():
        for kind, target in [*mapping.kinds.items(), *((r.kind, r.target) for r in mapping.refine)]:
            assert not VOCABULARY.get(target).facet, (language, kind, target)


@pytest.mark.parametrize("language", sorted(set(LexiconService.available())))
def test_every_spelled_token_is_in_that_languages_lexicon(language):
    """Mutation: rename `trait` in rust.yaml -- this fails and names it."""
    index = LexiconService.load(language).index_by_token()
    missing = [(c.id, tok) for c in VOCABULARY.constructs
               for tok in (c.spelled.get(language).tokens if language in c.spelled else [])
               if tok not in index]
    assert not missing


CANVAS = Path(__file__).resolve().parent.parent / "web/src/features/graph/services/node_shapes.ts"


def canvas_shapes() -> set[str]:
    """`KNOWN_SHAPES`, read from the file the canvas and its key draw with --
    not a Python copy of it, which is a second definition free to drift."""
    source = CANVAS.read_text(encoding="utf-8")
    found = re.search(r"export const KNOWN_SHAPES = \[(.*?)\] as const", source, re.S)
    assert found, "node_shapes.ts no longer exports KNOWN_SHAPES in the form read here"
    return set(re.findall(r"'([a-z]+)'", found.group(1)))


def test_every_look_is_a_shape_the_canvas_draws():
    """Mutation: drop `'ngon'` from `KNOWN_SHAPES` in node_shapes.ts -- this
    fails naming it, where a Python list of the canvas's shapes stayed green."""
    shapes = {c.look.shape for c in VOCABULARY.constructs if c.look}
    assert shapes <= canvas_shapes(), shapes - canvas_shapes()


def test_rust_parser_kinds_and_the_vocabulary_agree_both_ways():
    mapped = set(VOCABULARY.languages["rust"].kinds)
    assert set(rust_language_parser.KINDS) == mapped


def test_c_adapter_kinds_are_all_mapped():
    c_kinds = c_language_parser._DEPTH_2_KINDS | c_language_parser._DEPTH_3_KINDS
    assert c_kinds == set(VOCABULARY.languages["c"].kinds)


def test_c_reference_design_and_the_vocabulary_agree():
    """C's adapter carries the c-visualizer design; the vocabulary carries the
    same looks for the same constructs, so a Rust struct is drawn as a C one.
    When the two disagree, the vocabulary is the one to keep."""
    disagree = []
    for kind, construct_id in VOCABULARY.languages["c"].kinds.items():
        look = VOCABULARY.get(construct_id).look
        actual = (c_language_parser._C_SHAPE.get(kind), c_language_parser._C_COLOR.get(kind))
        if actual != (look.shape, look.color):
            disagree.append((kind, actual, (look.shape, look.color)))
    assert not disagree


def test_linker_kinds_are_mapped():
    graph = linker_script_parser.LinkerScriptParser().parse_files([
        linker_script_parser.File(name="m.x", raw="MEMORY { RAM : ORIGIN = 0, LENGTH = 1K }\n"
                                                   "ENTRY(r)\nx = 1;\nSECTIONS { .t : { } > RAM }")])
    kinds = {d["kind"] for _, d in graph.nodes(data=True)}
    assert kinds == set(VOCABULARY.languages["linker"].kinds)


# ── annotate ──────────────────────────────────────────────────────────────────


def graph_of(*nodes: tuple[str, dict]) -> nx.DiGraph:
    g = nx.DiGraph()
    for node_id, attrs in nodes:
        g.add_node(node_id, **attrs)
    return g


def test_annotate_stamps_construct_and_facets_and_a_default_look():
    g = graph_of(("s", {"language": "rust", "kind": "struct",
                        "meta": {"attributes": ["repr(C)"], "field_count": 7}}))
    assert construct_service.annotate(g) == 1
    data = g.nodes["s"]
    assert data["construct"] == "type.product"
    assert data["meta"]["facets"] == ["layout.repr"]
    assert (data["shape"], data["color"], data["meta"]["sides"]) == ("ngon", "#4a9eff", 7)


@pytest.mark.parametrize("kind, meta, sides", [
    ("struct", {"field_count": 0}, 3),     # a unit struct: no fields is a count
    ("union", {"field_count": 2}, 3),
    ("struct", {"field_count": 7}, 7),
    ("struct", {"field_count": 40}, construct_service.NGON_SIDES[1]),
    ("struct", {}, None),                   # no count: the canvas's default, not an invented one
])
def test_a_records_sides_are_its_own_count_within_one_range(kind, meta, sides):
    """`0 or ... or 4` read a unit struct's zero fields as "no count" and gave
    it four sides. Mutation: put the `or` chain back -- the zero-field case
    fails with 4."""
    g = graph_of(("s", {"language": "rust", "kind": kind, "meta": dict(meta)}))
    construct_service.annotate(g)
    assert g.nodes["s"]["shape"] == "ngon"
    assert g.nodes["s"]["meta"].get("sides") == sides


def test_the_c_adapter_and_the_vocabulary_clamp_sides_alike():
    """One range, stated once (`NGON_SIDES`). Mutation: clamp to 12 in the C
    adapter -- the forty-field struct fails."""
    raw = {"nodes": [{"id": "f::Big", "kind": "struct", "name": "Big", "file": "f", "line": 1,
                      "qualifiers": [], "type_str": "", "field_count": 40},
                     {"id": "f::U", "kind": "union", "name": "U", "file": "f", "line": 2,
                      "qualifiers": [], "type_str": "", "field_count": 0}],
           "edges": [], "meta": {}}
    g = c_language_parser.CLangaugeParser()._convert(raw, max_depth=3)
    assert g.nodes["f::Big"]["meta"]["sides"] == construct_service.NGON_SIDES[1]
    assert g.nodes["f::U"]["meta"]["sides"] == construct_service.NGON_SIDES[0]


def test_a_parsers_own_look_wins():
    g = graph_of(("f", {"language": "c", "kind": "function", "shape": "square", "color": "#000"}))
    construct_service.annotate(g)
    assert (g.nodes["f"]["shape"], g.nodes["f"]["color"]) == ("square", "#000")
    assert g.nodes["f"]["construct"] == "callable.function"


def test_an_unlisted_language_is_left_exactly_as_it_arrived():
    g = graph_of(("j", {"language": "javascript", "kind": "function", "meta": {}}))
    assert construct_service.annotate(g) == 0
    assert g.nodes["j"] == {"language": "javascript", "kind": "function", "meta": {}}


def test_annotate_is_idempotent():
    g = graph_of(("e", {"language": "rust", "kind": "enum", "meta": {"c_like": True,
                                                                      "qualifiers": ["pub"]}}))
    construct_service.annotate(g)
    once = {k: (dict(v) if isinstance(v, dict) else v) for k, v in g.nodes["e"].items()}
    construct_service.annotate(g)
    assert g.nodes["e"] == once
    assert once["construct"] == "type.enumeration"


def test_attribute_names():
    name = construct_service.attribute_name
    assert name("cortex_m_rt::entry") == "entry"
    assert name("repr(C, packed)") == "repr"
    assert name('link_section = ".x"') == "link_section"
    assert name("unsafe(no_mangle)") == "no_mangle"


# ── the chrestomathy ──────────────────────────────────────────────────────────


def test_a_construct_read_across_languages_keeps_the_silent_ones():
    """C has no keyword for a method; the row is there, with its note."""
    reading = construct_service.reading("callable.method")
    rows = {r["language"]: r for r in reading["languages"]}
    assert set(rows) >= {"c", "rust", "python"}
    assert rows["c"]["tokens"] == [] and rows["c"]["note"]
    assert [t["token"] for t in rows["rust"]["tokens"]] == ["fn", "impl"]
    assert rows["rust"]["kinds"] == ["method"]


def test_tokens_carry_their_lexicon_layer():
    reading = construct_service.reading("type.product")
    rust = next(r for r in reading["languages"] if r["language"] == "rust")
    (context,) = rust["tokens"][0]["contexts"]
    assert (context["layer_ordinal"], context["group"]) == (2, "aggregate")


def test_one_keyword_two_constructs():
    """`enum` spells both an enumeration and a sum type in Rust; the parser
    kind tells them apart only through the refinement."""
    enumeration = construct_service.reading("type.enumeration")
    rust = next(r for r in enumeration["languages"] if r["language"] == "rust")
    assert rust["kinds"] == ["enum"]
    assert construct_service.construct_for("rust", "enum", {"c_like": True}) == "type.enumeration"
    assert construct_service.construct_for("rust", "enum", {"c_like": False}) == "type.sum"


def test_facets_say_what_carries_them():
    reading = construct_service.reading("firmware.interrupt")
    rust = next(r for r in reading["languages"] if r["language"] == "rust")
    assert set(rust["carried_by"]) == {"#[interrupt]", "#[exception]"}


def test_the_graph_puts_the_construct_at_the_centre_and_colours_tokens_by_layer():
    graph = construct_service.as_graph("memory.volatile")
    root = "construct:memory.volatile"
    assert set(graph.successors(root)) == {"language:c", "language:rust"}
    token = graph.nodes["token:c:volatile"]
    assert token["color"] == construct_service.layer_color(token["layer_ordinal"])
    # Rust spells it with no token: drawn, dashed, with its note.
    rust_edge = graph.edges[root, "language:rust"]
    assert rust_edge["style"] == "dashed"
    assert "read_volatile" in graph.nodes["language:rust"]["hover"]


PANEL_FIXTURE = Path(__file__).resolve().parent.parent / "web/tests/pure/fixtures/chrestomathy-readings.json"


def test_the_panels_fixture_is_what_the_server_sends():
    """The Chrestomathy panel's pure test reads its rows from this fixture, so
    they are the rows `reading` sends -- the test carried an assembly row for a
    record, which the server never sends. When the server's rows change, so
    must the fixture: `uv run python -c "import json; from codecarto.services
    import construct_service as c; print(json.dumps({k: c.reading(k)['languages']
    for k in ('type.product', 'memory.volatile')}, indent=2, ensure_ascii=False))"`.
    Mutation: add a row to the fixture -- this fails."""
    fixture = json.loads(PANEL_FIXTURE.read_text(encoding="utf-8"))
    for construct, rows in fixture.items():
        assert rows == construct_service.reading(construct)["languages"], construct


def test_a_drawn_token_says_whose_it_is():
    """An ordinal is a rank in one lexicon, so the key names a layer by
    language where two share a number -- which it can only do for a node that
    says its language. Mutation: drop `language` from the token node -- this
    fails."""
    graph = construct_service.as_graph("control.loop")
    tokens = [(n, d) for n, d in graph.nodes(data=True) if d["kind"] == "token"]
    assert {d.get("language") for _, d in tokens} == {"c", "rust", "python"}
    assert all(n.startswith(f"token:{d['language']}:") for n, d in tokens)


def test_an_unknown_construct_is_none():
    assert construct_service.reading("no.such") is None
    assert construct_service.as_graph("no.such") is None


def test_layer_ramp():
    assert construct_service.layer_color(0) == construct_service.LAYER_RAMP[0]
    assert construct_service.layer_color(99) == construct_service.LAYER_RAMP[-1]
    assert construct_service.layer_color(-1) not in construct_service.LAYER_RAMP
