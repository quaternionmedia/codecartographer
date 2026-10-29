"""The Showcase layout: a code map whose every node is a dot, packed tight
(`show_layout.showcase`), and the settings it takes on its name
(`position_service.layout_spec`).

A parse is drawn as its directories' and files' discs with every function,
class, variable and call a dot in them, as large as the source it stands for,
so a picture says how much code is in a file and what kind, not only that the
file is there. These tests hold what makes it that: the settings reach the
layout and nothing else does, no two dots overlap, a file's dots fill its disc
and stand apart from the next file's, a symbol's members lie together, two
symbols that hold alike are drawn alike, and what the canvas draws is what the
server laid out. Each is over a real parse of a small package written here.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest

from codecarto.services import show_layout
from codecarto.services.local_repo_service import get_local_repo
from codecarto.services.position_service import Positions, layout_key, layout_spec
from codecarto.services.show_layout import (SHOWCASE_PAD, SHOWCASE_SCALE, chars_scale, code_map, showcase,
                                            showcase_radius)
from codecarto.services.unified_parser_service import UnifiedParserService

ROOT = Path(__file__).resolve().parent.parent
SHOWCASE_TS = ROOT / "web" / "src" / "features" / "graph" / "services" / "showcase.ts"

MODULES = ["os", "re", "json", "math", "time", "shlex", "string", "random"]


def _source(index: int) -> str:
    """A module with constants, a class and functions full of variables."""
    lines = [f"import {MODULES[index % len(MODULES)]}", f"import {MODULES[(index + 3) % len(MODULES)]}", ""]
    lines += [f"LIMIT_{k} = {k}" for k in range(4)]
    lines += ["", "", f"class Thing{index}:", "    def run(self, step):"]
    lines += [f"        v{k} = step + {k}" for k in range(6)]
    lines += ["        return v5", ""]
    # The parser names a variable, and a literal, once per module, so each
    # function's are its own: no literal, and its own names.
    for f in range(8):
        lines += ["", f"def work{f}(a{f}, b{f}):"]
        lines += [f"    x{f}_{k} = a{f} + b{f} + LIMIT_{k % 4}" for k in range(8)]
        lines += [f"    return helper{f}(x{f}_7)", "", f"def helper{f}(value):", "    out = value", "    return out"]
    return "\n".join(lines) + "\n"


@pytest.fixture(scope="module")
def parse(tmp_path_factory):
    root = tmp_path_factory.mktemp("pkg")
    (root / "core").mkdir()
    for i in range(3):
        (root / f"top{i}.py").write_text(_source(i), encoding="utf-8")
        (root / "core" / f"inner{i}.py").write_text(_source(i + 3), encoding="utf-8")
    return lambda: UnifiedParserService.build_graph(get_local_repo(str(root)), 3, None)


def _depth(graph, node) -> int:
    return graph.nodes[node].get("depth", 1)


def _held(graph) -> dict[str, list[str]]:
    held: dict[str, list[str]] = {}
    for source, target, kind in graph.edges(data="kind"):
        if kind in ("contains", "field_of"):
            held.setdefault(source, []).append(target)
    return held


def _code_of(graph, file_id: str) -> set[str]:
    held, found, frontier = _held(graph), set(), [file_id]
    while frontier:
        for child in held.get(frontier.pop(), []):
            if child not in found:
                found.add(child)
                frontier.append(child)
    return found


def _radius(graph, node, dot: float = 2.0) -> float:
    """A dot's radius as the layout set it, which the canvas draws it at."""
    return dot * graph.nodes[node]["dot_scale"]


def _span(places) -> float:
    xs = [x for x, _ in places.values()]
    ys = [y for _, y in places.values()]
    return max(max(xs) - min(xs), max(ys) - min(ys))


# ── The settings on a layout's name ────────────────────────────────────────


def test_a_layout_s_name_carries_its_settings_in_brackets():
    # Mutation: read no settings from the brackets -- and this fails.
    assert layout_spec("Showcase(dot=2, gap=0.5,nest=false)") == (
        "Showcase", {"dot": "2", "gap": "0.5", "nest": "false"})
    assert layout_spec("Map") == ("Map", {})
    assert layout_spec(" Spring ") == ("Spring", {})


def test_a_layout_s_key_keeps_its_settings_in_one_order():
    # `GraphSerializer` lays a graph out by its layout's key, so the key keeps
    # the settings, in one order: two spellings of one setting are one key,
    # and two settings are two. Mutation: keep the settings in the order
    # written -- and this fails.
    assert layout_key("Showcase(gap=1,dot=3)") == layout_key("showcase_layout(dot=3, gap=1)") \
        == "showcase_layout(dot=3,gap=1)"
    assert layout_key("Showcase(dot=3)") != layout_key("Showcase(dot=4)")
    assert layout_key("Map") == "map_layout"


