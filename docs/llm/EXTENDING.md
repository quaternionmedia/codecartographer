# Extending CodeCartographer

Guide for adding new renderers, language parsers, styling options, and backend endpoints.

---

## Adding a New Language Parser (Unified Architecture)

### Backend parser tiers

Three tiers exist, from lightest to most capable:

| Tier | File | When to use |
|------|------|-------------|
| **Phase 1 — Regex** | `regex_language_parser.py` | Any language where top-level symbols (functions, classes, structs, headings, SQL tables, …) can be identified by a line-anchored regex. Zero new dependencies. Add a `_PATTERNS` list + one entry in `_LANGUAGES`. |
| **Dedicated libclang** | `c_language_parser.py` | C/C++ only. Cross-file `CALLS` resolution, `#include` tracking via `unsaved_files`. Requires `uv sync --extra c-parsing`. |
| **Phase 2 — tree-sitter** (planned) | not yet implemented | Full AST quality for all languages. Stubs declared in `pyproject.toml` under `[multilang]` optional deps. Planned to replace regex parsers per language when accuracy becomes a priority. |

**Currently registered parsers and extensions:**

| Language | Extensions |
|----------|-----------|
| Python | `.py` (PythonLanguageParser — custom AST visitor) |
| C/C++ | `.c`, `.h`, `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx` (libclang) |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` |
| TypeScript | `.ts`, `.tsx`, `.cts`, `.mts` |
| Rust | `.rs` |
| Go | `.go` |
| Java | `.java` |
| C# | `.cs` |
| Kotlin | `.kt`, `.kts` |
| Swift | `.swift` |
| Ruby | `.rb` |
| PHP | `.php` |
| Scala | `.scala` |
| Shell/Bash | `.sh`, `.bash` |
| Lua | `.lua` |
| Assembly | `.asm`, `.s`, `.S` |
| SQL | `.sql` |
| Markdown | `.md`, `.mdx` |
| HTML | `.html`, `.htm`, `.xhtml` |
| CSS/SCSS/Sass/Less | `.css`, `.scss`, `.sass`, `.less` |
| Dockerfile | `.dockerfile` |
| TOML | `.toml` |

**Fastest path to add a new language:** edit `_LANGUAGES` in `regex_language_parser.py` with a `(depth, kind, compiled_regex)` pattern list — see existing entries as templates. The new extensions appear in `/parse/languages` immediately.

The recommended way to add support for a new language is via the **LanguageParser protocol**.
The parser self-registers at import time and immediately works with `/parse/unified`.

### Step 1: Create the adapter

```python
# codecarto/services/parsers/js_language_parser.py
from __future__ import annotations
from typing import ClassVar
import networkx as nx
from codecarto.models.source_data import File
from codecarto.services.parsers.language_parser import (
    LanguageParser, ParserRegistry, make_node, make_edge,
)

class JavaScriptLanguageParser:
    language: ClassVar[str] = "javascript"
    extensions: ClassVar[list[str]] = [".js", ".ts", ".mjs"]

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        graph = nx.DiGraph()
        for file in files:
            if not file.raw:
                continue
            # ... parse file.raw, build nodes/edges using make_node() / make_edge()
            # Depth guidance:
            #   depth=1 -> emit module node only
            #   depth=2 -> emit classes + functions
            #   depth=3 -> emit params, inner functions, etc.
            node_id = f"{file.name}::MyClass"
            graph.add_node(node_id, **make_node(
                node_id,
                depth=2, language="javascript", kind="class",
                label="MyClass", file=file.name, line=1,
                shape="square",   # visual grammar owned by this parser
                color="#00d4ff",
            ))
        return graph

# Self-register
_instance = JavaScriptLanguageParser()
ParserRegistry.register(_instance)
```

### Step 2: Import in `unified_parser_service.py`

```python
# At the top of unified_parser_service.py (alongside existing adapters):
import codecarto.services.parsers.js_language_parser  # noqa: F401
```

That's it. The new parser is now available via `/parse/unified` for `.js`/`.ts`/`.mjs` files.
No router changes, no mode string additions.

### Does your parser need the whole tree at once?

By default `_walk_folder` dispatches one file at a time:
`parser.parse_files([file], depth)`. That's fine when each file's nodes/edges
are self-contained — true for Python (and for most languages, including the
JavaScript example above). If your parser needs to resolve references
*across* files in one call (the way `CLangaugeParser` resolves cross-file
`CALLS` edges — see `docs/llm/ARCHITECTURE.md`'s `batch_whole_tree` section),
set:

```python
class JavaScriptLanguageParser:
    batch_whole_tree: ClassVar[bool] = True
    ...
