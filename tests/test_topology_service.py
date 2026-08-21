"""This window, against the payload the harness actually emits.

THE TESTS WORTH READING ARE THE FIRST TWO. Everything else here is arithmetic.
The first says an unmeasured edge is never drawn as a weak one; the second says
a measured zero is not filed with the unlooked-at. Both are the same mistake
seen from opposite sides, and both were possible in this file.

**THE VECTORS ARE THE REAL SHAPE.** `_payload` below is what
`qmcp.topology_view.as_payload` emits, copied rather than imported -- the two
repositories do not depend on each other, which is the seam this whole exercise
is about. A copy can go stale, so it is small, and `test_the_vector_still_looks
_like_the_contract` fails loudly if a field goes missing.
"""

from __future__ import annotations

import pytest

from codecarto.services.topology_service import (
    MAX_WIDTH,
    MEASURED_STYLE,
    MIN_WIDTH,
    UNMEASURED_STYLE,
    UNMEASURED_WIDTH,
    render,
)


def _payload(**over):
    """A view as the harness emits it, with two measured edges and one not."""
    found = {
        "topology": "delegation",
        "level": 1,
        "caption": "one agent per repository",
        "status": "measured",
        "marks": [],
        "boxes": [
            {"id": "subject", "label": "sweep", "kind": "input",
             "note": "", "count": None},
            {"id": "r0", "label": "dossier", "kind": "worker",
             "note": "qm/dossier", "count": None},
            {"id": "r1", "label": "qmcp", "kind": "worker",
             "note": "qm/qmcp", "count": None},
            {"id": "r2", "label": "rad", "kind": "worker",
             "note": "qm/rad", "count": None},
        ],
        "arrows": [
            {"from": "subject", "to": "r0", "label": "part-of", "kind": "flow",
             "weight": 0.9, "basis": "mentions"},
            {"from": "subject", "to": "r1", "label": "crosses", "kind": "flow",
             "weight": 0.2, "basis": "mentions"},
            {"from": "subject", "to": "r2", "label": "crosses", "kind": "flow",
             "weight": None, "basis": ""},
        ],
    }
    found.update(over)
    return found


# --- the two that matter ------------------------------------------------------


def test_an_unmeasured_edge_is_never_drawn_as_a_weak_one():
    """THE ONE THAT MATTERS.

    A null weight means nobody looked. A thin line means somebody looked and
    found little. Drawing the first as the second is a claim the data does not
    make, and it is the easiest mistake to make here because both end up near
    the bottom of a width scale.

    Mutation: default a missing weight to 0.0 and this fails.
    """
    view = render(_payload())
    unmeasured = [e for e in view.edges if not e.measured]

    assert len(unmeasured) == 1
    edge = unmeasured[0]
    assert edge.style == UNMEASURED_STYLE
    assert edge.width == UNMEASURED_WIDTH
    assert edge.weight is None
    # And it must not land on the strength scale at all, at either end.
    assert edge.width != MIN_WIDTH
    assert "not measured" in edge.title


def test_a_measured_zero_is_not_filed_with_the_unlooked_at():
    """THE OTHER ONE.

    Somebody measured this relation and found nothing there. That is a finding,
    and `if not weight` throws it away -- the classic falsiness bug, in the one
    place where the two values mean opposite things.

    Mutation: test `if not weight` instead of `is None` and this fails.
    """
    view = render(_payload(arrows=[
        {"from": "a", "to": "b", "label": "crosses", "kind": "flow",
         "weight": 0.0, "basis": "mentions"}]))

    edge = view.edges[0]
    assert edge.measured is True
    assert edge.style == MEASURED_STYLE
    assert edge.width == pytest.approx(MIN_WIDTH)
    assert view.unmeasured == 0
    assert "not measured" not in edge.title


# --- the channels carry the axes they were declared to carry ------------------


def test_strength_reaches_width_monotonically():
    view = render(_payload())
    measured = sorted((e for e in view.edges if e.measured),
                      key=lambda e: e.weight)
    widths = [e.width for e in measured]
    assert widths == sorted(widths)
    assert MIN_WIDTH <= widths[0] and widths[-1] <= MAX_WIDTH


