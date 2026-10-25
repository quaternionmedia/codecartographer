# Extending CodeCartographer

Guide for adding new renderers, language parsers, styling options, and backend endpoints.

---

## Adding a New Language Parser (Unified Architecture)

### Backend parser tiers

Three tiers exist, from lightest to most capable:

| Tier | File | When to use |
|------|------|-------------|
| **Regex** | `regex_language_parser.py` | Any language where top-level symbols (functions, classes, structs, headings, SQL tables, …) can be identified by a line-anchored regex. Zero new dependencies. Add a `_PATTERNS` list + one entry in `_LANGUAGES`. |
| **Dedicated libclang** | `c_language_parser.py` | C/C++ only. Cross-file `CALLS` resolution, `#include` tracking via `unsaved_files`. Requires the `c-parsing` extra: `uv sync --locked --extra dev --extra c-parsing`. |
| **Structural reader** | `rust_language_parser.py`, `linker_script_parser.py` | A tokenizer and brace matcher, stdlib only, for a language whose items are delimited by keywords and brackets: nesting, attributes, the module tree, relations each labelled with how they were resolved. Stops where name resolution begins; that is the compiler's. |

**Currently registered parsers and extensions:**

| Language | Extensions |
|----------|-----------|
| Python | `.py` (PythonLanguageParser — custom AST visitor) |
| C/C++ | `.c`, `.h`, `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx` (libclang) |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` |
| TypeScript | `.ts`, `.tsx`, `.cts`, `.mts` |
| Rust | `.rs` (RustLanguageParser — item-level structural reader) |
| Linker scripts | `.ld`, `.lds`, `.x` (LinkerScriptParser — MEMORY, SECTIONS, symbols) |
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

### Step 2: Import it in `codecarto/services/parsers/__init__.py`

```python
# codecarto/services/parsers/__init__.py, beside the other adapters:
from . import js_language_parser  # noqa: F401
```

That's it. The new parser is now available via `/parse/unified` for `.js`/`.ts`/`.mjs` files.
No router changes, no mode string additions.

### Does your parser need the whole tree at once?

By default `_walk_folder` dispatches one file at a time:
`parser.parse_files([file], depth)`. That's fine when each file's nodes/edges
are self-contained — true for Python (and for most languages, including the
JavaScript example above). If your parser needs to resolve references
*across* files in one call (the way `CLangaugeParser` resolves cross-file
`CALLS` edges — see [Architecture](architecture.md#the-unified-graph)),
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

**A file's key is `File.url or File.name`**, and that is what a node's `file`
attribute should hold. A file with neither unique -- two uploaded `lib.rs` --
is given its place in the tree as a `tree://` url before batching, so two files
with one name are never one key. Folder and file node ids are the path from
the root (`file::ws/crates/hal/src/lib.rs`) for the same reason.

