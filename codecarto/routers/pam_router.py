"""
PAM Auth Visualizer Router
==========================
Integrates PAM log monitoring into the codecarto FastAPI app.

Endpoints (all under /pam prefix in main.py):
  GET  /status                  → log file status and system info
  GET  /history?minutes=30      → parsed PAM events from recent log history
  GET  /sessions                → list of captured authentication sessions
  GET  /sessions/{session_id}   → all events for a specific session
  GET  /ui                      → serve the PAM visualizer HTML frontend
  WS   /ws/live                 → real-time event stream from auth.log
  WS   /ws/replay?session_id=X  → replay a captured session at 3x speed

The log-tailer runs in a background thread (blocking I/O), and pushes
parsed events to an asyncio queue consumed by the broadcast loop.

Log file auto-detection order:
  /var/log/auth.log  (Debian/Ubuntu)
  /var/log/secure    (RHEL/Fedora/CentOS)
  /var/log/messages  (older distros)
  /var/log/syslog    (generic fallback)

Override with PAM_LOG_FILE environment variable.
Set PAM_USE_JOURNALD=1 to use journalctl instead.
"""

import asyncio
import json
import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse

from codecarto.services.parsers.pam_parser import parse_line, read_history, tail_file

PamRouter = APIRouter()

# ─── Log file detection ───────────────────────────────────────────────────────

_CANDIDATE_LOGS = [
    '/var/log/auth.log',
    '/var/log/secure',
    '/var/log/messages',
    '/var/log/syslog',
]

_USE_JOURNALD = os.environ.get('PAM_USE_JOURNALD', '').lower() in ('1', 'true', 'yes')


def _detect_log_file() -> Optional[str]:
    env_path = os.environ.get('PAM_LOG_FILE')
    if env_path:
        return env_path
    for path in _CANDIDATE_LOGS:
        if os.path.isfile(path) and os.access(path, os.R_OK):
            return path
    return None


# ─── Module-level state ───────────────────────────────────────────────────────

_live_clients: Set[WebSocket] = set()
_sessions: Dict[str, List[dict]] = {}
_recent_events: List[dict] = []
_MAX_RECENT = 2000

_log_path: Optional[str] = None
_log_available: bool = False
_log_error: str = ""
_event_queue: Optional[asyncio.Queue] = None
_broadcast_task: Optional[asyncio.Task] = None


# ─── Journald helpers ─────────────────────────────────────────────────────────

def _journald_tail():
    """Yield lines from journalctl -f filtered for PAM-related services."""
    cmd = [
        'journalctl', '-f', '--output=short-iso', '--no-pager',
        '-u', 'sssd', '-u', 'ssh', '-u', 'sshd',
        '_COMM=sshd', '_COMM=login', '_COMM=su', '_COMM=sudo',
    ]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1,
        )
        for line in proc.stdout:
            yield line
    except FileNotFoundError:
        pass


