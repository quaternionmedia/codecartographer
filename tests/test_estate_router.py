"""The liveness table, against seams that are there and seams that are not.

**NO REAL SERVER IS CONTACTED AND NO REAL FILE OUTSIDE `tmp_path` IS READ.**
Every probe is pointed at a fixture answer or at a path nothing holds. The table
is about telling four situations apart -- down, answering as something else,
answering too old, answering as itself -- and a suite that needed the real
estate up would only ever see the fourth.

The mutations run against this file, each seen red before the check was trusted:
`probe_harness` returning `ok=True` on a body with no `schema` turned the
identity test red; dropping a row from `survey` turned the every-seam test red;
making `caveat` return the all-live sentence for zero live rows turned the
caveat test red; `fetch` ignoring `remedy_404` turned the remedy test red; and
`probe_prose` accepting any 200 turned the prose impostor test red. Each was
restored and seen green again before the file was committed, against a tracked
copy -- the first attempt ran the ritual on an untracked file, `git checkout`
restored nothing, and three mutations stacked while the "restored" run reported
the same red as the mutated one.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codecarto.services import estate_service, qmcp_client
from codecarto.services.qmcp_client import Reach


def _down(path, base=None, remedy_404=None):
    return Reach(False, f"{base or 'http://127.0.0.1:0'}{path}",
                 problem="nothing is answering at http://127.0.0.1:0",
                 remedy="start it with `uv run qm dashboard --start harness`",
                 status=None)


# --- the harness probe: identity, not reachability ---------------------------

def test_harness_identified_by_its_encoding_document(monkeypatch):
    def answered(path, base=None, remedy_404=None):
        assert path == "/v1/topology/encoding"
        return Reach(True, "http://h/v1/topology/encoding",
                     {"schema": 1, "encoding": [{"channel": "line_weight",
                                                 "axis": "strength"}]},
                     status=200)
    monkeypatch.setattr(qmcp_client, "fetch", answered)
    found = estate_service.probe_harness()
    assert found.ok and found.schema == 1
    assert "encoding channel" in found.detail
    assert found.problem == ""


def test_something_else_on_the_harness_port_is_not_the_harness(monkeypatch):
    """A 200 with the wrong shape is reported as an impostor, not as up."""
    def other(path, base=None, remedy_404=None):
        return Reach(True, "http://h/v1/topology/encoding",
                     {"status": "ok", "message": "some other API"}, status=200)
    monkeypatch.setattr(qmcp_client, "fetch", other)
    found = estate_service.probe_harness()
    assert not found.ok
    assert "did not describe a topology encoding" in found.problem
    assert "qm dashboard" in found.remedy


def test_harness_down_carries_the_start_command(monkeypatch):
    monkeypatch.setattr(qmcp_client, "fetch", _down)
    found = estate_service.probe_harness()
    assert not found.ok
    assert "nothing is answering" in found.problem
    assert "--start harness" in found.remedy


# --- the corpus and overview probes: files, present or not --------------------

def test_corpus_absent_names_the_propagation(tmp_path):
    found = estate_service.probe_corpus(tmp_path)
    assert not found.ok
    assert "no capability registry" in found.problem
    assert "propagat" in found.remedy


def test_corpus_present_counts_its_declarations(tmp_path):
    registry = tmp_path / "ci" / "capability-registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "schema: 1\ncapabilities:\n  - id: a/b\n    phase: design\n"
        "  - id: c/d\n    phase: execution\n", encoding="utf-8")
    found = estate_service.probe_corpus(tmp_path)
    assert found.ok and found.schema == 1
    assert found.detail.startswith("2 capability")


def test_overview_absent_names_the_producer(tmp_path):
    found = estate_service.probe_overview(tmp_path / "overview.json")
    assert not found.ok
    assert "dossier overview --json" in found.remedy


def test_overview_present_reports_scope_and_sections(tmp_path):
    seam = tmp_path / "overview.json"
    seam.write_text(json.dumps({"schema": 1, "scope": "quaternionmedia",
                                "masthead": [], "sections": [
                                    {"title": "a", "rows": []},
                                    {"title": "b", "rows": []}]}),
                    encoding="utf-8")
    found = estate_service.probe_overview(seam)
    assert found.ok
    assert "quaternionmedia" in found.detail and "2 section" in found.detail


# --- the prose probe: a sibling server, asked what it is -----------------------

def test_prose_identified_by_its_health_document(monkeypatch):
    def answered(path, base=None, remedy_404=None):
        assert path == "/health" and base == estate_service.prose_base_url()
        return Reach(True, f"{base}{path}",
                     {"status": "ok", "message": "the reader is running"},
                     status=200)
    monkeypatch.setattr(qmcp_client, "fetch", answered)
    found = estate_service.probe_prose()
    assert found.ok and found.detail == "the reader is running"


def test_prose_down_names_its_own_start_command(monkeypatch):
    monkeypatch.setattr(qmcp_client, "fetch", _down)
    found = estate_service.probe_prose()
    assert not found.ok
    assert "--start prose" in found.remedy
    assert "--start harness" not in found.remedy


def test_prose_impostor_is_not_green(monkeypatch):
    def other(path, base=None, remedy_404=None):
        return Reach(True, f"{base}{path}", {"hello": "world"}, status=200)
    monkeypatch.setattr(qmcp_client, "fetch", other)
    found = estate_service.probe_prose()
    assert not found.ok and "did not describe itself" in found.problem


def test_prose_base_url_from_the_environment(monkeypatch):
    monkeypatch.setenv("LOOKSATWORDS_URL", "http://127.0.0.1:9/")
    assert estate_service.prose_base_url() == "http://127.0.0.1:9"


# --- fetch's remedy for a route the far side lacks ----------------------------

def _http_404(url, timeout=None):
    raise urllib.error.HTTPError(url.full_url, 404, "not found", {},
                                 io.BytesIO(b'{"detail": "no such route"}'))


def test_fetch_404_remedy_is_the_harness_sentence_by_default(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _http_404)
    reach = qmcp_client.fetch("/v1/topology", base="http://127.0.0.1:0")
    assert not reach.ok and reach.status == 404
    assert "predates the topology routes" in reach.remedy


def test_fetch_404_remedy_can_be_the_callers(monkeypatch):
    """A prose reader without /health must not be told to index an archive."""
    monkeypatch.setattr(urllib.request, "urlopen", _http_404)
    reach = qmcp_client.fetch("/health", base="http://127.0.0.1:0",
                              remedy_404="this build does not answer /health")
    assert reach.remedy == "this build does not answer /health"
    assert "no such route" in reach.problem


# --- the table ----------------------------------------------------------------

def _all_down(monkeypatch, tmp_path):
    monkeypatch.setattr(qmcp_client, "fetch", _down)
    monkeypatch.setattr(estate_service.capability_service, "CORPUS",
                        tmp_path / "nowhere")
    monkeypatch.setenv(estate_service.overview_service.SEAM_ENV,
                       str(tmp_path / "no-overview.json"))


def test_every_seam_gets_a_row_even_when_nothing_is_up(monkeypatch, tmp_path):
    _all_down(monkeypatch, tmp_path)
    rows = estate_service.survey()
    assert [r["name"] for r in rows] == [s.name for s in estate_service.SEAMS]
    assert all(not r["ok"] for r in rows)
    # An absent seam says what would change that. Every one of them.
    assert all(r["problem"] and r["remedy"] for r in rows)
    assert "no seam identified itself" in estate_service.caveat(rows)


def test_caveat_distinguishes_all_some_and_none():
    live = {"ok": True}
    down = {"ok": False}
    assert "every seam identified itself" in estate_service.caveat([live, live])
    assert "1 of 2" in estate_service.caveat([live, down])
    assert "no seam identified itself" in estate_service.caveat([down])
    assert "no seams are declared" in estate_service.caveat([])


def test_a_seam_with_routes_and_no_panel_is_visible_as_such():
    """The table's reason to exist: the gap between served and drawn."""
    prose = estate_service.BY_NAME["prose"]
    assert prose.panel == ""
    for name in ("harness", "corpus", "overview"):
        assert estate_service.BY_NAME[name].panel.endswith("-panel")
        assert estate_service.BY_NAME[name].routes