def test_a_setting_the_layout_does_not_take_is_refused(parse):
    # Mutation: drop a setting the layout does not declare -- it is laid out
    # as though none was asked, and this fails.
    graph = parse()
    with pytest.raises(ValueError, match="takes no parameter size"):
        Positions().get_node_positions(graph, "Showcase(size=3)")
    with pytest.raises(ValueError, match="takes no parameter dot"):
        Positions().get_node_positions(graph, "Spring(dot=3)")


def test_the_showcase_is_laid_out_by_the_settings_on_its_name(parse):
    # Mutation: pass the layout none of the settings its name carries -- every
    # dot size is laid out the same, and this fails.
    graph = parse()
    small = Positions().get_node_positions(graph, "Showcase(dot=1)")
    large = Positions().get_node_positions(graph, "Showcase(dot=4,gap=1)")
    assert _span(large) > 2.5 * _span(small)
    mixed = Positions().get_node_positions(graph, "Showcase(nest=false)")
    assert mixed != Positions().get_node_positions(graph, "Showcase(nest=true)")
    unsized = Positions().get_node_positions(graph, "Showcase(sized=false)")
    assert unsized != Positions().get_node_positions(graph, "Showcase(sized=true)")


# ── The layout ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("nest", [True, False])
def test_no_two_dots_overlap(parse, nest):
    # Each dot at its own size, a gap clear of the next. Mutation: lay a
    # file's code out for dots half as wide as the canvas draws them -- and
    # this fails.
    graph = parse()
    dot, gap = 2.0, 0.5
    places = showcase(graph, dot=dot, gap=gap, nest=nest)
    nodes = list(places)
    worst = math.inf
    for i, a in enumerate(nodes):
        ra = _radius(graph, a, dot)
        for b in nodes[i + 1:]:
            clear = math.dist(places[a], places[b]) - ra - _radius(graph, b, dot)
            worst = min(worst, clear)
    assert worst >= gap - 1e-6, f"two dots are {worst:.2f} apart"


def test_two_files_outlines_do_not_overlap(parse):
    # The canvas draws an outline round each file half `SHOWCASE_PAD` dots
    # past the smallest circle round its code (`compound_layout.ts`); two
    # such are clear of each other. Mutation: pad a file's disc by nothing -- the outlines drawn
    # round two neighbours overlap, and this fails.
    graph = parse()
    dot = 2.0
    places = showcase(graph, dot=dot)
    files = [n for n in graph.nodes if _depth(graph, n) == 1 and _code_of(graph, n)]
    assert len(files) == 6
    drawn = {}
    for f in files:
        x, y, r = show_layout.circle_pack.enclose(
            [(*places[n], _radius(graph, n, dot)) for n in [f, *_code_of(graph, f)]])
        drawn[f] = (x, y, r + SHOWCASE_PAD * dot / 2)
    for i, a in enumerate(files):
        for b in files[i + 1:]:
            (ax, ay, ar), (bx, by, br) = drawn[a], drawn[b]
            apart = math.dist((ax, ay), (bx, by)) - ar - br
            assert apart >= -1e-6, f"{a}'s outline and {b}'s overlap by {-apart:.1f}"


def test_a_symbol_s_members_lie_together_when_clustered(parse):
    # With `nest`, a function's variables are a patch of its file's disc
    # beside it; without, they are mixed through it. Mutation: give the
    # members their places in the sunflower's own order either way -- and
    # this fails.
    graph = parse()
    held = _held(graph)
    symbols = [n for n in graph.nodes if _depth(graph, n) == 2 and len(held.get(n, [])) >= 8]
    assert len(symbols) >= 6 * 8

    def spread(places) -> float:
        """How far a symbol's members lie from the middle of them, on average."""
        total = 0.0
        for s in symbols:
            xs, ys = zip(*(places[m] for m in held[s]))
            middle = (sum(xs) / len(xs), sum(ys) / len(ys))
            total += sum(math.dist(places[m], middle) for m in held[s]) / len(xs)
        return total / len(symbols)

    assert spread(showcase(graph, nest=True)) < 0.5 * spread(showcase(graph, nest=False))


def test_a_file_s_code_fills_its_disc(parse):
    # A file's dots, glyph by glyph, fill the circle round them about as
    # densely as circles pack. Mutation: lay a file's code out as the Map lays
    # out a directory -- a disc round each symbol, each padded for an outline
    # it is never drawn -- and the worst file is an eighth dots, and this fails.
    graph = parse()
    dot = 2.0
    places = showcase(graph, dot=dot)
    for file in (n for n in graph.nodes if _depth(graph, n) == 1 and _code_of(graph, n)):
        code = [file, *_code_of(graph, file)]
        _, _, outer = show_layout.circle_pack.enclose([(*places[n], _radius(graph, n, dot)) for n in code])
        full = sum(_radius(graph, n, dot) ** 2 for n in code) / outer ** 2
        assert full >= 0.22, f"{file} is {full:.0%} dots"


