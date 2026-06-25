"""
pam_parser.py — Parse PAM events from /var/log/auth.log (and equivalents)
Supports: syslog, journald export, sssd logs, audit.log
"""

import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Literal
from enum import Enum

# ─── Data models ─────────────────────────────────────────────────────────────

class PamPhase(str, Enum):
    AUTH = "auth"
    ACCOUNT = "account"
    SESSION = "session"
    PASSWORD = "password"
    RESULT = "result"

class EventType(str, Enum):
    PAM_START      = "pam_start"
    PAM_END        = "pam_end"
    MODULE_CALL    = "module_call"
    MODULE_RESULT  = "module_result"
    SSSD_CALL      = "sssd_call"
    SSSD_CACHE     = "sssd_cache"
    SSSD_RESULT    = "sssd_result"
    KRB_CALL       = "krb_call"
    KRB_RESULT     = "krb_result"
    NSS_CALL       = "nss_call"
    SESSION_OPEN   = "session_open"
    SESSION_CLOSE  = "session_close"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED  = "access_denied"
    UNKNOWN        = "unknown"

@dataclass
class PamEvent:
    timestamp: float          # unix epoch float
    raw: str                  # original log line
    event_type: EventType = EventType.UNKNOWN
    service: str = ""         # sshd, login, su, sudo …
    user: str = ""
    rhost: str = ""
    tty: str = ""
    pid: int = 0
    phase: Optional[PamPhase] = None
    module: str = ""          # pam_sss, pam_unix …
    control: str = ""         # required, sufficient …
    result: str = ""          # PAM_SUCCESS, PAM_AUTH_ERR …
    success: Optional[bool] = None
    detail: str = ""          # free-form extra info
    session_id: str = ""      # synthetic: service+pid key

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        d["phase"] = self.phase.value if self.phase else None
        return d


# ─── Regex patterns ───────────────────────────────────────────────────────────

# Syslog prefix: "Feb 27 14:32:01 hostname sshd[1234]:"
_SYSLOG_HDR = re.compile(
    r'^(?P<month>\w{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+'
    r'(?P<host>\S+)\s+(?P<service>\w[\w/-]*)\[(?P<pid>\d+)\]:\s+(?P<body>.+)$'
)

# journald: "2025-02-27T14:32:01.123456+00:00 hostname sshd[1234]: body"
_JOURNAL_HDR = re.compile(
    r'^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.\d]*[Z+\-\d:]*)\s+'
    r'(?P<host>\S+)\s+(?P<service>\w[\w/-]*)\[(?P<pid>\d+)\]:\s+(?P<body>.+)$'
)

# PAM sub-patterns (matched against body)
_PAM_MODULE    = re.compile(r'pam_(\w+)\.so', re.I)
_PAM_AUTH_OPEN = re.compile(r'pam_start\(\)', re.I)
_PAM_AUTH_DONE = re.compile(r'pam_end\(\)', re.I)
_PAM_USER      = re.compile(r'\buser[=\s](?P<u>\S+)', re.I)
_PAM_RHOST     = re.compile(r'\brhost[=\s](?P<h>\S+)', re.I)
_PAM_TTY       = re.compile(r'\btty[=\s](?P<t>\S+)', re.I)
_PAM_SUCCESS   = re.compile(r'PAM_SUCCESS|Accepted|succeeded|success', re.I)
_PAM_FAIL      = re.compile(r'PAM_(AUTH_ERR|ACCT_EXPIRED|CRED_ERR|USER_UNKNOWN|MAXTRIES|PERM_DENIED)'
                             r'|Failed|failure|authentication fail|Invalid user', re.I)
_PAM_OPEN_SES  = re.compile(r'session opened|pam_open_session', re.I)
_PAM_CLOSE_SES = re.compile(r'session closed|pam_close_session', re.I)

# SSSD
_SSSD_AUTH     = re.compile(r'sssd.*pam.*auth|pam.*sssd', re.I)
_SSSD_CACHE    = re.compile(r'cache\s*(hit|miss)', re.I)
_KRB_TGT       = re.compile(r'kerberos|krb5|TGT|AS-REQ|kinit', re.I)

# Phase detection from body
_PHASE_WORDS = {
    PamPhase.AUTH:     re.compile(r'\bauth(entication)?\b', re.I),
    PamPhase.ACCOUNT:  re.compile(r'\baccount\b', re.I),
    PamPhase.SESSION:  re.compile(r'\bsession\b', re.I),
    PamPhase.PASSWORD: re.compile(r'\bpassword\b', re.I),
}

# Month abbreviation → int
_MONTHS = {m: i+1 for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}


# ─── Parser ───────────────────────────────────────────────────────────────────

def _parse_syslog_ts(month: str, day: str, time_str: str) -> float:
    """Return unix epoch for syslog timestamp (assumes current year)."""
    import datetime
    now = datetime.datetime.now()
    mo = _MONTHS.get(month, now.month)
    dy = int(day)
    h, m, s = map(int, time_str.split(':'))
    try:
        dt = datetime.datetime(now.year, mo, dy, h, m, s)
    except ValueError:
        dt = now
    return dt.timestamp()