**A batch parser that knows facts *about files*** -- a declaration naming
another file, an import reaching one, a file-level attribute -- sets
`graph.graph["file_relations"]` (`[(source, target, attrs)]`, each end a node
id or a file key, `attrs["kind"]` the edge kind) and `graph.graph["file_meta"]`
(`{file_key: {...}}`, merged into that file node's `meta`). The parser does not
create file nodes -- the walk does -- so the pipeline resolves the keys to them.
Relations are resolved on the in-memory and the GitHub streaming paths alike.
`file_meta` reaches the file node on the in-memory path only: the GitHub stream
has already sent its file nodes when the parser runs, so their `meta` is not
updated there.

### Joining the construct vocabulary

A parser's `kind` says what its language calls a thing. To have its nodes carry
`construct` (what the thing *is*, the same in every language), drawn with the
shared looks and read by the chrestomathy, add the language under `languages:`
in `codecarto/data/constructs.yaml`:

- `kinds`: each kind the parser emits, to a construct; `not_constructs`: each
  kind it emits that is not one, with the reason. The parser declares `kinds`,
  every kind it can emit, and `tests/test_construct_service.py` holds the two
  lists to it in both directions: nothing emitted goes unnamed, and nothing is
  named that no parser emits -- the chrestomathy draws a kind as "(parsed)".
- `qualifiers`, `attributes`, `macros`, `meta`: what in a node's `meta` makes it
  *also* a facet (`unsafe` -> `memory.unsafe`, `#[interrupt]` ->
  `firmware.interrupt`).
- `refine`: a kind that is a different construct when a meta flag is set (a
  Rust `enum` with `c_like` is an enumeration, not a sum type).

Add the language's spellings under each construct's `spelled:` -- every token
there must be in that language's lexicon, a token the lexicon files in more
than one group names the one that spells this construct under `groups:`, and a
language with no spelling gets a `note` saying how it does without. A parser may call
`construct_service.annotate(graph)` itself; the pipeline calls it on every parse
regardless, and a look the parser set is never overwritten.

A graph a service draws that is no language's parse -- the crate graph -- maps
its kinds under `graphs:` instead, in the same shape. Its nodes are stamped
and the census places them, but it is no row of the chrestomathy: nothing is
written in it, and under `languages:` every construct would carry a row saying
it records no spelling there.

---

## The node schema

Every node a parser emits is built by `make_node()`, and every edge by
`make_edge()`, both in `codecarto/services/parsers/language_parser.py`:

```python
attrs = make_node(
    node_id,                # unique string ID
    depth=2,                # 0=dir, 1=file, 2=symbol, 3=sub-symbol
    language="javascript",
    kind="function",        # 'class'|'function'|'struct'|'enum'|...
    label="myFunc",
    file="src/app.js",      # the file's key: File.url or File.name
    line=42,
    meta={"async": True},   # any language-specific extras
    shape="hexagon",        # optional: the parser's visual grammar
    color="#00ff41",        # optional: a hex colour
)

edge_attrs = make_edge("contains", weight=1.0)
```

| field | holds |
|-------|-------|
| `depth` | 0 directory, 1 file, 2 top-level symbol, 3 sub-symbol |
| `language` | the parser's `language`; `unknown` for directories |
| `kind` | what the language calls the thing: `class`, `function`, `struct`, `import`, ... |
| `label`, `file`, `line` | the name shown, the file's key, the line it starts on |
| `meta` | language-specific extras: `sides` for a C struct, `qualifiers`, `param_count`, ... |
| `shape`, `color` | optional; drawn as given |

The pipeline adds the rest: `construct`, `meta.facets`, `construct_color` and
`construct_name` from the construct vocabulary (below); `layer_ordinal` and
`layer_color` when the lexicon is joined; and `has_parse_warning`, at the top
level, when the node's file produced parser errors. An edge's `kind` is
`contains` for nesting, `depends_on` between files, and the parser's own
otherwise (`CALLS`, `FIELD_OF`, ...).

### Visual grammar

A parser sets `shape` and `color`, so no renderer holds language-specific
logic. The two parsers that set them:

| language | kind | shape | color |
|----------|------|-------|-------|
| Python | `module` | diamond | `#9b59b6` |
| Python | `class` | square | `#00d4ff` |
| Python | `function` | hexagon | `#00ff41` |
| Python | `import` | triangle | `#e74c3c` |
| Python | `call` | hexagon | `#00aa2a` |
| C | `struct`, `union` | ngon, `meta.sides` from the field count | `#4a9eff`, `#6ab0e8` |
| C | `function` | diamond | `#ff9d3d` |
| C | `enum` | circle | `#a855f7` |
| C | `typedef` | circle | `#22d3ee` |
| C | `field` | square | `#3d5070` |

`ngon` draws a polygon of `meta.sides` sides, turned a quarter of a side so that
no count draws as `diamond`, `square` or `hexagon`. A parser sets `meta.sides`
with `construct_service.ngon_sides(count)`, which clamps to `NGON_SIDES`, the
one statement of the range; the renderer draws the count it is sent, and a
pentagon when there is none. The C parser counts a struct's or union's fields,
and the construct vocabulary does the same for every record.

A node without them is given one on the canvas (`StreamingGraphRenderer`):
a directory is a grey diamond, a file a purple square, a function a hexagon, a
class or struct a square, an import or call a triangle, and anything else a
circle. `GraphSerializer` sizes a node by depth (40, 20, 10 and 6 for depths 0
to 3) plus its degree, unless the node already carries a `size`.

---

## Renderers

`web/src/features/graph/services/renderers.ts` registers four renderers with
`GraphRendererRegistry`, and `d3` is the default:

| type | class | draws | chosen by its data |
|------|-------|-------|--------------------|
| `d3` | `D3GraphRenderer` | gJGF, handed to `StreamingGraphRenderer`, the canvas every graph draws on | yes: `{graph: {nodes, edges}, metadata}` |
| `gravis` | `GravisGraphRenderer` | gJGF, through vis-network, loaded on first use | yes: gJGF |
| `notebook` | `NotebookGraphRenderer` | pre-rendered HTML, `{"text/html": "..."}`, in an iframe | yes: `text/html` |
| `system` | `SystemRenderer` | a `SystemDefinition`'s diagram and its live events; see *System Renderers* | no |

`PlotActions.createGraphVnode()` (`web/src/state/actions.ts`) uses the renderer
selected in the settings; else the one `metadata.type` names; else the first
registered whose `canHandle(data)` is true; else `d3`. The
[UI reference](ui.md) says where the selection is made.

Given gJGF, the notebook renderer asks `POST /plotter/render/html` to render it
with gravis on the server. These `metadata` keys theme that page, each also
accepted in camelCase: `background_color`, `edge_color`, `node_label_color`,
`edge_label_color`, `arrow_color`, `node_border_color`, `node_label_size`,
`edge_label_size`.

### Adding a renderer

#### Step 1: Create renderer class

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
    // True to be chosen for this data; false to be chosen only by name.
    if (!data || typeof data !== 'object') return false;
    return 'graph' in data && 'nodes' in (data as any).graph;
  }

  cleanup(): void {
    // Remove event listeners, cancel animations, etc.
  }
}
```

#### Step 2: Register

```typescript
// web/src/features/graph/services/renderers.ts
import { MyRenderer } from './my_renderer';
GraphRendererRegistry.register('myrenderer', () => new MyRenderer());
```

#### Step 3: Add to type union

```typescript
// web/src/state/types.ts
export type GraphRendererType = 'd3' | 'gravis' | 'notebook' | 'system' | 'myrenderer';
```

#### Step 4: Add UI option

```typescript
// In control_panel.ts renderer dropdown:
m('option', { value: 'myrenderer' }, 'My Custom Renderer'),
```

---

## Adding a New Styling Option

### Step 1: Update interface

```typescript
// web/src/state/types.ts
export interface GraphStylingOptions {
  // ...existing...
  myOption?: number;
}
```

### Step 2: Add default

```typescript
// web/src/state/cell_state.ts
public graphStyling: GraphStylingOptions = {
  // ...existing...
  myOption: 10,
};
```

### Step 3: Add a control

The Graph Settings panel renders `ControlPanel`'s settings controls; each one
reads `styling` and reports a change through `onGraphStylingChange`:

```typescript
// web/src/components/codecarto/control_panel/control_panel.ts
m('input[type=range]', {
  min: 0, max: 100, step: 5, value: styling.myOption,
  oninput: (e: Event) => callbacks.onGraphStylingChange({
    myOption: parseFloat((e.target as HTMLInputElement).value) }),
}),
```

### Step 4: Apply in renderer

```typescript
// web/src/features/graph/services/streaming_renderer.ts
.attr('some-attribute', styling.myOption || 10)
```

---

## Adding a New Graph Extension

Extensions add interactivity to the canvas. `web/src/features/graph/extensions/`
holds drag, zoom, selection, highlight, tooltip, colour and the legend; rad,
the radial menu, mounts the same way from `rad/host/rad_extension.ts`.

### Step 1: Create extension

```typescript
// web/src/features/graph/extensions/my_extension.ts
import { ExtensionContext } from './index';
import { GraphNode, GraphEdge } from '../services/graph_types';

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