```

This changes nothing about `parse_files()`'s signature — it's still called
with a list of files, just now with *every* file your parser owns across
the whole tree, in one call, after the directory walk finishes instead of
per-folder. You're responsible for attributing resulting nodes back to
their origin file via each node's `file` attribute if you want correct
`contains` edges — see `_merge_batch_subgraph` for the depth==2 convention
the unified pipeline uses.

### Unified node schema helpers

```python
# make_node: returns a dict of node attributes
attrs = make_node(
    node_id,                # unique string ID
    depth=2,                # 0=dir, 1=file, 2=symbol, 3=sub-symbol
    language="javascript",
    kind="function",        # 'class'|'function'|'struct'|'enum'|...
    label="myFunc",
    file="src/app.js",
    line=42,
    meta={"async": True},   # any language-specific extras
    # Visual grammar — parsers own these; renderers read them directly:
    shape="hexagon",        # 'circle'|'square'|'diamond'|'hexagon'|'triangle'|'ngon'|...
    color="#00ff41",        # hex colour hint
)

# make_edge: returns edge attribute dict
edge_attrs = make_edge("contains", weight=1.0)
```

> **Principle**: parsers set `shape` and `color` so that no language-specific logic
> is needed in any renderer. The D3 renderer reads `node.shape` / `node.color` directly.
> It only falls back to its own heuristics for nodes that have neither field set (e.g. raw
> directory/file nodes emitted by the directory walker).
>
> The `'ngon'` shape draws an N-sided polygon. Set `meta["sides"]` to control the
> polygon order (clamped 3–12 by the renderer). Used by the C parser for `struct`/`union`
> nodes where `sides = min(max(field_count, 3), 10)`.

---

## Adding a New Renderer

### Step 1: Create renderer class

```typescript
// web/src/features/graph/services/my_renderer.ts
import { IGraphRenderer } from './base_renderer';
import { GraphStylingOptions } from '../../../state/types';

export class MyRenderer implements IGraphRenderer {
  readonly type = 'myrenderer';
  readonly name = 'My Custom Renderer';

  render(container: HTMLElement, data: unknown, styling?: GraphStylingOptions): void {
    container.innerHTML = '';
    // Receive GraphData JSON: data.graph.nodes / data.graph.edges
    // Receive styling options for consistent look
  }

  canHandle(data: unknown): boolean {
    // Return true for auto-detection, false for opt-in only.
    // Use false if your renderer is a specialised view that should
    // not capture standard gJGF graphs (like CSemanticRenderer).
    if (!data || typeof data !== 'object') return false;
    return 'graph' in data && 'nodes' in (data as any).graph;
  }

  cleanup(): void {
    // Remove event listeners, cancel animations, etc.
  }
}
```

### Step 2: Register

```typescript
// web/src/features/graph/services/renderers.ts
import { MyRenderer } from './my_renderer';
GraphRendererRegistry.register('myrenderer', () => new MyRenderer());
```

### Step 3: Add to type union

```typescript
// web/src/state/types.ts
export type GraphRendererType = 'd3' | 'gravis' | 'notebook' | 'system' | 'myrenderer';
```

### Step 4: Add UI option

```typescript
// In control_panel.ts renderer dropdown:
m('option', { value: 'myrenderer' }, 'My Custom Renderer'),
```

---

## Adding a New Styling Option

### Step 1: Add to schema

```typescript
// web/src/features/graph/config/styling_schema.ts
{
  key: 'myOption',
  label: 'My Option',
  type: 'range',  // 'range' | 'color' | 'boolean' | 'select'
  category: 'node',
  default: 10,
  min: 0, max: 100, step: 5,
  description: 'What this option does',
},
```

### Step 2: Update interface

```typescript
// web/src/state/types.ts
export interface GraphStylingOptions {
  // ...existing...
  myOption?: number;
}
```

### Step 3: Add default

```typescript
// web/src/state/cell_state.ts
public graphStyling: GraphStylingOptions = {
  // ...existing...
  myOption: 10,
};
```

### Step 4: Apply in renderer

```typescript
// web/src/features/graph/services/graph_renderer.ts
.attr('some-attribute', styling.myOption || 10)
```

---

## Adding a New Graph Extension

Extensions add interactivity to the D3 renderer.

### Step 1: Create extension

```typescript
// web/src/features/graph/extensions/my_extension.ts
import { ExtensionContext } from './index';
import { GraphNode, GraphEdge } from '../services/graph_renderer';

