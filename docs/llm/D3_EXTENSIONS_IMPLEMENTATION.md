# D3 Extensions System - Layer 1 Implementation

**Date**: 2026-01-17
**Status**: ✅ Complete
**Build**: Passing (249.76 kB, gzipped: 82.11 kB)

## Overview

Implemented a comprehensive plugin-based D3 extensions architecture that adds advanced interactive functionality to graph visualizations in a modular, composable way.

## Architecture

### Extension Registry System

Created a plugin architecture with:
- Base extension interface for consistency
- Extension registry for managing multiple extensions
- Context-based initialization
- Enable/disable functionality
- Clean lifecycle management (initialize → apply → destroy)

**Files Created:**
- [web/src/features/graph/extensions/index.ts](web/src/features/graph/extensions/index.ts) - Core architecture (270 lines)

### Extension Context

All extensions receive a unified context with access to:
```typescript
interface ExtensionContext<TNode, TEdge> {
  svg: d3.Selection<SVGSVGElement, ...>;
  graphGroup: d3.Selection<SVGGElement, ...>;
  nodes: d3.Selection<SVGCircleElement, TNode, ...>;
  edges: d3.Selection<SVGLineElement, TEdge, ...>;
  labels: d3.Selection<SVGTextElement, TNode, ...>;
  zoom?: d3.ZoomBehavior<...>;
  simulation?: d3.Simulation<TNode, TEdge>;
  container: HTMLElement;
  data: { nodes: TNode[]; edges: TEdge[]; };
  selectedNodes: Set<TNode>;
  onGraphChange?: () => void;
}
```

## Layer 1 Extensions

### 1. Drag Extension ✅

**File**: [drag_extension.ts](web/src/features/graph/extensions/drag_extension.ts) (235 lines)

**Features:**
- Multi-node dragging (drag all selected nodes together)
- Grid snapping with configurable grid size
- Axis locking (X-only or Y-only dragging)
- Customizable drag callbacks
- Automatic simulation heat-up during drag
- Position preservation for pinned nodes

**Options:**
```typescript
{
  gridSnap: false,          // Enable grid snapping
  gridSize: 20,             // Grid size in pixels
  lockX: false,             // Lock to X axis
  lockY: false,             // Lock to Y axis
  multiDrag: true,          // Drag all selected nodes
  showGhost: false,         // Show drag preview
  alphaTarget: 0.3,         // Simulation heat during drag
  onDragStart: (node) => {},
  onDrag: (node) => {},
  onDragEnd: (node) => {},
}
```

**Usage Example:**
```typescript
const drag = new DragExtension({ multiDrag: true, gridSnap: true });
drag.initialize(context);
drag.apply();
```

### 2. Selection Extension ✅

**File**: [selection_extension.ts](web/src/features/graph/extensions/selection_extension.ts) (380 lines)

**Features:**
- **Box Selection**: Shift+Drag to select nodes in rectangular area
- **Lasso Selection**: Alt+Drag for freeform selection path
- **Multi-select**: Ctrl+Click to add to selection
- **Select Neighbors**: Select all connected nodes
- **Invert Selection**: Flip selected/unselected nodes
- **Select All**: Select all nodes programmatically
- **Real-time visual feedback** during selection

**Options:**
```typescript
{
  enableBoxSelect: true,      // Shift+Drag box select
  enableLassoSelect: true,    // Alt+Drag lasso select
  boxStroke: '#00ff41',       // Box border color
  boxFill: '#00ff4120',       // Box fill color
  lassoStroke: '#00ff41',     // Lasso path color
  selectionColor: '#00ff41',  // Selected node highlight
  selectionWidth: 3,          // Highlight stroke width
  onSelectionChange: (set) => {},
}
```

**Usage Example:**
```typescript
const selection = new SelectionExtension({ enableBoxSelect: true });
selection.initialize(context);
selection.apply();

// Public API
selection.selectNeighbors(context);  // Select connected nodes
selection.invertSelection(context);   // Invert selection
selection.selectAll(context);         // Select all
```

**Selection Methods:**
- Shift+Drag on canvas → Box selection
- Alt+Drag on canvas → Lasso selection
- Ctrl during selection → Add to existing selection
- Uses point-in-polygon algorithm for lasso

### 3. Zoom Extension ✅

**File**: [zoom_extension.ts](web/src/features/graph/extensions/zoom_extension.ts) (320 lines)

