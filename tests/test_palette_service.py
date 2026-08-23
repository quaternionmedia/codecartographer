"""The palette, actually deciding something.

**THE PALETTE WAS DECLARED AND UNUSED.** `Palette` has carried `bases`,
`labels`, `alphas`, `sizes`, `shapes` and `colors` for as long as it has
existed, and nothing on the rendering path read any of them: sizes came from an
edge-count heuristic and colours from two hard-coded names in the dependency
branch. A palette could be edited, saved and selected without changing a pixel.

THE TEST WORTH READING IS THE FIRST: the dotted base is a hierarchy, and that
hierarchy is the whole reason a palette can be coarse. If nothing walks it, an
author must enumerate every leaf or get grey.
"""

from __future__ import annotations

import pytest

from codecarto.models.plot_data import DefaultPalette, Palette
from codecarto.services import palette_service
from codecarto.services.palette_service import (
    MARKER_TO_SHAPE,
    UNKNOWN,
    ancestry,
    base_for,
    style_for,
    style_for_type,
)


# --- the hierarchy -------------------------------------------------------------


def test_a_base_inherits_from_the_base_it_is_a_kind_of():
    """THE ONE THAT MATTERS.

    `control.cond.if` is a kind of `control.cond`, which is a kind of
    `control`. A palette naming a colour for `control` has said what colour an
    `if` is, and resolution has to walk leftwards for that to be true.

    Mutation: look up the exact base only and this fails.
    """
    palette = Palette(id="t", bases={}, labels={}, alphas={},
                      sizes={}, shapes={}, colors={"control": "orange",
                                                   UNKNOWN: "gray"})
    assert style_for("control.cond.if", palette).color == "orange"
    assert style_for("control.cond.if", palette).base == "control"


def test_ancestry_is_most_specific_first_and_ends_at_unknown():
    assert ancestry("a.b.c") == ["a.b.c", "a.b", "a", UNKNOWN]
    assert ancestry("") == [UNKNOWN]
    assert ancestry(UNKNOWN) == [UNKNOWN]


def test_an_exact_entry_beats_an_ancestor():
    palette = Palette(id="t", bases={}, labels={}, alphas={}, sizes={},
                      shapes={}, colors={"a": "red", "a.b": "blue"})
    assert style_for("a.b", palette).color == "blue"


def test_a_base_nothing_names_resolves_to_unknown_rather_than_raising():
    """A graph with one node of an unrecognised type should still draw."""
    style = style_for("nothing.like.this")
    assert style.base == UNKNOWN
    assert style.inherited is True
    assert style.color


def test_a_type_the_palette_does_not_name_is_unknown():
    assert base_for("NoSuchNodeType") == UNKNOWN


# --- two vocabularies ----------------------------------------------------------


def test_matplotlib_markers_become_gravis_shapes():
    """The palette speaks markers because matplotlib drew these first; the
    canvas names shapes. The translation lives in one place.

    Mutation: pass the marker through unchanged and this fails.
    """
    assert style_for_type("Worker").shape in {"circle", "rectangle", "hexagon"}
    assert MARKER_TO_SHAPE["o"] == "circle"
    assert MARKER_TO_SHAPE["^"] == "hexagon"


def test_every_marker_in_the_default_palette_translates():
    """A marker with no mapping silently becomes a circle, so every shape in
    the palette collapses to one and nobody sees why.

    Mutation: remove a marker from the table and this fails.
    """
    missing = {marker for marker in DefaultPalette.shapes.values()
               if marker not in MARKER_TO_SHAPE}
    assert not missing, f"markers with no gravis shape: {sorted(missing)}"


def test_the_marker_is_kept_beside_the_shape():
    """matplotlib is still a renderer here. Throwing the marker away to store
    the shape would make this service useless to it."""
    style = style_for_type("Gate")
    assert style.marker and style.shape != style.marker


# --- the topology vocabulary ---------------------------------------------------


def test_the_topology_kinds_are_in_the_palette():
    """A harness topology is drawn by this project's renderer, so it is
    described in this project's palette. A second styling table would be a
    second thing to keep in step."""
    for node_type, base in (("Input", "topology.input"),
                            ("Worker", "topology.worker"),
                            ("Gate", "topology.gate"),
                            ("Store", "topology.store"),
                            ("Output", "topology.output")):
        style = style_for_type(node_type)
        assert style.base == base, f"{node_type} resolved to {style.base}"
        assert style.color.startswith("#")


def test_topology_kinds_are_visually_distinct():
    """A gate is a gate at any size. Two kinds sharing a colour and a shape
    would make the encoding's `node_shape` channel carry nothing."""
    seen = {(s.color, s.shape) for s in
            (style_for_type(t) for t in
             ("Input", "Worker", "Gate", "Store", "Output"))}
    assert len(seen) >= 4, "the topology kinds are not distinguishable"


def test_a_topology_base_still_inherits():
    """`topology.gate` falls back to `topology` before `unknown`, so a palette
    may style the whole family in one entry."""
    assert ancestry("topology.gate") == ["topology.gate", "topology", UNKNOWN]


# --- applying it ---------------------------------------------------------------


def test_applying_a_palette_does_not_overwrite_what_something_else_decided():
    """A node already carrying a colour was coloured by something that knew
    more -- a dependency plot marking an external package. A styling pass that
    stamped over it would discard that silently.

    Mutation: always overwrite and this fails.
    """
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_node("a", type="Worker", color="red")
    graph.add_node("b", type="Worker")

    palette_service.apply_to(graph)
    assert graph.nodes["a"]["color"] == "red"
    assert graph.nodes["b"]["color"] == style_for_type("Worker").color


def test_overwriting_is_available_to_a_caller_who_means_it():
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_node("a", type="Worker", color="red")
    palette_service.apply_to(graph, overwrite=True)
    assert graph.nodes["a"]["color"] != "red"


def test_sizes_keep_their_relations_when_they_change_units():
    """The palette's sizes were chosen for matplotlib's area scale. Dividing
    keeps what an author chose -- that one kind is bigger than another -- and
    drops the units, which they did not choose."""
    big = style_for("topology.input").size
    small = style_for("topology.worker").size
    assert big > small
    assert small >= palette_service.MIN_SIZE
