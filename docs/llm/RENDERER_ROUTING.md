# Renderer Routing Guide

## Current System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Sources                              │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         │                    │                    │
    ┌────▼────┐         ┌─────▼──────┐      ┌─────▼─────┐
    │  Demo   │         │  Uploaded  │      │  GitHub   │
    │  Button │         │    File    │      │   Repo    │
    └────┬────┘         └─────┬──────┘      └─────┬─────┘
         │                    │                    │
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  getDemoData()     │
                    │  PlotService       │
                    │  (API calls)       │
                    └─────────┬──────────┘
                              │
                              │
                    ┌─────────▼──────────┐
                    │  handlePlotData()  │
                    │  (PlotActions)     │
                    └─────────┬──────────┘
                              │
                              │
         ┌────────────────────▼───────────────────┐
         │  GraphRendererRegistry.findForData()   │
         │         (Auto-Detection)               │
         └────────────────────┬───────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
      ┌────▼────┐      ┌──────▼──────┐    ┌─────▼─────┐
      │Notebook │      │     D3      │    │  Gravis   │
      │Renderer │      │  Renderer   │    │ Renderer  │
      └────┬────┘      └──────┬──────┘    └─────┬─────┘
           │                  │                  │
      ┌────▼────┐      ┌──────▼──────┐    ┌─────▼─────┐
      │ iframe  │      │ D3.js SVG   │    │Placeholder│
      │with HTML│      │Force Graph  │    │  (TODO)   │
      └─────────┘      └─────────────┘    └───────────┘
```

## Data Format Detection

### Notebook Renderer Trigger

**Detects**:
```javascript
data = [{
  "text/html": "<div>...</div>",
  "text/plain": "..."
}]
```

**Check**: `'text/html' in data[0]`

**Routes To**: `NotebookGraphRenderer`

**Use Cases**:
- 🎯 Demo button (pre-rendered gravis HTML)
- Jupyter notebook outputs
- Any HTML visualization

---

### D3 Renderer Trigger

**Detects**:
```javascript
data = {
  "graph": {
    "nodes": [...],
    "edges": [...]
  },
  "metadata": {
    "type": "d3",
    "layout": "Spring",
    ...
  }
}
```

**Check**: `'graph' in data && 'metadata' in data`

**Routes To**: `D3GraphRenderer`

**Use Cases**:
- 🎯 File upload (Python AST)
- 🎯 GitHub repo import
- 🎯 URL file import
- Any structured graph data

---

### Gravis Renderer Trigger

**Detects**:
```javascript
data = {
  "graph": {...},
  "metadata": {
    "type": "gravis",  // ← Key difference
    ...
  }
}
```

**Check**: `metadata.type === 'gravis'`

**Routes To**: `GravisGraphRenderer` (stub)

**Use Cases**:
- 🚧 Future: Client-side gravis rendering
- Alternative to D3 for same data

---

## Current Production Routing

### Scenario 1: User Clicks "Demo"

```
User clicks Demo
  │
  └─→ getDemoData()
      │
      └─→ Fetches: /demo/demo.txt
          │
          └─→ Returns: [{text/html: "...", text/plain: "..."}]
              │
              └─→ handlePlotData(data)
                  │
                  └─→ GraphRendererRegistry.findForData(data)
                      │
                      └─→ NotebookGraphRenderer.canHandle(data) ✓
                          │
                          └─→ NotebookGraphRenderer.render()
                              │
                              └─→ Creates iframe with gravis HTML
```

**Result**: Pre-rendered gravis visualization in iframe

---

### Scenario 2: User Uploads Python File

```
User uploads file.py
  │
  └─→ PlotService.plotFile()
      │
      └─→ POST /plotter/file
          │
          └─→ Backend parses AST
              │
              └─→ Returns: {graph: {...}, metadata: {type: "d3"}}
                  │
                  └─→ handlePlotData(data)
                      │
                      └─→ GraphRendererRegistry.findForData(data)
                          │
                          └─→ D3GraphRenderer.canHandle(data) ✓
                              │
                              └─→ D3GraphRenderer.render()
                                  │
                                  └─→ Interactive D3 force graph
