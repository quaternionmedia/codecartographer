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
│  │  /cargo /system /auth                                   │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                      Services                            │    │
│  │  UnifiedParserService  GitHubService  CacheService       │    │
│  │  PositionService       CParserService   LexiconService   │    │
│  │  topology_service  capability_service  overview_service  │    │
│  │  estate_service (the seam registry)   qmcp_client        │    │
│  │  construct_service (what a node is, across languages)    │    │
│  │  cargo_service (manifests and what cargo wrote)          │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                      Parsers                             │    │
│  │  PythonLanguageParser  CLangaugeParser                   │    │
│  │  RustLanguageParser    LinkerScriptParser                │    │
│  │  RegexLanguageParser   (one regex adapter per language)  │    │
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
│   ├── system_router.py          # /system/* a system diagram derived from a sibling clone
│   ├── lexicon_router.py         # /lexicon/* (lexicons, the construct vocabulary, the chrestomathy)
│   ├── cargo_router.py           # /cargo/*  a Cargo workspace and its recorded build, as GraphData
│   ├── palette_router.py         # /palette/*
│   ├── topology_router.py        # /topology/*     the harness's shapes, as GraphData
│   ├── capability_router.py      # /capabilities/* the corpus's registry, as GraphData
│   ├── overview_router.py        # /overview/*     dossier's seam, as GraphData
│   ├── estate_router.py          # /estate/seams   every seam above, identified or not
│   └── app_router.py             # /app, the built front end on the API's origin
│                                 # (/auth/github is declared in main.py itself)
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
│   ├── construct_service.py       # what a node *is* across languages; the chrestomathy
│   ├── cargo_service.py           # manifests + what cargo recorded -> networkx; never runs cargo
│   └── parsers/
│       ├── language_parser.py          # LanguageParser Protocol + ParserRegistry
│       ├── python_language_parser.py   # Python (custom AST visitor)
│       ├── c_language_parser.py        # C/H (libclang adapter, batch_whole_tree)
│       ├── c_parser.py                 # libclang core
│       ├── rust_language_parser.py     # Rust, item level (tokenizer, batch_whole_tree)
│       ├── linker_script_parser.py     # GNU ld scripts and memory.x
│       ├── regex_language_parser.py    # one regex adapter per language
│       └── pam_parser.py              # PAM log parser
│
├── models/
│   ├── source_data.py       # File, Folder, Directory
│   └── custom_layouts/
│       └── compound_layout.py  # 4-pass hierarchical layout
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
│   └── panels/                  # one file per panel; docs/ui.md describes each
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
│   ├── extensions/                  # drag, zoom, selection, highlight, tooltip, colour, legend
│   └── rad/                         # the radial menu, conformant to rad's vectors
│
├── state/
│   ├── types.ts             # GraphStylingOptions, app state shapes
│   ├── api_base.ts          # API endpoint base URLs
│   └── state_controller.ts  # Meiosis cell wrapper
│
└── services/
    ├── plot_service.ts          # SSE stream helpers
    └── graphbase_service.ts     # /db/bookmarks client

web/src/features/repository/services/
    └── repo_service.ts          # repo tree fetch/expand
