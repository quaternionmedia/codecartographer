# CodeCartographer Architecture

System overview and component interactions for the CodeCartographer codebase visualization tool.

## Overview

CodeCartographer parses source code and generates interactive graph visualizations to help developers understand code structure, dependencies, and relationships.

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Graph Processing**: NetworkX
- **Visualization**: Gravis (for HTML rendering)
- **Package Manager**: uv

### Frontend
- **Framework**: Mithril.js
- **State Management**: Meiosis
- **Build Tool**: Vite
- **Visualization**: D3.js, vis-network
- **Language**: TypeScript

---

## Directory Structure

```
codecartographer/
|-- codecarto/                       # Backend Python package
|   |-- main.py                      # FastAPI application entry
|   |-- routers/
|   |   |-- unified_parser_router.py # /parse/* endpoints (all languages)
|   |   |-- plotter_router.py        # Legacy graph visualization endpoints
|   |   |-- parser_router.py         # Legacy Python parsing endpoints
|   |   |-- c_parser_router.py       # C/H semantic parse endpoints
|   |   |-- repo_router.py           # GitHub repository endpoints
|   |   `-- pam_router.py            # PAM auth log monitor
|   |-- services/
|   |   |-- unified_parser_service.py  # Unified parse orchestration
|   |   |-- graph_serializer.py        # NetworkX -> gJGF (depth-aware sizing)
|   |   |-- c_parser_service.py        # C parser service layer
|   |   `-- parsers/
|   |       |-- language_parser.py          # LanguageParser Protocol + ParserRegistry
|   |       |-- python_language_parser.py   # Python adapter (.py)
|   |       |-- c_language_parser.py        # C/H adapter (.c, .h)
|   |       |-- c_parser.py                 # libclang-based C semantic parser
|   |       |-- pam_parser.py               # PAM log parser
|   |       |-- ASTs/                       # PythonCustomAST visitor (legacy)
|   |       `-- python/                     # Legacy Python parsers
|   `-- models/
|
|-- web/src/
|   |-- components/codecarto/
|   |   `-- control_panel/    # 2-tab panel (Source / Graph)
|   |-- features/graph/
|   |   |-- services/         # Renderers: D3, Gravis, Notebook, System (PAM)
|   |   |-- config/           # Styling schema
|   |   `-- extensions/       # Graph extensions (drag, zoom, select, etc.)
|   |-- state/                # Meiosis state + PlotActions
|   `-- services/             # API service clients (PlotService, RepoService)
|
`-- docs/llm/                 # LLM-focused docs
    `-- archive/              # Historical implementation notes
```

---

## Unified Graph Architecture

### Core concept: depth-based hierarchy

All parsers produce nodes using the **unified node schema** so any renderer
can display any language without format negotiation.

| depth | meaning | node_id prefix | shape source | size multiplier |
|-------|---------|----------------|--------------|-----------------|
| 0 | directory | `dir::` | D3 fallback (diamond) | 3.0× base |
| 1 | file | `file::` | D3 fallback (square) | 1.8× base |
| 2 | top-level symbol | parser-specific | **parser-set** (`node.shape`) | 1.0× base |
| 3 | sub-symbol (arg, field…) | parser-specific | **parser-set** (`node.shape`) | 0.6× base |

### Unified node schema

```python
{
  "depth":    int,          # 0=dir, 1=file, 2=symbol, 3=sub-symbol
  "language": str,          # 'python' | 'c' | 'unknown'
  "kind":     str,          # 'directory'|'file'|'class'|'function'|'struct'|...
  "label":    str,          # human-readable name
  "file":     str,          # source file path
  "line":     int,          # source line number
  "meta":     dict,         # language-specific extras (qualifiers, param_count, etc.)
  # Visual grammar — set by the parser, read directly by the renderer:
  "shape":    str | None,   # 'circle'|'square'|'diamond'|'hexagon'|'triangle'|'ngon'|...
  "color":    str | None,   # hex colour, e.g. '#4a9eff'
}
```

> **Parser-owned visual grammar**: parsers set `shape` and `color` so that no
> language-specific logic is needed inside the renderer. Renderers fall back to their
> own depth/kind heuristics only when these fields are absent (e.g. directory/file nodes).
>
> | language | example shape mapping |
> |----------|-----------------------|
> | Python | `class`→square, `function`→hexagon, `import`→triangle |
> | C | `struct`→ngon (sides from `meta.sides`), `function`→diamond, `enum`→circle |

### LanguageParser Protocol + ParserRegistry

Each language adapter implements the `LanguageParser` Protocol and
self-registers at import time:

```python
class LanguageParser(Protocol):
    language: ClassVar[str]           # e.g. 'python'
    extensions: ClassVar[list[str]]   # e.g. ['.py']
    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph: ...

