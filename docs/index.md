# Codecarto Documentation

> Multi-language source code visualization tool — parses repos into interactive D3 graphs.

## Quick Links

| Document | Description |
|----------|-------------|
| [Getting Started](getting-started.md) | Installation and first run |
| [CLI Reference](cli.md) | Command-line interface |
| [API Reference](api.md) | REST API endpoints, including the estate seams |
| [Architecture](architecture.md) | High-level system design |
| [Services](services.md) | The service layer, module by module |
| [Contributing](../.github/CONTRIBUTING.md) | Development guidelines |

The plan this window is built to -- the estate frame, the topology designer, and
the chrestomathy of code -- is `plans/the-web-window.md` in the governance corpus
(`governance/qm` once the pin carries it).

## LLM / AI Context

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](llm/ARCHITECTURE.md) | Detailed component architecture, data flows, parser internals |
| [EXTENDING.md](llm/EXTENDING.md) | How to add language parsers, renderers, and endpoints |
| [UI_REFERENCE.md](llm/UI_REFERENCE.md) | Control panel, Golden Layout shell, radial menu, streaming renderer |
| [RENDERER_GUIDE.md](llm/RENDERER_GUIDE.md) | Renderer plugin system — D3, Gravis, Notebook, System |
| [LARGE_REPOS.md](llm/LARGE_REPOS.md) | Scaling roadmap (phases 1–6) |

## Roadmap

| Document | Description |
|----------|-------------|
| [roadmap/lexicon.md](llm/roadmap/lexicon.md) | Language lexicons on abstraction layers -- C, Python and Rust -- and the construct vocabulary the chrestomathy reads |
| [roadmap/rust.md](llm/roadmap/rust.md) | Rust, Cargo, linker scripts and the construct vocabulary the chrestomathy reads |
| [roadmap/topology-functionality-abstraction-maps.md](llm/roadmap/topology-functionality-abstraction-maps.md) | What maps of code and of systems already mean here, and what is open |
| [roadmap/c_parser_phase3_compile_commands.md](llm/roadmap/c_parser_phase3_compile_commands.md) | C parser phase 3 — compile_commands.json support |

---

## What is Codecarto?

Codecarto parses source code repositories into interactive graph visualizations:

- **Multi-language**: Python by AST, C/H by libclang, Rust and linker scripts by structural readers, and a regex parser per language for the rest -- `GET /parse/languages` lists every extension
- **Streaming**: nodes stream progressively via SSE as each file is parsed
- **Compound layout**: directories, files, and symbols in nested hierarchical orbits
- **Interactive**: drag nodes, right-click radial menu, zoom/pan, group outline circles

## Quick Start

```bash
git clone https://github.com/quaternionmedia/codecartographer.git
cd codecartographer
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

uv run codecarto dev
```

Open `http://localhost:1234` for the web UI; `codecarto dev` prints the API address and its `/docs`.

## Documentation Structure

```
docs/
├── index.md              ← this file
├── getting-started.md
├── cli.md
├── api.md
├── architecture.md
├── services.md
└── llm/                  ← LLM-optimized context docs
    ├── ARCHITECTURE.md
    ├── EXTENDING.md
    ├── RENDERER_GUIDE.md
    ├── UI_REFERENCE.md
    ├── LARGE_REPOS.md
    └── roadmap/          ← upcoming features
```