def test_relation_kind_reaches_colour_and_strength_does_not():
    """A refusal is drawn a refusal however heavily travelled the path it
    forbids. Folding kind into strength would lose that."""
    view = render(_payload(arrows=[
        {"from": "a", "to": "b", "label": "x", "kind": "refusal",
         "weight": 0.95, "basis": "m"},
        {"from": "a", "to": "c", "label": "y", "kind": "flow",
         "weight": 0.95, "basis": "m"}]))

    colours = {e.target: e.colour for e in view.edges}
    assert colours["b"] != colours["c"], "kind must survive equal strength"


def test_box_kind_reaches_shape():
    shapes = {n["id"]: n["shape"] for n in render(_payload()).nodes}
    assert shapes["subject"] != shapes["r0"]


def test_the_encoding_is_read_rather_than_assumed():
    """The harness declares which channel carries which axis. A window that
    ignored the declaration would keep drawing an old contract.

    Mutation: ignore the `encoding` argument and this fails.
    """
    told_colour_carries_nothing = [
        {"channel": "line_colour", "axis": "unassigned", "scale": "categorical"}]
    view = render(_payload(arrows=[
        {"from": "a", "to": "b", "label": "x", "kind": "refusal",
         "weight": 0.5, "basis": "m"}]), encoding=told_colour_carries_nothing)

    assert view.edges[0].colour != "#e06c75", (
        "colour was applied for an axis the harness did not assign to it")


# --- what a reader is told ----------------------------------------------------


def test_the_caveat_says_how_much_of_the_picture_is_measured():
    view = render(_payload())
    assert view.measured == 2 and view.unmeasured == 1
    assert "2 of 3" in view.caveat()


def test_an_entirely_unmeasured_picture_says_so_rather_than_looking_weak():
    """Every line dashed is a different artefact from every line thin, and the
    difference must not be left to a reader counting."""
    view = render(_payload(arrows=[
        {"from": "a", "to": "b", "label": "x", "kind": "flow",
         "weight": None, "basis": ""}]))
    assert "none of the" in view.caveat()
    assert "says nothing about strength" in view.caveat()


def test_an_empty_payload_draws_nothing_rather_than_raising():
    view = render({})
    assert view.edges == [] and view.nodes == []
    assert view.caveat() == "nothing to draw"


def test_parallel_relations_to_one_address_all_survive_the_graph():
    """THE ONE THE DEMO FOUND.

    Three threads each finding a relation to the same delta is three
    observations, not one. `networkx.DiGraph` keeps one edge per ordered pair
    and replaces the rest without a word, so the graph showed one line where
    three were measured -- and the picture looked complete.

    Mutation: use `DiGraph` instead of `MultiDiGraph` and this fails.
    """
    pytest.importorskip("networkx")
    from codecarto.services.topology_service import as_graph

    view = render(_payload(
        boxes=[{"id": "subject", "label": "s", "kind": "input",
                "note": "", "count": None},
               {"id": "r0", "label": "the-work", "kind": "worker",
                "note": "owner/repo/delta/the-work", "count": None}],
        arrows=[{"from": "subject", "to": "r0", "label": "crosses",
                 "kind": "flow", "weight": 0.06, "basis": "mentions"},
                {"from": "subject", "to": "r0", "label": "part-of",
                 "kind": "flow", "weight": 0.17, "basis": "mentions"},
                {"from": "subject", "to": "r0", "label": "crosses",
                 "kind": "flow", "weight": 0.13, "basis": "mentions"}]))

    assert len(view.edges) == 3
    graph = as_graph(view)
    assert graph.number_of_edges() == 3, (
        "parallel observations were collapsed into one edge")
    labels = sorted(d["label"] for _, _, d in graph.edges(data=True))
    assert labels == ["crosses", "crosses", "part-of"]


# --- the seam -----------------------------------------------------------------