### Step 3: Mount it against the canvas

**NOT INSIDE A RENDERER.** An extension built into one renderer belongs to
one rendering path, which is how this project ended up with a menu on the
path most readers never took. `GraphSurface` announces the live canvas;
subscribe once and mount against whatever drew it. `layout_context.ts` does
this for rad and the legend:

```typescript
// layout_context.ts, in the constructor
GraphSurface.subscribe((renderer) => {
  const ext = new MyExtension();
  ext.initialize(renderer.buildExtensionContext(selection, () => m.redraw()));
  ext.apply();
});
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

## Standalone visualizers: C and PAM

Two routers serve HTML pages of their own. The pages are packaged in
`codecarto/static/` (`c-visualizer.html`, `pam-frontend.html`), so the wheel
carries them.

### C (`c-parsing` extra)

C reaches the canvas as gJGF like every other language: the parser's `shape`
and `color` carry its visual grammar. The files:

- `codecarto/services/parsers/c_parser.py`: `CParser`, with libclang imported
  lazily. `parse_files()` takes an optional `contents: dict[path_str, text]`
  that it passes to libclang as `unsaved_files`, so content with no file on
  disk can be parsed.
- `codecarto/services/c_parser_service.py`: path validation, error wrapping,
  and the repository-extraction cache (`list_cached_repos`, `evict_repo_cache`).
- `codecarto/routers/c_parser_router.py`: `/c-parser/*`; the two C pipelines
  are in [Architecture](architecture.md#c-two-pipelines).
- `codecarto/services/parsers/c_language_parser.py`: `CLangaugeParser`, the
  `/parse/*` adapter, with `batch_whole_tree = True`.
- `codecarto/static/c-visualizer.html`, served by `GET /c-parser/visualizer`.

An optional dependency is imported where it is used, never at module level:

```toml
# pyproject.toml
[project.optional-dependencies]
c-parsing = ["libclang>=16.0.0"]
```
```python
def _get_clang():
    global _clang, _clang_idx
    if _clang_idx is not None:
        return _clang, _clang_idx
    try:
        import clang.cindex as cindex
    except ImportError as exc:
        raise ImportError(
            "libclang is not installed, so C and C++ declarations cannot be read. "
            "Install it with: uv sync --locked --extra dev --extra c-parsing"
        ) from exc
    ...
```

### PAM

The PAM monitor tails an auth log, or journald, and streams each PAM event over
a WebSocket as a JSON object; it draws no gJGF.

- `codecarto/services/parsers/pam_parser.py`: the line parser, regular
  expressions over the standard library.
- `codecarto/routers/pam_router.py`: REST, the WebSockets and the page.
- `codecarto/static/pam-frontend.html`, served by `GET /pam/ui` with its
  URLs rewritten to the origin that served it.

`main.py`'s startup hook calls `on_pam_startup()`, which starts the tailer
through `start_threaded_feeder` (`codecarto/util/threaded_feeder.py`) and a
loop that broadcasts each event to `/pam/ws/live`. The tailer reads journald
when `PAM_USE_JOURNALD` is set, and otherwise `PAM_LOG_FILE` or the first
readable system auth log:

```python
def make_tail_worker(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    def worker() -> None:
        for line in tail_file(log_path, from_start=False):
            ev = parse_line(line)
            if ev:
                asyncio.run_coroutine_threadsafe(queue.put(ev.to_dict()), loop)
    return worker

_event_queue = start_threaded_feeder(make_tail_worker)
```

---

## Testing Changes

The test commands are in [`AGENTS.md`](../AGENTS.md), *Tests*; running the
application is in [Getting Started](getting-started.md).

---

## System Renderers (non-graph visualizations)

`SystemRenderer` is a **concrete, definition-driven** renderer for fixed-layout
system diagrams with live event feeds. It owns the machinery — DOM layout at
fractional positions, SVG bezier edges, packet animation, the WebSocket
lifecycle, the demo loop, the log strip and badge — and everything it draws
comes from a `SystemDefinition` selected by `styling.systemId` out of
`SystemDefinitionRegistry`.

Two definitions ship, and they are the two ways to build one:

- **`pam_definition.ts`** — hand-drawn. The Linux PAM stack is a known, fixed
  system, so its nodes and edges are authored data. Live mode tails
  `/var/log/auth.log` via `/pam/ws/live`.
- **`derived_system.ts`** — derived. `DerivedSystemDefinition('moat')` asks the
  backend (`/system/compose`) what the moat repository *declares* — charts,
  the ArgoCD Applications that deploy them, terraform, container apps — and
  lays that out. Events (`/system/events`) are the history of the same
  contents; the WebSocket replays them, labelled as a replay. The diagram is
  about the system the repository describes, never about the repository, and
  a chart added to the repo appears with no layout edit. Why derivation beat
  curation is the draft record *The system monitor derives its diagram*,
  `adr/DRAFT-the-system-monitor-derives-its-diagram.md` on the corpus's
  `adr/the-monitor-derives-the-system` branch, proposed to the project's
  record branch in [qm#155](https://github.com/quaternionmedia/qm/pull/155)
  and not on it yet.

### Adding a new system

**Step 1 — write a `SystemDefinition`** (an object or class; no subclassing):

```typescript
import { SystemDefinition } from './system_core';

export const MY_SYSTEM: SystemDefinition = {
  id: 'my-system',
  name: 'My System',
  description: 'what it shows',
  wsPath: '',                      // '' = demo only
  httpStatusPath: '',
  getNodes: () => ({
    frontend: { label: 'Frontend', sub: 'nginx',    px: .1, py: .5, type: 'service' },
    backend:  { label: 'API',      sub: 'fastapi',  px: .5, py: .5, type: 'backend' },
  }),
  getEdges: () => [{ from: 'frontend', to: 'backend', style: 'dim' }],
  getDemoEvents: () => [{ event_type: 'ping', timestamp: 0.5 }],
  handleEvent: (ev, cb) => {
    if (ev.event_type === 'ping') cb.setNodeState('backend', 'active');
  },
};
```

For a system another repository declares, instantiate
`new DerivedSystemDefinition('<sibling-repo-name>')` instead — the backend
resolves the name beside the checkout (`CODECARTO_REPO_ROOTS` overrides the
roots), and `/system/repos` lists what is reachable.

**Step 2 — register it** in `renderers.ts`'s `initializeRenderers()`:

```typescript
SystemDefinitionRegistry.register(MY_SYSTEM);
```

**Step 3 — nothing else.** The control panel's System dropdown lists every
registered definition; `styling.systemId` selects one ('moat' is the default).
A definition may also provide `load()` (async derivation before first draw —
throwing shows the failure instead of an empty diagram) and `nodeTypeColor()`.

### The callback surface

`handleEvent(ev, cb)` drives the renderer through `cb` — the whole surface:

| Callback | Purpose |
|---|---|
| `setNodeState(id, state)` | `'idle'` / `'active'` / `'success'` / `'failed'` |
| `resetAllNodes()` | Reset all nodes to `'idle'` |
| `firePacket(from, to, color)` | Animate a packet along the bezier edge |
| `log(text, level)` | Append a line to the log strip |

### Node type default palette

Unmatched by a definition's `nodeTypeColor`, these `type` strings map to CSS
theme variables:

| type | CSS variable |
|---|---|
| `service` | `--c-accent` |
| `core` | `--c-font` |
| `auth`, `account` | `--c-secondary` |
| `session` | `--c-warning` |
| `backend` | `--c-accent` |
| `storage` | `--c-warning` |
| `external` | `--c-font-muted` |

The derived definition adds `infrastructure`, `deployer`, `chart`,
`application`.

### Live WebSocket protocol

`connectLive(wsUrl)` accepts two frame shapes:

```json
{ "event_type": "...", ... }                          // bare — /system/ws/replay
{ "type": "event",    "data": { "event_type": "..." } }  // enveloped — /pam/ws/live
{ "type": "backfill", "events": [ ... ] }
{ "type": "connected" }
```

The platform-free half (types, registry, layout, replay sequencing) lives in
`system_core.ts` and is tested with `npm run test:system` — no browser.
