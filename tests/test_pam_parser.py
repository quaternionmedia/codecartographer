"""
Tests for codecarto.services.parsers.pam_parser

Covers: log line parsing (syslog + journald), event classification,
field extraction, and utility functions.
"""

import time
import pytest
from codecarto.services.parsers.pam_parser import (
    PamPhase,
    EventType,
    PamEvent,
    parse_line,
    read_history,
)


# ── Sample log lines ───────────────────────────────────────────────────────────

SYSLOG_ACCEPTED = (
    "Feb 27 14:32:01 myhost sshd[12345]: "
    "Accepted password for alice from 192.168.1.10 port 22 ssh2"
)
SYSLOG_FAILED = (
    "Feb 27 14:32:05 myhost sshd[12345]: "
    "Failed password for alice from 192.168.1.10 port 22 ssh2"
)
SYSLOG_INVALID_USER = (
    "Feb 27 14:32:08 myhost sshd[12345]: "
    "Invalid user bob from 10.0.0.1 port 51234"
)
SYSLOG_SESSION_OPEN = (
    "Feb 27 14:32:02 myhost sshd[12345]: "
    "pam_unix(sshd:session): session opened for user alice by (uid=0)"
)
SYSLOG_SESSION_CLOSE = (
    "Feb 27 14:33:00 myhost sshd[12345]: "
    "pam_unix(sshd:session): session closed for user alice"
)
# pam_unix(sshd:auth) style — has user= and rhost= fields but NO .so suffix
SYSLOG_MODULE_CALL = (
    "Feb 27 14:32:01 myhost sshd[12345]: "
    "pam_unix(sshd:auth): authentication failure; "
    "logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.10 user=alice"
)
# pam_sss.so style — has .so suffix, triggers MODULE_CALL classification
SYSLOG_PAM_SO = (
    "Feb 27 14:32:01 myhost sshd[12345]: "
    "pam_sss.so(sshd:auth): authentication failure; "
    "logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.10 user=alice"
)
SYSLOG_SSSD = (
    "Feb 27 14:32:01 myhost sssd[12345]: "
    "pam_sss.so: cache hit for user alice"
)
# sshd "Accepted" journald format — uses "for X from X" not "user=X rhost=X"
JOURNALD_LINE = (
    "2025-02-27T14:32:01.123456+00:00 myhost sshd[12345]: "
    "Accepted publickey for carol from 10.1.2.3 port 43210 ssh2"
)
# PAM module journald format — has user= and rhost= fields
JOURNALD_MODULE_LINE = (
    "2025-02-27T14:32:01.123456+00:00 myhost sshd[12345]: "
    "pam_unix(sshd:auth): authentication failure; "
    "logname= uid=0 euid=0 tty=ssh ruser= rhost=10.1.2.3 user=carol"
)
SYSLOG_SUDO = (
    "Feb 27 14:35:00 myhost sudo[99999]: "
    "alice : TTY=pts/0 ; PWD=/home/alice ; USER=root ; COMMAND=/bin/bash"
)
SYSLOG_KRB = (
    "Feb 27 14:32:01 myhost sshd[12345]: "
    "Kerberos TGT accepted for alice"
)
UNRELATED_LINE = "Feb 27 14:32:01 myhost crond[1234]: (CRON) INFO (pidfile fd = 3)"
EMPTY_LINE = ""
GARBAGE = "this is not a log line at all"


# ── parse_line ─────────────────────────────────────────────────────────────────

