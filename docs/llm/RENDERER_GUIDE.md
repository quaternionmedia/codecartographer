# Renderer System Guide

Guide to the graph renderer system in CodeCartographer.

## Overview

CodeCartographer uses a plugin-based renderer architecture. The system auto-detects the
appropriate renderer based on data format, while allowing users to override the selection
from the renderer dropdown in the Graph tab.

---

## Available Renderers

### D3GraphRenderer
- **Type**: `'d3'`
- **Use case**: Interactive force-directed graphs (default)
- **Features**: Physics simulation, drag, box-select, zoom, tooltips, radial context menu
- **Data format**: GraphData JSON (gJGF)
- **Auto-detected**: yes
- **Depth encoding**: directory=diamond/3×, file=square/1.8×, symbol=kind-based/1×, sub=circle/0.6×

### GravisGraphRenderer
- **Type**: `'gravis'`
- **Use case**: vis-network based alternative layout
- **Features**: Alternative physics engine, different visual style
- **Data format**: GraphData JSON (gJGF)
- **Auto-detected**: yes

### NotebookGraphRenderer
- **Type**: `'notebook'`
- **Use case**: Pre-rendered HTML visualizations
- **Features**: Displays HTML in iframe, no client-side processing
- **Data format**: `{ "text/html": "<html>..." }`
- **Auto-detected**: yes (when data has `text/html` key)

### SystemRenderer / PamRenderer
- **Type**: `'system'`
- **Use case**: Fixed-layout system architecture diagrams with live event feeds (e.g. PAM auth)
- **Features**: WebSocket live events, packet animations, demo loop, node state badges
- **Data format**: WebSocket JSON events (not gJGF)
- **Auto-detected**: no (selected via dropdown or `metadata.type`)

> `CSemanticRenderer` exists as an **unregistered opt-in class** (`canHandle()` = false,
> not in `renderers.ts`). C parser output is gJGF; D3 renders C graphs using the
> `shape`/`color` fields set by `c_language_parser.py` — no special renderer needed.

---

## Renderer Selection

### Priority Order
1. **User Selection**: `state.selectedRenderer` from UI dropdown
2. **Metadata Type**: `graphData.metadata.type` from backend
3. **Auto-Detection**: `canHandle(data)` on each registered renderer
4. **Default**: Falls back to D3

### Selection Code
```typescript
// PlotActions.createGraphVnode()
let renderer;

if (selectedRenderer) {
  renderer = GraphRendererRegistry.get(selectedRenderer);      // Priority 1
}
if (!renderer && graphData.metadata?.type) {
  renderer = GraphRendererRegistry.get(graphData.metadata.type); // Priority 2
}
if (!renderer) {
  renderer = GraphRendererRegistry.findForData(graphData);     // Priority 3
}
if (!renderer) {
  renderer = GraphRendererRegistry.getDefault();               // Priority 4 (D3)
}
```

---

## Data Formats

### GraphData JSON (D3 / Gravis / C Semantic)

All graph-based renderers consume this format (gJGF wrapped in CodeCartographer envelope):

```json
{
  "graph": {
    "nodes": {
      "dir::src": {
        "metadata": { "depth": 0, "language": "unknown", "kind": "directory", "label": "src" }
      },
      "file::src/main.py": {
        "metadata": { "depth": 1, "language": "python", "kind": "file", "label": "main.py" }
      },
      "main.MyClass": {
        "metadata": { "depth": 2, "language": "python", "kind": "class", "label": "MyClass" }
      }
    },
    "edges": [
      { "source": "dir::src", "target": "file::src/main.py", "metadata": { "kind": "contains" } }
    ],
    "directed": true
  },
  "metadata": {
    "layout": "Spring",
    "type": "d3",
    "nodeCount": 3,
    "edgeCount": 1,
    "palette_id": "0"
  }
}
```

> **Unified node attributes** (from `/parse/unified`):
> - `depth` — 0=directory, 1=file, 2=symbol, 3=sub-symbol
> - `language` — `'python'` | `'c'` | `'unknown'`
> - `kind` — `'directory'` | `'file'` | `'class'` | `'function'` | `'struct'` | …
> - `label` — human-readable display name
> - `file` — source file path
> - `line` — source line number
> - `meta` — language-specific extras (e.g. `sides` for ngon struct nodes)
> - `shape` *(optional)* — parser-set shape hint: `'circle'`|`'square'`|`'diamond'`|`'hexagon'`|`'triangle'`|`'ngon'`|…
> - `color` *(optional)* — parser-set hex colour, e.g. `'#4a9eff'`

### Notebook HTML
```json
{ "text/html": "<html><head>...</head><body>...</body></html>" }
```

---

## Renderer Interface