**Features:**
- **Zoom to Fit**: Automatically fit all nodes in viewport
- **Zoom to Selection**: Fit only selected nodes
- **Zoom to Node**: Focus on specific node with scale
- **Zoom Level Indicator**: Shows current zoom percentage
- **Animated Transitions**: Smooth zoom animations
- **Programmatic Zoom**: Set specific zoom levels

**Options:**
```typescript
{
  minZoom: 0.1,              // Minimum zoom level
  maxZoom: 10,               // Maximum zoom level
  transitionDuration: 750,    // Animation duration (ms)
  fitPadding: 0.1,           // Padding when fitting (0-1)
  showZoomLevel: true,        // Show zoom % indicator
  onZoomChange: (scale) => {},
}
```

**Public API:**
```typescript
zoomExtension.zoomToFit(context, animated);          // Fit all nodes
zoomExtension.zoomToSelection(context, animated);    // Fit selected
zoomExtension.zoomToNode(context, node, scale);      // Focus node
zoomExtension.zoomIn(context, factor);               // Zoom in
zoomExtension.zoomOut(context, factor);              // Zoom out
zoomExtension.resetZoom(context);                    // Reset to 1:1
zoomExtension.getCurrentZoom(context);               // Get scale
```

**Zoom Level Indicator:**
- Appears in top-right corner during zoom
- Shows percentage (e.g., "150%")
- Auto-hides after 1.5 seconds
- Theme-aware styling

### 4. Highlight Extension ✅

**File**: [highlight_extension.ts](web/src/features/graph/extensions/highlight_extension.ts) (300 lines)

**Features:**
- **Hover Highlighting**: Highlight node on mouse hover
- **Neighbor Highlighting**: Show connected nodes
- **Path Highlighting**: Highlight shortest path between nodes
- **Fade Non-highlighted**: Dim unrelated elements
- **Smooth Transitions**: Animated opacity changes
- **Edge Highlighting**: Highlight connecting edges

**Options:**
```typescript
{
  enableHover: true,         // Enable hover effects
  highlightNeighbors: true,  // Highlight connected nodes
  fadeOpacity: 0.15,         // Opacity for non-highlighted
  highlightColor: '#00ff41', // Main highlight color
  highlightWidth: 4,         // Highlight stroke width
  neighborColor: '#00d4ff',  // Neighbor highlight color
  edgeColor: '#00ff41',      // Highlighted edge color
  transitionDuration: 200,   // Animation speed (ms)
  onHighlight: (node) => {},
  onUnhighlight: () => {},
}
```

**Public API:**
```typescript
highlightExtension.highlightNode(node, context);           // Manual highlight
highlightExtension.highlightPath(start, end, context);     // Path highlight
highlightExtension.clearHighlight();                       // Clear all
highlightExtension.pulse(context);                         // Pulse effect
```

**Behavior:**
- Hover over node → Highlight node + neighbors + connecting edges
- Non-highlighted elements fade to 15% opacity
- Smooth 200ms transitions
- Uses BFS for path finding

### 5. Tooltip Extension ✅

**File**: [tooltip_extension.ts](web/src/features/graph/extensions/tooltip_extension.ts) (360 lines)

**Features:**
- **Rich Tooltips**: HTML content with metadata
- **Smart Positioning**: Avoids viewport overflow
- **Configurable Delay**: Show/hide delays
- **Follow Cursor or Anchor**: Two positioning modes
- **Custom Formatters**: Customize tooltip content
- **Auto-metadata**: Shows node properties automatically

**Options:**
```typescript
{
  enabled: true,             // Enable tooltips
  showDelay: 300,            // Delay before showing (ms)
  hideDelay: 100,            // Delay before hiding (ms)
  followCursor: false,       // Follow mouse or anchor to node
  offset: { x: 12, y: 12 }, // Offset from cursor/node
  maxWidth: 300,             // Maximum tooltip width
  formatter: (node) => {},   // Custom content formatter
  showMetadata: true,        // Auto-show node metadata
}
```

**Default Tooltip Content:**
```
┌─────────────────────────┐
│ Node Label              │
├─────────────────────────┤
│ ID: node-123            │
│ Type: file              │
│ Size: 450               │
│ Color: #ff0000          │
│ [custom properties...]  │
└─────────────────────────┘
```

**Public API:**
```typescript
tooltipExtension.showForNode(node, context);  // Manual show
tooltipExtension.hideTooltip();               // Manual hide
tooltipExtension.updateOptions({ ... });      // Update options
```

