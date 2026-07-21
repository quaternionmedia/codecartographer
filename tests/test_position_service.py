"""Tests for layout position generation.

Run: pytest tests/test_position_service.py
"""

import math

import networkx as nx
import pytest

from codecarto.models.custom_layouts.compound_layout import compound_layout
from codecarto.services.parsers.language_parser import make_edge
from codecarto.services.position_service import Positions


def test_registered_layouts_no_longer_include_dead_ones():
    names = Positions().get_layout_names()
    assert "arch_layout" not in names
    assert "cluster_layout" not in names
    assert "compound_layout" in names
    assert "sorted_square_layout" in names


# Edges are built via make_edge() (the same helper every real parser uses)
# rather than a hand-rolled {"kind": "contains"} dict, so these tests stay
# tied to the actual unified-schema edge shape instead of silently drifting
# from it the way a hardcoded field name could.


def _add_dir(g: nx.DiGraph, dir_id: str, label: str) -> None:
    g.add_node(dir_id, depth=0, label=label)


def _add_file(g: nx.DiGraph, parent_dir: str, file_id: str, label: str) -> None:
    g.add_node(file_id, depth=1, label=label)
    g.add_edge(parent_dir, file_id, **make_edge("contains"))


def _add_symbol(g: nx.DiGraph, parent_file: str, sym_id: str, line: int) -> None:
    g.add_node(sym_id, depth=2, label=sym_id, line=line)
    g.add_edge(parent_file, sym_id, **make_edge("contains"))


def _dist(pos: dict, node: str) -> float:
    x, y = pos[node]
    return math.hypot(x, y)


def _lopsided_graph() -> nx.DiGraph:
    """One directory with a deep nested subtree; four small sibling dirs
    with a single, symbol-less file each."""
    g = nx.DiGraph()

    _add_dir(g, "dir_big", "big")
    _add_dir(g, "dir_big_sub", "big/sub")
    g.add_edge("dir_big", "dir_big_sub", **make_edge("contains"))
    _add_file(g, "dir_big", "dir_big_file0", "root.py")

    for i in range(8):
        fid = f"dir_big_sub_file{i}"
        _add_file(g, "dir_big_sub", fid, f"f{i}.py")
        for j in range(4):
            _add_symbol(g, fid, f"{fid}_sym{j}", line=j)

    for k in range(4):
        d = f"dir_small_{k}"
        _add_dir(g, d, d)
        _add_file(g, d, f"{d}_file0", "only.py")

    return g


def test_compound_layout_gives_directory_with_deep_subtree_more_room():
    """A directory whose room-need comes from a deep/wide nested subtree
    (not just direct file children) should end up proportionally further
    from the pack than siblings with a single, flat file each."""
    g = _lopsided_graph()
    pos = compound_layout(g)

    big_dist = _dist(pos, "dir_big")
    small_dists = [_dist(pos, f"dir_small_{k}") for k in range(4)]
    avg_small_dist = sum(small_dists) / len(small_dists)

    assert big_dist > avg_small_dist


def test_compound_layout_places_every_node_with_finite_coordinates():
    g = _lopsided_graph()
    pos = compound_layout(g)

    assert set(pos.keys()) == set(g.nodes)
    for x, y in pos.values():
        assert math.isfinite(x)
        assert math.isfinite(y)


def test_compound_layout_orbits_files_around_their_own_directory():
    """Regression test: parent detection must key off the edge attribute
    real parsers actually emit (`kind`, via make_edge()), not a
    differently-named field. Under the bug this guards against, every
    'contains' edge silently failed to match, `file_parent` stayed empty,
    and every file in the graph fell back to one shared ring centered on
    the origin regardless of which directory it belonged to — so two
    files in two different, well-separated directories would land
    equidistant from the origin instead of near their own directory."""
    g = nx.DiGraph()
    _add_dir(g, "dir_a", "a")
    _add_dir(g, "dir_b", "b")
    for i in range(5):
        _add_file(g, "dir_a", f"dir_a_file{i}", f"a{i}.py")
    for i in range(5):
        _add_file(g, "dir_b", f"dir_b_file{i}", f"b{i}.py")

    pos = compound_layout(g)
    ax, ay = pos["dir_a"]
    bx, by = pos["dir_b"]

    for i in range(5):
        fx, fy = pos[f"dir_a_file{i}"]
        dist_to_own_dir = math.hypot(fx - ax, fy - ay)
        dist_to_other_dir = math.hypot(fx - bx, fy - by)
        assert dist_to_own_dir < dist_to_other_dir


def test_orphan_file_ring_radius_scales_with_orphan_count():
    """Regression test: the orphan fallback ring's radius must grow with
    how many nodes land on it, the same way subsym_orbit_r's orphan ring
    already scaled with count — a fixed radius means adjacent-node spacing
    shrinks toward zero as more orphans accumulate, producing a visibly
    overlapping ring."""
    def _build(n_orphans: int) -> nx.DiGraph:
        g = nx.DiGraph()
        _add_dir(g, "dir_a", "a")
        _add_file(g, "dir_a", "real_file", "real.py")
        for i in range(n_orphans):
            g.add_node(f"orphan{i}", depth=1, label=f"orphan{i}.py")
        return g

    pos_small = compound_layout(_build(3))
    pos_large = compound_layout(_build(60))

    r_small = _dist(pos_small, "orphan0")
    r_large = _dist(pos_large, "orphan0")

    assert r_large > r_small