All renderers implement `IGraphRenderer`:

```typescript
interface IGraphRenderer {
  readonly type: string;
  readonly name: string;

  render(container: HTMLElement, data: unknown, styling?: GraphStylingOptions): void;
  canHandle(data: unknown): boolean;
  cleanup(): void;
}
```

---

## GraphData -> HTML Conversion (Notebook Renderer)

When the user selects Notebook renderer with GraphData JSON:

1. Frontend calls `POST /plotter/render/html` with the graph data
2. Backend converts gJGF to NetworkX, renders HTML with gravis
3. Frontend receives HTML string and injects it into an iframe

```typescript
// PlotActions.createNotebookVnode()
const htmlData = await PlotService.renderToHtml(api.plotter, themedGraphData, layout);
renderer.render(element, htmlData, stylingOptions);
```

### HTML theming metadata

Pass these keys in `graphData.metadata` for notebook-level styling:
- `background_color`, `edge_color`, `node_label_color`, `edge_label_color`, `arrow_color`, `node_border_color`

Per-node overrides: `color`, `label_color`, `label_size`, `border_color`, `border_size`
Per-edge overrides: `color`, `label_color`, `label_size`

---

## Styling Options

```typescript
interface GraphStylingOptions {
  // Node
  nodeSize: number;             // base radius in pixels
  nodeOpacity: number;          // 0.0–1.0
  nodeBorderWidth: number;      // pixels
  nodeColorOverride?: string;   // override per-node color

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

  // Physics (D3)
  enablePhysics: boolean;
  chargeStrength: number;
  linkDistance: number;

  // Canvas
  backgroundColor?: string;

  // Interaction
  interactionProfile: string;  // 'default' | 'cad' | 'gaming' | 'touch'
}
```

---

## D3 Visual Encoding

### Parser-set shape and color (depth 2–3)

For symbol nodes produced by the unified parser, `shape` and `color` are set by the
**language parser** and read directly by D3 — no renderer-level language logic:

| language | kind | shape | color |
|----------|------|-------|-------|
| Python | `module` | diamond | `#9b59b6` |
| Python | `class` | square | `#00d4ff` |
| Python | `function` | hexagon | `#00ff41` |
| Python | `import` | triangle | `#e74c3c` |
| C | `struct` / `union` | ngon (sides = field_count) | `#4a9eff` / `#6ab0e8` |
| C | `function` | diamond | `#ff9d3d` |
| C | `enum` | circle | `#a855f7` |
| C | `typedef` | circle | `#22d3ee` |
| C | `field` | square | `#3d5070` |

### D3 fallback encoding (depth 0–1, or nodes without parser-set shape)

| depth | kind | shape | size multiplier |
|-------|------|-------|-----------------|
| 0 | directory | diamond | 3.0× |
| 1 | file | square | 1.8× |
| 2–3 | any (no parser shape) | circle | 1.0× / 0.6× |

Node sizing in serializer (backend): `depth_base + edge_count * 10`
where `depth_base` is `{0: 40, 1: 20, 2: 10, 3: 6}`.

---

## Adding a New Renderer

1. **Create renderer class** implementing `IGraphRenderer` in `web/src/features/graph/services/`:
```typescript
export class MyRenderer implements IGraphRenderer {
  readonly type = 'myrenderer';
  readonly name = 'My Custom Renderer';
  render(container, data, styling) { /* ... */ }
  canHandle(data) { return /* auto-detect logic, or false for opt-in only */; }
  cleanup() { /* ... */ }
}
```

2. **Register** in `web/src/features/graph/services/renderers.ts`:
```typescript
GraphRendererRegistry.register('myrenderer', () => new MyRenderer());
```

3. **Add to type union** in `web/src/state/types.ts`:
```typescript
export type GraphRendererType = 'd3' | 'gravis' | 'notebook' | 'system' | 'myrenderer';
```

4. **Add UI option** in `control_panel.ts` renderer dropdown.

---

## Troubleshooting

### Renderer not switching
- Verify `selectedRenderer` is updated in state
- Check vnode key includes timestamp for forced re-render
- Ensure `createGraphVnode()` is called after state update

### Notebook shows warning
- GraphData JSON cannot be rendered by Notebook directly
- The frontend automatically calls `/plotter/render/html` to convert
- Select D3/Gravis to skip conversion

### Graph not appearing
- Check browser console for renderer errors
- Verify container has dimensions (width/height)
- Ensure `graphData` is not null in state

### C code not showing correct shapes
- Expected: C nodes use `ngon` / `diamond` / `circle` shapes set by the parser
- If shapes look wrong, verify `c_language_parser.py` is registered (libclang must be installed for C parsing)
- `CSemanticRenderer` is intentionally unregistered; D3 handles C output by default
