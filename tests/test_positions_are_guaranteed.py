"""Every graph this project serves arrives positioned, and the seam that keeps it so.

**WHY THIS FILE EXISTS.** The web application's streaming renderer has no force
simulation. When a node arrives without coordinates it falls back to placing it
on a ring by depth, with a one-shot collision nudge -- a real fallback, but not a
layout. That is an acceptable trade only while nothing actually reaches it, and
"nothing reaches it" is a claim about the backend that had never been checked.

`test_every_graph_route_is_positioned` is that check. It walks the routes that
answer in gJGF and asserts every node carries `x` and `y`. If a future route
builds a graph by hand and forgets to lay it out, this goes red here rather than
appearing as a ring of nodes in a browser nobody connects to a backend change.

`ensure_positions` is the one call such a route should make. Nothing calls it
yet, on purpose -- every current route reaches gJGF through
`GraphSerializer.serialize_to_gjgf`, which lays the graph out on the way past.
"""

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app
from codecarto.services.position_service import ensure_positions, is_positioned


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


# --- the seam ------------------------------------------------------------------


def _bare(*ids):
    """A gJGF document whose nodes carry no coordinates."""
    return {"nodes": {i: {"metadata": {"label": i}} for i in ids},
            "edges": [{"source": ids[0], "target": ids[1]}] if len(ids) > 1 else []}


def test_a_document_with_no_positions_gets_them():
    doc = _bare("a", "b", "c")
    assert not is_positioned(doc)

    ensure_positions(doc)

    assert is_positioned(doc)
    for node in doc["nodes"].values():
        assert isinstance(node["metadata"]["x"], float)
        assert isinstance(node["metadata"]["y"], float)


def test_a_position_the_caller_set_is_never_moved():
    """**THE FAILURE THIS FUNCTION EXISTS TO PREVENT RATHER THAN CAUSE.**

    Laying the whole document out whenever any node is short would move nodes a
    caller had deliberately placed. Only the gaps are filled.

    Mutation: lay out every node instead of `missing` and this fails.
    """
    doc = _bare("a", "b", "c")
    doc["nodes"]["a"]["metadata"].update(x=42.0, y=-17.0)

    ensure_positions(doc)

    assert doc["nodes"]["a"]["metadata"]["x"] == 42.0
    assert doc["nodes"]["a"]["metadata"]["y"] == -17.0
    assert is_positioned(doc)


def test_an_already_positioned_document_is_left_entirely_alone():
    """Idempotent, and cheap: a positioned document runs no layout at all.

    Mutation: drop the `if not missing` short-circuit and this fails, because
    the layout would replace coordinates that were already correct.
    """
    doc = _bare("a", "b")
    for i, node in enumerate(doc["nodes"].values()):
        node["metadata"].update(x=float(i), y=float(i))
    before = {k: dict(v["metadata"]) for k, v in doc["nodes"].items()}

    ensure_positions(doc)

    assert {k: dict(v["metadata"]) for k, v in doc["nodes"].items()} == before


def test_an_empty_graph_is_positioned_rather_than_pending():
    """Reporting an empty document as unpositioned would make `ensure_positions`
    lay out nothing and hand back the same document, which reads as work done."""
    assert is_positioned({"nodes": {}, "edges": []})


def test_a_list_shaped_nodes_map_is_refused_rather_than_guessed_at():
    """gJGF keys nodes by id. Normalising a list here would be inventing a
    convention this project does not emit, and inventing it silently."""
    with pytest.raises(TypeError, match="id-keyed"):
        ensure_positions({"nodes": [{"id": "a"}], "edges": []})


# --- the claim about the backend -----------------------------------------------


GJGF_ROUTES = [
    "/topology/gjgf",
    "/capabilities/gjgf",
    "/lexicon/c/graph",
    "/lexicon/python/graph",
]


@pytest.mark.parametrize("route", GJGF_ROUTES)
def test_every_graph_route_is_positioned(client, route):
    """**THE FRONTEND'S DEPTH-RING FALLBACK HAS NO BACKEND TRIGGER.**

    Asserted rather than assumed, and asserted per route so a failure names the
    one that regressed. A route answering anything but 200 fails here too: a
    broken route cannot be evidence that graphs arrive positioned.

    Mutation: strip `x` from one node in `serialize_to_gjgf` and this fails.
    """
    answer = client.get(route)
    assert answer.status_code == 200, f"{route} did not answer"

    graph = answer.json()["results"]["graph"]
    nodes = graph["nodes"]
    assert nodes, f"{route} returned no nodes, so it proves nothing"

    unplaced = [nid for nid, n in nodes.items()
                if "x" not in n.get("metadata", n) or "y" not in n.get("metadata", n)]
    assert not unplaced, (
        f"{route} served {len(unplaced)} of {len(nodes)} nodes without "
        f"coordinates; the streaming renderer would place them on a depth ring")
