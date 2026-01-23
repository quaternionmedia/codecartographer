# Renderer System Guide

Guide to the graph renderer system in CodeCartographer.

## Overview

CodeCartographer uses a plugin-based renderer architecture that supports multiple visualization backends. The system auto-detects the appropriate renderer based on data format, while allowing users to override the selection.

---

## Available Renderers

### D3GraphRenderer
- **Type**: `'d3'`
- **Use case**: Interactive force-directed graphs
- **Features**: Physics simulation, drag, zoom, selection, tooltips
- **Data format**: GraphData JSON `{ graph: { nodes, edges }, metadata }`

### GravisGraphRenderer
- **Type**: `'gravis'`
- **Use case**: vis-network based visualization
- **Features**: Alternative physics engine, different visual style
- **Data format**: GraphData JSON

### NotebookGraphRenderer
- **Type**: `'notebook'`
- **Use case**: Pre-rendered HTML visualizations
- **Features**: Displays HTML in iframe, no client-side processing
- **Data format**: `{ "text/html": "<html>..." }`

---

## Renderer Selection

### Priority Order
1. **User Selection**: `state.selectedRenderer` from UI dropdown
2. **Metadata Type**: `graphData.metadata.type` from backend
3. **Auto-Detection**: `canHandle(data)` method on each renderer
4. **Default**: Falls back to D3

### Selection Code
```typescript
// In PlotActions.createGraphVnode()
let renderer;

// Priority 1: User selection
if (selectedRenderer) {
  renderer = GraphRendererRegistry.get(selectedRenderer);
}

// Priority 2: Metadata type
if (!renderer && graphData.metadata?.type) {
  renderer = GraphRendererRegistry.get(graphData.metadata.type);
}

// Priority 3: Auto-detect
if (!renderer) {
  renderer = GraphRendererRegistry.findForData(graphData);
}

// Priority 4: Default
if (!renderer) {
  renderer = GraphRendererRegistry.getDefault();
}
```

---

## Data Formats

### GraphData JSON (D3/Gravis)
```json
{
  "graph": {
    "nodes": {
      "node1": { "id": "node1", "label": "Function", "color": "#00ff41" },
      "node2": { "id": "node2", "label": "Class", "color": "#ff6b6b" }
    },
    "edges": [
      { "source": "node1", "target": "node2", "label": "calls" }
    ]
  },
  "metadata": {
    "layout": "Spring",
    "type": "d3",
    "nodeCount": 2,
    "edgeCount": 1
  }
}
```

### Notebook HTML
```json
{
  "text/html": "<html><head>...</head><body>...</body></html>"
}
```

---

## Renderer Interface

All renderers implement `IGraphRenderer`:

```typescript
interface IGraphRenderer {
  readonly type: string;
  readonly name: string;

  render(
    container: HTMLElement,
    data: unknown,
    styling?: GraphStylingOptions
  ): void;

  canHandle(data: unknown): boolean;

  cleanup(): void;
}
```

---

## GraphData to HTML Conversion

When user selects Notebook renderer with GraphData JSON:

1. Frontend detects mismatch (GraphData vs HTML expected)
2. Calls `/plotter/render/html` endpoint
3. Backend converts GraphData to NetworkX graph
4. Backend generates HTML using gravis
5. Frontend receives HTML and renders in Notebook renderer

```typescript
// In PlotActions.createNotebookVnode()
const htmlData = await PlotService.renderToHtml(plotterUrl, graphData);
renderer.render(element, htmlData, stylingOptions);
```

### HTML Theming Metadata

When converting GraphData to HTML, the backend passes graph-level metadata through to gravis:

- `background_color`
- `edge_color`
- `node_label_color`
- `edge_label_color`
- `arrow_color`

Per-node and per-edge overrides are supported via:

- Node: `label_color`, `label_size`, `border_color`, `border_size`, `color`
- Edge: `label_color`, `label_size`, `color`

The Notebook renderer also injects theme CSS variables and resize hooks so gravis fills the iframe and adapts when the container size changes.

---

## Styling Options

Renderers receive `GraphStylingOptions`:

```typescript
interface GraphStylingOptions {
  // Node
  nodeSize: number;
  nodeOpacity: number;
  nodeBorderWidth: number;
  nodeColorOverride?: string;

  // Edge
  edgeWidth: number;
  edgeOpacity: number;
  edgeColor?: string;
  edgeStyle?: 'solid' | 'dashed' | 'dotted';

  // Labels
  showNodeLabels: boolean;
  showEdgeLabels: boolean;
  labelSize: number;
  labelColor: string;

  // Physics
  enablePhysics: boolean;
  chargeStrength: number;
  linkDistance: number;

  // Canvas
  backgroundColor?: string;
}
```

---

## Adding a New Renderer

1. **Create renderer class** implementing `IGraphRenderer`:
```typescript
// web/src/features/graph/services/my_renderer.ts
export class MyRenderer implements IGraphRenderer {
  readonly type = 'myrenderer';
  readonly name = 'My Custom Renderer';

  render(container, data, styling) { /* ... */ }
  canHandle(data) { return /* detection logic */; }
  cleanup() { /* ... */ }
}
```

2. **Register in renderers.ts**:
```typescript
import { MyRenderer } from './my_renderer';
GraphRendererRegistry.register('myrenderer', () => new MyRenderer());
```

3. **Add to type union**:
```typescript
// types.ts
export type GraphRendererType = 'd3' | 'gravis' | 'notebook' | 'myrenderer';
```

4. **Add UI option** in control_panel.ts renderer dropdown.

---

## Troubleshooting

### Renderer not switching
- Verify `selectedRenderer` is updated in state
- Check vnode key includes timestamp for forced re-render
- Ensure `createGraphVnode()` is called after state update

### Notebook shows warning
- GraphData JSON cannot be rendered by Notebook directly
- Use `/render/html` endpoint to convert, or select D3/Gravis

### Graph not appearing
- Check console for renderer errors
- Verify container has dimensions (width/height)
- Ensure graphData is not null
