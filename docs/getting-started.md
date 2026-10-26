# Getting Started

This page installs Codecarto, runs it, and draws a first graph. It is the one
setup page: the other documents link here, and the few that give the install
command give this page's sync, which `tests/test_docs_routes.py` holds every
document and the code to.

## Prerequisites

- **Python 3.10+** and **[uv](https://docs.astral.sh/uv/)**
- **Node.js 18+**, for the frontend
- **Git**
- **[GitHub CLI](https://cli.github.com/)**, optional: it gives the server a
  token for GitHub repositories

## Install

```bash
git clone https://github.com/quaternionmedia/codecartographer.git
cd codecartographer
git submodule update --init governance/qm
uv sync --locked --extra dev --extra c-parsing
```

The sync installs exactly what `uv.lock` pins; `--locked` stops it, rather than
rewriting the lockfile, when `pyproject.toml` has moved past it. The `c-parsing`
extra is libclang: without it C and C++ files draw empty, and a sync that
leaves it out removes it. The `dev` extra carries the test and lint tools, and
a sync without it removes those.

`governance/qm` holds the project's decision records. The other submodule,
`graphbase`, is the optional MongoDB store and needs access to its private
repository; nothing else needs it.

## Run

```bash
uv run codecarto dev
```

This starts the backend and the frontend (http://localhost:1234). Both print
their addresses; `codecarto serve --help` shows the backend's default port. The
first run installs the frontend's packages with `npm install`. `Ctrl+C` stops
both.

`codecarto serve` and `codecarto web` start one half each; the
[CLI reference](cli.md) has every command and option.

## A first graph

**In the browser.** Open http://localhost:1234; a graph starts from the
[Open panel](ui.md#open).

**From the command line.**

```bash
uv run codecarto repo graph .            # counts what a parse of this directory finds
uv run codecarto repo graph . -o json    # the graph itself
```

**From the API.** With the backend running, `$API` being the address it printed:

```bash
curl "$API/repo/tree?url=/path/to/project"   # a local directory's tree; a GitHub URL works too
```

The [API reference](api.md) describes each route. The running server lists
those in its OpenAPI schema at `$API/docs`; the WebSockets and the few routes
kept out of the schema are only in the reference.

## A tour of the window

The browser suite's tour, `web/tests/e2e/tour.spec.ts`, walks the window's
main states, from a first visit to a drawn graph and its rings, and attaches a
screenshot of each to the suite's report:

```bash
cd web && npx playwright test tour && npx playwright show-report
```

It starts its own servers, on ports that are not the defaults. The Web workflow
keeps the same report from each of its runs for seven days, as the artifact
`browser-suite-report-with-tour-screenshots`.

## GitHub token

Run `gh auth login` once and the server reads its token; [Services](services.md#github-token)
gives the full order the server tries.

## Next

- [Architecture](architecture.md): how the pieces fit
- [Extending](extending.md): adding a parser, renderer, panel or route
- [`AGENTS.md`](../AGENTS.md): how a change is made here, the test commands and
  the gates
