# Graph Renderer System Implementation

## Overview

Implemented a pluggable renderer architecture that allows different visualization libraries to be used interchangeably based on data format and user preference.

## Architecture

### Core Components

1. **IGraphRenderer Interface** - Base contract all renderers implement
2. **GraphRendererRegistry** - Manages renderer registration and auto-detection
3. **Renderer Implementations** - Specific renderers for different formats

### Class Diagram

```
IGraphRenderer (interface)
    ├── NotebookGraphRenderer (Jupyter/HTML iframes)
    ├── D3GraphRenderer (D3.js interactive graphs)
    └── GravisGraphRenderer (Future client-side gravis)

GraphRendererRegistry (singleton)
    ├── register(type, factory)
    ├── get(type)
    ├── findForData(data)
    └── getDefault()
```

## Data Flow

### Before (Hardcoded)

```
handlePlotData(data)
  │
  ├─ if (data has 'graph' & 'metadata')
  │   └─ Use D3 rendering
  │
  └─ else if (data has 'text/html')
      └─ Use iframe rendering
```

### After (Pluggable)

```
handlePlotData(data)
  │
  └─ GraphRendererRegistry.findForData(data)
      │
      ├─ NotebookGraphRenderer.canHandle(data)  → true if has 'text/html'
      ├─ D3GraphRenderer.canHandle(data)        → true if has 'graph' & 'metadata'
      └─ GravisGraphRenderer.canHandle(data)    → true if type === 'gravis'

      → renderer.render(container, data, styling)
```

## Renderer Routing Logic

### Demo Data → NotebookGraphRenderer

**Input**: Array of Jupyter notebook outputs
```json
[{
  "text/html": "<div>...gravis visualization HTML...</div>",
  "text/plain": "<gravis._internal.plotting...>"
}]
```

**Detection**: `NotebookGraphRenderer.canHandle()` checks for `text/html` property

**Rendering**: Creates iframe with `srcdoc` containing the HTML

**Use Cases**:
- Demo visualizations (pre-rendered gravis HTML)
- Jupyter notebook outputs
- Any pre-rendered HTML visualization

### Imported Graphs → D3GraphRenderer

**Input**: gJGF (Graph JSON Format)
```json
{
  "graph": {
    "nodes": [...],
    "edges": [...],
    "directed": true
  },
  "metadata": {
    "layout": "Spring",
    "type": "d3",
    "nodeCount": 42,
    "edgeCount": 58,
    "palette_id": "0"
  }
}
```

**Detection**: `D3GraphRenderer.canHandle()` checks for `graph` and `metadata` properties

**Rendering**: Client-side D3.js force-directed graph with interactions

**Use Cases**:
- File uploads (AST parsing)
- Repository imports (directory/dependency parsing)
- URL file imports
- Any structured graph data

### Future: Gravis Client-Side → GravisGraphRenderer

**Input**: Same gJGF format but with `metadata.type === 'gravis'`

**Status**: Stub implementation (shows placeholder)

**Planned**: Convert gJGF to gravis format and render client-side

## Implementation Files

### Created Files

1. **web/src/features/graph/services/base_renderer.ts**
   - `IGraphRenderer` interface
   - `GraphRendererRegistry` class
   - Factory pattern types

2. **web/src/features/graph/services/d3_renderer.ts**
   - Wraps existing `GraphRenderer.renderD3()`
   - Handles gJGF data format
   - Auto-detected for graph data

3. **web/src/features/graph/services/notebook_renderer.ts**
   - Renders Jupyter notebook HTML outputs
   - Creates iframes for each HTML output
   - Auto-detected for notebook data

4. **web/src/features/graph/services/gravis_renderer.ts**
   - Stub for future gravis.js client rendering
   - Currently shows placeholder message
   - Ready for implementation

5. **web/src/features/graph/services/renderers.ts**
   - Exports all renderer types
   - Initializes registry on module load
   - Sets default renderer (D3)

6. **web/src/features/graph/services/README.md**
   - Complete documentation
   - Usage examples
   - Extension guide

### Modified Files