export class MyExtension {
  initialize(context: ExtensionContext<GraphNode, GraphEdge>): void {
    // Set up using context.svg, context.nodes, context.simulation, etc.
  }

  apply(): void {
    // Attach event listeners, overlays, etc.
  }

  cleanup(): void {
    // Remove listeners, cancel RAF loops
  }
}
```

### Step 2: Export

```typescript
// web/src/features/graph/extensions/index.ts
export { MyExtension } from './my_extension';
```

### Step 3: Use in renderer

```typescript
// graph_renderer.ts in initializeExtensions():
this.myExtension = new MyExtension();
this.myExtension.initialize(context);
this.myExtension.apply();
```

---

## Adding a Backend Endpoint

### Step 1: Create router function

```python
# In any router file, or a new one:
from fastapi import APIRouter
from codecarto.util.exceptions import CodeCartoException, proc_exception
from codecarto.util.utilities import generate_return

MyRouter = APIRouter()

@MyRouter.post("/my-endpoint")
async def my_endpoint(request: MyRequestModel) -> dict:
    try:
        result = MyService.process(request)
        return generate_return(200, "my-endpoint - Success", {"data": result})
    except CodeCartoException as exc:
        return proc_exception(exc.source, exc.message, exc.params, exc, exc.status_code)
    except Exception as exc:
        return proc_exception("my-endpoint", "Unexpected error", {}, exc)
```

### Step 2: Register in `main.py`

```python
from codecarto.routers.my_router import MyRouter
app.include_router(MyRouter, prefix="/my", tags=["my"])
```

### Step 3: Add frontend service method

```typescript
// web/src/services/plot_service.ts
public static async myMethod(baseUrl: string, data: unknown): Promise<unknown> {
  const url = `${baseUrl}/my-endpoint`;
  const result = await RequestHandler.postRequest(url, data);
  if (typeof result === 'string') return null;
  return result;
}
```

### Step 4: Add API endpoint to `api_base.ts`

```typescript
private _my: string = 'my';
get my(): string { return `${this._base}/${this._my}`; }
```

---

## Chrestromathy Integration Reference

Two specialised visualization systems originally adapted from an external Chrestromathy
reference project. HTML frontends now ship as packaged assets in `codecarto/static/`
(`c-visualizer.html`, `pam-frontend.html`) so they're included in the built wheel.

### C Semantic Parser (`c-parsing` optional group)

Parses C/H source files via libclang into a semantic graph.

**Output is gJGF** (converted by `c_language_parser.py`). Visual grammar (ngon for struct,
diamond for function, etc.) is encoded in `node.shape` / `node.color` by the parser, so D3
renders C graphs correctly without any renderer-level language logic.

`CSemanticRenderer` exists as an **unregistered opt-in** class (`canHandle()` = false,
not in `renderers.ts`). It is a standalone deep-dive tool, not part of the main renderer
dropdown.

**Key files:**
- Low-level parser: `codecarto/services/parsers/c_parser.py` — `CParser` class, lazy libclang.
  `parse_files()` takes an optional `contents: dict[path_str, text]` passed to
  libclang as `unsaved_files`, so content with no real file on disk (e.g.
  fetched from GitHub) can still be parsed.
- Service layer: `codecarto/services/c_parser_service.py` — path validation + error wrapping
  + the repo-extraction cache (`list_cached_repos`/`evict_repo_cache`)
- REST router: `codecarto/routers/c_parser_router.py` — `POST /c-parser/file|directory|github` (blocking) + `POST /c-parser/stream-github` (SSE, real per-file libclang progress — see `docs/llm/ARCHITECTURE.md`'s "C semantic stream path") + `GET /c-parser/cache` / `DELETE /c-parser/cache/{key}`
- Unified adapter: `codecarto/services/parsers/c_language_parser.py` — `CLangaugeParser`.
  Sets `batch_whole_tree = True` so the unified pipeline collects every C/H
  file across the whole tree before parsing (needed for cross-file `CALLS`
  resolution) — see `docs/llm/ARCHITECTURE.md`'s `batch_whole_tree` section
  if you're writing a new language adapter that also needs whole-tree context.
- Frontend renderer: `web/src/features/graph/services/c_semantic_renderer.ts` (opt-in)
- Standalone visualizer HTML: `codecarto/static/c-visualizer.html` (served by `GET /c-parser/visualizer`)

**Optional dependency pattern** (system-level libs):
```toml
# pyproject.toml
[project.optional-dependencies]
c-parsing = ["libclang>=16.0.0"]
```
```python
# Lazy import — never at module level when optional:
def _get_clang():
    global _clang, _clang_idx
    if _clang_idx is not None:
        return _clang, _clang_idx
    try:
        import clang.cindex as cindex
    except ImportError as exc:
        raise ImportError(
            "Install with: uv pip install 'codecarto[c-parsing]'"
        ) from exc
    ...
