# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
│              (http://localhost:1234 via Vite dev)                │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP / SSE
┌─────────────────────────▼───────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                       Routers                            │    │
│  │  /parse /repo /plotter /c-parser /pam /lexicon /palette │    │
│  │  /topology /capabilities /overview /estate  /db (opt)   │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                      Services                            │    │
│  │  UnifiedParserService  GitHubService  CacheService       │    │
│  │  PositionService       CParserService   LexiconService   │    │
│  │  topology_service  capability_service  overview_service  │    │
│  │  estate_service (the seam registry)   qmcp_client        │    │
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
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ qmcp (HTTP)  │  │ governance/qm│  │ dossier's overview   │  │
│  │ the harness  │  │ the registry │  │ seam (a file)        │  │
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
│   ├── pam_router.py             # /pam/*    (PAM log monitor, WebSocket)
│   ├── lexicon_router.py         # /lexicon/* (hand-authored ontologies, as graphs)
│   ├── palette_router.py         # /palette/*
│   ├── topology_router.py        # /topology/*     the harness's shapes, as GraphData
│   ├── capability_router.py      # /capabilities/* the corpus's registry, as GraphData
│   ├── overview_router.py        # /overview/*     dossier's seam, as GraphData
│   ├── estate_router.py          # /estate/seams   every seam above, identified or not
│   └── app_router.py             # /app, the built front end on the API's origin
│
├── services/
│   ├── unified_parser_service.py  # orchestrates all language parsing
│   ├── github_service.py          # GitHub API + size-tier repo fetching
│   ├── cache_service.py           # filesystem + optional MongoDB cache
│   ├── graph_serializer.py        # NetworkX → gJGF
│   ├── position_service.py        # layout registry (spring, compound …)
│   ├── c_parser_service.py        # C-specific service layer
│   ├── lexicon_service.py         # lexicon YAML -> graph; lexicon_bridge.py joins parsed nodes to layers
│   ├── qmcp_client.py             # the seam to the harness: a URL and a JSON shape, never an import
│   ├── topology_service.py        # harness payload -> networkx -> GraphSerializer
│   ├── capability_service.py      # registry YAML -> networkx -> GraphSerializer
│   ├── overview_service.py        # overview seam -> networkx -> GraphSerializer
│   ├── estate_service.py          # the seam registry: identity probes, the liveness table
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
│       ├── graph_panel.ts           # the one canvas
│       ├── file_tree_panel.ts       # repo + upload file browser
│       ├── upload_panel.ts          # local file dropzone
│       ├── repo_panel.ts            # GitHub URL fetch + recent/examples
│       ├── graphbase_panel.ts       # durable named bookmarks (MongoDB)
│       ├── graph_settings_panel.ts  # styling/layout controls
│       ├── actions_panel.ts         # plot/cancel/status
│       ├── estate_panel.ts          # every seam, live or not, with the way to its panel
│       ├── topology_panel.ts        # choose a harness flow; the drawing goes to the canvas
│       ├── capabilities_panel.ts    # the registry's declarations; draw them
│       └── overview_panel.ts        # dossier's masthead and sections; draw them
│
├── features/estate/                 # what every estate panel shares
│   ├── seam_client.ts               # the four outcomes a seam can answer, told apart (pure; tested under node)
│   ├── estate_service.ts            # the URLs and document shapes
│   ├── problem_view.ts              # the one "nothing was drawn" component
│   └── provenance.ts                # source and caveat, above the controls
│
├── features/graph/
│   ├── services/
│   │   ├── streaming_renderer.ts    # the D3 canvas — every graph draws here
│   │   ├── d3_renderer.ts           # registry entry; hands a finished graph to the above
│   │   ├── graph_surface.ts         # announces the live canvas so rad/legend can attach
│   │   ├── graph_types.ts           # GraphNode / GraphEdge / GraphData
│   │   ├── compound_layout.ts       # CompoundLayoutManager (bounding circles + child map)
│   │   └── renderers.ts             # renderer registry (gravis, notebook, system)
│   ├── extensions/                  # BaseExtension seam; legend mounts here
│   └── rad/                         # the radial menu, conformant to rad's vectors
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

## Calculated, stored, displayed

Every figure on the screen was calculated somewhere, may have been stored
somewhere, and is displayed here. The three are different places with
different owners, and a window that blurs them is how two windows onto one
estate start disagreeing. `tests/test_boundaries.py` is the check; this is the
statement.

| | who calculates | who stores | who displays |
|---|---|---|---|
| **Code maps** (`/parse`, `/repo`) | this backend: parsers produce nodes and edges, `PositionService` lays them out, `GraphSerializer` sizes by degree | `CacheService` — content-addressed, keyed by url + mode + layout + extensions, filesystem or MongoDB; `graphbase` for named bookmarks (separate store, separate decision) | the one canvas, `StreamingGraphRenderer`; the legend counts what was drawn |
| **Topologies** (`/topology`) | the harness declares shapes (boxes, arrows, no coordinates) and measures relation weights from its archive; this backend resolves the *encoding* — width from strength, dashed from unmeasured, colour from kind — and lays out | nothing here. Read live on every request; the harness stores its own archive and its own runs | the canvas draws exactly the channels `topology_service` resolved; the panel shows the harness's caveat verbatim |
| **Capabilities** (`/capabilities`) | the corpus's registry states claims; this backend counts nothing but the rungs naming no evidence, and lays out | nothing here; the registry is the corpus's file at the governance pin | the canvas; the panel lists the claims as stated, with who stated them and when |
| **Overview** (`/overview`) | dossier builds masthead figures and sections from its database and writes them as a seam; this backend draws the one relation the seam states (a section lists a subject) and lays out | dossier's seam file — a snapshot; this window reads it and never writes it | the canvas; the panel shows the masthead as written, with the producer's own `note` beside each figure, and when the reading was made |
| **Liveness** (`/estate/seams`) | this backend probes each seam for a document whose shape it knows | nothing | the Estate panel, one row per seam, the server's `ok` and the server's sentence |

**Rules, and where each was learned.**

1. **The window calculates two things and no more: a layout, and the palette's
   vocabulary for a kind.** Layouts are `PositionService`; the vocabulary is
   `palette_service.vocabulary`, the one place a kind becomes a shape, colour
   and size (three services once held three private copies). The serializer
   does not apply the palette, which is why a service carries the result; the
   right eventual home is the serializer, so a service sets `type` alone.
2. **A calculation does not depend on how the caller spelled its name.**
   `layout_key` normalises once and everything downstream keys on the result.
   The same layout used to come out five times larger for `Kamada_Kawai` than
   for `Kamada Kawai`, and `compound_layout` — the menu's own name — raised.
3. **A data document carries no display constants.** Three hex colours rode in
   the topology metadata and the front end overwrote them on arrival. The canvas
   themes itself from the application's tokens.
4. **The estate services and panels store nothing.** No cache, no database, no
   `localStorage`. What a panel remembers between renders is application state
   and is gone with the tab. The one thing persisted on this side of the estate
   is the saved Golden Layout arrangement, which is a fact about the window and
   not about the estate.
5. **A panel displays the producer's figures and may count the rows it was
   handed; it never derives a figure the producer also states.** The caveat is
   shown verbatim. `unmeasured`, `live`, `surveyed` are read, not recomputed. A
   panel may map a stated figure to a style (`is-partial` when `unmeasured > 0`)
   — that is display, not calculation.
6. **A seam that cannot be drawn as asked is a sentence.** An unknown layout
   answers 200 with `unreadable`, the registry's own message and the registered
   names; nothing in an estate router raises to the browser.
7. **A layout choice is a choice about the graph on the canvas, whichever seam
   drew it.** Every panel that draws goes through `LayoutContext.plotWith`, so
   changing the layout in Graph Settings — or rad's `relayout` — re-runs the
   last draw with the new one. The estate draws were once not remembered, and
   the setting changed while the canvas did not.
8. **One translation between the menu's names and the backend's.**
   `layout_names.ts` strips `_layout` and capitalises; there is no fallback.
   Two hand tables used to fall back to `Spring` for any name they did not
   list.

**What a reader should still not expect.** That a seam's *content* is right —
the probes say a seam is there and is what this window expects, and each seam's
own caveat says what it could not see. And that a producer's figure is current:
the overview panel shows when the reading was made (the producer's stamp when
the seam carries one, else the file's time, named as such) so a stale number is
delivered with its date.

## Key Architectural Decisions

All non-obvious structural choices are documented as ADR drafts in
`governance/qm/adr/` (on this repo's `project/codecartographer` branch of the
`quaternionmedia/qm` submodule) following its governance discipline
(see `governance/qm/adr/README.md`). Short index:

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

For the *why* behind non-obvious structural choices, see [`governance/qm/adr/`](../governance/qm/adr/README.md).
