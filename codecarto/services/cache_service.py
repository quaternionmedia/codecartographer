"""
Cache Service
=============
Filesystem-first cache for parsed gJGF graphs.

Cache location: ~/.codecarto/cache/
  {key}.json   — serialised gJGF payload
  index.json   — metadata index [{key, label, url, mode, layout, ts, size_bytes}]

Optional MongoDB backend: activated when the MONGODB_URI environment variable is
set AND pymongo is importable.  Falls back to filesystem if Mongo is unreachable.

Cache key: first 16 hex chars of SHA-256( url :: mode :: layout :: sorted(extensions) )
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


# ── Constants ──────────────────────────────────────────────────────────────────

_CACHE_DIR = Path("~/.codecarto/cache").expanduser()
_INDEX_FILE = _CACHE_DIR / "index.json"
_TTL_SECONDS = int(os.getenv("CC_CACHE_TTL", "86400"))   # 24 h default


# ── Key generation ─────────────────────────────────────────────────────────────

def _make_key(url: str, mode: str, layout: str, extensions: list[str]) -> str:
    payload = f"{url}::{mode}::{layout}::{sorted(extensions)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ── Index helpers ──────────────────────────────────────────────────────────────

def _read_index() -> list[dict]:
    try:
        return json.loads(_INDEX_FILE.read_text())
    except Exception:
        return []


def _write_index(entries: list[dict]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _INDEX_FILE.write_text(json.dumps(entries, indent=2))


# ── MongoDB helpers (optional) ─────────────────────────────────────────────────

_mongo_collection = None   # lazy singleton


def _mongo_col():
    global _mongo_collection
    if _mongo_collection is not None:
        return _mongo_collection

    uri = os.getenv("MONGODB_URI")
    if not uri:
        return None
    try:
        from pymongo import MongoClient  # type: ignore
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        client.server_info()  # trigger connection
        _mongo_collection = client["codecartographer"]["graph_cache"]
        return _mongo_collection
    except Exception:
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

class CacheService:
    """Static methods for reading/writing the graph cache."""

    @staticmethod
    def cache_key(url: str, mode: str, layout: str, extensions: list[str]) -> str:
        return _make_key(url, mode, layout, extensions)

    @staticmethod
    def get(key: str) -> dict[str, Any] | None:
        """Return cached graph data or None if absent/stale."""
        col = _mongo_col()
        if col is not None:
            try:
                doc = col.find_one({"key": key})
                if doc and (time.time() - doc["ts"]) < _TTL_SECONDS:
                    return doc["data"]
            except Exception:
                pass  # fall through to filesystem

        path = _CACHE_DIR / f"{key}.json"
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > _TTL_SECONDS:
            return None
        try:
            return json.loads(path.read_text())
        except Exception:
            return None

    @staticmethod
    def set(
        key: str,
        data: dict[str, Any],
        label: str,
        url: str = "",
        mode: str = "",
        layout: str = "",
    ) -> None:
        """Persist graph data to cache (filesystem and optionally Mongo)."""
        ts = time.time()
        serialised = json.dumps(data)
        size_bytes = len(serialised.encode())

        # Filesystem
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / f"{key}.json").write_text(serialised)

        # Update index
        entries = [e for e in _read_index() if e.get("key") != key]
        entries.insert(0, {
            "key": key,
            "label": label,
            "url": url,
            "mode": mode,
            "layout": layout,
            "ts": ts,
            "size_bytes": size_bytes,
        })
        # Keep at most 50 entries
        _write_index(entries[:50])

        # Mongo (best-effort)
        col = _mongo_col()
        if col is not None:
            try:
                col.replace_one(
                    {"key": key},
                    {"key": key, "data": data, "label": label, "ts": ts},
                    upsert=True,
                )
            except Exception:
                pass

    @staticmethod
    def list_cached() -> list[dict]:
        """Return index entries, newest first, with age_seconds added."""
        now = time.time()
        entries = _read_index()
        for e in entries:
            e["age_seconds"] = int(now - e.get("ts", now))
        return entries

    @staticmethod
    def evict(key: str) -> bool:
        """Remove a cached entry. Returns True if something was deleted."""
        deleted = False

        path = _CACHE_DIR / f"{key}.json"
        if path.exists():
            path.unlink()
            deleted = True

        entries = _read_index()
        new_entries = [e for e in entries if e.get("key") != key]
        if len(new_entries) != len(entries):
            _write_index(new_entries)
            deleted = True

        col = _mongo_col()
        if col is not None:
            try:
                result = col.delete_one({"key": key})
                if result.deleted_count:
                    deleted = True
            except Exception:
                pass

        return deleted
