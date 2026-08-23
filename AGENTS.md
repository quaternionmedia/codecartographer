# AGENTS.md

This project is governed by the Quaternion Media constitution, vendored at
`governance/qm` (a submodule pinned to this project's `project/codecartographer`
branch of that repo). If you are an AI coding agent opening this repo with no
other briefing, read this file fully before your first commit or edit.

## Before you do anything

1. Read `governance/qm/README.md` and `governance/qm/PRINCIPLES.md` in full
   — the namespaces/precedence rules and the charter. Both are short.
2. This project's own decision records live in `governance/qm/adr/` — inside
   the submodule, on this project's own branch, not at this repo's root — as
   `ADR-NNNN` (numbered locally, at ratification) or `DRAFT-*.md` before
   ratification. A human ratifies; you draft. **There are eleven of them
   already**, and they carry the reasoning behind most non-obvious structure
   here; read the index before proposing a change to the parser, the cache,
   or the layout.
3. **Everything you produce arrives as a pull request.** Work on a branch and
   open a PR for human review — in this repo, and in the `governance/qm`
   submodule when you touch this project's records there. Never commit to,
   merge into, or push a shared branch directly, and never merge your own
   work, however small or mechanical the change looks. If you cannot open a
   PR, hand the branch back rather than merging it.
4. **Human-only contributorship applies to every commit you make here** (see
   `governance/qm/records/DRAFT-human-only-contributorship.md`): do not add
   yourself, your model name, or any co-author trailer naming an unmonitored
   address (e.g. a vendor `noreply@` address) to any commit. If your default
   tooling normally appends a `Co-Authored-By:` trailer, suppress it for
   this repo. Tool involvement is disclosed as a `Tools:` note where the
   artifact calls for one, never as a byline.
5. Follow the drafting-session handoff contract in
   `governance/qm/adr/README.md` before writing or amending any record.
6. A QM record may be tightened by this project's own records, never
   relaxed — see `governance/qm/README.md`'s "Namespaces and precedence."
7. Banned in any pre-ratification `DRAFT-*.md` record: "previously",
   "originally", "earlier draft", "re-review", "renumber", "retroactive",
   "supersedes the ... (stance|finding)", "corrected". Drafts are rewritten
   in place, not narrated. The ADR lint enforces this over prose only, so
   quoting the list in a code span is fine.

## One-time setup on a fresh clone (Windows)

`CLAUDE.md` and `.github/copilot-instructions.md` are real symlinks to this
file, not copies — POSIX checkouts resolve them with no setup. On Windows,
enable Developer Mode (Settings → For developers) and run `git config
core.symlinks true` once per clone, then `git checkout -- .` if the files
were already checked out before that. The submodule is a separate clone and
does not inherit the setting: run it inside `governance/qm` too.

<!-- Project-specific setup commands, test commands, and conventions belong
     below this line; this seed only carries the governance-discovery part. -->

## What codecarto is

A development tool that parses source code and renders it as interactive
graphs — directories, files and symbols — to make structure, dependencies and
relationships legible.

Python backend (FastAPI) plus a TypeScript frontend under `web/`, with
`graphbase` vendored as a second submodule.

## Running it

```sh
uv venv
uv pip install -e ".[dev]"

uv run codecarto dev      # backend and frontend together
uv run codecarto serve    # backend only
uv run codecarto web      # frontend only
```

**Never bind a default port.** Other agent sessions run on this workstation
at the same time, in other repositories, and `codecarto serve` defaults to
`127.0.0.1:8000` — which is exactly the port another QM project was already
serving when a session spent an afternoon measuring the wrong program. Pass a
non-default port, and ask whatever you are measuring what it is rather than
trusting that a 200 means it is yours.

## Tests

```sh
uv run pytest tests -q
```

355 tests, around three minutes. Pure Python — no browser or Node needed, which
is why CI runs them without installing either.

A passing test is not evidence until it has been seen to fail. After writing a
check, break the thing it names and confirm the check goes red.

## Governance gates

```sh
python governance/qm/project-seed/ci/run_workflows_locally.py
```

Runs the workflows' real steps. It reproduces no `uses:` steps, no runner
image and no secrets, so say that when reporting rather than letting a local
pass stand for a remote one.

The three governance workflows are **copied verbatim from the seed** and must
stay that way: `adr-lint.yml`, `submodule-check.yml`, `reuse-lint.yml`. The
lint they run comes out of the submodule, so a fix in the corpus reaches this
project at its next pin bump. Do not hand-port a check into this repository —
a copy that reimplements a rule is a second definition of it, and this project
carried exactly that for a while: a workflow that grepped for banned words
itself, implementing one of the lint's four checks and matching prose the real
lint deliberately skips.

## Where the structure is explained

`docs/architecture.md` for the shape, `docs/api.md` for the surface, and
`governance/qm/adr/` for why any of it is the way it is.
