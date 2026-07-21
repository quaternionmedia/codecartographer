# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
│              (http://localhost:5173 via Vite dev)                │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP / SSE
┌─────────────────────────▼───────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                       Routers                            │    │
│  │  /parse  /repo  /plotter  /c-parser  /pam  /db (opt)   │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                      Services                            │    │
│  │  UnifiedParserService  GitHubService  CacheService       │    │
│  │  PositionService       CParserService                    │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                      Parsers                             │    │
│  │  PythonLanguageParser  CLangaugeParser                   │    │
│  │  RegexLanguageParser   (20 languages, Phase 1 regex)    │    │
│  └─────────────────────────┬───────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                    Data Sources                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Local Files  │  │   GitHub     │  │   MongoDB (optional) │  │
│  │  (Filesystem)│  │     API      │  │     (graphbase)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Package Structure

```
codecarto/
├── main.py                # FastAPI app, router registration
│
├── routers/               # HTTP endpoint handlers
│   ├── unified_parser_router.py  # /parse/*  (all languages, SSE streaming)
│   ├── plotter_router.py         # /plotter/demo + /render/html
│   ├── repo_router.py            # /repo/*   (GitHub tree, local paths)
│   ├── c_parser_router.py        # /c-parser/* (libclang semantic parse)
│   └── pam_router.py             # /pam/*    (PAM log monitor, WebSocket)
│
├── services/
│   ├── unified_parser_service.py  # orchestrates all language parsing
│   ├── github_service.py          # GitHub API + size-tier repo fetching
│   ├── cache_service.py           # filesystem + optional MongoDB cache
│   ├── graph_serializer.py        # NetworkX → gJGF
│   ├── position_service.py        # layout registry (spring, compound …)
│   ├── c_parser_service.py        # C-specific service layer
│   └── parsers/
│       ├── language_parser.py          # LanguageParser Protocol + ParserRegistry
│       ├── python_language_parser.py   # Python (custom AST visitor)
│       ├── c_language_parser.py        # C/H (libclang adapter, batch_whole_tree)
│       ├── c_parser.py                 # libclang core
│       ├── regex_language_parser.py    # 20-language regex adapter (Phase 1)
│       └── pam_parser.py              # PAM log parser
│
├── models/
│   ├── source_data.py       # File, Folder, Directory
│   └── custom_layouts/
│       └── compound_layout.py  # 3-pass hierarchical layout
│
└── static/                # Bundled HTML assets (c-visualizer, pam-frontend)
```

## Frontend Structure

```
web/src/
├── layout/
│   ├── golden_layout_shell.ts   # GL bootstrap; "+" add-window; layout save/restore
│   ├── layout_context.ts        # shared state hub for all GL panels
│   ├── panel_registry.ts        # panel definitions (id/config/mount) — add panels here
│   ├── default_layout.ts        # built-in panel arrangement
│   └── panels/
│       ├── graph_panel.ts           # D3/vis-network canvas
│       ├── file_tree_panel.ts       # repo + upload file browser
│       ├── upload_panel.ts          # local file dropzone
│       ├── repo_panel.ts            # GitHub URL fetch + recent/examples
│       ├── graphbase_panel.ts       # durable named bookmarks (MongoDB)
│       ├── graph_settings_panel.ts  # styling/layout controls
│       └── actions_panel.ts         # plot/cancel/status
│
├── features/graph/
│   ├── services/
│   │   ├── graph_renderer.ts        # static D3 renderer
│   │   ├── streaming_renderer.ts    # progressive SSE renderer
│   │   ├── compound_layout.ts       # CompoundLayoutManager (bounding circles + child map)
│   │   └── renderers.ts             # renderer registry
│   └── extensions/                  # drag, zoom, select, highlight, tooltip, color
│
├── state/
│   ├── types.ts             # GraphStylingOptions, app state shapes
│   ├── api_base.ts          # API endpoint base URLs
│   └── state_controller.ts  # Meiosis cell wrapper
│
└── services/
    ├── plot_service.ts          # SSE stream helpers
    ├── repo_service.ts          # repo tree fetch/expand
    └── graphbase_service.ts     # /db/bookmarks client
```

## Data Flow

### Unified parse path (all languages, depth=2)

```
User submits URL / clicks Plot
  │
  ▼
PlotService.streamFromUrl() → POST /parse/stream-url  (SSE)
  │
  ▼
UnifiedParserService.stream_parse_url()
  │── fetch GitHub tree (3-tier size: full / structure / shallow)
  │── walk folder: depth-0 dir nodes, depth-1 file nodes
  │── per language: ParserRegistry.get(ext) → parser.parse_files()
  │     regular parsers: per-file dispatch
  │     batch_whole_tree parsers (C/H): collect all, parse once via asyncio.to_thread
  │── compute layout (NetworkX → PositionService)
  │── SSE: meta → nodes (BFS) → edges → done
  │
  ▼
StreamingGraphRenderer (frontend rAF loop)
  │── addNode() per SSE 'node' event → pop-in animation
  │── addEdge() per SSE 'edge' event
  │── finalize() on 'done' → fit view + draw compound backgrounds
```

## Key Architectural Decisions

All non-obvious structural choices are documented as ADR drafts in
`docs/qm/adr/` (on this repo's `project/codecartographer` branch of the
`quaternionmedia/qm` submodule) following its governance discipline
(see `docs/qm/adr/README.md`). Short index:

| ADR | Decision |
|-----|----------|
| *Parser/cache unification* | Deleted legacy router generations; `batch_whole_tree` opt-in for cross-file C parsing |
| *Golden Layout as primary shell* | Replaced monolithic `codecarto.ts`; panel registry in `panel_registry.ts` |
| *Compound hierarchical layout* | 3-pass dirs→files→symbols orbit algorithm |
| *CacheService vs graphbase* | TTL'd content-addressed cache vs. user-named durable store — kept separate |
| *GL panel registry + add-window menu* | Generalized from hardcoded map; real `LayoutManager` import fixed restore bug |
| *D3 hierarchy layout improvements* | Hierarchical drag, per-depth labels, cumulative spread scaling |

## Extension Points

### Adding a New Language Parser (fastest path)

Add a `_PATTERNS` list and one entry in `_LANGUAGES` in
`codecarto/services/parsers/regex_language_parser.py`.
The new extensions appear in `/parse/languages` immediately.
See `docs/llm/EXTENDING.md` for the full guide including the
`batch_whole_tree` option for cross-file languages.

### Adding a New GL Panel

Add one entry to `PANEL_DEFINITIONS` in
`web/src/layout/panel_registry.ts` (id, title, GL config, mount fn).
It automatically appears in the "+" add-window menu.

### Adding a New Renderer

Implement `IGraphRenderer`, register in
`web/src/features/graph/services/renderers.ts`.

### Adding a New Graph Layout

Add `my_layout(G: nx.DiGraph) -> dict` in
`codecarto/models/custom_layouts/`, import inside `add_custom_layouts()`
in `position_service.py`, register with `params=["graph"]`.

## Architecture Decision Records

For the *why* behind non-obvious structural choices, see [`docs/qm/adr/`](qm/adr/README.md).