```

**C Semantic Renderer — opt-in, not auto-detected:**
```typescript
// c_semantic_renderer.ts
canHandle(_data: unknown): boolean {
    // Opt-in only. C parser output is now gJGF; D3 handles it by default.
    // Users select 'c-semantic' from the dropdown for the polygon-based view.
    return false;
}
```

---

### PAM Auth Visualizer (real-time system monitoring)

Tails `/var/log/auth.log` (or journald) in a background thread, streams PAM events
over WebSocket. No gJGF output — events are raw JSON dicts.

**Key files:**
- Parser: `codecarto/services/parsers/pam_parser.py` — regex-based, pure stdlib
- Router: `codecarto/routers/pam_router.py` — REST + WebSocket + HTML frontend serving
- Frontend HTML: `codecarto/static/pam-frontend.html` (served by `GET /pam/ui`)
- Frontend: "PAM Monitor" button in Tools tab -> `GET /pam/ui`

**Background task pattern:**
```python
# In on_pam_startup():
_event_queue = asyncio.Queue()
loop = asyncio.get_event_loop()
t = threading.Thread(target=_tail_thread, args=(log_path, _event_queue, loop), daemon=True)
t.start()
asyncio.create_task(_broadcast_loop(_event_queue))

# In _tail_thread (runs in thread, not async):
asyncio.run_coroutine_threadsafe(queue.put(ev.to_dict()), loop)
```

**Startup hook** (in `main.py`):
```python
@app.on_event("startup")
async def startup():
    from codecarto.routers.pam_router import on_pam_startup
    await on_pam_startup()
```

**HTML frontend URL patching:**
```python
@PamRouter.get("/ui")
async def pam_ui(request: Request):
    html = html_path.read_text(encoding='utf-8')
    http_base = str(request.base_url).rstrip('/')
    ws_base = http_base.replace('http://', 'ws://', 1)
    html = html.replace('ws://localhost:8765/ws/live', f'{ws_base}/pam/ws/live')
    html = html.replace("'http://localhost:8765'", f"'{http_base}/pam'")
    return HTMLResponse(html)
```

---

## Testing Changes

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_unified_parser_service.py -v

# Build frontend
cd web && node_modules/.bin/vite build

# Run backend
uv run codecarto

# Run frontend dev server
cd web && node_modules/.bin/vite
```

---

## System Renderers (non-graph visualizations)

`SystemRenderer` is an abstract base class for **fixed-layout system architecture diagrams
with live event feeds**. It handles all shared infrastructure:

- DOM layout (nodes at fractional positions, SVG bezier edges)
- Packet animations (cubic bezier, pure `requestAnimationFrame`)
- WebSocket lifecycle (connect → cancel demo → backfill → live → reconnect on close)
- Demo loop (auto-plays built-in event sequence, loops continuously)
- Log strip + badge state

The renderer type string is `'system'` in `GraphRendererType`. Currently `PamRenderer`
is the concrete implementation registered under that key.

