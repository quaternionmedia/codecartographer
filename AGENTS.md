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
   ratification. A human ratifies; you draft. **Read the index in
   `governance/qm/adr/README.md` before proposing a change** to the parser,
   the cache, the layout or the radial menu -- the records carry the
   reasoning behind most non-obvious structure here, and `ls
   governance/qm/adr/DRAFT-*.md` is the count.
3. **Everything you produce arrives as a pull request, and the pull request
   is an audit record rather than a request for anyone's attention.** Work on
   a branch, open a PR, assign the person who asked for the work, and never
   request a review -- in this repo, and in the `governance/qm` submodule when
   you touch this project's records there (that PR is based on
   `project/codecartographer`, never on `main`). Get every gate green.
   **Nothing reaches `main` without the human's explicit click**: leave the
   green PR open and say so in the handoff. Never push `main` directly, and
   never close a PR by pushing its commits onto its base -- pushing first
   *merges* it. `governance/qm/AGENTS.md` item 3 and
   `governance/qm/handbook/async-contract.md` §1-3 are the rules; where this
   summary and those disagree, they win and this is repaired.
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
uv sync --extra dev       # the lockfile is the environment

uv run codecarto dev      # backend and frontend together
uv run codecarto serve    # backend only; `serve --help` prints the port
uv run codecarto web      # frontend only, http://localhost:1234
```

**The port is a constant the corpus allocates, and it is not 8000.**
`codecarto.cli.DEFAULT_PORT` is what `uv run qm dashboard` in the corpus
assigns this project -- one fixed port per surface so that several of this
org's servers can run on one workstation without a reader measuring the wrong
one, which has happened here for an afternoon. Other agent sessions run on this
workstation at the same time. Override with `CODECARTO_PORT` or `--port` when
you need a second instance, and **ask whatever you are measuring what it is**
(`/openapi.json` names this app `codecarto`) rather than trusting that a 200
means it is yours. The browser tests bind their own non-default ports and
refuse to reuse a server they did not start.

## Tests

```sh
uv run pytest tests -q               # the Python suite; pure Python, no browser or Node
cd web && npm run typecheck          # the front end compiles
cd web && npm run test:pure && npm run test:state && npm run test:rad
cd web && npm run test:e2e           # starts its own servers on non-default ports
```

The command prints the count and the time; neither is restated here. **Unset
`MONGODB_URI` before timing anything** -- with it set and no database listening,
the suite waits on server selection and reports several minutes for work that
takes under one. `tests/test_docs_routes.py` reads the documents against the
application and fails when a route, a proxy prefix or a port is stated wrongly.

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
