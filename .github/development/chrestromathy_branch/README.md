# PAM Auth Visualizer — Live System Integration

A real-time node-graph visualizer for Linux PAM authentication flows,
with live log tailing, session replay, and built-in demo mode.

## Architecture

```
Linux Host                          Browser
──────────────────────              ─────────────────────────────
/var/log/auth.log  ──tail──►  server.py  ──WebSocket──►  frontend.html
/var/log/secure                   │                         │
journald  ───────────────────►    │                         │
                               REST API ◄──────────── session replay
                               /api/history                 │
                               /api/sessions           node-graph
                               /api/status             anime.js
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
# or:
pip install fastapi uvicorn websockets python-multipart
```

### 2. Grant log read access (choose one)

```bash
# Option A — grant read (simplest)
sudo chmod a+r /var/log/auth.log

# Option B — add user to adm group (Debian/Ubuntu)
sudo usermod -aG adm $USER && newgrp adm

# Option C — run server as root (not recommended for production)
sudo python server.py
```

### 3. Start the backend

```bash
# Auto-detect log file (/var/log/auth.log or /var/log/secure)
python server.py

# Specify log file explicitly
python server.py --log /var/log/secure

# Use journald (systemd systems)
python server.py --journald

# Listen on all interfaces (for remote access)
python server.py --host 0.0.0.0 --port 8765
```

Then open: **http://localhost:8765/**

### 4. Remote host monitoring (SSH tunnel)

```bash
# On your local machine:
ssh -L 8765:localhost:8765 user@remote-host

# Backend already running on remote host at :8765
# Open http://localhost:8765/ in your browser
# In ⚙ CONFIG, URL is already ws://localhost:8765/ws/live
```

## Log file locations by distro

| Distribution | Log file |
|---|---|
| Ubuntu / Debian | `/var/log/auth.log` |
| RHEL / CentOS / Fedora | `/var/log/secure` |
| Arch Linux | journald (`--journald` flag) |
| SUSE | `/var/log/messages` |

## Frontend Modes

- **LIVE** — Real-time WebSocket tail of auth.log. Nodes and edges light up as PAM events arrive.
- **REPLAY** — Click any captured session in the left panel to replay it at 3× speed with full packet animation.
- **DEMO** — Built-in SSSD domain login simulation (works without backend).

## Generating test events (safe)

```bash
# Trigger a local login attempt (will fail but generates PAM events)
ssh -o StrictHostKeyChecking=no localhost -l testuser echo hi 2>/dev/null || true

# Switch user (generates su PAM events)
su -c 'whoami' nobody 2>/dev/null || true

# sudo attempt
sudo -u nobody whoami 2>/dev/null || true
```

## API endpoints

```
GET  /               → Frontend HTML
GET  /api/status     → Server info, log path, connectivity
GET  /api/history?minutes=30  → Historical events (parsed)
GET  /api/sessions   → List of captured PAM sessions
GET  /api/sessions/{id}  → Events for a specific session
WS   /ws/live        → Real-time event stream
WS   /ws/replay?session_id=X  → Replay a captured session
```

## Security notes

- The backend only **reads** log files — no write access required.
- Bind to `127.0.0.1` (default) for local-only access.
- Use SSH tunneling for remote monitoring rather than exposing :8765.
- The frontend is served from the same origin — no CORS issues.
- Log files may contain sensitive usernames/IPs; treat accordingly.

## Parsed event types

| Event | Trigger |
|---|---|
| `pam_start` | `pam_start()` call in log |
| `pam_end` | `pam_end()` / session close |
| `module_call` | Any `pam_*.so` invocation |
| `module_result` | Module returning PAM_SUCCESS/PAM_AUTH_ERR |
| `sssd_call` | sssd pam responder request |
| `sssd_cache` | Cache hit/miss in sssd logs |
| `sssd_result` | sssd returning auth result |
| `krb_call` | Kerberos TGT / AS-REQ |
| `krb_result` | KDC response |
| `session_open` | `pam_open_session()` |
| `access_granted` | Accepted / PAM_SUCCESS final |
| `access_denied` | Failed / PAM_AUTH_ERR final |
