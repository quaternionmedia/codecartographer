"""
Tests for codecarto.routers.pam_router REST endpoints.

Uses FastAPI TestClient (sync). PAM startup is NOT called, so the background
thread and broadcast loop never start — safe for CI with no auth.log.

Module-level state (_recent_events, _sessions, _log_path, _log_available) is
patched directly via monkeypatch to control test fixtures.
"""

import pytest
from fastapi.testclient import TestClient

from codecarto.main import app
import codecarto.routers.pam_router as pam_router


@pytest.fixture()
def client():
    return TestClient(app)


# ─── /pam/status ─────────────────────────────────────────────────────────────

class TestPamStatus:
    def test_returns_200(self, client):
        resp = client.get("/pam/status")
        assert resp.status_code == 200

    def test_has_required_fields(self, client):
        data = client.get("/pam/status").json()
        for field in ("log_path", "log_available", "hostname"):
            assert field in data, f"Missing field: {field}"

    def test_log_available_is_bool(self, client):
        data = client.get("/pam/status").json()
        assert isinstance(data["log_available"], bool)

    def test_hostname_is_string(self, client):
        data = client.get("/pam/status").json()
        assert isinstance(data["hostname"], str)

    def test_recent_event_count_is_int(self, client):
        data = client.get("/pam/status").json()
        assert isinstance(data["recent_event_count"], int)


# ─── /pam/history ────────────────────────────────────────────────────────────

class TestPamHistory:
    def test_returns_503_when_no_log(self, client, monkeypatch):
        monkeypatch.setattr(pam_router, "_log_available", False)
        monkeypatch.setattr(pam_router, "_log_error", "no log")
        resp = client.get("/pam/history")
        assert resp.status_code == 503

    def test_503_includes_events_key(self, client, monkeypatch):
        monkeypatch.setattr(pam_router, "_log_available", False)
        monkeypatch.setattr(pam_router, "_log_error", "no log")
        data = client.get("/pam/history").json()
        assert "events" in data

    def test_minutes_param_accepted(self, client, monkeypatch):
        monkeypatch.setattr(pam_router, "_log_available", False)
        resp = client.get("/pam/history?minutes=60")
        assert resp.status_code == 503   # no log — but param was parsed fine (no 422)

    def test_minutes_too_large_rejected(self, client):
        resp = client.get("/pam/history?minutes=99999")
        assert resp.status_code == 422

    def test_minutes_zero_rejected(self, client):
        resp = client.get("/pam/history?minutes=0")
        assert resp.status_code == 422

    def test_minutes_1440_accepted(self, client, monkeypatch):
        monkeypatch.setattr(pam_router, "_log_available", False)
        resp = client.get("/pam/history?minutes=1440")
        assert resp.status_code == 503   # no log — but 1440 is within the allowed max


# ─── /pam/sessions ───────────────────────────────────────────────────────────

class TestPamSessions:
    def test_returns_200(self, client):
        resp = client.get("/pam/sessions")
        assert resp.status_code == 200

    def test_returns_list(self, client):
        data = client.get("/pam/sessions").json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_sessions_empty_when_no_data(self, client, monkeypatch):
        monkeypatch.setattr(pam_router, "_sessions", {})
        data = client.get("/pam/sessions").json()
        assert data["sessions"] == []

    def test_sessions_have_required_keys(self, client, monkeypatch):
        fake_events = [
            {"event_type": "pam_start", "service": "sshd", "user": "alice",
             "rhost": "10.0.0.1", "session_id": "s1", "timestamp": 1000.0},
            {"event_type": "access_granted", "service": "sshd", "user": "alice",
             "session_id": "s1", "timestamp": 1001.0},
        ]
        monkeypatch.setattr(pam_router, "_sessions", {"s1": fake_events})
        data = client.get("/pam/sessions").json()
        assert len(data["sessions"]) == 1
        sess = data["sessions"][0]
        for key in ("session_id", "service", "user", "event_count", "result"):
            assert key in sess, f"Missing key: {key}"

    def test_granted_session_has_correct_result(self, client, monkeypatch):
        fake_events = [
            {"event_type": "pam_start", "service": "sshd", "user": "alice",
             "session_id": "s2", "timestamp": 2000.0},
            {"event_type": "access_granted", "service": "sshd", "user": "alice",
             "session_id": "s2", "timestamp": 2001.0},
        ]
        monkeypatch.setattr(pam_router, "_sessions", {"s2": fake_events})
        data = client.get("/pam/sessions").json()
        assert data["sessions"][0]["result"] == "granted"

    def test_denied_session_has_correct_result(self, client, monkeypatch):
        fake_events = [
            {"event_type": "pam_start", "service": "sshd", "user": "bob",
             "session_id": "s3", "timestamp": 3000.0},
            {"event_type": "access_denied", "service": "sshd", "user": "bob",
             "session_id": "s3", "timestamp": 3001.0},
        ]
        monkeypatch.setattr(pam_router, "_sessions", {"s3": fake_events})
        data = client.get("/pam/sessions").json()
        assert data["sessions"][0]["result"] == "denied"


# ─── /pam/sessions/{session_id} ──────────────────────────────────────────────

class TestPamSessionById:
    def test_404_when_missing(self, client, monkeypatch):
        monkeypatch.setattr(pam_router, "_sessions", {})
        resp = client.get("/pam/sessions/nonexistent-id")
        assert resp.status_code == 404

    def test_404_includes_error_key(self, client, monkeypatch):
        monkeypatch.setattr(pam_router, "_sessions", {})
        data = client.get("/pam/sessions/nonexistent-id").json()
        assert "error" in data

    def test_returns_events_for_known_session(self, client, monkeypatch):
        fake_events = [
            {"event_type": "pam_start", "session_id": "s4", "timestamp": 4000.0},
        ]
        monkeypatch.setattr(pam_router, "_sessions", {"s4": fake_events})
        data = client.get("/pam/sessions/s4").json()
        assert "events" in data
        assert len(data["events"]) == 1
        assert data["session_id"] == "s4"


# ─── /pam/ui ─────────────────────────────────────────────────────────────────

class TestPamUi:
    def test_returns_html_or_404(self, client):
        resp = client.get("/pam/ui")
        # Either 200 HTML (frontend.html found) or 404 HTML (file missing)
        assert resp.status_code in (200, 404)
        assert "text/html" in resp.headers.get("content-type", "")

    def test_404_contains_helpful_message(self, client):
        resp = client.get("/pam/ui")
        if resp.status_code == 404:
            assert b"frontend.html" in resp.content or b"not found" in resp.content.lower()
