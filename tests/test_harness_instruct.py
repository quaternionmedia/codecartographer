"""`/harness/instructions`: an instruction typed in the window, relayed once.

The harness is stood in for at `urllib.request.urlopen`, below the client, so
each test runs the real route, the real service and the real `send`. The
window relays only for a request that stands on this machine; `standing` is
tested as a function and through the route.

Mutations each test was seen to fail under are named in its docstring.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest
from fastapi.testclient import TestClient

from codecarto.services import instruct_service, qmcp_client

HERE = ("127.0.0.1", 50000)


class Harness:
    """Stands at `urlopen`: records each request and answers as told."""

    def __init__(self, status: int = 201, body: dict | None = None,
                 error: Exception | None = None):
        self.status, self.error = status, error
        self.body = body if body is not None else {
            "id": "ins-1", "text": "draw the gallery", "project": "codecartographer",
            "status": "recorded", "source": "page"}
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if self.status >= 400:
            raise urllib.error.HTTPError(request.full_url, self.status, "refused", {},
                                         io.BytesIO(json.dumps(self.body).encode()))
        return _Answer(self.status, self.body)

    def sent(self) -> list[dict]:
        return [json.loads(r.data) for r in self.requests]


class _Answer:
    def __init__(self, status: int, body: dict):
        self.status, self._body = status, json.dumps(body).encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


@pytest.fixture
def harness(monkeypatch):
    stand_in = Harness()
    monkeypatch.setattr(urllib.request, "urlopen", stand_in)
    monkeypatch.delenv("QMCP_URL", raising=False)
    return stand_in


def window(client=HERE, base="http://127.0.0.1:2718") -> TestClient:
    from codecarto.main import app

    return TestClient(app, base_url=base, client=client)


def post(text="draw the gallery", project=None, headers=None, **where) -> dict:
    body = {"text": text} if project is None else {"text": text, "project": project}
    answer = window(**where).post("/harness/instructions", json=body, headers=headers or {})
    assert answer.status_code == 200
    return answer.json()["results"]


# --- what is sent ---------------------------------------------------------------

def test_an_instruction_is_relayed_once_with_page_as_its_way_in(harness):
    """Mutation: send `typed` as the source, and the harness's row says the
    instruction came from a terminal. Mutation: call `send` twice, and the
    harness holds two rows for one press."""
    results = post("  draw the gallery  ")
    assert harness.sent() == [{"text": "draw the gallery", "source": "page"}]
    (request,) = harness.requests
    assert request.get_method() == "POST"
    assert request.full_url == "http://127.0.0.1:3141/v1/instructions"
    assert request.get_header("Content-type") == "application/json"
    assert results["recorded"] is True
    assert results["instruction"] == harness.body


def test_a_stated_project_is_sent_and_a_blank_one_is_not(harness):
    """Mutation: always send `project`, and a blank field states the empty
    project instead of leaving the harness to read the text."""
    post(project="codecartographer")
    post(project="   ")
    assert [sent.get("project", "absent") for sent in harness.sent()] == [
        "codecartographer", "absent"]


def test_blank_text_is_refused_here_and_nothing_is_sent(harness):
    """Mutation: drop the blank test, and an empty instruction is posted."""
    results = post("   ")
    assert harness.requests == []
    assert results["refused"] is True and "blank" in results["problem"]
    assert "recorded" not in results


# --- what comes back ------------------------------------------------------------

def test_the_harnesss_refusal_is_shown_in_its_own_words(monkeypatch):
    """Mutation: report every failure as `unreachable`, and a refused
    instruction tells the reader to start a harness that is running."""
    stand_in = Harness(status=422, body={"detail": "text is too long"})
    monkeypatch.setattr(urllib.request, "urlopen", stand_in)
    results = post()
    assert results["refused"] is True and "unreachable" not in results
    assert "422" in results["problem"] and "text is too long" in results["problem"]
    assert results["where"].endswith("/v1/instructions")


def test_a_harness_that_is_not_running_is_unreachable_with_its_start_command(monkeypatch):
    """Mutation: report every failure as `refused`, and a harness that is down
    reads as one that said no."""
    stand_in = Harness(error=urllib.error.URLError("refused"))
    monkeypatch.setattr(urllib.request, "urlopen", stand_in)
    results = post()
    assert results["unreachable"] is True and "refused" not in results
    assert qmcp_client.START_COMMAND in results["remedy"]
    assert len(stand_in.requests) == 1, "a post is sent once and never retried"


def test_a_harness_without_the_route_says_so(monkeypatch):
    stand_in = Harness(status=404, body={"detail": "Not Found"})
    monkeypatch.setattr(urllib.request, "urlopen", stand_in)
    results = post()
    assert results["refused"] is True
    assert results["remedy"] == qmcp_client.LOOPBACK_ONLY


# --- who may send ---------------------------------------------------------------

@pytest.mark.parametrize("server, client, headers", [
    ("127.0.0.1", "127.0.0.1", {}),
    ("::1", "::1", {}),
    ("localhost", "127.0.0.1", {"Origin": "http://localhost:1234"}),
    ("127.0.0.1", "127.0.0.1", {"origin": "http://127.0.0.1:2718"}),
])
def test_a_request_from_this_machine_to_this_machine_stands(server, client, headers):
    assert instruct_service.standing(server, client, headers) == ""


@pytest.mark.parametrize("server, client, headers, said", [
    ("192.168.1.20", "127.0.0.1", {}, "an address other than this machine's own"),
    ("0.0.0.0", "127.0.0.1", {}, "an address other than this machine's own"),
    (None, "127.0.0.1", {}, "an address other than this machine's own"),
    ("127.0.0.1", "192.168.1.31", {}, "came from another machine"),
    ("127.0.0.1", None, {}, "came from another machine"),
    ("127.0.0.1", "127.0.0.1", {"X-Forwarded-For": "203.0.113.9"}, "passed through a proxy"),
    ("127.0.0.1", "127.0.0.1", {"Forwarded": "for=203.0.113.9"}, "passed through a proxy"),
    ("127.0.0.1", "127.0.0.1", {"X-Real-IP": "203.0.113.9"}, "passed through a proxy"),
    ("127.0.0.1", "127.0.0.1", {"Origin": "https://example.org"}, "not served from this machine"),
    ("127.0.0.1", "127.0.0.1", {"Origin": "null"}, "not served from this machine"),
])
def test_a_request_that_does_not_stand_is_told_why(server, client, headers, said):
    """Mutations, one per line: drop the server test; drop the client test;
    drop the forwarding headers; drop the origin test. Each lets through the
    request its lines name."""
    assert said in instruct_service.standing(server, client, headers)


@pytest.mark.parametrize("where, headers", [
    ({"client": ("192.168.1.31", 50000)}, {}),
    ({"base": "http://192.168.1.20:2718"}, {}),
    ({}, {"X-Forwarded-For": "203.0.113.9"}),
    ({}, {"Origin": "https://example.org"}),
])
def test_the_route_sends_nothing_for_a_request_that_does_not_stand(harness, where, headers):
    """Mutation: pass "" for `why` in the route, and a page on another site, or
    a device the window is shared to, writes to the harness."""
    results = post(headers=headers, **where)
    assert harness.requests == []
    assert results["refused"] is True and results["available"] is False
    assert "qmcp instruct" in results["remedy"]


def test_the_form_is_told_whether_an_instruction_is_taken(harness):
    """Mutation: answer `available` whatever `standing` said, and the form is
    offered where its press is refused."""
    here = window().get("/harness/instructions").json()["results"]
    assert here == {"available": True, "way_in": "page", "problem": "", "remedy": "",
                    "where": "/harness/instructions"}
    away = window(client=("192.168.1.31", 50000)).get("/harness/instructions").json()["results"]
    assert away["available"] is False and "another machine" in away["problem"]
    assert "qmcp instruct" in away["remedy"]
    assert harness.requests == [], "asking whether sends nothing"
