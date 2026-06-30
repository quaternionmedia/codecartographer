# Code Cartographer — AI Assistant Instructions

> Consolidated guide for AI assistants working on this codebase.
> See `docs/llm/ARCHITECTURE.md` for deep architectural detail and `docs/llm/EXTENDING.md` for extension patterns.

---

## Project Overview

**Code Cartographer** is a multi-language source code visualization tool. It parses repositories (Python, C/H, more planned) into interactive D3 graph visualizations showing code structure, dependencies, and relationships.

- **Stack**: Python (FastAPI) backend + TypeScript (Mithril.js + Golden Layout) frontend
- **Primary parse flow**: POST `/parse/stream` → SSE → `StreamingGraphRenderer` → D3 canvas
- **Package manager**: `uv` (Python), `npm` (frontend)

---

## Quick Start

```bash
# Backend + frontend dev server
uv run codecarto dev

# Backend only (with auto-reload)
uv run codecarto serve --reload

# Frontend only
cd web && npm run dev

# Production build check
cd web && npm run build
```

URLs: `http://localhost:1234` (UI) · `http://127.0.0.1:8000/docs` (API docs)

---

## Directory Structure

```
codecartographer/
├── codecarto/                         # Python backend package
│   ├── main.py                        # FastAPI app + router registration
│   ├── routers/
│   │   ├── unified_parser_router.py   # /parse/* (main parse endpoints)
│   │   ├── repo_router.py             # /repo/* (GitHub tree + cache)
│   │   ├── c_parser_router.py         # /c-parser/* (libclang optional)
│   │   ├── plotter_router.py          # /plotter/demo + /render/html only
│   │   └── pam_router.py             # /pam/* (PAM log monitor)
│   ├── services/
│   │   ├── unified_parser_service.py  # Directory walk + language dispatch
│   │   ├── graph_serializer.py        # NetworkX → gJGF (depth-aware sizing)
│   │   ├── cache_service.py           # Filesystem + MongoDB graph cache
│   │   ├── position_service.py        # Layout registry
│   │   └── parsers/
│   │       ├── language_parser.py          # LanguageParser Protocol + ParserRegistry
│   │       ├── python_language_parser.py   # .py adapter
│   │       └── c_language_parser.py        # .c/.h adapter (batch_whole_tree)
│   └── models/
│       └── custom_layouts/
│           └── compound_layout.py          # 3-pass hierarchical layout
│
└── web/src/
    ├── components/codecarto/
    │   └── control_panel/             # 2-tab panel (Source / Graph)
    ├── features/graph/
    │   ├── services/
    │   │   ├── streaming_renderer.ts  # Primary renderer (rAF + SSE)
    │   │   ├── graph_renderer.ts      # Static D3 renderer + radial menu
    │   │   ├── compound_layout.ts     # CompoundLayoutManager + GroupBounds
    │   │   └── renderers.ts           # Renderer registry
    │   └── components/
    │       └── radial_menu.ts         # D3 pie/arc context menu
    ├── layout/
    │   ├── golden_layout_shell.ts     # GL2 primary shell
    │   ├── default_layout.ts          # Panel definitions
    │   └── panels/                    # graph_panel, actions_panel
    └── state/
        ├── cell_state.ts              # Meiosis state + PlotActions
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
  "language": str,          # 'python' | 'c' | 'unknown'
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

| Prefix | Description |
|--------|-------------|
| `/parse` | **Unified parse** (all languages, recommended) |
| `/repo` | GitHub + local repository tree operations |
| `/c-parser` | C/H semantic parse (requires `[c-parsing]` optional dep) |
| `/plotter` | `/demo` + `/render/html` only (legacy + Notebook renderer) |
| `/pam` | PAM auth log monitor |

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

The UI has two main areas:

1. **Golden Layout shell** — dock tabs: Graph (main canvas), Source/Info (file tree), Actions (plot controls). Close a tab → Restore button appears in header.
2. **Control panel sidebar** — 2 tabs:
   - **Source**: Demo button, GitHub URL input + file tree, recent cache list.
   - **Graph**: Layout dropdown (Spring/Compound/Circular/Kamada-Kawai/Spectral), physics sliders, node/edge/label styling, Group Outlines toggle.

See `docs/llm/UI_REFERENCE.md` for the full UI reference.

---

## Common Patterns

### Add a Backend Endpoint

```python
# In a new or existing router file
@router.post("/my-endpoint")
async def my_endpoint(body: MyRequestModel) -> dict:
    result = await some_service.do_work(body)
    return generate_return(results={"data": result})

# Register in codecarto/main.py:
app.include_router(my_router, prefix="/my-prefix", tags=["my-tag"])
```

### Add a Language Parser

```python
# Implement LanguageParser Protocol in codecarto/services/parsers/
class MyLanguageParser:
    language: ClassVar[str] = "mylang"
    extensions: ClassVar[list[str]] = [".ml"]
    batch_whole_tree: ClassVar[bool] = False  # True only if cross-file resolution needed

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        # Use make_node(..., shape='hexagon', color='#4a9eff') for visual grammar
        ...

# Import in unified_parser_service.py to trigger self-registration via ParserRegistry
```

### Add a Custom Layout

```python
# In codecarto/models/custom_layouts/my_layout.py
def my_layout(G: nx.DiGraph) -> dict:
    return {node: (x, y) for node, (x, y) in ...}

# Register in position_service.py add_custom_layouts():
from codecarto.models.custom_layouts.my_layout import my_layout
self.add_layout("my_layout", my_layout, ["graph"])
```

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

`CLangaugeParser` sets `batch_whole_tree = True` because `CParser`'s cross-file CALLS resolution needs the complete file set in one call. `_parse_pending_batches` in `unified_parser_service.py` collects all `.c`/`.h` files across the whole tree before dispatching. The batch runs in `asyncio.to_thread` to avoid freezing the event loop.

---

## Testing

```bash
# Python backend tests
uv run pytest

# Specific test file
uv run pytest tests/test_unified_parser_router.py -v

# Frontend type check + build
cd web && npm run build
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `npm run build` fails | TypeScript errors in console; fix types, avoid `any` |
| Graph doesn't appear | Browser console for JS errors; check API response is gJGF |
| Empty C graph from GitHub | Verify `[c-parsing]` dep installed; check `has_parse_warning` node attribute |
| Backend 500 on `/parse/stream` | Check `uv run codecarto serve` logs; likely a parser exception |
| MongoDB connection refused | Set `MONGODB_URI` env var or start docker-compose (optional feature) |

---

**Last Updated**: 2026-06-30  
**Current Branch**: `consolidate-68-69-70-71`
