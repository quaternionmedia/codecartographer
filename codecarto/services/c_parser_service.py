"""
C Parser Service
================
Thin service layer wrapping CParser for use by the API router.
"""

import io
import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable, Optional

from codecarto.services.github_service import create_headers
from codecarto.util.exceptions import CodeCartoException

# Callback shape shared by the streaming entry points below: called
# synchronously (possibly from a background thread — see c_parser_router.py's
# /c-parser/stream-github) with (event_type, payload) as progress happens.
# event_type is one of: 'fetching' | 'meta' | 'nodes'.
OnProgress = Callable[[str, dict], None]

# Persistent cache for downloaded + extracted GitHub archives.
# Layout: ~/.codecarto/cache/repos/{owner}-{repo}/src/   (extracted tree)
#                                                /metadata.json  (ts, url)
_REPO_CACHE_DIR = Path("~/.codecarto/cache/repos").expanduser()
_REPO_TTL = int(os.getenv("CC_CACHE_TTL", "86400"))  # 24 h default, same var as graph cache


def _repo_cache_is_fresh(cache_dir: Path) -> bool:
    meta = cache_dir / "metadata.json"
    if not meta.exists():
        return False
    try:
        ts = json.loads(meta.read_text(encoding="utf-8")).get("ts", 0)
        return (time.time() - ts) < _REPO_TTL
    except Exception:
        return False


def _dir_size_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