```

## The unified graph

Every parser produces nodes in one schema, so any renderer draws any language
without negotiating a format. `make_node()` and `make_edge()` in
`codecarto/services/parsers/language_parser.py` build them; the fields, and
how a renderer reads them, are in [Extending](extending.md#the-node-schema).

| depth | meaning | node id |
|-------|---------|---------|
| 0 | directory | `dir::<path from the root>` |
| 1 | file | `file::<path from the root>` |
| 2 | top-level symbol | the parser's own |
| 3 | sub-symbol (argument, field, enum constant) | the parser's own |

Each language adapter implements the `LanguageParser` protocol
(`language`, `extensions`, `parse_files(files, depth)`) and registers itself
with `ParserRegistry` when `codecarto/services/parsers/__init__.py` imports
it. The registry
maps an extension to its parser; `GET /parse/languages` lists every one.

**`batch_whole_tree`.** By default the walk (`_walk_folder`) hands a parser one
file at a time. A parser that sets `batch_whole_tree = True` (C, Rust, linker
scripts) instead receives every file it owns across the whole tree in one
`parse_files` call, made after the walk (`_parse_pending_batches`). C needs
this because a call is resolved to a function that may be declared in another
file, which takes the complete file set in one `CParser` call.

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
  │     batch_whole_tree parsers: collect all, parse once via asyncio.to_thread
  │── compute layout (NetworkX → PositionService)
  │── SSE: meta → nodes (BFS) → edges → done
  │
  ▼
StreamingGraphRenderer (frontend rAF loop)
  │── addNode() per SSE 'node' event → pop-in animation
  │── addEdge() per SSE 'edge' event
  │── finalize() on 'done' → fit view + draw compound backgrounds
```

A local directory takes the same path through `POST /parse/stream`
(`UnifiedParserService.stream_parse`). Either is replayed from `CacheService`
when the same url, mode, layout and extensions were parsed before.

### Expanding one node

`POST /parse/expand` (`UnifiedParserService.expand_node`) returns a file
node's sub-graph to the requested depth; `LayoutContext` merges it into the
graph on the canvas, using the directory the last parse read. The
[UI reference](ui.md) says where Expand is.

### C: two pipelines

C and C++ are read by libclang (`c_parser.py`'s `CParser`, the `c-parsing`
extra) through two routes that share that engine.

**Through `/parse/*`, like every other language.** `CLangaugeParser`
(`c_language_parser.py`) is a `batch_whole_tree` adapter, so cross-file `CALLS`
resolve. Content with no file on disk -- a GitHub file, which exists only as
`File.raw` -- is passed to libclang as `unsaved_files` under a virtual path.
Every virtual file in a batch shares one root (`_VIRTUAL_ROOT`), so a sibling
`#include "x.h"` resolves; an include through a subdirectory
(`#include "sub/x.h"`) does not, because the virtual tree is flat. In
`stream_parse_url`, structure streams at once and the batch parse runs in
`asyncio.to_thread`, so a C-heavy repository does not block the server; its
symbols arrive as one burst after every file of the batch has been fetched and
parsed, with no progress signal in between.

**Through `/c-parser/*`, the dedicated pipeline.** These routes answer a flat
`{nodes, edges, meta}` rather than gJGF; the web application does not call
them. `/c-parser/stream-github` runs the parse in a background thread
(`start_threaded_feeder`, the pattern the PAM log tailers share) and streams
each file's declarations as libclang finishes it. Calls and the derived type
edges (`FIELD_OF`, `POINTS_TO`) need the complete node set, so they arrive in
one batch at the end:

```
POST /c-parser/stream-github  (SSE)
  │
  ▼
c_parser_router.stream_c_github()
  │── background thread: CParserService.parse_github(url, on_progress=...)
  │     │── download + extract the archive (or reuse Cache B)  -> 'fetching'
  │     │── skip platform-specific compat files                -> 'meta'
  │     │── CParser.parse_files() pass 1, one file at a time   -> on_file_parsed
  │     └── pass 2 (cross-file CALLS) + type-edge derivation
  │
  ▼
the request coroutine drains the queue: 'node' events as the thread produces
them, then 'reposition', every 'edge', and 'done'
```

Both pipelines put `has_parse_warning` at the top level of a node rather than
under `meta`, so the canvas reads it in one place whichever produced the node.

## The two caches

Both live under `~/.codecarto/cache/repos/`, kept as two caches because a hit
in each skips different work:

