"""Tests for layout position generation.

Run: pytest tests/test_position_service.py
"""

import math

import networkx as nx
import pytest

from codecarto.models.custom_layouts.compound_layout import compound_layout
from codecarto.services.position_service import Positions


def test_registered_layouts_no_longer_include_dead_ones():
    names = Positions().get_layout_names()
    assert "arch_layout" not in names
    assert "cluster_layout" not in names
    assert "compound_layout" in names
    assert "sorted_square_layout" in names


def _add_dir(g: nx.DiGraph, dir_id: str, label: str) -> None:
    g.add_node(dir_id, depth=0, label=label)


def _add_file(g: nx.DiGraph, parent_dir: str, file_id: str, label: str) -> None:
    g.add_node(file_id, depth=1, label=label)
    g.add_edge(parent_dir, file_id, relation="contains")


def _add_symbol(g: nx.DiGraph, parent_file: str, sym_id: str, line: int) -> None:
    g.add_node(sym_id, depth=2, label=sym_id, line=line)
    g.add_edge(parent_file, sym_id, relation="contains")


def _dist(pos: dict, node: str) -> float:
    x, y = pos[node]
    return math.hypot(x, y)


def _lopsided_graph() -> nx.DiGraph:
    """One directory with a deep nested subtree; four small sibling dirs
    with a single, symbol-less file each."""
    g = nx.DiGraph()

    _add_dir(g, "dir_big", "big")
    _add_dir(g, "dir_big_sub", "big/sub")
    g.add_edge("dir_big", "dir_big_sub", relation="contains")
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


def test_compound_layout_single_directory_is_centered():
    g = nx.DiGraph()
    _add_dir(g, "only_dir", "only")
    _add_file(g, "only_dir", "f0", "f0.py")
    pos = compound_layout(g)
    assert pos["only_dir"] == (0.0, 0.0)


def test_compound_layout_handles_empty_graph():
    g = nx.DiGraph()
    assert compound_layout(g) == {}