def test_the_vector_still_looks_like_the_contract():
    """The copied vector, checked for shape.

    This cannot notice that the harness renamed a field -- nothing here can
    import it. It notices that somebody edited the vector into something the
    contract never had, which is the failure mode a copied fixture actually has.
    """
    payload = _payload()
    assert set(payload) >= {"topology", "level", "caption", "status", "marks",
                            "boxes", "arrows"}
    for arrow in payload["arrows"]:
        assert set(arrow) == {"from", "to", "label", "kind", "weight", "basis"}
    for box in payload["boxes"]:
        assert set(box) == {"id", "label", "kind", "note", "count"}


def test_an_unrecognised_field_does_not_break_the_render():
    """The far side must be able to add a field without a release here."""
    payload = _payload()
    payload["arrows"][0]["confidence"] = 0.4
    payload["provenance"] = "somewhere new"
    assert len(render(payload).edges) == 3


def test_the_graph_carries_the_channels_through():
    networkx = pytest.importorskip("networkx")
    from codecarto.services.topology_service import as_graph

    graph = as_graph(render(_payload()))
    assert graph.number_of_nodes() == 4
    dashed = [d for _, _, d in graph.edges(data=True) if not d["measured"]]
    assert len(dashed) == 1 and dashed[0]["style"] == UNMEASURED_STYLE
    assert isinstance(networkx.get_edge_attributes(graph, "width"), dict)


# --- through this project's own pipeline ---------------------------------------


def test_the_graph_speaks_the_palettes_vocabulary():
    """A topology node carries `type` and `base`, so anything else in codecarto
    can restyle it without knowing what a topology is.

    Mutation: stop setting `base` and this fails.
    """
    from codecarto.services.topology_service import as_graph, render

    graph = as_graph(render(_payload()))
    for _, data in graph.nodes(data=True):
        assert data["type"] in {"Input", "Worker", "Gate", "Store", "Output"}
        assert data["base"].startswith("topology.")
        assert data["color"].startswith("#")


def test_the_measurement_is_not_called_weight_on_the_graph():
    """**`weight` IS NETWORKX'S.** Shortest-path layouts read it as a distance,
    and an unmeasured edge carries `None`, so `kamada_kawai_layout` raised
    comparing `None` with a float -- several frames below anything naming a
    topology.

    Mutation: name the attribute `weight` and this fails.
    """
    from codecarto.services.topology_service import as_graph, render

    graph = as_graph(render(_payload()))
    for _, _, data in graph.edges(data=True):
        assert "weight" not in data, "the harness's measurement shadows networkx's"
        assert "strength" in data


def test_a_topology_lays_out_with_a_shortest_path_layout():
    """The layout that broke. Unmeasured edges must not stop a graph being
    laid out at all."""
    pytest.importorskip("gravis")
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.topology_service import as_gjgf, render

    gjgf = as_gjgf(render(_payload()), PlotOptions(layout="Kamada Kawai"))
    assert len(gjgf["nodes"]) == 4
    for node in gjgf["nodes"].values():
        assert "x" in node["metadata"] and "y" in node["metadata"]


def test_parallel_readings_survive_the_serializer():
    """Three observations of one relation, through codecarto's own serializer.

    Mutation: build a `DiGraph` in `as_graph` and this fails.
    """
    pytest.importorskip("gravis")
    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.topology_service import as_gjgf, render

    view = render(_payload(arrows=[
        {"from": "subject", "to": "r0", "label": "crosses", "kind": "flow",
         "weight": 0.06, "basis": "m"},
        {"from": "subject", "to": "r0", "label": "part-of", "kind": "flow",
         "weight": 0.17, "basis": "m"},
        {"from": "subject", "to": "r0", "label": "crosses", "kind": "flow",
         "weight": 0.13, "basis": "m"}]))
    assert len(as_gjgf(view, PlotOptions())["edges"]) == 3


def test_the_metadata_carries_the_caveat_to_any_other_client():
    """A client rendering this gJGF elsewhere must be able to reach the
    sentence saying how much of the picture was measured."""
    from codecarto.services.topology_service import metadata, render

    view = render(_payload())
    found = metadata(view, {"source": "thread archive", "surveyed": 128})
    assert found["caveat"] == view.caveat()
    assert found["unmeasured"] == 1 and found["source"] == "thread archive"
