# Codecarto

Codecarto reads a codebase and draws it as a graph you can explore: folders, files, and the functions and types inside them.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

It reads Python, C and Rust in depth and many other languages at the level of
their top-level definitions. The graph streams into the browser as each file is
parsed, laid out as nested clusters: folders around their files, files around
their symbols. It also draws a Cargo workspace's crates, a linker script's
memory map, and one programming construct set beside itself across languages.

## Start

In a clone of this repository, with Python, [uv](https://docs.astral.sh/uv/) and Node.js:

```bash
uv sync --locked --extra dev --extra c-parsing   # install
uv run codecarto dev                             # run, then open http://localhost:1234
```

[Getting Started](docs/getting-started.md) has the prerequisites, the
submodules and a first graph.

## Where to go next

- [Getting Started](docs/getting-started.md): install, run, and draw a first graph
- [CLI](docs/cli.md): every `codecarto` command, option and environment variable
- [API](docs/api.md): the backend's routes. The running server lists every route
  at `/docs`. `docs/api.md` describes each one.
- [Architecture](docs/architecture.md): how the pieces fit
- [Extending](docs/llm/EXTENDING.md): adding a parser, renderer, panel or route
- [UI reference](docs/llm/UI_REFERENCE.md): the panels, the canvas and the menus
- Planned work is listed in [the roadmap](docs/llm/roadmap/README.md).
- [Contributing](.github/CONTRIBUTING.md) and [`AGENTS.md`](AGENTS.md): how a
  change is made here
- Decision records: `governance/qm/adr/`, in the governance submodule

## License

MIT License; see [LICENSE](LICENSE).