| | Cache A (`CacheService`) | Cache B (`CParserService`'s repo cache) |
|---|---|---|
| Caches | repository trees and parsed graphs | extracted source trees (the unzipped GitHub archive) |
| Location | `{repo_key}/tree.json` and `{repo_key}/graphs/{hash}.json`; `index.json` lists the graphs | `{owner}-{repo}/src/` and `metadata.json` |
| Key | `repo_key` is `{owner}-{repo}` for GitHub, `sha256(url)[:16]` otherwise; a graph is `{repo_key}::{sha256(url, mode, layout, extensions)[:16]}` | `{owner}-{repo}` |
| Freshness | `CC_CACHE_TTL` seconds (24 h by default) | the same variable |
| A hit skips | fetching (a tree) or parsing (a graph) | the download and extract; the parse still runs |
| List / evict | `GET /parse/cache`, `DELETE /parse/cache/{key}`; `CacheService.evict_repo` drops a repository's tree and graphs | `GET /c-parser/cache`, `DELETE /c-parser/cache/{key}` |
| Used by | `/repo/tree`, `/repo/subtree`, `/repo/expand-all` (trees); `/parse/unified`, `/parse/stream`, `/parse/stream-url`, `/c-parser/stream-github` (graphs) | `/c-parser/github`, `/c-parser/stream-github` |

A tree in Cache A holds what `github_service.get_raw_from_repo` fetched for the
repository's size tier: full content under about 5 MB, structure only under
about 50 MB, a shallow listing above that. `stream_parse_url` uses a cached
tree in place of a fetch only when it is complete and carries content. With
`MONGODB_URI` set, Cache A's graphs are also kept in MongoDB, keyed the same
way, and the filesystem remains the fallback.

## The graphbase store

`graphbase` is a separate, user-named store, mounted at `/db` only when
`MONGODB_URI` is set; `GET /db/` answers `available: false` otherwise. It is a
submodule; `codecarto/` imports it as `from graphbase import graphdb, get_db`.
Its collections:

| Collection | Holds | Key | Eviction |
|------------|-------|-----|----------|
| `graph` | named NetworkX graphs (`nx.node_link_data`) | `name` | manual |
| `snapshots` | a rendered graph's gJGF nodes and edges, replayed without a parse | `name` | manual |
| `bookmarks` | a URL and its parse settings, re-streamed on load | `name` | manual |
| `history` | per-URL render snapshots, appended when tracking is on | `(url_hash, captured_at)` | automatic, 20 per URL |

`web/src/services/graphbase_service.ts` is the client; the Graphbase panel is
in the [UI reference](ui.md). The routes are in [the API reference](api.md).

## Compound layout

`compound_layout` (`codecarto/models/custom_layouts/compound_layout.py`,
registered in `position_service.py` with `params=["graph"]`) places a code map
in four passes:

1. **Directories**: a spring layout of the directory nodes, stretched
   horizontally (`x_stretch` 1.6, `y_stretch` 0.7) and scaled so no two
   clusters overlap.
2. **Files**: an even ring around their directory.
3. **Symbols**: a 300° arc around their file, in source order: sorted by
   `line`, line 1 at 12 o'clock, later lines clockwise, and a 60° gap at 6
   o'clock.
4. **Sub-symbols**: the same arc around their nearest depth-2 ancestor; a
   module-level statement with none orbits its file just outside the symbol
   ring.

A node's parent is the source of its `contains` or `field_of` edge (the C
parser's kind for a struct's fields); a node with neither falls back to its
`file` attribute, then to a ring of orphans at its level. One layout unit is
about 100 px in the browser (`GraphSerializer`'s `spread`).

On the canvas, `CompoundLayoutManager` (`web/src/features/graph/services/compound_layout.ts`)
draws a translucent circle behind each directory's and each file's group,
assigning children by the same containment edges and by nearest position only
for an orphan. `computeChildrenMap` covers all four tiers, so dragging a node
moves its whole subtree. The circles are drawn only for `compound_layout`, in a
`<g class="compound-backgrounds">` that is the transform group's first child,
so they sit behind links and nodes. Where the layout and its outline toggle
are chosen is in the [UI reference](ui.md).

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
| **Cargo workspaces** (`/cargo`) | cargo resolves the workspace and rustc checks it, when a person runs `codecarto cargo record`; this backend reads the manifests and those documents, counts diagnostics per target, measures each recorded link map's region use, and lays out | the two documents, in the workspace's own `target/codecarto/`, written on a person's command; nothing on this side | the canvas; the Cargo panel names the engine that answered and each document's age and staleness |
| **Chrestomathy** (`/lexicon/chrestomathy`) | nothing new: the hand-authored construct vocabulary and lexicons are read and laid out | the YAML files, shipped in the package | the canvas, tokens coloured from the one layer ramp; the panel's table, a language with no spelling included |

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
9. **A construct's look is the code map's visual grammar, said once.** Parsers
   own how their nodes look; `constructs.yaml` is where looks shared across
   languages live, and a node keeps any look its parser gave it. The estate
   palette (rule 1) is a different vocabulary for a different kind of graph.
   **And every graph says what its nodes are**: `GraphSerializer` stamps each
   node's construct for every route, a cached graph is stamped again as it is
   replayed, and `construct_service.stamp` is the one place the decision is
   made -- the census (`/lexicon/chrestomathy/census`) that reads a drawn graph
   as a chrestomathy calls it too, and the client never decides a construct.
10. **The window runs nothing it reads.** Running cargo runs a workspace's build
    scripts, proc macros and configured `rustc`, so no route does: a person runs
    `codecarto cargo record`, and the window reads what it wrote with its age.
    A recorded resolution older than a manifest is not used, and says so.

**What a reader should still not expect.** That a seam's *content* is right —
the probes say a seam is there and is what this window expects, and each seam's
own caveat says what it could not see. And that a producer's figure is current:
the overview panel shows when the reading was made (the producer's stamp when
the seam carries one, else the file's time, named as such) so a stale number is
delivered with its date.

## Known limitations

**A popped-out panel is empty.** Golden Layout opens a popped-out panel in a
new browser window, which loads the page and redraws the frame, but the
component factories are bound to the first window's Mithril instance and are
not registered again in the new one, so nothing mounts. `popInOnClose`
(`default_layout.ts`) returns the panel to the main window when the pop-out is
closed. Mounting in the new window needs Golden Layout's virtual-layout or
binding-context API.

## Key Architectural Decisions

All non-obvious structural choices are documented as ADR drafts in
`governance/qm/adr/` (on this repo's `project/codecartographer` branch of the
`quaternionmedia/qm` submodule) following its governance discipline
(see `governance/qm/adr/README.md`). Short index:

| ADR | Decision |
|-----|----------|
| *Parser/cache unification* | Deleted legacy router generations; `batch_whole_tree` opt-in for cross-file C parsing |
| *Golden Layout as primary shell* | Replaced monolithic `codecarto.ts`; panel registry in `panel_registry.ts` |
| *Compound hierarchical layout* | 4-pass dirs→files→symbols→sub-symbols orbit algorithm |
| *CacheService vs graphbase* | TTL'd content-addressed cache vs. user-named durable store — kept separate |
| *GL panel registry + add-window menu* | Generalized from hardcoded map; real `LayoutManager` import fixed restore bug |
| *D3 hierarchy layout improvements* | Hierarchical drag, per-depth labels, cumulative spread scaling |

## Extension Points

[Extending](extending.md) has the steps for each: a language parser (the
fastest is one entry in `regex_language_parser.py`'s `_LANGUAGES`), a renderer,
a styling option, a canvas extension, a route, and a system diagram. A panel is
one entry in `PANEL_DEFINITIONS` (`web/src/layout/panel_registry.ts`). A layout
is a function `my_layout(G) -> dict` in `codecarto/models/custom_layouts/`,
added in `position_service.py`'s `add_custom_layouts()` with
`params=["graph"]`.

## Architecture Decision Records

For the *why* behind non-obvious structural choices, see [`governance/qm/adr/`](../governance/qm/adr/README.md).