**Smart Positioning:**
- Prevents overflow beyond viewport edges
- Automatically adjusts position
- Maintains 8px minimum padding

### 6. Color Extension ✅

**File**: [color_extension.ts](web/src/features/graph/extensions/color_extension.ts) (400 lines)

**Features:**
- **Multiple Color Schemes**: 18 built-in D3 schemes
- **Automatic Coloring**: Color by any node property
- **Sequential Scales**: For numerical data
- **Categorical Scales**: For discrete categories
- **Color by Degree**: Color based on connectivity
- **Color by Cluster**: Automatic cluster coloring
- **Theme-aware Palettes**: Generate from CSS variables
- **Custom Colors**: Provide custom color array

**Supported Schemes:**
- **Categorical**: category10, category20, tableau10, accent, dark2, paired, pastel1, pastel2, set1, set2, set3
- **Sequential**: viridis, inferno, magma, plasma, warm, cool, rainbow, sinebow
- **Custom**: Provide your own color array

**Options:**
```typescript
{
  scheme: 'category10',      // Color scheme
  customColors: [],          // Custom palette
  colorBy: 'type',           // Property to color by
  minValue: 0,               // Min for sequential
  maxValue: 100,             // Max for sequential
  autoApply: false,          // Auto-apply on init
}
```

**Public API:**
```typescript
colorExtension.applyColorScheme(context);            // Apply current scheme
colorExtension.colorByProperty('type', context);     // Color by property
colorExtension.setColorScheme('viridis', context);   // Change scheme
colorExtension.colorByDegree(context);               // Color by connectivity
colorExtension.colorByClusters(context);             // Color by cluster
colorExtension.randomize(context);                   // Random colors
colorExtension.reset(context);                       // Reset to original
colorExtension.generateGradient(start, end, steps);  // Create gradient
colorExtension.generateThemePalette(count);          // Theme-aware colors
```

**Example - Color by Node Degree:**
```typescript
// Automatically colors nodes based on number of connections
// Uses viridis gradient from low to high connectivity
colorExtension.colorByDegree(context);
```

## Integration with Graph Renderer

### Automatic Initialization

All extensions are automatically initialized when rendering a graph:

```typescript
// In graph_renderer.ts
private static initializeExtensions(...) {
  const context = { svg, nodes, edges, ... };

  // Initialize all 6 extensions
  this.dragExtension = new DragExtension({ multiDrag: true });
  this.dragExtension.initialize(context);
  this.dragExtension.apply();

  // ... repeat for all extensions
}
```

### Public API Methods

Added public methods to GraphRenderer for easy access:

```typescript
GraphRenderer.zoomToFit();           // Zoom to show all nodes
GraphRenderer.zoomToSelection();     // Zoom to selected nodes
GraphRenderer.selectNeighbors();     // Select connected nodes
GraphRenderer.applyColorScheme(scheme);  // Change colors
GraphRenderer.colorByDegree();       // Color by connectivity
GraphRenderer.getExtensions();       // Access extension instances
```

### Extension Context Creation

Helper method to create context from current state:

```typescript
private static createExtensionContext(): ExtensionContext {
  return {
    svg: this.currentSvg,
    graphGroup: this.currentSvg.select('g'),
    nodes: graphGroup.selectAll('.graph-node'),
    edges: graphGroup.selectAll('line'),
    labels: graphGroup.selectAll('text'),
    zoom: this.currentZoom,
    simulation: this.currentSimulation,
    container: this.currentSvg.node().parentElement,
    data: { nodes: this.currentNodes, edges: this.currentEdges },
    selectedNodes: this.selectedNodes,
  };
}
```

## Usage Guide

### Basic Usage

Extensions are automatically applied when rendering. Use public API for advanced operations:

```typescript
// Render graph (extensions auto-initialize)
GraphRenderer.renderD3(container, graphData, styling);

// Use public API
GraphRenderer.zoomToFit();              // Fit all nodes
GraphRenderer.selectNeighbors();        // Select connected
GraphRenderer.colorByDegree();          // Color by connectivity
```

### Advanced Usage

Access extension instances directly for full control:

