"""Record a bundled cargo example afresh, naming no machine in what it writes.

    uv run python scripts/record_example.py examples/rust-firmware --map blinky

With a Rust toolchain and the example's target installed, this is `uv run
codecarto cargo record PATH --map BIN`, which RUNS THE EXAMPLE'S BUILD (`cargo
check` compiles and executes build scripts and proc macros), and then a
rewrite of every absolute path in what that wrote under `target/codecarto/`:
the workspace cargo names to `/ws`, cargo's home (`CARGO_HOME`, else
`~/.cargo`) to `/cargo-home`, rustup's (`RUSTUP_HOME`, else `~/.rustup`) to
`/rustup-home`, with a Windows path's separators made `/`. The JSON records
are written back by Python's `json`, one document per line in `check.jsonl`.

**WHAT IS LEFT IS NAMED, AND FAILS.** Any other absolute path still in the
records -- a target directory outside the workspace, a toolchain somewhere
else -- names the machine they were recorded on: each is printed and this
exits 1, so they are not committed believing them clean.

`--rewrite-only` skips the recording, for records `codecarto cargo record`
already wrote. `portable_document` and `machine_paths` are what
`tests/test_examples.py` holds the committed records to.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# What an absolute path in a committed record may start with.
STAND_INS = ("/ws", "/cargo-home", "/rustup-home")

_SEP = r"[\\/]+"
_NAME = r"[^\\/\s\"'<>|:*?#()]"  # one character of a path component
_END = rf"(?!{_NAME})"  # a root ends where its last component does


def _root_pattern(root: str) -> tuple[re.Pattern, bool]:
    """How *root* is written in a record, and whether it is a Windows path."""
    root = re.sub(r"^\\\\\?\\", "", root)  # a verbatim `\\?\` prefix
    parts = [p for p in re.split(_SEP, root) if p]
    if parts and re.fullmatch(r"[A-Za-z]:", parts[0]):
        # Backslashes or slashes, any case, and `/C:/...` inside a file URL.
        head = r"(?:\\\\\?\\|/)?" + re.escape(parts[0]) + "".join(_SEP + re.escape(p) for p in parts[1:])
        rest = rf"(?P<rest>(?:{_SEP}{_NAME}*)*)"
        return re.compile(rf"(?<![\w.]){head}{_END}{rest}", re.IGNORECASE), True
    # One `/` first, so `file:///home/...` keeps its `file://`.
    head = "/" + "/+".join(re.escape(p) for p in parts)
    return re.compile(rf"(?<![\w.~-]){head}{_END}(?P<rest>(?:/+{_NAME}*)*)"), False


def portable(text: str, roots: list[tuple[str, str]]) -> str:
    """*text* with each root's paths rewritten to start at its stand-in."""
    for root, stand_in in sorted(roots, key=lambda pair: len(pair[0]), reverse=True):
        pattern, windows = _root_pattern(root)
        separators = _SEP if windows else "/+"
        text = pattern.sub(lambda m: stand_in + re.sub(separators, "/", m["rest"]), text)
    return text


def _walk(value: Any, roots: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        return portable(value, roots)
    if isinstance(value, list):
        return [_walk(v, roots) for v in value]
    if isinstance(value, dict):
        return {portable(k, roots): _walk(v, roots) for k, v in value.items()}
    return value


def portable_document(name: str, text: str, roots: list[tuple[str, str]]) -> str:
    """A record's text with its paths rewritten. JSON is rewritten string by
    string, so a path's escaped backslashes are its separators and nothing else."""
    if name.endswith(".json"):
        return json.dumps(_walk(json.loads(text), roots))
    if name.endswith(".jsonl"):
        lines = []
        for line in text.splitlines():
            try:
                lines.append(json.dumps(_walk(json.loads(line), roots)))
            except json.JSONDecodeError:
                lines.append(portable(line, roots))  # cargo's plain text, kept
        return "".join(line + "\n" for line in lines)
    return portable(text, roots)


_DRIVE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:(?:\\\\|\\|/)[^\s\"'<>|]*")
_FILE_URL = re.compile(r"file://(/[^\s\"'<>|#]*)")
# A `/` that starts a path: not inside a word (`and/or`), a URL (`https://`),
# a feature (`quote?/proc-macro`) or a file URL, which `_FILE_URL` reads.
_POSIX = re.compile(r"(?<![\w.:/~?-])/[^\s\"'`<>|,;()\[\]{}#]+")


def _under_a_stand_in(path: str) -> bool:
    return any(path == s or path.startswith(s + "/") for s in STAND_INS)


def machine_paths(text: str) -> list[str]:
    """Each absolute path in *text* that is not under a stand-in: a drive
    letter's, or a POSIX one anywhere else."""
    found = [m.group(0) for m in _DRIVE.finditer(text)]
    found += [p for p in _FILE_URL.findall(text) if not _under_a_stand_in(p)]
    found += [m.group(0) for m in _POSIX.finditer(text) if not _under_a_stand_in(m.group(0))]
    return list(dict.fromkeys(found))


def stand_ins(workspace: str, environ: dict | None = None, home: Path | None = None) -> list[tuple[str, str]]:
    """The roots a recording's paths start at, each with its stand-in."""
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else home
    return [
        (workspace, "/ws"),
        (environ.get("CARGO_HOME") or str(home / ".cargo"), "/cargo-home"),
        (environ.get("RUSTUP_HOME") or str(home / ".rustup"), "/rustup-home"),
    ]


def rewrite(docs: Path, roots: list[tuple[str, str]]) -> list[str]:
    """Rewrite each record in *docs* in place; the machine paths left in them."""
    left: list[str] = []
    for doc in sorted(p for p in docs.iterdir() if p.is_file()):
        text = portable_document(doc.name, doc.read_text(encoding="utf-8"), roots)
        doc.write_text(text, encoding="utf-8", newline="\n")
        left += [f"{doc.name}: {path}" for path in machine_paths(text)]
    return left


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("path", help="the example's workspace root, e.g. examples/rust-firmware")
    parser.add_argument("--map", action="append", default=[], metavar="BIN",
                        help="also link BIN and keep its map (repeatable), as `cargo record --map`")
    parser.add_argument("--rewrite-only", action="store_true",
                        help="rewrite the records already there; run nothing")
    args = parser.parse_args(argv)
    root = Path(args.path).resolve()
    stopped = 0  # how `cargo record` exited, when it failed
    if not args.rewrite_only:
        from codecarto.cli import cli

        maps = [arg for binary in args.map for arg in ("--map", binary)]
        try:
            cli.main(["cargo", "record", str(root), *maps], standalone_mode=False)
        except SystemExit as exited:
            # What it did write is rewritten all the same: a tracked record is
            # not left naming the machine because a later step failed.
            stopped = exited.code if isinstance(exited.code, int) and exited.code else 1
    docs = root / "target" / "codecarto"
    try:
        workspace = json.loads((docs / "metadata.json").read_text(encoding="utf-8"))["workspace_root"]
    except (OSError, ValueError, KeyError) as error:
        print(f"No workspace to rewrite from: {docs / 'metadata.json'} could not be read ({error}).",
              file=sys.stderr)
        return stopped or 1
    left = rewrite(docs, stand_ins(workspace))
    if left:
        print("These records still name the machine; do not commit them:", file=sys.stderr)
        for path in left:
            print(f"  {path}", file=sys.stderr)
        return 1
    if stopped:
        print("`cargo record` failed (above): what it wrote is rewritten, but it is not a whole "
              "recording.", file=sys.stderr)
        return stopped
    print(f"Rewrote {docs}: every absolute path is under {', '.join(STAND_INS)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
