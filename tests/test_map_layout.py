"""The Map layout: a code graph as each directory a disc of its files, its
subdirectories packed around it (`show_layout.code_map`), the layout a
showgraph's code view opens in.

A code map is framed whole in the canvas. The compound layout spaces a
repository's directories by a spring layout, and framed whole a parse of this
repository came out at a twentieth of its size, every node under a pixel. So
these tests hold what makes a code map small enough to frame and still drawn
apart: no two nodes overlap, a directory's files fill a disc rather than a
ring, and a directory holding one large subdirectory is not twice its size.
"""

import math
import re
from pathlib import Path

import networkx as nx

from codecarto.models.custom_layouts.compound_layout import compound_layout
from codecarto.models.custom_layouts.map_layout import map_layout
from codecarto.models.plot_data import PlotOptions
from codecarto.services import show_layout
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.services.position_service import Positions

RENDERER = (Path(__file__).resolve().parent.parent / "web" / "src" / "features" / "graph"
            / "services" / "streaming_renderer.ts")


def _tree(shape: dict, graph: nx.DiGraph | None = None, parent: str | None = None) -> nx.DiGraph:
    """A parse's graph from `{"dir": {"sub": {...}, "files": n}}`: directories at
    depth 0 and files at depth 1, joined by `contains` edges."""
    graph = graph if graph is not None else nx.DiGraph()
    for name, inside in shape.items():
        path = f"{parent}/{name}" if parent else name
        graph.add_node(f"dir::{path}", depth=0, label=name, kind="directory")
        if parent:
            graph.add_edge(f"dir::{parent}", f"dir::{path}", kind="contains")
        for i in range(inside.get("files", 0)):
            leaf = f"file::{path}/f{i:03d}.py"
            graph.add_node(leaf, depth=1, label=f"f{i:03d}.py", kind="file")
            graph.add_edge(f"dir::{path}", leaf, kind="contains")
        _tree({k: v for k, v in inside.items() if k != "files"}, graph, path)
    return graph


def _drawn_r(graph: nx.DiGraph, node: str) -> float:
    return show_layout.NODE_R.get(graph.nodes[node]["depth"], show_layout.LEAF_R)


def _extent(places: dict) -> tuple[float, float]:
    xs = [x for x, _ in places.values()]
    ys = [y for _, y in places.values()]
    return max(xs) - min(xs), max(ys) - min(ys)


REPO = {"repo": {"files": 6,
                 "src": {"files": 40, "core": {"files": 25}, "util": {"files": 8}},
                 "tests": {"files": 47, "fixtures": {"cargo": {"workspace": {"files": 30}}}},
                 "docs": {"files": 12}}}


def test_every_node_is_placed_and_none_is_drawn_over_another():
    graph = _tree(REPO)
    places = show_layout.code_map(graph)
    assert set(places) == set(graph.nodes)
    names = sorted(places)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert math.dist(places[a], places[b]) >= _drawn_r(graph, a) + _drawn_r(graph, b), \
                f"{a} and {b} were drawn over each other"


def test_a_directory_s_files_fill_a_disc_round_it():
    # Sixty files on a ring, each its own width apart, stand about 400 units
    # from their directory and leave the ring's middle empty. Filled in, the
    # farthest is under two thirds of that. Mutation: lay the files on a ring
    # (`_ring` with their arcs) -- the farthest is at the ring, and this fails.
    graph = _tree({"big": {"files": 60}})
    places = show_layout.code_map(graph)
    hub = places["dir::big"]
    files = [n for n in graph.nodes if n.startswith("file::")]
    ring = sum(2 * _drawn_r(graph, f) + show_layout.FILE_GAP for f in files) / (2 * math.pi)
    farthest = max(math.dist(places[f], hub) for f in files)
    assert farthest < ring * 2 / 3, f"the files stood {farthest:.0f} from their directory, a ring's {ring:.0f}"


def test_a_directory_holding_one_large_one_is_not_twice_its_size():
    # Each level holds one directory and a file, four deep. Measured around its
    # own node, each level's circle reached past the one it held on the far
    # side too, so each level doubled the map: twelve times as wide as its
    # deepest directory. Measured by what it holds, about three. Mutation:
    # measure each group by its node's circle, and this fails.
    graph = _tree({"a": {"files": 1, "b": {"files": 1, "c": {"files": 1, "d": {"files": 1, "e": {"files": 40}}}}}})
    places = show_layout.code_map(graph)
    deepest = max(_extent({n: p for n, p in places.items() if n.startswith("file::a/b/c/d/e/")}))
    whole = max(_extent(places))
    assert whole < deepest * 5, f"the map was {whole:.0f} across for a deepest directory {deepest:.0f} across"


