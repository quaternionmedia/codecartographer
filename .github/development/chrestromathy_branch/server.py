"""
server.py — PAM Auth Visualizer backend
Serves:
  GET  /          → frontend HTML
  GET  /api/status → system info + log file status
  GET  /api/history?minutes=30  → parsed events from log history
  WS   /ws/live   → real-time tail of auth.log, broadcast parsed events
  WS   /ws/replay?session_id=X → replay a captured session

Usage:
  python server.py [--log /var/log/auth.log] [--port 8765] [--host 0.0.0.0]
"""

import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Local
sys.path.insert(0, str(Path(__file__).parent))
from pam_parser import parse_line, read_history, tail_file, PamEvent

# ─── CLI args (parsed at startup) ────────────────────────────────────────────
def get_args():
    p = argparse.ArgumentParser()
    p.add_argument('--log',  default=None, help='Path to auth log (auto-detected if omitted)')
    p.add_argument('--port', default=8765, type=int)
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--journald', action='store_true', help='Use journald instead of file')
    # Allow unknown args for uvicorn
    args, _ = p.parse_known_args()
    return args

ARGS = get_args()


# ─── Log file auto-detection ──────────────────────────────────────────────────

CANDIDATE_LOGS = [
    '/var/log/auth.log',          # Debian/Ubuntu
    '/var/log/secure',            # RHEL/Fedora/CentOS
    '/var/log/messages',          # Some older distros
    '/var/log/syslog',            # Generic fallback
]

def detect_log_file() -> Optional[str]:
    if ARGS.log:
        return ARGS.log
    for path in CANDIDATE_LOGS:
        if os.path.isfile(path) and os.access(path, os.R_OK):
            return path
    return None


# ─── Journald reader ─────────────────────────────────────────────────────────

def journald_tail():
    """Yield lines from journalctl -f --output=short-iso filtered for PAM."""
    cmd = ['journalctl', '-f', '--output=short-iso', '--no-pager',
           '-u', 'sssd', '-u', 'ssh', '-u', 'sshd', '_COMM=sshd',
           '_COMM=login', '_COMM=su', '_COMM=sudo']
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, bufsize=1)
        for line in proc.stdout:
            yield line
    except FileNotFoundError:
        # journalctl not available, fall back to file
        pass

def journald_history(minutes: int = 30) -> List[str]:
    since = f"{minutes} minutes ago"
    cmd = ['journalctl', '--output=short-iso', '--no-pager',
           '--since', since, '-u', 'sssd', '_COMM=sshd', '_COMM=login',
           '_COMM=su', '_COMM=sudo']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.splitlines()
    except Exception:
        return []


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="PAM Visualizer")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Connected WS clients (live mode)
_live_clients: Set[WebSocket] = set()

# Event store for replay (session_id → list of events)
_sessions: Dict[str, List[dict]] = {}

# Ring buffer of recent events (up to 2000)
_recent_events: List[dict] = []
_MAX_RECENT = 2000


# ─── Background tailer task ───────────────────────────────────────────────────

_log_path: Optional[str] = None
_log_available: bool = False
_log_error: str = ""
_tail_task: Optional[asyncio.Task] = None
_event_queue: asyncio.Queue = asyncio.Queue()