def test_route_answers_200_with_the_absences_in_the_rows(monkeypatch, tmp_path):
    _all_down(monkeypatch, tmp_path)
    from codecarto.main import app

    answer = TestClient(app).get("/estate/seams")
    assert answer.status_code == 200
    body = answer.json()
    assert body["status"] == 200
    results = body["results"]
    assert results["live"] == 0
    assert len(results["seams"]) == len(estate_service.SEAMS)
    for row in results["seams"]:
        assert set(row) >= {"name", "role", "ok", "where", "problem", "remedy",
                            "routes", "panel", "detail", "schema"}
    assert results["caveat"]


def test_route_counts_the_live_ones(monkeypatch, tmp_path):
    _all_down(monkeypatch, tmp_path)
    registry = tmp_path / "corpus" / "ci" / "capability-registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text("schema: 1\ncapabilities: []\n", encoding="utf-8")
    monkeypatch.setattr(estate_service.capability_service, "CORPUS",
                        tmp_path / "corpus")
    from codecarto.main import app

    results = TestClient(app).get("/estate/seams").json()["results"]
    assert results["live"] == 1
    corpus = next(r for r in results["seams"] if r["name"] == "corpus")
    assert corpus["ok"] and corpus["detail"].startswith("0 capability")
    assert "1 of" in results["caveat"]