def _journald_history(minutes: int = 30) -> List[str]:
    since = f"{minutes} minutes ago"
    cmd = [
        'journalctl', '--output=short-iso', '--no-pager',
        '--since', since,
        '-u', 'sssd', '_COMM=sshd', '_COMM=login', '_COMM=su', '_COMM=sudo',
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.splitlines()
    except Exception:
        return []


# ─── Background worker threads ────────────────────────────────────────────────

def _tail_thread(log_path: str, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """Tail log file in a thread; push parsed events to async queue."""
    try:
        for line in tail_file(log_path, from_start=False):
            ev = parse_line(line)
            if ev:
                asyncio.run_coroutine_threadsafe(queue.put(ev.to_dict()), loop)
    except Exception as exc:
        asyncio.run_coroutine_threadsafe(queue.put({'__error__': str(exc)}), loop)


def _journald_thread(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """Stream journald in a thread; push parsed events to async queue."""
    for line in _journald_tail():
        ev = parse_line(line)
        if ev:
            asyncio.run_coroutine_threadsafe(queue.put(ev.to_dict()), loop)


# ─── Broadcast loop ───────────────────────────────────────────────────────────

async def _broadcast_loop(queue: asyncio.Queue):
    """Consume events from queue, store in ring buffer + sessions, broadcast."""
    global _recent_events, _sessions
    while True:
        try:
            ev_dict = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue

        if '__error__' in ev_dict:
            msg = json.dumps({'type': 'error', 'message': ev_dict['__error__']})
            for ws in list(_live_clients):
                try:
                    await ws.send_text(msg)
                except Exception:
                    _live_clients.discard(ws)
            continue

        _recent_events.append(ev_dict)
        if len(_recent_events) > _MAX_RECENT:
            _recent_events = _recent_events[-_MAX_RECENT:]

        sid = ev_dict.get('session_id', '')
        if sid:
            if sid not in _sessions:
                _sessions[sid] = []
            _sessions[sid].append(ev_dict)
            if len(_sessions) > 500:
                oldest = next(iter(_sessions))
                del _sessions[oldest]

        msg = json.dumps({'type': 'event', 'data': ev_dict})
        dead: Set[WebSocket] = set()
        for ws in list(_live_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        _live_clients -= dead


# ─── Startup hook (called from main.py) ──────────────────────────────────────

async def on_pam_startup():
    """Start log-tailer thread and broadcast loop. Call from app startup."""
    global _log_path, _log_available, _log_error, _event_queue, _broadcast_task

    _event_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    if _USE_JOURNALD:
        t = threading.Thread(
            target=_journald_thread, args=(_event_queue, loop), daemon=True
        )
        t.start()
        _log_available = True
        _log_path = "journald"
    else:
        _log_path = _detect_log_file()
        if _log_path:
            _log_available = True
            t = threading.Thread(
                target=_tail_thread, args=(_log_path, _event_queue, loop), daemon=True
            )
            t.start()
        else:
            _log_available = False
            _log_error = (
                "No readable auth log found. "
                "Set PAM_LOG_FILE env var or PAM_USE_JOURNALD=1."
            )

    _broadcast_task = asyncio.create_task(_broadcast_loop(_event_queue))


# ─── REST endpoints ───────────────────────────────────────────────────────────

@PamRouter.get("/status")
async def pam_status():
    return JSONResponse({
        "log_path":           _log_path,
        "log_available":      _log_available,
        "log_error":          _log_error,
        "hostname":           platform.node(),
        "platform":           platform.system(),
        "recent_event_count": len(_recent_events),
        "session_count":      len(_sessions),
        "session_ids":        list(_sessions.keys())[-20:],
        "candidates_tried":   _CANDIDATE_LOGS,
    })


@PamRouter.get("/history")
async def pam_history(minutes: int = Query(default=30, ge=1, le=1440)):
    if not _log_available:
        return JSONResponse({"error": _log_error, "events": []}, status_code=503)

    cutoff = time.time() - minutes * 60

    if _USE_JOURNALD:
        lines = _journald_history(minutes)
        events = []
        for line in lines:
            ev = parse_line(line)
            if ev and ev.timestamp >= cutoff:
                events.append(ev.to_dict())
    else:
        all_events = read_history(_log_path, max_lines=10000)
        events = [e.to_dict() for e in all_events if e.timestamp >= cutoff]

    return JSONResponse({"events": events, "count": len(events)})


@PamRouter.get("/sessions")
async def pam_sessions():
    result = []
    for sid, evs in list(_sessions.items())[-50:]:
        if not evs:
            continue
        first, last = evs[0], evs[-1]
        granted = any(e.get('event_type') == 'access_granted' for e in evs)
        denied  = any(e.get('event_type') == 'access_denied'  for e in evs)
        result.append({
            "session_id":   sid,
            "service":      first.get('service'),
            "user":         first.get('user') or last.get('user'),
            "rhost":        first.get('rhost') or last.get('rhost'),
            "event_count":  len(evs),
            "start_ts":     first.get('timestamp'),
            "end_ts":       last.get('timestamp'),
            "result":       "granted" if granted else ("denied" if denied else "unknown"),
        })
    result.reverse()
    return JSONResponse({"sessions": result})


@PamRouter.get("/sessions/{session_id}")
async def pam_session_events(session_id: str):
    evs = _sessions.get(session_id)
    if evs is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return JSONResponse({"session_id": session_id, "events": evs})


@PamRouter.get("/ui")
async def pam_ui(request: Request):
    """Serve the PAM visualizer HTML frontend, with WS/API URLs patched for this server."""
    html_path = (
        Path(__file__).parent.parent.parent
        / ".github" / "development" / "chrestromathy_branch" / "frontend.html"
    )
    if not html_path.exists():
        return HTMLResponse(
            "<h1>PAM Visualizer frontend not found</h1>"
            "<p>Expected at: chrestromathy_branch/frontend.html</p>",
            status_code=404,
        )

    # Determine server base URLs from the incoming request so the HTML works
    # regardless of which host/port codecarto is running on.
    http_base = str(request.base_url).rstrip('/')          # e.g. http://localhost:8000
    ws_base   = http_base.replace('http://', 'ws://', 1).replace('https://', 'wss://', 1)

    html = html_path.read_text(encoding='utf-8')

    # Patch WebSocket URLs (ws://localhost:8765/ws/... → ws://<host>/pam/ws/...)
    html = html.replace('ws://localhost:8765/ws/live',   f'{ws_base}/pam/ws/live')
    html = html.replace('ws://localhost:8765/ws/replay', f'{ws_base}/pam/ws/replay')

    # Patch apiBase config value used for REST calls before WS connects
    html = html.replace("'http://localhost:8765'", f"'{http_base}/pam'")

    return HTMLResponse(html)


# ─── /api/* aliases (used by the HTML frontend) ──────────────────────────────
# The PAM frontend.html calls /api/status, /api/history, /api/sessions.
# These aliases forward to the same handlers as the clean routes above.

@PamRouter.get("/api/status", include_in_schema=False)
async def pam_api_status():
    return await pam_status()


@PamRouter.get("/api/history", include_in_schema=False)
async def pam_api_history(minutes: int = Query(default=30, ge=1, le=1440)):
    return await pam_history(minutes)


@PamRouter.get("/api/sessions", include_in_schema=False)
async def pam_api_sessions():
    return await pam_sessions()


@PamRouter.get("/api/sessions/{session_id}", include_in_schema=False)
async def pam_api_session_events(session_id: str):
    return await pam_session_events(session_id)


# ─── WebSocket endpoints ──────────────────────────────────────────────────────

@PamRouter.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    _live_clients.add(ws)

    await ws.send_text(json.dumps({
        "type":          "connected",
        "log_path":      _log_path,
        "log_available": _log_available,
        "log_error":     _log_error,
        "hostname":      platform.node(),
    }))

    if _recent_events:
        await ws.send_text(json.dumps({
            "type":   "backfill",
            "events": _recent_events[-50:],
        }))

    try:
        while True:
            await asyncio.sleep(15)
            await ws.send_text(json.dumps({"type": "ping"}))
    except (WebSocketDisconnect, Exception):
        _live_clients.discard(ws)


@PamRouter.websocket("/ws/replay")
async def ws_replay(ws: WebSocket, session_id: str = Query(...)):
    await ws.accept()

    evs = _sessions.get(session_id)
    if not evs:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": f"Session '{session_id}' not found",
        }))
        await ws.close()
        return

    await ws.send_text(json.dumps({
        "type": "replay_start",
        "session_id": session_id,
        "total": len(evs),
    }))

    t0 = evs[0]['timestamp']
    wall0 = time.time()

    for ev in evs:
        target_offset = min(ev['timestamp'] - t0, 30) / 3.0  # 3x speed
        elapsed = time.time() - wall0
        wait = target_offset - elapsed
        if wait > 0:
            await asyncio.sleep(min(wait, 3.0))
        try:
            await ws.send_text(json.dumps({"type": "event", "data": ev}))
        except Exception:
            break

    try:
        await ws.send_text(json.dumps({"type": "replay_end", "session_id": session_id}))
    except Exception:
        pass
