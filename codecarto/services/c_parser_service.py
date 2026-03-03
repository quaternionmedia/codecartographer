"""
C Parser Service
================
Thin service layer wrapping CParser for use by the API router.
"""

import io
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from codecarto.util.exceptions import CodeCartoException


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

        c_files = sorted(
            list(dir_path.rglob("*.c")) + list(dir_path.rglob("*.h"))
        )
        if not c_files:
            raise CodeCartoException(
                source="CParserService.parse_directory",
                params={"path": path},
                message="No .c or .h files found in directory",
                status_code=404,
            )

        if max_files:
            c_files = c_files[:max_files]

        try:
            return parser.parse_files(c_files, cache_dir=cache_dir)
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

        tmp_dir = tempfile.mkdtemp(prefix="codecarto_c_")
        try:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                zf.extractall(tmp_dir)

            # GitHub archives extract to "{repo}-{sha}/" — pick the first dir
            extracted = next(
                (
                    d
                    for d in sorted(os.listdir(tmp_dir))
                    if os.path.isdir(os.path.join(tmp_dir, d))
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

            return CParserService.parse_directory(
                os.path.join(tmp_dir, extracted),
                max_files=max_files,
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
            shutil.rmtree(tmp_dir, ignore_errors=True)