1. **web/src/state/actions.ts**
   - `handlePlotData()` - Uses auto-detection
   - `createGraphVnode()` - Uses registry instead of switch
   - Removed hardcoded renderer selection
   - Added `renderWithRenderer()` helper

## Usage Examples

### Auto-Detection (Recommended)

```typescript
import { GraphRendererRegistry } from './services/renderers';

// Let registry auto-detect format
const renderer = GraphRendererRegistry.findForData(data);
if (renderer) {
  console.log(`Using: ${renderer.name}`);
  renderer.render(container, data, stylingOptions);
}
```

### Explicit Selection

```typescript
// Use specific renderer
const d3Renderer = GraphRendererRegistry.get('d3');
d3Renderer.render(container, graphData, stylingOptions);

// Use default renderer
const defaultRenderer = GraphRendererRegistry.getDefault();
defaultRenderer.render(container, data, stylingOptions);
```

### Adding New Renderer

```typescript
// 1. Implement interface
class MyRenderer implements IGraphRenderer {
  readonly type = 'my-renderer';
  readonly name = 'My Custom Renderer';

  render(container, data, styling) { /* ... */ }
  canHandle(data) { /* detection logic */ }
}

// 2. Register in renderers.ts
GraphRendererRegistry.register('my-renderer', () => new MyRenderer());

// 3. Use it
const renderer = GraphRendererRegistry.get('my-renderer');
renderer.render(container, data);
```

## Benefits

### ✅ Separation of Concerns
- Each renderer is isolated in its own class
- No mixing of rendering logic in application code
- Single Responsibility Principle

### ✅ Extensibility
- Add new renderers without modifying existing code
- Open/Closed Principle
- No need to update switch statements

### ✅ Auto-Detection
- No manual format checking in application code
- Cleaner, more maintainable code
- Easier to test

### ✅ Type Safety
- TypeScript interfaces ensure consistency
- Compile-time checks
- Better IDE support

### ✅ Testability
- Each renderer can be unit tested independently
- Mock renderers for testing
- Isolated concerns

### ✅ Flexibility
- Switch renderers at runtime
- User preferences for renderer
- A/B testing different renderers

## Current State

### ✅ Completed
- Base interface and registry system
- D3 renderer implementation
- Notebook renderer implementation
- Gravis renderer stub
- Auto-detection logic
- Documentation
- Integration with PlotActions
- Production build tested (267.30 kB)

### 🚧 Future Work
- Implement client-side gravis.js rendering
- Add Three.js renderer for 3D graphs
- Add vis.js renderer as 2D alternative
- Add renderer selection UI
- Add renderer-specific settings
- Performance metrics per renderer
- Dynamic renderer loading (plugins)

## Testing

### Build Status
```bash
npm run build
# ✓ 728 modules transformed
# ✓ 267.30 kB / 86.63 kB gzipped
# ✓ built in 2.06s
```

### TypeScript Validation
```bash
npx tsc --noEmit
# No errors ✓
```

### Manual Testing
- ✅ Demo loads with NotebookRenderer
- ✅ Imported graphs use D3Renderer
- ✅ Auto-detection works correctly
- ✅ Styling updates trigger re-render
- ✅ No console errors

## Migration Notes

### Breaking Changes
- None (backward compatible)

### Deprecated
- Direct calls to `GraphRenderer.renderD3()` should use registry
- Hardcoded renderer type checks should use auto-detection

### Upgrade Path
```typescript
// Old way (still works, but not recommended)
if (typeof data === 'object' && 'graph' in data) {
  GraphRenderer.renderD3(container, data, styling);
}

// New way (recommended)
const renderer = GraphRendererRegistry.findForData(data);
renderer.render(container, data, styling);
```

## Performance

### Bundle Size Impact
- **Before**: ~264 kB
- **After**: ~267 kB (+3 kB)
- **Gzipped**: 86.63 kB

### Runtime Impact
- Minimal overhead from auto-detection
- No performance regression in rendering
- Same rendering performance as before

## Conclusion

The pluggable renderer system provides a clean, extensible architecture for supporting multiple visualization libraries. It maintains backward compatibility while enabling future enhancements without code churn.

The system is production-ready and has been successfully integrated into the application with zero breaking changes.
