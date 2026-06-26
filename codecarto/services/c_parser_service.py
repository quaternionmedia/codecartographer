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
from typing import Optional

from codecarto.util.exceptions import CodeCartoException

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


class CParserService:
    """Service for parsing C source files into semantic graphs."""

    @staticmethod
    def parse_file(path: str, cache_dir: Optional[str] = None) -> dict:
        """
        Parse a single C/H source file.

        Parameters
        ----------
        path : str
            Absolute or relative path to the C/H file.
        cache_dir : str, optional
            Directory for caching libclang results.

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
            return CParser().parse_files([fpath], cache_dir=cache_dir)
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
        cache_dir: Optional[str] = None,
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
        cache_dir : str, optional
            Directory for caching libclang results.

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

        try:
            # Always include the project root, not just each file's own
            # directory — multi-directory projects (e.g. git's builtin/*.c
            # including the root-level builtin.h) need both on the path.
            result = parser.parse_files(
                c_files,
                extra_args=default_parse_args(project_root=dir_path),
                cache_dir=cache_dir,
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
    def parse_github(url: str, max_files: Optional[int] = 200) -> dict:
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

        Returns
        -------
        dict with 'nodes', 'edges', 'meta'

        Raises
        ------
        CodeCartoException on bad URL, download failure, or parse error.
        """
        import requests  # already in core deps

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
            return CParserService.parse_directory(str(src_dir), max_files=max_files)

        # Cache miss — download, extract into staging, promote to cache
        zip_url = f"https://github.com/{owner}/{repo}/archive/HEAD.zip"
        try:
            resp = requests.get(zip_url, timeout=60)
        except Exception as exc:
            raise CodeCartoException(
                source="CParserService.parse_github",
                params={"url": url},
                message=f"Failed to download repo archive: {exc}",
                status_code=502,
            ) from exc

        if resp.status_code != 200:
            raise CodeCartoException(
                source="CParserService.parse_github",
                params={"url": url, "zip_url": zip_url},
                message=f"GitHub returned HTTP {resp.status_code}",
                status_code=404,
            )

        # Extract to a throwaway staging dir, then move into the persistent cache.
        # The staging dir is always cleaned up; the cache dir survives.
        staging = tempfile.mkdtemp(prefix="codecarto_c_")
        try:
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

            return CParserService.parse_directory(str(src_dir), max_files=max_files)
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
