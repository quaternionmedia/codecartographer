# Code Cartographer — AI Assistant Instructions

> Technical orientation for AI assistants working on this codebase. Read
> [`AGENTS.md`](../AGENTS.md) first: `.github/copilot-instructions.md` and
> `CLAUDE.md` point at it, and it carries the rules every change follows --
> pull requests, contributorship, decision records. `docs/llm/ARCHITECTURE.md`
> has the architecture in depth and `docs/llm/EXTENDING.md` the extension
> patterns. Where this page and the tree disagree, the tree is right: fix the
> page.

---

## Project Overview

**Code Cartographer** parses repositories into interactive D3 graphs of their
structure -- directories, files and symbols -- and draws the estate around them
(a harness's topologies, the corpus's capability registry, dossier's overview)
on the same canvas.

- **Stack**: Python (FastAPI) backend + TypeScript (Mithril.js + Golden Layout 2)
  frontend, built by Vite 8
- **Languages parsed**: Python (AST), C/H (libclang, the optional `c-parsing`
  extra), and 20 more through the regex parser
- **Primary parse flow**: POST `/parse/stream` → SSE → `StreamingGraphRenderer` → D3 canvas
- **Package managers**: `uv` (Python; `uv.lock` is the environment), `npm`
  (frontend; `web/package-lock.json`)
- **Versions**: Python 3.10+; Node.js 20.19+ or 22.12+ (Vite 8's minimum).
  `.github/workflows/copilot-setup-steps.yml` prepares Python 3.12 and Node 22.

---

## Quick Start

```bash
uv sync --extra dev               # the lockfile is the environment
cd web && npm ci && cd ..         # the frontend's lockfile

uv run codecarto dev              # backend + frontend
uv run codecarto serve            # backend only, reloading on change
uv run codecarto web              # frontend only, http://localhost:1234
cd web && npm run build           # typecheck, then the production build
```

**The backend's port is `codecarto.cli.DEFAULT_PORT`, and it is not 8000.**
`serve --help` prints it, `CODECARTO_PORT` or `--port` moves it, and `/docs` on
that address lists every route the backend registered. Other servers run on
this workstation: before trusting an answer, check that `/openapi.json` names
the application `codecarto`.

---

## Directory Structure

```
codecartographer/
├── codecarto/                         # Python backend package
│   ├── main.py                        # FastAPI app + router registration (the prefixes live here)
│   ├── cli.py                         # `codecarto` -- dev, serve, web, repo, lint, …; DEFAULT_PORT
│   ├── routers/
│   │   ├── unified_parser_router.py   # /parse/* (main parse endpoints)
│   │   ├── repo_router.py             # /repo/* (GitHub tree + local paths)
│   │   ├── c_parser_router.py         # /c-parser/* (libclang optional)
│   │   ├── plotter_router.py          # /plotter/demo + /render/html
│   │   ├── pam_router.py              # /pam/* (PAM log monitor)
│   │   ├── lexicon_router.py          # /lexicon/* (hand-authored ontologies, as graphs)
│   │   ├── palette_router.py          # /palette/*
│   │   ├── topology_router.py         # /topology/* (the harness's flows)
│   │   ├── capability_router.py       # /capabilities/* (the corpus's registry)
│   │   ├── overview_router.py         # /overview/* (dossier's seam)
│   │   ├── estate_router.py           # /estate/seams (every seam, identified or not)
│   │   └── app_router.py              # /app (the built front end)
│   ├── services/
│   │   ├── unified_parser_service.py  # Directory walk + language dispatch
│   │   ├── graph_serializer.py        # NetworkX → gJGF (depth-aware sizing)
│   │   ├── cache_service.py           # Filesystem + MongoDB graph cache
│   │   ├── position_service.py        # Layout registry
│   │   ├── estate_service.py          # The seam registry
│   │   └── parsers/
│   │       ├── __init__.py                 # imports each parser, which registers itself
│   │       ├── language_parser.py          # LanguageParser Protocol + ParserRegistry
│   │       ├── python_language_parser.py   # .py adapter
│   │       ├── c_language_parser.py        # .c/.h adapter (batch_whole_tree)
│   │       └── regex_language_parser.py    # 20 more languages
│   └── models/
│       └── custom_layouts/
│           └── compound_layout.py          # hierarchical dirs → files → symbols layout
│
└── web/src/
    ├── index.html, index.ts           # the page and its entry
    ├── layout/                        # the Golden Layout shell
    │   ├── golden_layout_shell.ts     # builds the dock and the "+" menu; loads the saved or built-in layout
    │   ├── panel_registry.ts          # every dock panel, once -- a new panel is an entry here
    │   ├── default_layout.ts          # the built-in arrangement, and the settings every layout loads with
    │   ├── saved_layout.ts            # the check a saved arrangement passes before Golden Layout reads it
    │   ├── layout_context.ts          # the state, actions and callbacks every panel shares
    │   └── panels/                    # one Mithril component per panel (graph_panel, actions_panel, …)
    ├── components/codecarto/
    │   └── control_panel/             # the controls the Upload, Repository and Graph Settings panels render
    ├── features/
    │   ├── graph/
    │   │   ├── services/
    │   │   │   ├── streaming_renderer.ts  # The D3 canvas — every graph draws here
    │   │   │   ├── d3_renderer.ts         # Registry entry; hands it a finished graph
    │   │   │   ├── graph_surface.ts       # Announces the canvas; rad/legend subscribe
    │   │   │   ├── graph_types.ts         # GraphNode / GraphEdge / GraphData
    │   │   │   ├── compound_layout.ts     # CompoundLayoutManager + GroupBounds
    │   │   │   ├── layout_names.ts        # menu layout names → the backend's
    │   │   │   └── renderers.ts           # Renderer registry (gravis, notebook, system)
    │   │   ├── rad/                       # The radial menu, conformant to rad's vectors
    │   │   └── extensions/                # BaseExtension seam; the legend mounts here
    │   └── estate/                        # the seam client, problem view and provenance the estate panels share
    └── state/
        ├── cell_state.ts              # the Meiosis cell and the shape of its state
        ├── state_controller.ts        # the cell's wrapper
        ├── actions.ts                 # PlotActions and the rest: what changes the state
        └── types.ts                   # AppState, GraphStylingOptions, etc.
```

---

## Data Flow

```
User clicks Plot
    ↓
PlotService.streamUnified() → POST /parse/stream  (SSE, JSON body)
    ↓
UnifiedParserService.stream_parse(directory, depth=2)
    ├── Walk tree → depth-0 dir + depth-1 file nodes
    ├── ParserRegistry.get(ext) → language parser
    ├── parser.parse_files(files, depth=2) → nx.DiGraph (depth-2 symbol nodes)
    ├── compound_layout / spring_layout / … → {nodeId: (x, y)}
    └── Yield SSE: meta → nodes (BFS) → edges → done
    ↓
StreamingGraphRenderer (frontend rAF drain loop)
    ├── addNode() per SSE 'node' → pop-in animation
    ├── addEdge() per SSE 'edge'
    └── finalize() on 'done' → fitView + drawCompoundBackgrounds()
    ↓
D3 canvas: reads node.shape / node.color set by parser;
           falls back to depth/kind heuristics when absent
```

---

## Unified Node Schema

All parsers produce nodes in this format (read directly by renderers):

```python
{
  "depth":    int,          # 0=dir, 1=file, 2=symbol, 3=sub-symbol
  "language": str,          # 'python' | 'c' | ...
  "kind":     str,          # 'directory'|'file'|'class'|'function'|'struct'|...
  "label":    str,          # human-readable name
  "file":     str,          # source file path (stem for C symbols)
  "line":     int,          # source line number
  "shape":    str | None,   # 'circle'|'square'|'diamond'|'hexagon'|'triangle'
  "color":    str | None,   # hex colour — parsers own visual grammar
}
```

**Parser-owned visual grammar**: parsers set `shape`/`color` so renderers need no language-specific logic. Renderers fall back to depth/kind heuristics only when these fields are absent.

---

## API Endpoints

`/docs` on the backend's own address is the authority. The README's table and
`docs/api.md` map it, and `tests/test_docs_routes.py` checks both against the
mounted routes.

| Prefix | Description |
|--------|-------------|
| `/parse` | **Unified parse** (all languages, recommended) |
| `/repo` | GitHub + local repository tree operations |
| `/c-parser` | C/H semantic parse (requires the `c-parsing` extra) |
| `/plotter` | `/demo` + `/render/html` (legacy + Notebook renderer) |
| `/pam` | PAM auth log monitor |
| `/lexicon` | Hand-authored language lexicons, as graphs |
| `/palette` | Colour palette management |
| `/topology` | The harness's flows, as graph data |
| `/capabilities` | The corpus's capability registry, as graph data |
| `/overview` | dossier's overview seam, as graph data |
| `/estate` | Every seam above, and whether each one is there |
| `/auth` | Which GitHub credential source is active |
| `/app` | The built web application |
| `/db` | Graphbase -- mounted only when `MONGODB_URI` is set |

### Key parse endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/parse/stream` | POST | Parse pre-fetched directory → SSE (`meta`/`node`/`edge`/`done`) |
| `/parse/unified` | POST | Same but blocking JSON response |
| `/parse/stream-url` | POST | Fetch GitHub repo + stream parse in one call |
| `/parse/expand` | POST | Expand a file node to reveal its symbols |
| `/parse/languages` | GET | List registered parser extensions |
| `/parse/cache` | GET | List cached parsed graphs |
| `/parse/cache/{key}` | DELETE | Evict one cached graph |

### SSE event types (`/parse/stream`)

| event | payload |
|-------|---------|
| `meta` | `{nodeCount, edgeCount, layout, from_cache?}` |
| `node` | flat node dict (unified schema) |
| `edge` | `{source, target, label?, …}` |
| `done` | `{elapsed_ms, from_cache?}` |
| `error` | `{message}` |

---

## UI Overview

The UI is one **Golden Layout shell**; `docs/llm/UI_REFERENCE.md` is its full
reference, default dock included. Every panel is a dockable tab, listed once in
`web/src/layout/panel_registry.ts`, and Graph is the one canvas.

- The **`+`** menu in the header (or Ctrl+right-click on the dock) opens any
  panel not in the dock, and saves or resets the arrangement. A closed panel's
  header button also brings it back.
- Closing a panel unmounts it.
- A saved arrangement is checked before Golden Layout reads it. One that cannot
  be used gives way to the built-in default, with a toast saying why.
- No panel pops out: panels are Mithril roots bound to this window.

---

## Common Patterns

### Add a Backend Endpoint

```python
# In a new or existing router file: routers are declared without a prefix
MyRouter = APIRouter()

@MyRouter.post("/my-endpoint")
async def my_endpoint(body: MyRequestModel) -> dict:
    result = await some_service.do_work(body)
    return generate_return(results={"data": result})

# Register in codecarto/main.py, where the prefix is given:
app.include_router(MyRouter, prefix="/my-prefix", tags=["my-tag"])
```

A new prefix also needs a row in the README's endpoint table, a heading in
`docs/api.md`, and an entry in `API_PATHS` in `web/vite.config.js`;
`tests/test_docs_routes.py` fails until each is there.

### Add a Language Parser

```python
# Implement the LanguageParser Protocol in codecarto/services/parsers/
class MyLanguageParser:
    language: ClassVar[str] = "mylang"
    extensions: ClassVar[list[str]] = [".ml"]
    batch_whole_tree: ClassVar[bool] = False  # True only if cross-file resolution needed

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        # Use make_node(..., shape='hexagon', color='#4a9eff') for visual grammar
        ...

ParserRegistry.register(MyLanguageParser())

# Then import the module in codecarto/services/parsers/__init__.py, beside the
# others: importing it is what registers it.
```

A language that patterns can read needs only a `_PATTERNS` list and one
`_LANGUAGES` entry in `regex_language_parser.py`.

### Add a Custom Layout

```python
# In codecarto/models/custom_layouts/my_layout.py
def my_layout(G: nx.DiGraph) -> dict:
    return {node: (x, y) for node, (x, y) in ...}

# Register in position_service.py add_custom_layouts():
from codecarto.models.custom_layouts.my_layout import my_layout
self.add_layout("my_layout", my_layout, ["graph"])
```

### Add a Dock Panel

One entry in `PANEL_DEFINITIONS` (`web/src/layout/panel_registry.ts`), its
Golden Layout config's `id` equal to the registry id, and a row in
`docs/llm/UI_REFERENCE.md`'s panel table, which `tests/test_docs_routes.py`
checks. `.github/CONTRIBUTING.md` has the steps.

### SSE Streaming (frontend)

```typescript
// Use fetch + ReadableStream (NOT EventSource — that's GET-only)
const resp = await fetch(`${baseUrl}/parse/stream`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
  signal: abortController.signal,
});
const reader = resp.body!.pipeThrough(new TextDecoderStream()).getReader();
// parse "event: type\ndata: json\n\n" chunks manually
```

### Mithril + Animation

```typescript
// CORRECT: use oncreate/onupdate lifecycle hooks for entrance animation
// WRONG: never mix direct style.display manipulation with Mithril vdom
m('div.content', {
  oncreate: (vnode) => { /* animate in */ },
  onremove: (vnode, done) => { /* animate out, then call done() */ },
}, content)
```

### C Parser (`batch_whole_tree`)

`CLangaugeParser` (spelled so in the code) sets `batch_whole_tree = True` because `CParser`'s cross-file CALLS resolution needs the complete file set in one call. `_parse_pending_batches` in `unified_parser_service.py` collects all `.c`/`.h` files across the whole tree before dispatching. The batch runs in `asyncio.to_thread` to avoid freezing the event loop.

---

## Testing

```bash
# Python backend tests (unset MONGODB_URI first, or the suite waits on a database)
uv run pytest tests -q

# Specific test file
uv run pytest tests/test_unified_parser_router.py -v

# Frontend: types, the node suites, the browser suite, the build
cd web && npm run typecheck
cd web && npm run test:pure && npm run test:state && npm run test:rad
cd web && npm run test:e2e        # starts its own servers on non-default ports
cd web && npm run build           # typecheck, then vite build
```

The browser suite needs Chromium once: `cd web && npx playwright install chromium`.
A check is evidence only once it has been seen to fail (AGENTS.md).

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `npm run build` fails | It runs `npm run typecheck` first; fix the types, avoid `any` |
| Graph doesn't appear | Browser console for JS errors; check API response is gJGF |
| Empty C graph from GitHub | Verify the `c-parsing` extra is installed; check `has_parse_warning` node attribute |
| Backend 500 on `/parse/stream` | Check `uv run codecarto serve` logs; likely a parser exception |
| A panel sits on "asking…", or an answer looks wrong | Ask `/openapi.json` what is answering; `CODECARTO_API` tells the dev server where the backend is |
| The Python suite takes minutes | Unset `MONGODB_URI`: with it set and no database listening, the suite waits on server selection |
| MongoDB connection refused | `/db` needs `MONGODB_URI` and a running MongoDB (`uv run codecarto docker`); everything else runs without it |
| The dock opened with the default layout and a toast | The saved layout could not be used; the toast says why, and it has been forgotten |
