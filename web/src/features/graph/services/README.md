# Graph Renderer System

This directory contains a pluggable architecture for different graph visualization libraries.

## Architecture

### Base Interface (`base_renderer.ts`)

All renderers implement the `IGraphRenderer` interface:

```typescript
interface IGraphRenderer {
  readonly type: string;        // Unique identifier (e.g., 'd3', 'notebook', 'gravis')
  readonly name: string;        // Human-readable name
  render(container: HTMLElement, data: unknown, styling?: GraphStylingOptions): void;
  canHandle(data: unknown): boolean;
  cleanup?(): void;
}
```

### Registry Pattern

The `GraphRendererRegistry` provides:
- **Registration**: Add new renderer types
- **Auto-detection**: Find appropriate renderer for data format
- **Factory pattern**: Create renderer instances on demand
- **Default renderer**: Fallback when type not specified

## Available Renderers

### 1. NotebookGraphRenderer (`notebook_renderer.ts`)

**Purpose**: Renders pre-rendered HTML visualizations from Jupyter notebooks

**Data Format**:
```typescript
Array<{ 'text/html': string, 'text/plain'?: string }>
```

**Use Case**: Demo visualizations with pre-rendered gravis HTML

**Detection**: Checks for `text/html` property in data

### 2. D3GraphRenderer (`d3_renderer.ts`)

**Purpose**: Interactive force-directed graphs using D3.js

**Data Format** (gJGF - Graph JSON Format):
```typescript
{
  graph: {
    nodes: GraphNode[] | Record<string, GraphNode>,
    edges: GraphEdge[],
    directed?: boolean
  },
  metadata: {
    layout: string,
    type: string,
    nodeCount: number,
    edgeCount: number,
    palette_id: string
  }
}
```

**Use Case**: Imported repositories, uploaded files, parsed code graphs

**Detection**: Checks for `graph` and `metadata` properties

**Features**:
- Force simulation
- Drag nodes
- Box selection (shift+drag)
- Zoom/pan
- Radial context menu
- Custom node shapes
- Interactive legend

### 3. StreamingGraphRenderer (`streaming_renderer.ts`)

**Purpose**: Progressive node/edge rendering over an SSE stream via a requestAnimationFrame drain loop.

**Data Format**: Called directly via `addNode()` / `addEdge()` / `finalize()` — not registered in the registry (it's a streaming sink, not a batch renderer).

**Use Case**: All repo / file plots from `/parse/stream` — the primary render path.

**Features**:
- rAF drain loop with adaptive batch size (`setTotal(n)`)
- Pop-in entrance animation per node
- Loading overlay until first `meta` event
- Compound group backgrounds (`_drawCompoundBackgrounds()`) using `CompoundLayoutManager`
- Drag support (pre-computed positions — no force simulation)

### 4. CompoundLayoutManager (`compound_layout.ts`)

**Purpose**: Computes bounding circles for compound layout groups.

**API**: `computeGroupBounds(nodes, edges, padding, baseNodeSize): GroupBounds[]`

Assigns each file to its dir and each symbol/sub-symbol to its file using the real backend `kind === "contains"` edges (falling back to nearest-neighbor by position only for orphans with no such edge), then returns bounding circles depth-0 first (SVG z-order: dir circles drawn before file circles). Used by both `StreamingGraphRenderer` and `GraphRenderer`.

### 5. GravisGraphRenderer (`gravis_renderer.ts`)

**Purpose**: Client-side rendering via [vis-network](https://github.com/visjs/vis-network) — mirrors the visual style of Python gravis (the library this project's static reports use), rendered live in the browser instead of pre-baked HTML.

**Status**: Fully implemented — converts gJGF to vis-network's `{nodes, edges}` DataSets (shapes, colors with opacity, sizes from either `styling.nodeSize` or the backend's own `node.size`), configures physics/interaction/layout options from `GraphStylingOptions`, wires click/double-click/edge-select/stabilization event listeners, and handles container resize and cleanup.

**Data Format**: Same as D3 (gJGF) — `canHandle()` accepts any `{graph: {nodes, edges}, metadata}` shape.

**Selectable**: Via the Renderer dropdown (`'gravis'` in `GraphRendererType`), registered in `renderers.ts`'s `GraphRendererRegistry`.

## Usage

### Automatic Rendering (Recommended)

The system auto-detects the correct renderer:

```typescript
import { GraphRendererRegistry } from './renderers';

// Auto-detect based on data format
const renderer = GraphRendererRegistry.findForData(data);
if (renderer) {
  renderer.render(container, data, stylingOptions);
}
```

### Explicit Renderer Selection

```typescript
import { GraphRendererRegistry } from './renderers';

// Use specific renderer by type
const d3Renderer = GraphRendererRegistry.get('d3');
d3Renderer.render(container, graphData, stylingOptions);

// Or use default
const defaultRenderer = GraphRendererRegistry.getDefault();
defaultRenderer.render(container, data, stylingOptions);
```

### Current Routing Logic (in PlotActions)

```typescript
handlePlotData(data: unknown): void {
  const renderer = GraphRendererRegistry.findForData(data);

  if (renderer.type === 'd3' || renderer.type === 'gravis') {
    // Store in state for re-rendering when styling changes
    this.renderGraphData(data);
  } else {
    // Render directly (notebook/HTML)
    this.renderWithRenderer(renderer, data);
  }
}
```

## Adding a New Renderer

1. **Create renderer class** implementing `IGraphRenderer`:

```typescript
// my_renderer.ts
export class MyGraphRenderer implements IGraphRenderer {
  readonly type = 'my-renderer';
  readonly name = 'My Custom Renderer';

  render(container: HTMLElement, data: unknown, styling?: GraphStylingOptions): void {
    // Your rendering logic
  }

  canHandle(data: unknown): boolean {
    // Check if this renderer can handle the data format
    return /* your detection logic */;
  }

  cleanup?(): void {
    // Optional cleanup
  }
}
```

2. **Register in `renderers.ts`**:

```typescript
import { MyGraphRenderer } from './my_renderer';

function initializeRenderers(): void {
  // ... existing registrations
  GraphRendererRegistry.register('my-renderer', () => new MyGraphRenderer());
}
```

3. **Use it**:

The renderer will now be available for auto-detection or explicit use.

## Current Data Flow

### Demo Flow (Notebook Renderer)
```
demo.txt (HTML)
  → getDemoData()
  → handlePlotData()
  → NotebookGraphRenderer
  → iframe rendering
```

### Import Flow (D3 Renderer)
```
File/Repo upload
  → PlotService
  → Backend API (returns gJGF)
  → handlePlotData()
  → D3GraphRenderer
  → interactive D3 graph
```

## Benefits

✅ **Separation of Concerns**: Each renderer is isolated
✅ **Extensibility**: Easy to add new visualization libraries
✅ **Auto-detection**: No manual format checking in application code
✅ **Type Safety**: TypeScript interfaces ensure consistency
✅ **Testability**: Each renderer can be tested independently
✅ **Flexibility**: Can switch renderers at runtime

## Future Enhancements

- [ ] Implement GravisGraphRenderer with client-side gravis.js
- [ ] Add Three.js renderer for 3D graphs
- [ ] Add vis.js renderer as alternative 2D library
- [ ] Add renderer preferences/settings UI
- [ ] Support renderer-specific configuration
- [ ] Add performance metrics per renderer
- [ ] Support renderer plugins (dynamic loading)