# Registered adapters (import triggers registration):
#   python_language_parser.py  ->  PythonLanguageParser  (.py)
#   c_language_parser.py       ->  CLangaugeParser        (.c, .h, .cpp, …)
```

Each adapter calls `make_node(..., shape=..., color=...)` to encode visual grammar
into the node data. To add a new language, create an adapter and import it in
`unified_parser_service.py` — no renderer changes required.

---

## Data Flow

### Unified parse path (all languages, depth=2)

The UI always uses `depth=2` to produce a single combined graph that includes
directories, files, symbols, and dependency edges in one pass. There is no
separate mode selector — one plot shows everything.

```
User fetches repo / clicks Plot
  |
  v
PlotService.streamUnified() -> POST /parse/stream  (SSE)
  |
  v
UnifiedParserService.stream_parse(directory, depth=2, extensions?)
  |-- Walk folder tree -> depth-0 dir + depth-1 file nodes
  |-- For each file with content:
  |     ParserRegistry.get(ext) -> language parser
  |     parser.parse_files([file], depth=2) -> unified nx.DiGraph
  |        (adds depth-2 symbol nodes + dependency edges)
  |-- Compute layout (NetworkX)
  |-- Yield SSE: meta → nodes (BFS order) → edges → done
  |
  v
StreamingGraphRenderer (frontend rAF loop)
  |-- addNode() per SSE 'node' event → pop-in animation
  |-- addEdge() per SSE 'edge' event
  |-- finalize() on 'done' → fit view
  |
  v
D3 canvas: reads node.shape / node.color from parser; falls back to
           depth/kind heuristics for nodes without parser-set values
```

**File click**: clicking a file in the tree creates a single-file Directory
and streams it through the same pipeline, fetching raw content if needed.

**Auto-plot**: fetching a repository immediately triggers streaming — no
separate "Plot" button click required.

### Lazy node expansion

```
User right-clicks file node -> Expand
  |
  v