```typescript
const extensions = GraphRenderer.getExtensions();

// Configure drag extension
extensions.drag?.updateOptions({
  gridSnap: true,
  gridSize: 50,
  lockX: false,
});

// Configure selection extension
extensions.selection?.selectNeighbors(context);
extensions.selection?.invertSelection(context);

// Configure zoom extension
extensions.zoom?.zoomToNode(context, node, 2.0);
extensions.zoom?.zoomIn(context, 1.5);

// Configure highlight extension
extensions.highlight?.highlightPath(startNode, endNode, context);
extensions.highlight?.pulse(context);

// Configure tooltip extension
extensions.tooltip?.updateOptions({
  showDelay: 500,
  followCursor: true,
});

// Configure color extension
extensions.color?.setColorScheme('viridis', context);
extensions.color?.generateThemePalette(10);
```

## Interaction Methods

### Box Selection
1. Hold **Shift**
2. Click and drag on empty canvas
3. Release to select all nodes in box
4. Hold **Ctrl** while dragging to add to existing selection

### Lasso Selection
1. Hold **Alt**
2. Click and drag freeform path on canvas
3. Release to select all nodes within lasso
4. Hold **Ctrl** while dragging to add to existing selection

### Multi-node Drag
1. Select multiple nodes (Ctrl+Click or box/lasso select)
2. Drag any selected node
3. All selected nodes move together
4. Maintains relative positions

### Hover Highlighting
1. Move mouse over any node
2. Node highlights with bright color
3. Connected neighbors highlight with secondary color
4. Connecting edges highlight
5. All other elements fade to 15% opacity

### Tooltips
1. Hover over node for 300ms
2. Rich tooltip appears with metadata
3. Move away to hide after 100ms
4. Smart positioning prevents overflow

## Build Metrics

| Metric | Before Extensions | After Extensions | Change |
|--------|------------------|------------------|--------|
| JS Bundle | 195.41 kB | 249.76 kB | +54.35 kB |
| Gzipped JS | 64.50 kB | 82.11 kB | +17.61 kB |
| CSS Bundle | 32.58 kB | 32.58 kB | No change |
| Build Time | 1.71s | 1.73s | +0.02s |

**Analysis**: Moderate increase (+54 kB, +17 kB gzipped) for comprehensive interactive system is acceptable and expected.

## Technical Implementation Details

### Extension Lifecycle

1. **Initialize**: Extension receives context with D3 selections and state
2. **Apply**: Extension sets up event listeners and modifies DOM
3. **Destroy**: Extension cleans up listeners and removes DOM elements

```typescript
class MyExtension extends BaseExtension {
  public initialize(context: ExtensionContext): void {
    this.context = context;  // Store context
  }

  public apply(): void {
    // Setup event listeners
    this.context.nodes.on('click', ...);
  }

  public destroy(): void {
    // Remove listeners
    this.context.nodes.on('click', null);
    super.destroy();
  }
}
```

### Event Handling Patterns

All extensions use consistent event handling:

```typescript
// Attach namespaced listeners
context.svg.on('mousedown.selection', handler);

// Remove by namespace
context.svg.on('mousedown.selection', null);
```

### D3 v6+ Compatibility

Fixed compatibility issues with D3 v6+:
- Removed deprecated `d3.event` usage
- Track modifier keys via event parameters
- Use event object directly in handlers

**Before (D3 v5):**
```typescript
.on('click', function() {
  const event = d3.event;  // ❌ Deprecated in v6+
  if (event.ctrlKey) { ... }
});
```

**After (D3 v6):**
```typescript
.on('click', (event: MouseEvent) => {
  if (event.ctrlKey) { ... }  // ✅ Use event parameter
});
```

### Theme Integration

All extensions use CSS custom properties for theme-aware colors:

```typescript
const rootStyles = getComputedStyle(document.documentElement);
const secondaryColor = rootStyles.getPropertyValue('--c-secondary').trim();
const primaryColor = rootStyles.getPropertyValue('--c-primary').trim();
```

This ensures extensions adapt to active theme (Terminal/Light/Cyberpunk).

## Files Created

### Core Architecture
- [web/src/features/graph/extensions/base.ts](web/src/features/graph/extensions/base.ts) - Base classes and interfaces (120 lines)
- [web/src/features/graph/extensions/index.ts](web/src/features/graph/extensions/index.ts) - Extension registry and exports (140 lines)

### Layer 1 Extensions
- [web/src/features/graph/extensions/drag_extension.ts](web/src/features/graph/extensions/drag_extension.ts) (235 lines)
- [web/src/features/graph/extensions/selection_extension.ts](web/src/features/graph/extensions/selection_extension.ts) (380 lines)
- [web/src/features/graph/extensions/zoom_extension.ts](web/src/features/graph/extensions/zoom_extension.ts) (320 lines)
- [web/src/features/graph/extensions/highlight_extension.ts](web/src/features/graph/extensions/highlight_extension.ts) (300 lines)
- [web/src/features/graph/extensions/tooltip_extension.ts](web/src/features/graph/extensions/tooltip_extension.ts) (360 lines)
- [web/src/features/graph/extensions/color_extension.ts](web/src/features/graph/extensions/color_extension.ts) (400 lines)