def parse_line(line: str) -> Optional[PamEvent]:
    """Parse a single log line into a PamEvent, or None if not PAM-related."""
    line = line.strip()
    if not line:
        return None

    # Try syslog format
    m = _SYSLOG_HDR.match(line)
    if m:
        ts = _parse_syslog_ts(m['month'], m['day'], m['time'])
        service = m['service'].split('(')[0].rstrip(':')  # strip pam wrapper suffixes
        pid = int(m['pid'])
        body = m['body']
    else:
        # Try journald format
        m2 = _JOURNAL_HDR.match(line)
        if m2:
            try:
                import datetime
                ts = datetime.datetime.fromisoformat(
                    m2['ts'].replace('Z', '+00:00')).timestamp()
            except Exception:
                ts = time.time()
            service = m2['service']
            pid = int(m2['pid'])
            body = m2['body']
        else:
            return None  # unrecognised format

    # Only process PAM-related lines
    pam_related = any([
        'pam' in body.lower(),
        'sssd' in service.lower() or 'sssd' in body.lower(),
        bool(_PAM_SUCCESS.search(body)),
        bool(_PAM_FAIL.search(body)),
        bool(_PAM_OPEN_SES.search(body)),
        bool(_PAM_CLOSE_SES.search(body)),
    ])
    if not pam_related and service not in ('sshd','login','su','sudo','gdm','lightdm','polkit'):
        return None

    ev = PamEvent(
        timestamp=ts,
        raw=line,
        service=service,
        pid=pid,
        session_id=f"{service}:{pid}",
    )

    # Extract common fields
    if u := _PAM_USER.search(body):
        ev.user = u['u'].rstrip(')')
    if r := _PAM_RHOST.search(body):
        ev.rhost = r['h']
    if t := _PAM_TTY.search(body):
        ev.tty = t['t']

    # Detect module
    if mod := _PAM_MODULE.search(body):
        ev.module = 'pam_' + mod.group(1) + '.so'

    # Detect phase
    for phase, pat in _PHASE_WORDS.items():
        if pat.search(body):
            ev.phase = phase
            break

    # Classify event type
    if _PAM_AUTH_OPEN.search(body):
        ev.event_type = EventType.PAM_START
    elif _PAM_AUTH_DONE.search(body):
        ev.event_type = EventType.PAM_END
    elif _PAM_OPEN_SES.search(body):
        ev.event_type = EventType.SESSION_OPEN
        ev.phase = PamPhase.SESSION
    elif _PAM_CLOSE_SES.search(body):
        ev.event_type = EventType.SESSION_CLOSE
        ev.phase = PamPhase.SESSION
    elif _SSSD_CACHE.search(body):
        hit = 'hit' in body.lower()
        ev.event_type = EventType.SSSD_CACHE
        ev.detail = 'cache hit' if hit else 'cache miss'
        ev.success = hit
    elif 'sssd' in body.lower() or 'sssd' in service.lower():
        ev.event_type = EventType.SSSD_CALL if not _PAM_SUCCESS.search(body) and not _PAM_FAIL.search(body) else EventType.SSSD_RESULT
    elif _KRB_TGT.search(body):
        ev.event_type = EventType.KRB_CALL if 'request' in body.lower() or 'AS-REQ' in body else EventType.KRB_RESULT
    elif ev.module:
        ev.event_type = EventType.MODULE_CALL

    # Detect success / failure
    if _PAM_SUCCESS.search(body):
        ev.success = True
        ev.result = 'PAM_SUCCESS'
        if _PAM_AUTH_DONE.search(body) or 'granted' in body.lower() or 'accepted' in body.lower():
            ev.event_type = EventType.ACCESS_GRANTED
    elif _PAM_FAIL.search(body):
        ev.success = False
        ev.result = 'PAM_AUTH_ERR'
        if _PAM_AUTH_DONE.search(body) or 'failed password' in body.lower():
            ev.event_type = EventType.ACCESS_DENIED

    ev.detail = body
    return ev


# ─── File tailer ─────────────────────────────────────────────────────────────

import os

def tail_file(path: str, from_start: bool = False):
    """Generator: yield new lines appended to path (handles rotation)."""
    try:
        f = open(path, 'r', errors='replace')
    except PermissionError:
        raise PermissionError(f"Cannot read {path} — try: sudo chmod a+r {path}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Log file not found: {path}")

    if not from_start:
        f.seek(0, 2)  # seek to end

    inode = os.fstat(f.fileno()).st_ino

    while True:
        line = f.readline()
        if line:
            yield line
        else:
            time.sleep(0.1)
            # Check for log rotation
            try:
                new_inode = os.stat(path).st_ino
            except FileNotFoundError:
                new_inode = inode
            if new_inode != inode:
                f.close()
                try:
                    f = open(path, 'r', errors='replace')
                    inode = os.fstat(f.fileno()).st_ino
                except Exception:
                    pass


def read_history(path: str, max_lines: int = 5000) -> List[PamEvent]:
    """Read last N lines from log file and parse PAM events."""
    events = []
    try:
        with open(path, 'r', errors='replace') as f:
            lines = f.readlines()
        for line in lines[-max_lines:]:
            ev = parse_line(line)
            if ev:
                events.append(ev)
    except Exception as e:
        pass
    return events