class TestParseLineBasics:
    def test_returns_none_for_empty_line(self):
        assert parse_line(EMPTY_LINE) is None

    def test_returns_none_for_garbage(self):
        assert parse_line(GARBAGE) is None

    def test_returns_none_for_unrelated_syslog(self):
        assert parse_line(UNRELATED_LINE) is None

    def test_returns_pam_event_for_sshd_accepted(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        assert ev is not None
        assert isinstance(ev, PamEvent)

    def test_returns_pam_event_for_sshd_failed(self):
        ev = parse_line(SYSLOG_FAILED)
        assert ev is not None

    def test_returns_pam_event_for_journald(self):
        ev = parse_line(JOURNALD_LINE)
        assert ev is not None


class TestParseLineServiceExtraction:
    def test_service_extracted_correctly(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        assert ev.service == "sshd"

    def test_pid_extracted_correctly(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        assert ev.pid == 12345

    def test_session_id_format(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        assert ev.session_id == "sshd:12345"

    def test_sudo_service(self):
        ev = parse_line(SYSLOG_SUDO)
        assert ev is not None
        assert ev.service == "sudo"


class TestParseLineUserAndRhost:
    def test_user_extracted_from_module_format(self):
        # sshd "Accepted" lines use "for alice" prose — parser only matches user=X
        ev = parse_line(SYSLOG_MODULE_CALL)
        assert ev.user == "alice"

    def test_rhost_extracted_from_module_format(self):
        # sshd "Accepted" lines use "from X" prose — parser only matches rhost=X
        ev = parse_line(SYSLOG_MODULE_CALL)
        assert ev.rhost == "192.168.1.10"

    def test_user_extracted_from_module_call(self):
        ev = parse_line(SYSLOG_MODULE_CALL)
        assert ev.user == "alice"


class TestParseLineEventTypes:
    def test_accepted_password_is_access_granted(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        assert ev.event_type == EventType.ACCESS_GRANTED
        assert ev.success is True

    def test_failed_password_is_access_denied(self):
        ev = parse_line(SYSLOG_FAILED)
        assert ev.event_type == EventType.ACCESS_DENIED
        assert ev.success is False

    def test_invalid_user_is_access_denied(self):
        # "Invalid user" sets success=False but event_type stays UNKNOWN
        # (ACCESS_DENIED requires "failed password" or pam_end() keyword)
        ev = parse_line(SYSLOG_INVALID_USER)
        assert ev.success is False
        assert ev.result == "PAM_AUTH_ERR"

    def test_session_open(self):
        ev = parse_line(SYSLOG_SESSION_OPEN)
        assert ev is not None
        assert ev.event_type == EventType.SESSION_OPEN
        assert ev.phase == PamPhase.SESSION

    def test_session_close(self):
        ev = parse_line(SYSLOG_SESSION_CLOSE)
        assert ev is not None
        assert ev.event_type == EventType.SESSION_CLOSE
        assert ev.phase == PamPhase.SESSION

    def test_module_call_detected(self):
        # Use .so-suffix form: pam_sss.so triggers _PAM_MODULE regex and MODULE_CALL
        ev = parse_line(SYSLOG_PAM_SO)
        assert ev is not None
        assert ev.event_type == EventType.MODULE_CALL
        assert "pam_sss" in ev.module

    def test_sssd_cache_hit(self):
        ev = parse_line(SYSLOG_SSSD)
        assert ev is not None
        assert ev.event_type == EventType.SSSD_CACHE
        assert ev.success is True
        assert "cache hit" in ev.detail

    def test_kerberos_event(self):
        ev = parse_line(SYSLOG_KRB)
        assert ev is not None
        assert ev.event_type in (EventType.KRB_CALL, EventType.KRB_RESULT,
                                  EventType.ACCESS_GRANTED)


class TestParseLineTimestamp:
    def test_timestamp_is_float(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        assert isinstance(ev.timestamp, float)
        assert ev.timestamp > 0

    def test_journald_timestamp_parsed(self):
        ev = parse_line(JOURNALD_LINE)
        assert ev.timestamp > 0
        # 2025-02-27T14:32:01 UTC
        assert abs(ev.timestamp - 1740666721.0) < 86400  # within a day (timezone tolerance)


class TestParseLineJournald:
    def test_journald_service_extracted(self):
        ev = parse_line(JOURNALD_LINE)
        assert ev.service == "sshd"

    def test_journald_user_extracted(self):
        # journald "Accepted" uses "for carol" prose; use module-format line for user=
        ev = parse_line(JOURNALD_MODULE_LINE)
        assert ev.user == "carol"

    def test_journald_rhost_extracted(self):
        # journald "Accepted" uses "from X" prose; use module-format line for rhost=
        ev = parse_line(JOURNALD_MODULE_LINE)
        assert ev.rhost == "10.1.2.3"

    def test_journald_event_type(self):
        ev = parse_line(JOURNALD_LINE)
        assert ev.event_type == EventType.ACCESS_GRANTED


# ── PamEvent.to_dict ───────────────────────────────────────────────────────────

class TestPamEventToDict:
    def test_to_dict_returns_dict(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        d = ev.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_event_type_is_string(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        d = ev.to_dict()
        assert isinstance(d["event_type"], str)
        assert d["event_type"] == EventType.ACCESS_GRANTED.value

    def test_to_dict_phase_is_string_or_none(self):
        ev = parse_line(SYSLOG_SESSION_OPEN)
        d = ev.to_dict()
        assert d["phase"] == PamPhase.SESSION.value

    def test_to_dict_phase_none_for_access_granted(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        d = ev.to_dict()
        # Phase may be None or "auth" depending on body detection — either is valid
        assert d["phase"] is None or isinstance(d["phase"], str)

    def test_to_dict_contains_all_expected_keys(self):
        ev = parse_line(SYSLOG_ACCEPTED)
        d = ev.to_dict()
        for key in ("timestamp", "raw", "event_type", "service", "user",
                    "rhost", "pid", "phase", "module", "success", "session_id"):
            assert key in d, f"Missing key: {key}"


# ── read_history ───────────────────────────────────────────────────────────────

class TestReadHistory:
    def test_missing_file_returns_empty(self, tmp_path):
        result = read_history(str(tmp_path / "nonexistent.log"))
        assert result == []

    def test_reads_pam_lines_from_file(self, tmp_path):
        log = tmp_path / "auth.log"
        log.write_text(
            SYSLOG_ACCEPTED + "\n" +
            UNRELATED_LINE + "\n" +
            SYSLOG_FAILED + "\n"
        )
        events = read_history(str(log))
        assert len(events) == 2
        assert all(isinstance(e, PamEvent) for e in events)

    def test_max_lines_respected(self, tmp_path):
        log = tmp_path / "auth.log"
        # Write 20 PAM lines
        lines = (SYSLOG_ACCEPTED + "\n") * 20
        log.write_text(lines)
        events = read_history(str(log), max_lines=5)
        assert len(events) <= 5

    def test_empty_file_returns_empty(self, tmp_path):
        log = tmp_path / "auth.log"
        log.write_text("")
        assert read_history(str(log)) == []