def test_a_dot_is_as_large_as_the_source_it_stands_for(parse):
    # A symbol's or a member's radius grows a dot for each ten times as many
    # characters, from half a dot to four; a file's and a directory's are
    # fixed, their discs saying what they hold. Mutation: size every member
    # as one dot -- the longer function is drawn no larger, and this fails.
    graph = parse()
    showcase(graph)
    scale = {n: graph.nodes[n]["dot_scale"] for n in graph.nodes}
    chars = {n: (graph.nodes[n].get("meta") or {}).get("chars") for n in graph.nodes}
    assert chars["top0.work0"] > chars["top0.helper0"] and scale["top0.work0"] > scale["top0.helper0"]
    for node in graph.nodes:
        depth = _depth(graph, node)
        expected = SHOWCASE_SCALE[depth] if depth in SHOWCASE_SCALE else chars_scale(chars[node])
        assert scale[node] == pytest.approx(expected, abs=1e-3), node
    assert (chars_scale(None), chars_scale(5), chars_scale(100), chars_scale(10 ** 9)) == (1.0, 0.5, 1.5, 4.0)
    # Not sized, every member is a dot.
    unsized = parse()
    showcase(unsized, sized=False)
    assert {unsized.nodes[n]["dot_scale"] for n in unsized.nodes if _depth(unsized, n) >= 2} == {1.0}


def test_two_functions_that_hold_alike_are_drawn_alike(parse):
    # Each `work` function holds the same arguments, variables and calls,
    # each as long as the other's. A function's glyph depends on what it
    # holds alone, so wherever each is drawn, its members lie round it in the
    # same places. Mutation: give a file's code its places along a Hilbert
    # curve through its disc, as the Showcase did -- each function's members
    # are a run of the curve, shaped by where it falls, and this fails.
    graph = parse()
    places = showcase(graph)
    held = _held(graph)

    def shape(function: str):
        hx, hy = places[function]
        return sorted((round(places[m][0] - hx, 3), round(places[m][1] - hy, 3), graph.nodes[m].get("kind"))
                      for m in held[function])

    works = [n for n in graph.nodes if graph.nodes[n].get("label", "").startswith("work")]
    assert len(works) == 6 * 8
    shapes = {str(shape(w)) for w in works}
    assert len(shapes) == 1, f"{len(shapes)} shapes for {len(works)} functions that hold alike"


def test_only_a_function_or_a_class_is_a_glyph_of_its_own():
    # What a call or a name holds is packed in the glyph of the function over
    # it: each level a glyph nests is a circle round circles, and nested at
    # every level the walker holds by, a file was a quarter dots. Mutation:
    # nest a glyph for every holder -- the call holds its argument, and this
    # fails.
    held = {"file": ["f", "IMPORT"], "f": ["call", "x"], "call": ["arg"], "IMPORT": ["alias"]}
    symbols = {"f"}
    assert show_layout._by_symbol("file", held, symbols.__contains__) == {
        "file": ["f", "IMPORT", "alias"], "f": ["call", "arg", "x"]}


def test_modules_from_outside_are_one_disc_beside_the_map(parse):
    # What nothing holds -- a module imported from outside -- is gathered
    # into one disc. Mutation: row them, as the Map does -- the two farthest
    # are a row's length apart, and this fails.
    graph = parse()
    places = showcase(graph)
    outside = [n for n, data in graph.nodes(data=True) if data.get("kind") == "external_module"]
    assert len(outside) == len(MODULES)
    farthest = max(math.dist(places[a], places[b]) for a in outside for b in outside)
    a_row = sum(2 * showcase_radius(1, 2.0) + 2 * 2.0 + 1.0 for _ in outside)
    assert farthest < 0.5 * a_row


def test_a_showcase_is_smaller_than_a_map_of_the_same_parse(parse):
    # Mutation: size and space it as the Map does -- and this fails.
    graph = parse()
    assert _span(showcase(graph)) < 0.5 * _span(code_map(graph))


def test_the_map_is_laid_out_as_it_was():
    # The Showcase's spacing is the Map's made a parameter; the Map's own is
    # its constants. Mutation: pad a Map's file by the Showcase's padding --
    # and this fails.
    spacing = show_layout.MAP_SPACING
    assert spacing.pad == (show_layout.CODE_PAD, show_layout.CODE_PAD)
    assert spacing.apart == show_layout.GAP


# ── The canvas draws what the server laid out ──────────────────────────────


def test_a_dot_s_size_and_an_outline_s_padding_are_the_canvas_s():
    # The canvas draws each dot, and pads each outline, by `showcase.ts`; the
    # server lays them out by these. Mutation: draw a file's dot twice a
    # member's on the canvas -- the server packs it smaller than it is drawn,
    # and this fails.
    source = SHOWCASE_TS.read_text(encoding="utf-8")
    scale = re.search(r"DOT_SCALE: Readonly<Record<number, number>> = \{([^}]*)\}", source)
    pad = re.search(r"export const SHOWCASE_PAD = ([0-9.]+);", source)
    assert scale and pad, "showcase.ts's DOT_SCALE or SHOWCASE_PAD was not found"
    drawn = {int(k): float(v) for k, v in re.findall(r"(\d+):\s*([0-9.]+)", scale.group(1))}
    assert drawn == SHOWCASE_SCALE
    assert float(pad.group(1)) == SHOWCASE_PAD