def test_bare_module_level_subsymbol_orbits_its_file_not_the_orphan_ring():
    """Regression test: a sub-symbol whose real parent is the file itself
    (a bare top-level statement with no enclosing function/class -- e.g. a
    module-level call or constant) has no depth-2 symbol ancestor to orbit.
    Before Pass 4b existed, subsym_parent had no case for a depth-1 parent
    at all, so every one of these landed on the shared orphan fallback
    ring regardless of which file it actually belonged to -- on this
    project's own source, that was 43% of all sub-symbol nodes."""
    g = nx.DiGraph()
    _add_dir(g, "dir_a", "a")
    _add_file(g, "dir_a", "file_a", "a.py")
    _add_file(g, "dir_a", "file_b", "b.py")
    # Bare module-level statement: file -> sub-symbol directly, no symbol
    g.add_node("file_a_stmt", depth=3, label="stmt", line=1)
    g.add_edge("file_a", "file_a_stmt", **make_edge("contains"))
    g.add_node("file_b_stmt", depth=3, label="stmt", line=1)
    g.add_edge("file_b", "file_b_stmt", **make_edge("contains"))

    pos = compound_layout(g)
    ax, ay = pos["file_a"]
    bx, by = pos["file_b"]

    dist_a_to_own = math.hypot(pos["file_a_stmt"][0] - ax, pos["file_a_stmt"][1] - ay)
    dist_a_to_other = math.hypot(pos["file_a_stmt"][0] - bx, pos["file_a_stmt"][1] - by)
    assert dist_a_to_own < dist_a_to_other


def test_c_struct_field_orbits_its_struct_not_the_orphan_ring():
    """Regression test: c_language_parser.py deliberately uses the more
    specific edge kind 'field_of' (not 'contains') for struct/union/enum ->
    field/enum_constant membership (see c_language_parser.py's
    _EDGE_KIND_MAP) -- it's a real, intentional part of the unified schema,
    not a typo like the earlier relation/kind bug. But compound_layout.py's
    parent-detection only recognized 'contains', so every field and enum
    constant in every C struct/enum was orphaned. Verified live at scale
    against redis's real C source (github.com/redis/redis): 100% of 3,194
    sub-symbols (fields + enum constants) had no resolved parent before
    this fix, dropping to 4.7% after -- this test pins the mechanism with a
    minimal graph."""
    g = nx.DiGraph()
    _add_dir(g, "dir_a", "a")
    _add_file(g, "dir_a", "file_a", "a.c")
    g.add_node("struct_a", depth=2, label="StructA", line=1)
    g.add_edge("file_a", "struct_a", **make_edge("contains"))
    g.add_node("struct_a_field", depth=3, label="field", line=2)
    g.add_edge("struct_a", "struct_a_field", **make_edge("field_of"))

    # A second, unrelated struct in the same file, far enough around the
    # arc that a fallback-ring placement wouldn't coincidentally land near
    # struct_a's own orbit.
    g.add_node("struct_b", depth=2, label="StructB", line=50)
    g.add_edge("file_a", "struct_b", **make_edge("contains"))

    pos = compound_layout(g)
    sx, sy = pos["struct_a"]
    bx, by = pos["struct_b"]

    dist_to_own_struct = math.hypot(pos["struct_a_field"][0] - sx, pos["struct_a_field"][1] - sy)
    dist_to_other_struct = math.hypot(pos["struct_a_field"][0] - bx, pos["struct_a_field"][1] - by)
    assert dist_to_own_struct < dist_to_other_struct


def test_c_bare_stem_file_attribute_falls_back_via_stem_index():
    """Regression test: c_parser.py sets a sub-symbol's 'file' node attribute
    to a bare stem with no extension at all (Path(cursor.location.file.name)
    .stem -- see c_parser.py), unlike Python's parser, which always includes
    the extension. When a sub-symbol has no direct containment edge to
    resolve its parent (redis's real C source has deeply nested
    anonymous-struct/union fields that land in exactly this position), the
    file-attribute fallback needs a third, stem-indexed lookup tier --
    file_label_to_id's keys are always full "name.ext" labels, so neither of
    the first two fallback checks (stem-of-file_attr, or file_attr verbatim)
    can ever match a file_attr that is already bare. Verified live at scale
    against redis's real C source: 149/3194 (4.66%) sub-symbols were still
    orphaned by this gap even after the field_of fix, dropping to 0 once
    this stem index was added."""
    g = nx.DiGraph()
    _add_dir(g, "dir_a", "a")
    _add_file(g, "dir_a", "file_a", "a.c")
    g.add_node("struct_a", depth=2, label="StructA", line=1)
    g.add_edge("file_a", "struct_a", **make_edge("contains"))

    # A second file/struct pair the orphan must NOT land near, so a
    # coincidental fallback-ring placement can't pass this test by accident.
    _add_file(g, "dir_a", "file_b", "b.c")
    g.add_node("struct_b", depth=2, label="StructB", line=1)
    g.add_edge("file_b", "struct_b", **make_edge("contains"))

    # Deeply-nested field with no containment edge at all to any symbol --
    # only a bare-stem 'file' attribute to go on, exactly as c_parser.py
    # emits for real anonymous-union/struct fields.
    g.add_node("orphan_field", depth=3, label="field", line=2, file="a")

    pos = compound_layout(g)
    sx, sy = pos["struct_a"]
    bx, by = pos["struct_b"]

    dist_to_a = math.hypot(pos["orphan_field"][0] - sx, pos["orphan_field"][1] - sy)
    dist_to_b = math.hypot(pos["orphan_field"][0] - bx, pos["orphan_field"][1] - by)
    assert dist_to_a < dist_to_b


def test_compound_layout_single_directory_is_centered():
    g = nx.DiGraph()
    _add_dir(g, "only_dir", "only")
    _add_file(g, "only_dir", "f0", "f0.py")
    pos = compound_layout(g)
    assert pos["only_dir"] == (0.0, 0.0)


def test_compound_layout_handles_empty_graph():
    g = nx.DiGraph()
    assert compound_layout(g) == {}
