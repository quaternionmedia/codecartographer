# CodeCartographer Architecture

System overview and component interactions for the CodeCartographer codebase visualization tool.

## Overview

CodeCartographer parses source code and generates interactive graph visualizations to help developers understand code structure, dependencies, and relationships.

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
|-- codecarto/                    # Backend Python package
|   |-- main.py                   # FastAPI application entry
|   |-- routers/                  # HTTP endpoint handlers
|   |   |-- plotter_router.py     # Graph visualization endpoints
|   |   |-- parser_router.py      # Code parsing endpoints
|   |   `-- repo_router.py        # GitHub repository endpoints
|   |-- services/                 # Business logic
|   |   |-- parser_service.py     # Parse orchestration
|   |   |-- graph_serializer.py   # Graph JSON serialization
|   |   `-- parsers/              # Language-specific parsers
|   `-- models/                   # Pydantic data models
|
|-- web/                          # Frontend (Vite + TypeScript + Mithril)
|   `-- src/
|       |-- index.ts              # App entry point
|       |-- components/           # UI Components
|       |   `-- codecarto/        # Main app component
|       |-- features/             # Feature modules
|       |   `-- graph/            # Graph visualization
|       |       |-- services/     # Renderers (D3, Gravis, Notebook)
|       |       |-- config/       # Styling schema
|       |       `-- extensions/   # Graph extensions (drag, zoom, etc.)
|       |-- state/                # Meiosis state management
|       `-- services/             # API services
|
`-- docs/                         # Documentation
    `-- llm/                      # LLM-focused docs
```

---

## Data Flow

### 1. User Input -> Backend
```
User Input (GitHub URL / File Upload / Demo)
  |
  v
Frontend Component (codecarto.ts)
  |
  v
PlotService (HTTP Request)
  |
  v
Backend Router (plotter_router.py)
```

### 2. Backend Processing
```
Router receives request
  |
  v
ParserService selects parser based on mode:
  - AST: PythonCustomAST (code structure)
  - Directory: DirectoryParser (file hierarchy)
  - Dependencies: DependencyParser (import relationships)
  |
  v
Parser generates NetworkX DiGraph
  |
  v
GraphSerializer converts to gJGF format
  |
  v
Returns JSON: { graph: {...}, metadata: {...} }
```

### 3. Frontend Rendering
```
PlotActions.handlePlotData(response)
  |
  v
Store graphData in state
  |
  v
createGraphVnode() -> selects renderer:
  - D3GraphRenderer (interactive force-directed)
  - GravisGraphRenderer (vis-network physics)
  - NotebookGraphRenderer (pre-rendered HTML)
  |
  v
Renderer.render(element, data, styling)
  |
  v
Interactive visualization displayed
```

---

## State Management (Meiosis)

The frontend uses the Meiosis pattern for state management.

### State Structure
```typescript
ICellState {
  graphData: GraphData | null;     // Parsed graph data
  graphContent: m.Vnode[];         // Rendered graph elements
  graphStyling: GraphStylingOptions; // Visual styling
  parserOptions: ParserOptions;    // Parser configuration
  selectedRenderer: GraphRendererType; // 'd3' | 'gravis' | 'notebook'
  repo: DirectoryNavController;    // GitHub repo state
  local: DirectoryNavController;   // Local file state
}
```

### Actions
- `PlotActions`: Graph loading and rendering
- `RepoActions`: GitHub repository operations

---

## Renderer System

### Architecture
```
GraphRendererRegistry (Factory/Registry)
  |
  v
IGraphRenderer Interface
  |
  v
Implementations:
  - D3GraphRenderer (force-directed, interactive)
  - GravisGraphRenderer (vis-network physics)
  - NotebookGraphRenderer (pre-rendered HTML)
```

### Renderer Selection Priority
1. User-selected renderer from state
2. Metadata type from graphData
3. Auto-detection based on data format
4. Default fallback (D3)

### Data Formats
- **GraphData JSON**: `{ graph: { nodes, edges }, metadata }` -> D3/Gravis
- **Notebook HTML**: `{ "text/html": "<html>..." }` -> Notebook

---

## Parser Modes

| Mode | Parser | Output |
|------|--------|--------|
| `ast` | PythonCustomAST | Code structure (functions, classes, calls) |
| `directory` | DirectoryParser | File/folder hierarchy |
| `dependencies` | DependencyParser | Import relationships |

---

## Styling System

Graph styling uses a schema-driven approach defined in `styling_schema.ts`.

### Categories
- **Node**: size, opacity, border, color override
- **Edge**: width, opacity, color, style (solid/dashed/dotted)
- **Label**: show/hide, size, color
- **Physics**: enable/disable, charge strength, link distance
- **Canvas**: background color

### Flow
```
User changes styling option
  |
  v
onGraphStylingChange callback
  |
  v
Update state (panelState + cellState)
  |
  v
createGraphVnode() re-renders with new styling
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/plotter/demo` | POST | Generate demo graph from codecarto source |
| `/plotter/whole_repo` | POST | Parse entire repository |
| `/plotter/file` | POST | Parse single file |
| `/plotter/render/html` | POST | Convert GraphData to HTML for Notebook |
| `/repo/` | GET | Fetch GitHub repository structure |

---

## Extensions

The D3 renderer supports extensions for enhanced interactivity:

- **DragExtension**: Node dragging
- **ZoomExtension**: Pan and zoom
- **SelectionExtension**: Multi-select nodes
- **HighlightExtension**: Hover highlighting
- **TooltipExtension**: Node tooltips
- **ColorExtension**: Dynamic coloring

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `codecarto/main.py` | FastAPI app setup |
| `codecarto/routers/plotter_router.py` | Visualization endpoints |
| `web/src/components/codecarto/codecarto.ts` | Main app component |
| `web/src/state/actions.ts` | PlotActions business logic |
| `web/src/features/graph/services/graph_renderer.ts` | D3 rendering |
| `web/src/features/graph/services/renderers.ts` | Renderer registry |
| `web/src/features/graph/config/styling_schema.ts` | Styling definitions |
