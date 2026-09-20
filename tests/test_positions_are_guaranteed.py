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

#: Routes that answer from this process alone, needing no separate service and
#: no submodule checkout. The rest may legitimately report that something they
#: depend on is absent, and a test that treated that as a failure would go red
#: for a reason unrelated to positioning.
#:
#: `/capabilities/gjgf` is deliberately not here. It reads the capability
#: registry from the `governance/qm` submodule, which `pytest.yml` checks out
#: with `submodules: false`, so on a runner the route honestly answers
#: `unreadable` and draws nothing -- the contract `test_capability_router.py`
#: asserts. Listing it here made this a test of the author's working copy: green
#: where the submodule was present and red on CI where it was not.
SELF_CONTAINED = {"/lexicon/c/graph", "/lexicon/python/graph"}


def _graph_or_reason(answer) -> tuple[dict | None, str]:
    """The graph a route served, or why it served none.

    **A ROUTE MAY HONESTLY HAVE NO GRAPH TO GIVE.** `/topology/gjgf` reads a
    harness that is a separate process and usually is not running; it reports
    that as `unreachable` inside a 200, which is this project's convention and
    not a fault. An earlier version of this test read `["results"]["graph"]`
    directly and passed only while a harness happened to be up on the machine
    running it — the result described the tester's environment rather than the
    route.
    """
    results = answer.json().get("results")
    if not isinstance(results, dict):
        return None, f"results was {type(results).__name__}, not an object"
    if results.get("unreachable"):
        return None, str(results.get("problem", "reported unreachable"))
    if results.get("unreadable"):
        # `/capabilities/gjgf` reads a registry that lives in the governance
        # submodule; a checkout without it (CI's ordinary state) reports
        # `unreadable` and draws nothing, exactly as `unreachable` reports a
        # process that is not running. Both are honest no-graph answers.
        return None, str(results.get("problem", "reported unreadable"))
    graph = results.get("graph")
    if not isinstance(graph, dict):
        return None, "no `graph` in results, and neither `unreachable` nor `unreadable`"
    return graph, ""


def _unplaced(graph: dict) -> list[str]:
    nodes = graph.get("nodes") or {}
    return [nid for nid, n in nodes.items()
            if "x" not in n.get("metadata", n) or "y" not in n.get("metadata", n)]


@pytest.mark.parametrize("route", GJGF_ROUTES)
def test_every_graph_route_is_positioned(client, route):
    """**THE FRONTEND'S DEPTH-RING FALLBACK HAS NO BACKEND TRIGGER.**

    Asserted rather than assumed, and asserted per route so a failure names the
    one that regressed. Whenever a route serves a graph, every node in it
    carries coordinates. A route that serves no graph because a dependency is
    down is not evidence either way, and says so.

    Mutation: strip `x` from one node in `serialize_to_gjgf` and this fails.
    """
    answer = client.get(route)
    assert answer.status_code == 200, f"{route} did not answer"

    graph, reason = _graph_or_reason(answer)
    if graph is None:
        assert route not in SELF_CONTAINED, (
            f"{route} answers from this process alone and still served no graph: {reason}")
        pytest.skip(f"{route} served no graph: {reason}")

    nodes = graph.get("nodes") or {}
    assert nodes, f"{route} served a graph with no nodes, so it proves nothing"

    unplaced = _unplaced(graph)
    assert not unplaced, (
        f"{route} served {len(unplaced)} of {len(nodes)} nodes without "
        f"coordinates; the streaming renderer would place them on a depth ring")


def test_the_positioning_claim_is_not_vacuous(client):
    """**A SKIP IS NOT A PASS, AND A FILE OF SKIPS IS NOT EVIDENCE.**

    The test above skips a route whose dependency is down. If every route could
    skip, the whole claim would report green while checking nothing — so this
    asserts that at least one route actually served a positioned graph on this
    run. It is the assertion that makes the others mean something.

    Mutation: empty `SELF_CONTAINED` and point every route at a dead dependency,
    and this fails while the parametrized test above goes all-skip.
    """
    served = 0
    for route in GJGF_ROUTES:
        graph, _ = _graph_or_reason(client.get(route))
        if graph and (graph.get("nodes") or {}) and not _unplaced(graph):
            served += 1

    assert served, (
        "no route served a positioned graph on this run, so nothing here is "
        "evidence that graphs arrive positioned")