**Total**: ~2,395 lines of extension code

### Fix Applied
**Issue**: Circular dependency - extensions importing from `index.ts` which exports the extensions
**Solution**: Created separate `base.ts` file with base classes and interfaces, updated all extensions to import from `base.ts`

### Files Modified
- [web/src/features/graph/services/graph_renderer.ts](web/src/features/graph/services/graph_renderer.ts) (+170 lines)
  - Added extension imports
  - Added extension initialization
  - Added public API methods
  - Added context creation helper

## Future Extensions (Layer 2+)

### Potential Layer 2 Extensions
- **Layout Extension**: Dynamic layout switching (force, hierarchical, circular)
- **Animation Extension**: Animated transitions and effects
- **Filter Extension**: Filter nodes by properties
- **Search Extension**: Search and highlight nodes
- **Minimap Extension**: Overview minimap for large graphs
- **Export Extension**: Export graph as PNG, SVG, JSON
- **Undo/Redo Extension**: Action history with undo/redo
- **Clustering Extension**: Automatic node clustering

### Potential Layer 3 Extensions
- **Collaboration Extension**: Multi-user editing
- **Timeline Extension**: Time-based graph evolution
- **3D Extension**: 3D graph rendering with Three.js
- **VR Extension**: VR graph exploration
- **AI Extension**: AI-powered layout and insights

## Testing Checklist

### Drag Extension
- ✅ Single node drag works
- ✅ Multi-node drag works
- ✅ Grid snapping works (when enabled)
- ✅ Simulation heats up during drag
- ✅ Position preserved for pinned nodes

### Selection Extension
- ✅ Box selection works (Shift+Drag)
- ✅ Lasso selection works (Alt+Drag)
- ✅ Ctrl adds to selection
- ✅ Select neighbors works
- ✅ Invert selection works
- ✅ Visual feedback during selection

### Zoom Extension
- ✅ Zoom to fit works
- ✅ Zoom to selection works
- ✅ Zoom level indicator shows
- ✅ Smooth animations work
- ✅ Zoom in/out works

### Highlight Extension
- ✅ Hover highlighting works
- ✅ Neighbors highlight
- ✅ Non-highlighted elements fade
- ✅ Smooth transitions
- ✅ Path highlighting works (BFS)

### Tooltip Extension
- ✅ Tooltips appear on hover
- ✅ Delay works correctly
- ✅ Smart positioning prevents overflow
- ✅ Metadata displays correctly
- ✅ Theme-aware styling

### Color Extension
- ✅ Color schemes apply correctly
- ✅ Color by property works
- ✅ Color by degree works
- ✅ Gradient generation works
- ✅ Theme palette generation works

## Known Limitations

### Current Behavior

1. **Drag Extension**
   - No visual preview during drag (ghost can be enabled)
   - Grid snap uses simple rounding (no magnetic snapping)

2. **Selection Extension**
   - Lasso uses catmull-rom curve which may not match drawn path exactly
   - No keyboard shortcuts for selection operations yet

3. **Zoom Extension**
   - Zoom level indicator doesn't persist
   - No zoom history (can't undo zoom)

4. **Highlight Extension**
   - Path finding uses simple BFS (doesn't consider edge weights)
   - Can't highlight multiple paths simultaneously

5. **Tooltip Extension**
   - Tooltips don't resize dynamically
   - Custom formatter requires HTML knowledge

6. **Color Extension**
   - Auto-apply doesn't preserve original colors
   - No color persistence across re-renders

## Success Criteria

✅ Extension architecture implemented with registry system
✅ All 6 Layer 1 extensions implemented
✅ Extensions integrated with graph renderer
✅ Public API methods available
✅ Build passes without errors
✅ D3 v6+ compatibility ensured
✅ Theme-aware styling throughout
✅ Comprehensive documentation created

---

**Status**: ✅ Layer 1 Complete
**Build**: ✅ Passing (249.76 kB, gzipped: 82.11 kB)
**Extensions**: ✅ 6/6 Implemented and Tested
**Ready for**: Production use and Layer 2 development
