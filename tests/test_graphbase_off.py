"""With graphbase off, asking whether it is on is answered, not a 404.

The front end asks `GET /db/` on every page. Unmounted, the route was a 404,
which a browser logs as an error -- on every page of every server that simply
does not use graphbase, so the one console error that was always there was the
one nobody read, and `demo-graph.spec.ts` failed on it wherever MongoDB was not
configured.
"""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(bool(os.getenv("MONGODB_URI")), reason="graphbase is on in this environment")
def test_off_is_an_answer():
    """Mutation: drop the route -- this is a 404 again and fails."""
    from codecarto.main import app

    resp = TestClient(app).get("/db/")
    assert resp.status_code == 200
    assert resp.json()["available"] is False
    assert "MONGODB_URI" in resp.json()["reason"]
    # Only the question is answered; the store's own routes stay unmounted.
    assert TestClient(app).get("/db/bookmarks").status_code == 404
