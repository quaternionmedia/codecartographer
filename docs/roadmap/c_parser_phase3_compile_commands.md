# Next step: compile_commands-first parsing for the GitHub-example flow

## Background

The C parser (`codecarto/services/parsers/c_parser.py`) has two parse paths:

- `parse_files` / `parse_directory` — walks every `.c`/`.h` under a directory
  and parses each file standalone with only `-I<file's own dir>` and
  `-I<project root>`. No real build context.
- `parse_compile_commands` — parses using a real `compile_commands.json`,
  which gives the *actual* include paths, defines, and language standard
  used when the project was built.

The GitHub-example UI flow (`CParserService.parse_github` →
`parse_directory`) only ever uses the first path. Phase 1 (stub POSIX
headers under `codecarto/data/c_stubs/`, platform-define injection, and
skipping known single-platform compat files — see `c_parser.py`'s
`default_parse_args()` / `is_platform_specific_path()`) meaningfully
reduces the missing-header/unknown-type cascade for that path, but it's
explicitly a best-effort syntax aid, not a real build.

## What's still wrong without compile_commands.json

- Project-specific generated headers (e.g. git's `command-list.h`, version
  headers, or anything produced by `./configure`) are never found — they
  don't exist until the project is actually built.
- Per-file compiler flags (extra `-I`, feature-test macros like
  `_FILE_OFFSET_BITS=64`, `-DNDEBUG`, vendor-specific pragmas) are invisible.
- Stub-header type redefinition conflicts (observed: `time_t`/`size_t`
  redefined differently between our POSIX stubs and whatever the project's
  own compat headers pull in) — see the `diagnostics.other` count creep
  after Phase 1's project-root `-I` change.

## Proposed next step

For repos fetched via `parse_github`, prefer a real `compile_commands.json`
over naive directory walking, in priority order:

1. **If the repo already ships one** (rare, but some do) — use it directly.
2. **Generate one via a sandboxed build** — run `bear -- make` / `bear --
   ./configure && make` (or `compiledb`) inside the extracted repo cache
   (`~/.codecarto/cache/repos/{owner}-{repo}/src/`), capped by a timeout,
   before falling back to `parse_directory` on failure. This requires:
   - A sandboxed/ephemeral build environment (the current service runs
     arbitrary `make`/`configure` from an arbitrary GitHub repo — this is a
     real execution-of-untrusted-code concern and needs its own security
     review, likely a container or restricted subprocess with no network
     access and a hard CPU/time/disk budget).
   - Graceful fallback to the current `parse_directory` path when the build
     fails (missing build deps, no `Makefile`, Windows host can't run the
     repo's build system, etc.) — this is the common case for most repos,
     so Phase 1's stub-header approach remains the baseline, not a stopgap.
3. **Surface which path was used** in `meta` (e.g. `meta['parse_mode'] =
   'compile_commands' | 'directory_walk'`) so the frontend/legend can show
   the user how much to trust the resulting graph's completeness.

## Why this is its own phase

Sandboxed arbitrary code execution is a materially different risk profile
and engineering effort than the current "download zip, walk files, parse
each standalone" flow — it deserves its own design/security pass rather
than folding into the stub-header work. Phase 1 should remain in place
regardless, since most repos won't have a usable build (no configure step
documented, deps unavailable, cross-platform build systems that don't run
on the host) and will always fall back to it.
