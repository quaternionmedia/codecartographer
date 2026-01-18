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

### 3. GravisGraphRenderer (`gravis_renderer.ts`)

**Purpose**: Future client-side gravis.js rendering

**Status**: Stub implementation (shows placeholder)

**Data Format**: Same as D3 (gJGF)

**Detection**: Requires `metadata.type === 'gravis'`

**TODO**:
- Implement gravis.js client-side rendering
- Convert gJGF to gravis format
- Add interaction handlers

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