class CParserService:
    """Service for parsing C source files into semantic graphs."""

    @staticmethod
    def parse_file(path: str) -> dict:
        """
        Parse a single C/H source file.

        Parameters
        ----------
        path : str
            Absolute or relative path to the C/H file.

        Returns
        -------
        dict with 'nodes', 'edges', 'meta'

        Raises
        ------
        CodeCartoException on import failure or parse error.
        """
        try:
            from codecarto.services.parsers.c_parser import CParser
        except ImportError as exc:
            raise CodeCartoException(
                source="CParserService.parse_file",
                params={"path": path},
                message=str(exc),
            ) from exc

        fpath = Path(path)
        if not fpath.exists():
            raise CodeCartoException(
                source="CParserService.parse_file",
                params={"path": path},
                message=f"File not found: {path}",
                status_code=404,
            )

        try:
            return CParser().parse_files([fpath])
        except Exception as exc:
            raise CodeCartoException(
                source="CParserService.parse_file",
                params={"path": path},
                message=f"Parse error: {exc}",
                exc=exc,
            ) from exc

    @staticmethod
    def parse_directory(
        path: str,
        compile_commands: Optional[str] = None,
        subsystem: Optional[str] = None,
        max_files: Optional[int] = None,
        on_progress: Optional[OnProgress] = None,
    ) -> dict:
        """
        Parse all C/H files in a directory, or use compile_commands.json.

        Parameters
        ----------
        path : str
            Directory path (used when compile_commands is None).
        compile_commands : str, optional
            Path to compile_commands.json for kernel-style builds.
        subsystem : str, optional
            Path fragment to filter compile_commands entries.
        max_files : int, optional
            Limit on files parsed (useful for large codebases).
        on_progress : callable, optional
            Called with ('meta', {total_files, skipped_files}) once the file
            list is known, then with ('nodes', {file, nodes}) after each
            file's declarations are parsed — lets a caller stream progress
            instead of waiting for the full parse. See CParser.parse_files.

        Returns
        -------
        dict with 'nodes', 'edges', 'meta'
        """
        try:
            from codecarto.services.parsers.c_parser import CParser
        except ImportError as exc:
            raise CodeCartoException(
                source="CParserService.parse_directory",
                params={"path": path},
                message=str(exc),
            ) from exc

        parser = CParser()

        if compile_commands:
            cc_path = Path(compile_commands)
            if not cc_path.exists():
                raise CodeCartoException(
                    source="CParserService.parse_directory",
                    params={"compile_commands": compile_commands},
                    message=f"compile_commands.json not found: {compile_commands}",
                    status_code=404,
                )
            try:
                return parser.parse_compile_commands(
                    cc_path,
                    subsystem_filter=subsystem,
                    max_files=max_files,
                )
            except Exception as exc:
                raise CodeCartoException(
                    source="CParserService.parse_directory",
                    params={"compile_commands": compile_commands},
                    message=f"Parse error: {exc}",
                    exc=exc,
                ) from exc

        dir_path = Path(path)
        if not dir_path.is_dir():
            raise CodeCartoException(
                source="CParserService.parse_directory",
                params={"path": path},
                message=f"Directory not found: {path}",
                status_code=404,
            )

        all_files = sorted(
            list(dir_path.rglob("*.c")) + list(dir_path.rglob("*.h"))
        )
        if not all_files:
            raise CodeCartoException(
                source="CParserService.parse_directory",
                params={"path": path},
                message="No .c or .h files found in directory",
                status_code=404,
            )

        # Without a compile_commands.json we have no way to know which
        # platform variant was actually meant to build, so every compat
        # shim for every OS would otherwise get parsed unconditionally
        # (e.g. git ships compat/apple-*, compat/mingw.c, compat/solaris/*
        # that are never compiled together). Skip known single-platform
        # files rather than let them parse-with-errors.
        from codecarto.services.parsers.c_parser import is_platform_specific_path, default_parse_args

        skipped_files = [
            str(f.relative_to(dir_path)) for f in all_files
            if is_platform_specific_path(f.relative_to(dir_path))
        ]
        skipped_set = set(skipped_files)
        c_files = [f for f in all_files if str(f.relative_to(dir_path)) not in skipped_set]

        if max_files:
            c_files = c_files[:max_files]

        if on_progress:
            on_progress("meta", {"total_files": len(c_files), "skipped_files": skipped_files})

        def _on_file_parsed(file_name: str, new_nodes: list) -> None:
            if on_progress:
                on_progress("nodes", {"file": file_name, "nodes": new_nodes})

        try:
            # Always include the project root, not just each file's own
            # directory — multi-directory projects (e.g. git's builtin/*.c
            # including the root-level builtin.h) need both on the path.
            result = parser.parse_files(
                c_files,
                extra_args=default_parse_args(project_root=dir_path),
                on_file_parsed=_on_file_parsed if on_progress else None,
            )
            result.setdefault("meta", {})["skipped_files"] = skipped_files
            return result
        except Exception as exc:
            raise CodeCartoException(
                source="CParserService.parse_directory",
                params={"path": path},
                message=f"Parse error: {exc}",
                exc=exc,
            ) from exc

    @staticmethod
    def parse_github(
        url: str,
        max_files: Optional[int] = 200,
        on_progress: Optional[OnProgress] = None,
    ) -> dict:
        """
        Download a GitHub repository and parse all C/H files in it.

        Downloads the repo as a ZIP archive from GitHub, extracts it to a
        temporary directory, calls parse_directory, then cleans up.

        Parameters
        ----------
        url : str
            GitHub repository URL (https://github.com/owner/repo).
        max_files : int, optional
            Maximum number of C/H files to parse (default 200).
        on_progress : callable, optional
            Called with ('fetching', {message}) during download/extract,
            then forwarded into parse_directory's 'meta'/'nodes' events.
            See c_parser_router.py's /c-parser/stream-github for how this
            drives real-time SSE streaming from a background thread.

        Returns
        -------
        dict with 'nodes', 'edges', 'meta'

        Raises
        ------
        CodeCartoException on bad URL, download failure, or parse error.
        """
        import requests  # already in core deps

        # Use the same Authorization header as the Python/unified GitHub
        # path (create_headers reads GITHUB_TOKEN/GH_TOKEN) — without it
        # this archive download was unauthenticated, so it hit the much
        # lower unauthenticated rate limit and 404'd on private repos that
        # the token-bearing API path could otherwise see.
        headers = create_headers(url)

        m = re.match(
            r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$",
            url.strip(),
        )
        if not m:
            raise CodeCartoException(
                source="CParserService.parse_github",
                params={"url": url},
                message="Invalid GitHub URL — expected https://github.com/owner/repo",
                status_code=400,
            )
        owner, repo = m.group(1), m.group(2)

        cache_dir = _REPO_CACHE_DIR / f"{owner}-{repo}"
        src_dir = cache_dir / "src"

        # Cache hit — reuse the previously extracted tree
        if src_dir.is_dir() and _repo_cache_is_fresh(cache_dir):
            if on_progress:
                on_progress("fetching", {"message": f"Using cached clone of {owner}/{repo}"})
            return CParserService.parse_directory(
                str(src_dir), max_files=max_files, on_progress=on_progress
            )

        # Cache miss — download, extract into staging, promote to cache
        zip_url = f"https://github.com/{owner}/{repo}/archive/HEAD.zip"
        if on_progress:
            on_progress("fetching", {"message": f"Downloading {owner}/{repo}…"})
        try:
            resp = requests.get(zip_url, headers=headers, timeout=60)
        except Exception as exc:
            raise CodeCartoException(
                source="CParserService.parse_github",
                params={"url": url},
                message=f"Failed to download repo archive: {exc}",
                status_code=502,
            ) from exc

        if resp.status_code != 200:
            # Surface the real status — a 401 (invalid GITHUB_TOKEN/GH_TOKEN)
            # or 429/403 (rate limited) showing up as "404 Not Found" was
            # actively misleading about what actually went wrong.
            status = resp.status_code if resp.status_code in (401, 403, 404, 429) else 502
            hint = ""
            if resp.status_code == 401:
                hint = " (GITHUB_TOKEN/GH_TOKEN env var is set but invalid or expired)"
            elif resp.status_code in (403, 429):
                hint = " (likely rate limited)"
            raise CodeCartoException(
                source="CParserService.parse_github",
                params={"url": url, "zip_url": zip_url},
                message=f"GitHub returned HTTP {resp.status_code}{hint}",
                status_code=status,
            )

        # Extract to a throwaway staging dir, then move into the persistent cache.
        # The staging dir is always cleaned up; the cache dir survives.
        staging = tempfile.mkdtemp(prefix="codecarto_c_")
        try:
            if on_progress:
                on_progress("fetching", {"message": "Extracting archive…"})
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                zf.extractall(staging)

            # GitHub archives extract to "{repo}-{sha}/" — pick the first subdir
            extracted = next(
                (
                    d
                    for d in sorted(os.listdir(staging))
                    if os.path.isdir(os.path.join(staging, d))
                ),
                None,
            )
            if not extracted:
                raise CodeCartoException(
                    source="CParserService.parse_github",
                    params={"url": url},
                    message="Could not find extracted directory in archive",
                    status_code=500,
                )

            cache_dir.mkdir(parents=True, exist_ok=True)
            if src_dir.exists():
                shutil.rmtree(src_dir)
            shutil.move(os.path.join(staging, extracted), str(src_dir))

            (cache_dir / "metadata.json").write_text(
                json.dumps({"owner": owner, "repo": repo, "url": url, "ts": time.time()}),
                encoding="utf-8",
            )

            return CParserService.parse_directory(
                str(src_dir), max_files=max_files, on_progress=on_progress
            )
        except CodeCartoException:
            raise
        except Exception as exc:
            raise CodeCartoException(
                source="CParserService.parse_github",
                params={"url": url},
                message=f"Error processing GitHub archive: {exc}",
                status_code=500,
            ) from exc
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    @staticmethod
    def list_cached_repos() -> list[dict]:
        """List extracted GitHub repos in the repo cache (newest first).

        Counterpart to CacheService.list_cached() for the *other* cache —
        this one holds extracted source trees (see _REPO_CACHE_DIR), not
        parsed graphs. Kept separate on purpose: they cache different
        things. See docs/llm/ARCHITECTURE.md's "Two C-parser caches".
        """
        if not _REPO_CACHE_DIR.is_dir():
            return []

        now = time.time()
        entries: list[dict] = []
        for entry_dir in _REPO_CACHE_DIR.iterdir():
            meta_path = entry_dir / "metadata.json"
            if not entry_dir.is_dir() or not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            src_dir = entry_dir / "src"
            entries.append({
                "key": entry_dir.name,
                "owner": meta.get("owner", ""),
                "repo": meta.get("repo", ""),
                "url": meta.get("url", ""),
                "ts": meta.get("ts", 0),
                "age_seconds": int(now - meta.get("ts", now)),
                "size_bytes": _dir_size_bytes(src_dir) if src_dir.is_dir() else 0,
            })
        entries.sort(key=lambda e: e["ts"], reverse=True)
        return entries

    @staticmethod
    def evict_repo_cache(key: str) -> bool:
        """Remove a cached extracted repo by its `{owner}-{repo}` key.

        Returns True if a cache directory existed and was deleted.
        """
        # key comes straight from the URL path — reject anything that could
        # escape _REPO_CACHE_DIR (path separators, '..', etc).
        if not key or "/" in key or "\\" in key or ".." in key:
            return False
        entry_dir = _REPO_CACHE_DIR / key
        if not entry_dir.is_dir():
            return False
        shutil.rmtree(entry_dir)
        return True