### Creating a new system renderer

**Step 1 — Subclass `SystemRenderer`**

```typescript
// web/src/features/graph/services/my_renderer.ts
import { SystemRenderer, SystemNode, SystemEdge, SystemEvent } from './system_renderer';

const MY_NODES: Record<string, SystemNode> = {
  frontend: { label: 'Frontend', sub: 'nginx',    px: .1, py: .5, type: 'service' },
  backend:  { label: 'API',      sub: 'fastapi',  px: .5, py: .5, type: 'backend' },
  db:       { label: 'Database', sub: 'postgres', px: .9, py: .5, type: 'storage' },
};

const MY_EDGES: SystemEdge[] = [
  { from: 'frontend', to: 'backend', style: 'dim'    },
  { from: 'backend',  to: 'db',      style: 'dashed' },
];

const DEMO_EVENTS: SystemEvent[] = [
  { event_type: 'request',  timestamp: 0 },
  { event_type: 'db_query', timestamp: 0.5 },
  { event_type: 'response', timestamp: 1.0, success: true },
];

export class MyRenderer extends SystemRenderer {
  readonly type = 'system';   // use 'system' (the registered key)
  readonly name = 'My System';

  protected getNodes()       { return MY_NODES;    }
  protected getEdges()       { return MY_EDGES;    }
  protected getDemoEvents()  { return DEMO_EVENTS; }

  protected handleEvent(ev: SystemEvent): void {
    switch (ev.event_type) {
      case 'request':
        this.setNodeState('frontend', 'active');
        this.firePacket('frontend', 'backend', '#00d4ff');
        break;
      case 'db_query':
        this.setNodeState('db', 'active');
        this.firePacket('backend', 'db', '#00d4ff');
        break;
      case 'response':
        this.setNodeState('backend', ev.success ? 'success' : 'failed');
        this.firePacket('backend', 'frontend', '#00ffb3');
        this.log('Request complete', 'ok');
        break;
    }
  }
}
```

**Step 2 — Register it** in `renderers.ts`:

```typescript
import { MyRenderer } from './my_renderer';
// inside initializeRenderers():
GraphRendererRegistry.register('system', () => new MyRenderer());
```

**Step 3 — No other changes needed.** The `'system'` type is already in `GraphRendererType`,
the dropdown already shows "System Monitor", and `createSystemVnode()` in `actions.ts`
already injects `pamWsUrl` / `pamMode` via the `GraphStylingOptions` index signature.

### Key `SystemRenderer` API

| Method | Access | Purpose |
|---|---|---|
| `getNodes()` | abstract protected | Return node map with fractional `px`/`py` positions |
| `getEdges()` | abstract protected | Return edge list |
| `getDemoEvents()` | abstract protected | Return demo event sequence |
| `handleEvent(ev)` | abstract protected | Map one event to node states + packets |
| `setNodeState(id, state)` | protected | Set `'idle'`/`'active'`/`'success'`/`'failed'` |
| `resetAllNodes()` | protected | Reset all nodes to `'idle'` |
| `firePacket(from, to, color)` | protected | Animate a packet along the bezier edge |
| `log(text, level)` | protected | Append a line to the log strip |
| `setBadge(text, cls)` | protected | Update the header badge (DEMO / LIVE / OFFLINE) |
| `nodeTypeColor(type)` | protected override | Map node `type` string to CSS color string |

### Node type default palette

The base class maps these `type` strings to CSS theme variables:

| type | CSS variable |
|---|---|
| `service` | `--c-accent` |
| `core` | `--c-font` |
| `auth`, `account` | `--c-secondary` |
| `session` | `--c-warning` |
| `backend` | `--c-accent` |
| `storage` | `--c-warning` |
| `external` | `--c-font-muted` |

Override `nodeTypeColor(type: string): string` to add custom types.

### Live WebSocket protocol

The base `connectLive(wsUrl)` method expects JSON messages with this shape:

```json
{ "type": "event",    "data": { "event_type": "...", ... } }
{ "type": "backfill", "events": [ ... ] }
{ "type": "connected" }
```

The PAM backend (`pam_router.py`) already emits this format on `/pam/ws/live`.

See `pam_renderer.ts` (~150 lines) for a complete worked example.
