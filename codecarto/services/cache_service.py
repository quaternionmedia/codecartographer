"""
Cache Service
=============
Unified filesystem-first cache for everything fetched/derived per GitHub repo:
  - the source tree (file structure, ± file content) — so reopening a repo
    you've already looked at doesn't repull GitHub
  - parsed gJGF graphs, one per (mode, layout, extensions) combination

Cache location: ~/.codecarto/cache/repos/{repo_key}/
  tree.json          — cached Directory payload (source tree, ± content)
  graphs/{hash}.json — serialised gJGF payload for one parse setting

Top-level ~/.codecarto/cache/repos/index.json — flat list of ALL graph cache
entries across every repo (newest first, capped at 50). Backs the "Recent"
panel in the UI — unchanged shape from before this file was reorganised;
only the on-disk location of each blob moved into its repo's subfolder.

repo_key = "{owner}-{repo}" for GitHub URLs (same convention the C-parser's
repo cache already uses), or sha256(url)[:16] for anything else (local
paths, non-GitHub hosts) so unrelated caches never collide.

Graph cache key = "{repo_key}::{hash}" where
hash = sha256(url :: mode :: layout :: sorted(extensions))[:16]. The
repo_key prefix lets get()/evict() locate the right subfolder from the key
alone, without needing the original url again.

Optional MongoDB backend: activated when the MONGODB_URI environment variable is
set AND pymongo is importable.  Falls back to filesystem if Mongo is unreachable.
Mongo documents are keyed by the same composite key; the repo_key bucketing
only affects the filesystem layout, not Mongo.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any


# ── Constants ──────────────────────────────────────────────────────────────────

_CACHE_DIR = Path("~/.codecarto/cache").expanduser()
_REPOS_DIR = _CACHE_DIR / "repos"
_INDEX_FILE = _REPOS_DIR / "index.json"
_TTL_SECONDS = int(os.getenv("CC_CACHE_TTL", "86400"))   # 24 h default


# ── Key generation ─────────────────────────────────────────────────────────────

def _repo_key_from_url(url: str) -> str:
    """Derive a stable, filesystem-safe bucket name for a repo's cache.

    Parsed locally (not via github_service.get_owner_repo_from_url) to avoid
    a circular import — github_service imports CacheService, so CacheService
    can't import back.
    """
    if url.startswith("https://github.com/") or url.startswith("http://github.com/"):
        parts = url.split("/")
        if len(parts) >= 5 and parts[3] and parts[4]:
            return f"{parts[3]}-{parts[4]}"
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _make_key(url: str, mode: str, layout: str, extensions: list[str]) -> str:
    repo_key = _repo_key_from_url(url)
    payload = f"{url}::{mode}::{layout}::{sorted(extensions)}"
    h = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"{repo_key}::{h}"


# ── Directory helpers ──────────────────────────────────────────────────────────

def _repo_dir(repo_key: str) -> Path:
    d = _REPOS_DIR / repo_key
    d.mkdir(parents=True, exist_ok=True)
    return d


def _graphs_dir(repo_key: str) -> Path:
    d = _repo_dir(repo_key) / "graphs"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Index helpers (flat list of graph entries, across all repos) ───────────────

def _read_index() -> list[dict]:
    try:
        return json.loads(_INDEX_FILE.read_text())
    except Exception:
        return []


def _write_index(entries: list[dict]) -> None:
    _INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
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
    """Static methods for reading/writing the repo + graph cache."""

    # ── Parsed-graph cache ──────────────────────────────────────────────────

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

        repo_key, _, hash_part = key.partition("::")
        if not hash_part:
            return None
        path = _graphs_dir(repo_key) / f"{hash_part}.json"
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
        repo_key, _, hash_part = key.partition("::")
        if not hash_part:
            return

        ts = time.time()
        serialised = json.dumps(data)
        size_bytes = len(serialised.encode())

        (_graphs_dir(repo_key) / f"{hash_part}.json").write_text(serialised)

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
        """Remove a cached graph entry. Returns True if something was deleted."""
        deleted = False

        repo_key, _, hash_part = key.partition("::")
        if hash_part:
            path = _graphs_dir(repo_key) / f"{hash_part}.json"
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

    # ── Repo source-tree cache ──────────────────────────────────────────────
    # Separate purpose from the graph cache above: this holds the *source*
    # (Directory payload — structure ± file content, however much
    # github_service.get_raw_from_repo decided to fetch for that repo's
    # size tier) so re-browsing a repo's Source tab doesn't repull GitHub.
    # Populated only by get_raw_from_repo; read opportunistically elsewhere
    # (see unified_parser_service.stream_parse_url) when it happens to
    # already be warm — not guaranteed to be fresh enough for every caller's
    # needs (e.g. it skips file content for medium/large repos, which is
    # fine for browsing but not enough for parsing — callers must check).

    @staticmethod
    def get_tree(url: str) -> dict[str, Any] | None:
        """Return the cached repo source tree (Directory payload) or None."""
        repo_key = _repo_key_from_url(url)
        path = _repo_dir(repo_key) / "tree.json"
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
    def set_tree(url: str, data: dict[str, Any]) -> None:
        """Persist a repo's source tree (Directory payload)."""
        repo_key = _repo_key_from_url(url)
        (_repo_dir(repo_key) / "tree.json").write_text(json.dumps(data))

    @staticmethod
    def evict_repo(url: str) -> bool:
        """Remove everything cached for a repo (tree + every parsed graph)."""
        repo_key = _repo_key_from_url(url)
        d = _REPOS_DIR / repo_key
        if not d.is_dir():
            return False
        shutil.rmtree(d)

        entries = _read_index()
        new_entries = [e for e in entries if not e.get("key", "").startswith(f"{repo_key}::")]
        if len(new_entries) != len(entries):
            _write_index(new_entries)

        return True