def _tail_thread(log_path: str, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """Run in a thread: tail log file and push parsed events to async queue."""
    try:
        for line in tail_file(log_path, from_start=False):
            ev = parse_line(line)
            if ev:
                asyncio.run_coroutine_threadsafe(queue.put(ev.to_dict()), loop)
    except Exception as e:
        asyncio.run_coroutine_threadsafe(
            queue.put({'__error__': str(e)}), loop)


def _journald_thread(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    for line in journald_tail():
        ev = parse_line(line)
        if ev:
            asyncio.run_coroutine_threadsafe(queue.put(ev.to_dict()), loop)


async def _broadcast_loop():
    """Consume events from queue, store, and broadcast to WS clients."""
    global _recent_events, _sessions
    while True:
        try:
            ev_dict = await asyncio.wait_for(_event_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue

        if '__error__' in ev_dict:
            # Broadcast error
            msg = json.dumps({'type': 'error', 'message': ev_dict['__error__']})
            for ws in list(_live_clients):
                try:
                    await ws.send_text(msg)
                except Exception:
                    _live_clients.discard(ws)
            continue

        # Store in recent ring buffer
        _recent_events.append(ev_dict)
        if len(_recent_events) > _MAX_RECENT:
            _recent_events = _recent_events[-_MAX_RECENT:]

        # Store per-session for replay
        sid = ev_dict.get('session_id', '')
        if sid:
            if sid not in _sessions:
                _sessions[sid] = []
            _sessions[sid].append(ev_dict)
            # Keep last 500 sessions
            if len(_sessions) > 500:
                oldest = next(iter(_sessions))
                del _sessions[oldest]

        # Broadcast
        msg = json.dumps({'type': 'event', 'data': ev_dict})
        dead = set()
        for ws in list(_live_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        _live_clients -= dead


@app.on_event("startup")
async def startup():
    global _log_path, _log_available, _log_error, _tail_task

    loop = asyncio.get_event_loop()

    if ARGS.journald:
        t = threading.Thread(target=_journald_thread,
                             args=(_event_queue, loop), daemon=True)
        t.start()
        _log_available = True
        _log_path = "journald"
    else:
        _log_path = detect_log_file()
        if _log_path:
            _log_available = True
            t = threading.Thread(target=_tail_thread,
                                 args=(_log_path, _event_queue, loop), daemon=True)
            t.start()
        else:
            _log_available = False
            _log_error = (
                "No readable auth log found. Try one of:\n"
                "  sudo chmod a+r /var/log/auth.log\n"
                "  python server.py --log /var/log/secure\n"
                "  python server.py --journald"
            )

    asyncio.create_task(_broadcast_loop())


# ─── REST endpoints ───────────────────────────────────────────────────────────

@app.get("/api/status")
async def status():
    return JSONResponse({
        "log_path": _log_path,
        "log_available": _log_available,
        "log_error": _log_error,
        "hostname": platform.node(),
        "platform": platform.system(),
        "recent_event_count": len(_recent_events),
        "session_count": len(_sessions),
        "session_ids": list(_sessions.keys())[-20:],  # last 20
        "candidates_tried": CANDIDATE_LOGS,
    })


@app.get("/api/history")
async def history(minutes: int = Query(default=30, ge=1, le=1440)):
    """Return parsed PAM events from the last N minutes."""
    if not _log_available:
        return JSONResponse({"error": _log_error, "events": []}, status_code=503)

    cutoff = time.time() - minutes * 60

    if ARGS.journald:
        lines = journald_history(minutes)
        events = []
        for line in lines:
            ev = parse_line(line)
            if ev and ev.timestamp >= cutoff:
                events.append(ev.to_dict())
    else:
        all_events = read_history(_log_path, max_lines=10000)
        events = [e.to_dict() for e in all_events if e.timestamp >= cutoff]

    return JSONResponse({"events": events, "count": len(events)})


@app.get("/api/sessions")
async def sessions():
    """Return list of captured session IDs with summary info."""
    result = []
    for sid, evs in list(_sessions.items())[-50:]:
        if not evs:
            continue
        first, last = evs[0], evs[-1]
        granted = any(e.get('event_type') == 'access_granted' for e in evs)
        denied  = any(e.get('event_type') == 'access_denied' for e in evs)
        result.append({
            "session_id": sid,
            "service": first.get('service'),
            "user": first.get('user') or last.get('user'),
            "rhost": first.get('rhost') or last.get('rhost'),
            "event_count": len(evs),
            "start_ts": first.get('timestamp'),
            "end_ts": last.get('timestamp'),
            "result": "granted" if granted else ("denied" if denied else "unknown"),
        })
    result.reverse()  # newest first
    return JSONResponse({"sessions": result})


@app.get("/api/sessions/{session_id}")
async def session_events(session_id: str):
    """Return all events for a specific session."""
    evs = _sessions.get(session_id)
    if evs is None:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return JSONResponse({"session_id": session_id, "events": evs})


# ─── WebSocket endpoints ──────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    _live_clients.add(ws)

    # Send current status
    await ws.send_text(json.dumps({
        "type": "connected",
        "log_path": _log_path,
        "log_available": _log_available,
        "log_error": _log_error,
        "hostname": platform.node(),
    }))

    # Send last 50 recent events as backfill
    if _recent_events:
        await ws.send_text(json.dumps({
            "type": "backfill",
            "events": _recent_events[-50:]
        }))

    try:
        while True:
            # Keep connection alive; actual events pushed by broadcast loop
            await asyncio.sleep(15)
            await ws.send_text(json.dumps({"type": "ping"}))
    except (WebSocketDisconnect, Exception):
        _live_clients.discard(ws)


@app.websocket("/ws/replay")
async def ws_replay(ws: WebSocket, session_id: str = Query(...)):
    """Stream a captured session's events at realistic speed."""
    await ws.accept()

    evs = _sessions.get(session_id)
    if not evs:
        await ws.send_text(json.dumps({"type": "error", "message": f"Session {session_id} not found"}))
        await ws.close()
        return

    await ws.send_text(json.dumps({"type": "replay_start", "session_id": session_id, "total": len(evs)}))

    t0 = evs[0]['timestamp']
    wall0 = time.time()

    for ev in evs:
        # Real-time pacing (capped at 10x speed, max 3s gap)
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


# ─── Frontend HTML (inline) ───────────────────────────────────────────────────

@app.get("/")
async def root():
    html_path = Path(__file__).parent / "frontend.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text())
    return HTMLResponse("<h1>frontend.html not found</h1>", status_code=404)


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  PAM Auth Visualizer — Backend Server")
    print(f"  http://{ARGS.host}:{ARGS.port}/")
    print(f"  Log: {detect_log_file() or 'not found'}")
    print(f"  Mode: {'journald' if ARGS.journald else 'file tail'}")
    print(f"{'='*60}\n")
    uvicorn.run("server:app", host=ARGS.host, port=ARGS.port, reload=False, log_level="warning")