PlotService.expandNode(directory, nodeId, depth=2)
POST /parse/expand
UnifiedParserService.expand_node(directory, nodeId, depth)
-> Returns sub-graph of node + all descendants
```

### Legacy parse path (Python-only, still active)

```
POST /plotter/whole_repo  { parse_by: 'ast'|'directory'|'dependencies' }
-> ParserService -> PythonCustomAST | DirectoryParser | DependencyParser
-> GraphSerializer -> gJGF
```

---

## State Management (Meiosis)

### State Structure

```typescript
ICellState {
  graphData: GraphData | null;          // Parsed graph data (gJGF)
  graphContent: m.Vnode[];              // Rendered graph elements
  graphStyling: GraphStylingOptions;    // Visual styling
  parserOptions: { fileExtensions: string[] };  // Extension filter (no mode selector)
  selectedRenderer: GraphRendererType;  // 'd3' | 'gravis' | 'notebook' | 'system'
  repo: DirectoryNavController;         // GitHub repo state
  local: DirectoryNavController;        // Local file state
}
```

### API endpoint registry (`web/src/state/api_base.ts`)

```typescript
api.parse      // /parse  (unified parser)
api.plotter    // /plotter (legacy)
api.cParser    // /c-parser
api.repoReader // /repo
```

---

## Renderer System

### Available Renderers

| type | name | auto-detect | data format |
|------|------|:-----------:|------------|
| `d3` | D3 Force Graph | yes | GraphData JSON (gJGF) |
| `gravis` | Gravis vis-network | yes | GraphData JSON (gJGF) |
| `notebook` | Notebook HTML | yes | `{ "text/html": "..." }` |
| `system` | System Monitor (PAM) | no | WebSocket events |

> Renderers are **generic engines** — they draw whatever shape/color arrives on each node.
> Language-specific visual grammar lives in the parser, not in the renderer.
> `CSemanticRenderer` exists as an unregistered opt-in tool (`canHandle()` = false).

### Renderer Selection Priority

1. User-selected renderer (`state.selectedRenderer`)
2. Metadata type (`graphData.metadata.type`)
3. Auto-detection (`canHandle(data)` loop)
4. Default fallback (D3)

### GraphNode (TypeScript)

```typescript
interface GraphNode {
  id: string;
  label?: string;
  color?: string; shape?: string; size?: number;
  x?: number; y?: number; fx?: number | null; fy?: number | null;
  // Unified schema (populated by /parse/unified):
  depth?: number;    // 0=dir, 1=file, 2=symbol, 3=sub
  language?: string; // 'python' | 'c' | 'unknown'
  kind?: string;     // 'directory' | 'file' | 'class' | 'function' | ...
  meta?: Record<string, unknown>;
  [key: string]: unknown;
}
```

---

## Parser Modes

### Unified (all languages, depth-controlled)

| `depth` | included nodes |
|---------|---------------|
| 0 | directories only |
| 1 | directories + files |
| 2 | + top-level symbols (class, function, struct, …) |
| 3 | + sub-symbols (arguments, fields, enum constants) |

**Registered languages** (auto-detected by extension):

| extension | language | adapter |
|-----------|----------|---------|
| `.py` | python | `PythonLanguageParser` |
| `.c`, `.h` | c | `CLangaugeParser` (requires `[c-parsing]` optional dep) |

### Legacy Python modes (`POST /plotter/whole_repo`)

| `parse_by` | parser | output |
|------------|--------|--------|
| `ast` | PythonCustomAST | code structure |
| `directory` | DirectoryParser | file/folder hierarchy |
| `dependencies` | DependencyParser | import relationships |

---

## API Endpoints

| Prefix | Tag | Description |
|--------|-----|-------------|
| `/parse` | parse | **Unified parse (all languages)** |
| `/plotter` | plotter | Legacy graph visualization |
| `/parser` | parser | Legacy Python code parsing |
| `/c-parser` | c-parser | C/H semantic parsing (libclang optional) |
| `/repo` | repo | GitHub repository operations |
| `/local` | local | Local filesystem scanning |
| `/pam` | pam | PAM auth log monitor |
| `/palette` | palette | Color palette management |

### Unified parse endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/parse/unified` | POST | Parse directory tree to given depth |
| `/parse/expand` | POST | Expand a file node to reveal its symbols |
| `/parse/languages` | GET | List registered parser extensions |

---

## D3 Extensions

The D3 renderer supports extensions for enhanced interactivity:

- **DragExtension**: Node dragging (multi-drag, grid snap)
- **ZoomExtension**: Pan and zoom, fit-to-screen
- **SelectionExtension**: Box select, lasso select
- **HighlightExtension**: Hover with neighbor fade
- **TooltipExtension**: Rich node tooltips with metadata
- **ColorExtension**: Dynamic coloring by degree/type

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `codecarto/main.py` | FastAPI app, all router registrations |
| `codecarto/routers/unified_parser_router.py` | `/parse/*` endpoints |
| `codecarto/services/unified_parser_service.py` | Directory walk + language dispatch |
| `codecarto/services/parsers/language_parser.py` | LanguageParser Protocol + ParserRegistry |
| `codecarto/services/parsers/python_language_parser.py` | Python adapter |
| `codecarto/services/parsers/c_language_parser.py` | C/H adapter |
| `codecarto/services/graph_serializer.py` | NetworkX -> gJGF, depth-aware sizing |
| `web/src/components/codecarto/control_panel/control_panel.ts` | 2-tab panel (Source / Graph) |
| `web/src/state/actions.ts` | PlotActions: plotUnified, plotWholeRepo, plotCGithub, … |
| `web/src/features/graph/services/graph_renderer.ts` | D3 renderer + GraphNode type |
| `web/src/features/graph/services/renderers.ts` | Renderer registry |
| `docs/llm/EXTENDING.md` | How to add renderers, language parsers, endpoints |
