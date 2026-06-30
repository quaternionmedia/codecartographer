# Migration History

> Complete history of the Code Cartographer migration from Jupyter notebook rendering to API-based architecture

## Backend Migration: Jupyter Notebook → API-Based Rendering

**Date**: 2026-01-17
**Status**: ✅ Complete

### Architecture Changes

#### Before (Notebook-Based)
```
User Request → PlotterRouter → PlotterService.plot_nx_graph()
  → run_notebook() → Execute Jupyter cells → Extract HTML
  → Return [{text/html: "..."}] → Frontend renders in iframe
```

**Problems**:
- 600-second timeout risk for large graphs
- HTML payloads (500KB+) for simple graphs
- Tight coupling between backend and visualization library
- No client-side interactivity beyond what gravis embedded

#### After (API-Based)
```
Backend: PlotterRouter → ParserService → NetworkX Graph
  → GraphSerializer → gJGF JSON → Return {graph, metadata}

Frontend: PlotActions → GraphRenderer.renderD3()
  → D3.js force simulation → Interactive SVG
```

**Benefits**:
- API responses in <500ms for most graphs
- JSON payloads 10-50x smaller than HTML
- Client-side zoom, pan, drag nodes
- Easy to add alternative renderers (Three.js, vis.js)

### Files Changed

#### Backend (Python)

**Created**:
- `codecarto/services/graph_serializer.py` - NetworkX → gJGF conversion

**Modified**:
- `codecarto/routers/plotter_router.py` - 5 endpoints updated
- `codecarto/main.py` - Added CORS origin
- `pyproject.toml` - Removed nbformat/nbconvert dependencies

**Deleted**:
- `codecarto/services/plotter_service.py`
- `codecarto/notebooks/` - All notebook files
- `codecarto/util/exceptions.py` - NotebookError class

#### Frontend (TypeScript)

**Created**:
- `web/src/services/graph_renderer.ts` - D3.js visualization

**Modified**:
- `web/src/state/actions.ts` - Format detection
- `web/package.json` - Added d3 dependencies

### gJGF Format

```json
{
  "graph": {
    "nodes": {
      "node_id": {
        "metadata": {
          "x": 250.5,
          "y": 180.3,
          "color": "#00ff00",
          "size": 450,
          "label": "node_label"
        }
      }
    },
    "edges": [
      { "source": "A", "target": "B", "color": "#999" }
    ],
    "directed": true
  },
  "metadata": {
    "layout": "Spectral",
    "type": "d3",
    "nodeCount": 1208,
    "edgeCount": 2295
  }
}
```

### Performance Metrics

| Metric | Before (Notebook) | After (API) | Improvement |
|--------|------------------|-------------|-------------|
| Response time (100 nodes) | ~3-5s | ~300ms | **10-15x faster** |
| Payload size (100 nodes) | ~500KB HTML | ~50KB JSON | **10x smaller** |
| Timeout risk | 600s limit | No risk | **Eliminated** |
| Client interactivity | Limited | Full D3 controls | **Enhanced** |

---

## Graph Styling Integration

**Date**: 2026-01-17
**Status**: ✅ Complete

### Implementation

Connected control panel styling options to D3 GraphRenderer:

```typescript
export interface GraphStylingOptions {
  layout: string;
  enablePhysics: boolean;
  chargeStrength: number;
  linkDistance: number;
  nodeSize: number;
  nodeOpacity: number;
  nodeBorderWidth: number;
  edgeWidth: number;
  edgeOpacity: number;
  showNodeLabels: boolean;
  showEdgeLabels: boolean;
  labelSize: number;
  labelColor: string;
}
```

### Data Flow

```
User adjusts slider → onGraphStylingChange callback
    → Update panelState.graphStyling (local)
    → Update cellState.graphStyling (global)
    → Call actions.plot.createGraphVnode()
    → Creates vnode with key = JSON.stringify(styling)
    → Mithril detects key change, recreates DOM
    → oncreate fires, GraphRenderer.renderD3() with new options
```

### Critical Fix: Real-Time Updates

**Problem**: Graph was only rendered once on data load. Styling changes updated state but didn't re-render.

**Solution**: 
1. Store raw `graphData` in state
2. Use styling options as vnode `key`
3. When key changes, Mithril destroys/recreates element
4. Fresh `oncreate` hook reads current styling from state

---

## Layout Algorithm Integration

**Date**: 2026-01-17
**Status**: ✅ Complete

### Changes

Updated PlotService to accept layout parameter:

```typescript
public static async plotRepoWhole(
  directory: Directory,
  plotterUrl: string,
  layout: string = 'Spring'  // Now dynamic
): Promise<unknown>
```

Added format conversion:

```typescript
function convertLayoutToBackend(frontendLayout: string): string {
  const mapping: Record<string, string> = {
    'spring_layout': 'Spring',
    'spectral_layout': 'Spectral',
    'kamada_kawai_layout': 'Kamada_Kawai',
    // ...
  };
  return mapping[frontendLayout] || 'Spring';
}
```

### Last Plot Action Tracking

Stored last plot action for re-execution when layout changes:

```typescript
let lastPlotAction: (() => Promise<void>) | null = null;

// In plot callback
lastPlotAction = async () => {
  await actions.plot.loadDemo();
};

// When layout changes
if (newLayout !== oldLayout && lastPlotAction) {
  await lastPlotAction();  // Re-fetch with new layout
}
```

---

## Interactive Graph System

**Date**: 2026-01-17
**Status**: ✅ Complete

### Features Implemented

1. **Configurable Control Profiles** - 4 presets (Standard, CAD, Gaming, Touch)
2. **Context-Aware Radial Menu** - Dynamic menu based on selection context
3. **Keyboard Navigation** - Full shortcuts for all actions
4. **Mouse Interactions** - Click, drag, zoom, context menu
5. **Touch Gestures** - Tap, long-press, pinch-zoom, pan
6. **Node Selection** - Multi-select with visual feedback

### Files Created

- `web/src/features/graph/config/interaction_profiles.ts`
- `web/src/features/graph/components/radial_menu.ts`
- `web/src/features/graph/components/radial_menu.css`
- `web/src/features/graph/services/interaction_manager.ts`

### Keyboard Shortcuts (Standard Profile)

| Key | Action |
|-----|--------|
| Arrow Keys | Pan view |
| `+`/`-` | Zoom |
| `0` | Reset zoom |
| `f` | Fit to screen |
| `Space` | Toggle physics |
| `Ctrl+A` | Select all |
| `Esc` | Clear selection |
| `m` | Open radial menu |

---

## Build Metrics Over Time

| Date | JS Bundle | Gzipped | Notes |
|------|-----------|---------|-------|
| Initial | 154.32 kB | 54.34 kB | Before enhancements |
| After styling | 162.55 kB | 55.87 kB | +16 controls |
| After interactions | 192.35 kB | 63.73 kB | +radial menu, profiles |
| Final | 161.98 kB | 55.87 kB | Cleanup, removed unused |