```

**Result**: Interactive D3.js visualization with:
- Draggable nodes
- Box selection (shift+drag)
- Zoom/pan
- Radial context menu
- Custom node shapes
- Collapsible legend

---

### Scenario 3: User Imports GitHub Repo

```
User enters GitHub URL
  │
  └─→ RepoService.fetchGithubDirectory()
      │
      └─→ Downloads repo structure
          │
          └─→ PlotService.plotRepoWhole()
              │
              └─→ POST /plotter/whole_repo
                  │
                  └─→ Backend parses directory/AST
                      │
                      └─→ Returns: {graph: {...}, metadata: {type: "d3"}}
                          │
                          └─→ handlePlotData(data)
                              │
                              └─→ GraphRendererRegistry.findForData(data)
                                  │
                                  └─→ D3GraphRenderer.canHandle(data) ✓
                                      │
                                      └─→ D3GraphRenderer.render()
                                          │
                                          └─→ Interactive D3 graph
```

**Result**: Same interactive D3.js visualization as file upload

---

## Fallback Logic

```javascript
// In createGraphVnode()

// 1. Try explicit type from metadata
if (graphData.metadata?.type) {
  renderer = GraphRendererRegistry.get(graphData.metadata.type);
}

// 2. Fall back to auto-detection
if (!renderer) {
  renderer = GraphRendererRegistry.findForData(graphData);
}

// 3. Final fallback to default (D3)
if (!renderer) {
  renderer = GraphRendererRegistry.getDefault();
}
```

## Configuration

### Current Settings

```typescript
// In renderers.ts
GraphRendererRegistry.register('notebook', () => new NotebookGraphRenderer());
GraphRendererRegistry.register('d3', () => new D3GraphRenderer());
GraphRendererRegistry.register('gravis', () => new GravisGraphRenderer());

// Default renderer
GraphRendererRegistry.setDefault('d3');
```

### To Change Default

```typescript
// Set notebook as default
GraphRendererRegistry.setDefault('notebook');

// Set gravis when implemented
GraphRendererRegistry.setDefault('gravis');
```

## Overriding Renderer Selection

### Option 1: Via Metadata (Backend)

```python
# In backend graph_serializer.py
metadata = {
    "type": "gravis",  # Force gravis renderer
    "layout": "Spring",
    ...
}
```

### Option 2: Via Explicit Call (Frontend)

```typescript
// Force specific renderer regardless of data
const notebookRenderer = GraphRendererRegistry.get('notebook');
notebookRenderer.render(container, data);
```

### Option 3: Via User Setting (Future)

```typescript
// In settings UI
const userPreferredRenderer = settings.graphRenderer; // 'd3' | 'gravis' | 'notebook'
const renderer = GraphRendererRegistry.get(userPreferredRenderer);
renderer.render(container, data);
```

## Testing Renderer Selection

### Test Notebook Renderer

```typescript
const notebookData = [{
  'text/html': '<div>Test HTML</div>',
  'text/plain': 'Test'
}];

const renderer = GraphRendererRegistry.findForData(notebookData);
console.log(renderer.type); // 'notebook'
```

### Test D3 Renderer

```typescript
const graphData = {
  graph: {
    nodes: [{ id: '1' }, { id: '2' }],
    edges: [{ source: '1', target: '2' }]
  },
  metadata: {
    type: 'd3',
    layout: 'Spring',
    nodeCount: 2,
    edgeCount: 1
  }
};

const renderer = GraphRendererRegistry.findForData(graphData);
console.log(renderer.type); // 'd3'
```

### Test Gravis Renderer

```typescript
const gravisData = {
  graph: { nodes: [], edges: [] },
  metadata: { type: 'gravis' }
};

const renderer = GraphRendererRegistry.findForData(gravisData);
console.log(renderer.type); // 'gravis'
```

## Summary

| Data Source | Format | Detected Renderer | Current Behavior |
|------------|--------|-------------------|------------------|
| Demo | HTML array | NotebookRenderer | ✅ iframe with pre-rendered HTML |
| File upload | gJGF | D3Renderer | ✅ Interactive D3 graph |
| GitHub repo | gJGF | D3Renderer | ✅ Interactive D3 graph |
| URL file | gJGF | D3Renderer | ✅ Interactive D3 graph |
| Future gravis | gJGF (type=gravis) | GravisRenderer | 🚧 Placeholder (TODO) |

**Key Point**: The system **automatically** selects the correct renderer based on data format. No manual configuration needed for normal use.
