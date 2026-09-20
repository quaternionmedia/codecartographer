"""The palette routes, and the one that used to answer with the wrong thing.

**WHY THIS FILE EXISTS.** `palette_router` was the only router here with no test
of its own, and it was serving a placeholder: `/palette/custom` returned the
default palette for every id, at status 200, with no marker distinguishing that
from a real lookup. A stub that errors is found in a minute; a stub that
succeeds is found by whoever eventually trusts its output.
"""

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


def results(answer):
    return answer.json()["results"]


def test_the_default_palette_is_served(client):
    answer = client.get("/palette/default")
    assert answer.status_code == 200
    body = results(answer)
    assert body, "the default palette is a literal in plot_data.py; it cannot be empty"


def test_a_custom_palette_says_there_is_nowhere_to_keep_one(client):
    """**THE DEFECT THIS PINS.**

    The old answer was `DefaultPalette` — a complete, plausible palette — for
    any id at all. A caller could not tell a lookup that worked from a lookup
    that never happened.

    Mutation: return the default palette here and this fails.
    """
    answer = client.get("/palette/custom", params={"palette_id": "anything"})
    assert answer.status_code == 200, "the route works; the store is what is missing"

    body = results(answer)
    assert body["unavailable"] is True
    assert body["remedy"], "a caller told 'no' should be told what to do instead"
    assert "colors" not in body, "a palette shape here reads as a successful lookup"


def test_the_requested_id_is_echoed_back(client):
    """The one thing the placeholder never demonstrated: that the argument was
    read at all. Two different ids gave byte-identical responses.

    Mutation: drop `requested` from the payload and this fails.
    """
    first = results(client.get("/palette/custom", params={"palette_id": "alpha"}))
    second = results(client.get("/palette/custom", params={"palette_id": "beta"}))

    assert first["requested"] == "alpha"
    assert second["requested"] == "beta"
    assert first != second, "two different ids must not give identical answers"


def test_a_custom_palette_is_not_the_default_palette_wearing_a_label(client):
    """Cross-check against the route that does have something to serve.

    Mutation: make `/palette/custom` fall back to the default and this fails
    even if the `unavailable` marker is still present.
    """
    default = results(client.get("/palette/default"))
    custom = results(client.get("/palette/custom", params={"palette_id": "0"}))
    assert custom != default


def test_palette_id_is_required(client):
    """Without it the route would be a second spelling of `/palette/default`."""
    assert client.get("/palette/custom").status_code == 422