def test_the_map_is_far_smaller_than_the_compound_layout_s():
    # The compound layout's places are a hundredth of the canvas's units, as
    # `graph_serializer.py` multiplies them.
    graph = _tree(REPO)
    compound = {n: (x * 100, y * 100) for n, (x, y) in compound_layout(graph).items()}
    cw, ch = _extent(compound)
    mw, mh = _extent(show_layout.code_map(_tree(REPO)))
    assert mw * mh < cw * ch / 4, f"the map took {mw:.0f} by {mh:.0f}; the compound layout {cw:.0f} by {ch:.0f}"


def _fit(places: dict) -> float:
    w, h = _extent(places)
    return min(show_layout.CANVAS_ASPECT / w, 1.0 / h)


def test_the_map_is_turned_to_frame_largest_in_the_canvas():
    # Mutation: leave the map as packed -- a turn of it frames it larger, and
    # this fails.
    places = show_layout.code_map(_tree(REPO))
    best = _fit(places)
    for step in range(1, 36):
        a = math.radians(step * 5)
        turned = {n: (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))
                  for n, (x, y) in places.items()}
        assert _fit(turned) <= best * 1.0001, f"turned {step * 5} degrees, the map framed larger"


def test_a_name_goes_outward_from_its_directory_and_a_directory_is_named_by_its_outline():
    # Mutation: keep the sides from before the map was turned -- names face
    # into their directories, and this fails.
    graph = _tree(REPO)
    places = show_layout.code_map(graph)
    holder = {target: source for source, target in graph.edges}
    for node in graph.nodes:
        side = graph.nodes[node]["label_at"]
        if node.startswith("dir::") and any(s == node for s in holder.values()):
            assert side == "none", f"{node} is named by its outline and was named again"
            continue
        dx = places[node][0] - places[holder[node]][0]
        dy = places[node][1] - places[holder[node]][1]
        if side in ("left", "right"):
            assert (side == "right") == (dx > 0), f"{node}'s name faced into its directory"
        elif side in ("above", "below"):
            assert (side == "below") == (dy > 0), f"{node}'s name faced into its directory"


def test_the_map_draws_its_nodes_the_size_the_canvas_draws_them():
    # Mutation: change either constant -- the rings are spaced for nodes of
    # another size than the canvas draws, and this fails.
    stated = re.search(r"export const MAP_NODE_SCALE = ([0-9.]+);", RENDERER.read_text(encoding="utf-8"))
    assert stated, "streaming_renderer.ts no longer states MAP_NODE_SCALE"
    assert float(stated.group(1)) == show_layout.MAP_NODE_SCALE


def test_the_map_layout_is_registered_and_says_where_each_name_goes():
    assert "map_layout" in Positions().get_layout_names()
    graph = _tree(REPO)
    places = map_layout(graph)
    # In the registry's units: a hundredth of the canvas's.
    assert max(_extent(places)) < max(_extent(show_layout.code_map(_tree(REPO)))) / 50
    drawn = GraphSerializer.serialize_to_gjgf(_tree(REPO), PlotOptions(layout="Map", type="d3"))
    sides = {n["metadata"].get("label_at") for n in drawn["nodes"].values()}
    assert "none" in sides and sides & {"left", "right", "above", "below"}


def test_a_class_s_members_are_not_padded_for_an_outline_the_canvas_does_not_draw():
    # A code map held to its floor is drawn to its members (`stream_floor`):
    # a class holds its methods as a file holds its symbols. The canvas
    # outlines a directory and a file, not a class, and a disc padded for an
    # outline round each class left the file's map mostly empty. Mutation: pad
    # every disc for an outline -- the file of ten classes is six times as
    # large as its nodes laid edge to edge, and this fails.
    graph = nx.DiGraph()
    graph.add_node("dir::repo", depth=0)
    graph.add_node("file::repo/a.py", depth=1)
    graph.add_edge("dir::repo", "file::repo/a.py", kind="contains")
    for c in range(10):
        graph.add_node(f"a.C{c}", depth=2)
        graph.add_edge("file::repo/a.py", f"a.C{c}", kind="contains")
        for m in range(8):
            graph.add_node(f"a.C{c}.m{m}", depth=3)
            graph.add_edge(f"a.C{c}", f"a.C{c}.m{m}", kind="field_of")
    places = show_layout.code_map(graph)
    fx, fy = places["file::repo/a.py"]
    reach = max(math.hypot(x - fx, y - fy) for n, (x, y) in places.items() if n.startswith("a.C"))
    cell = 2 * show_layout.LEAF_R + show_layout.FILE_GAP
    assert math.pi * reach ** 2 <= 4 * 90 * cell ** 2, f"the file's ninety symbols and members spread {reach:.0f}"
    nodes = sorted(places)
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            touching = show_layout._drawn_r(graph.nodes[a]["depth"]) + show_layout._drawn_r(graph.nodes[b]["depth"])
            assert math.dist(places[a], places[b]) >= touching - 1e-6, f"{a} and {b} were drawn over each other"
