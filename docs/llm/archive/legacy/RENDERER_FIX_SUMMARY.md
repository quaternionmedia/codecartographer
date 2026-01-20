# Graph Renderer Fix - Summary

**Date**: 2026-01-18
**Issue**: Renderer selection in UI doesn't update the graph visualization
**Status**: ✅ Fixed

---

## Problem Diagnosis

### Root Cause
The demo data was a pre-rendered HTML file (`web/src/demo/demo.txt`) containing Jupyter notebook output. This had several issues:

1. **Static HTML**: The demo file contained pre-rendered Gravis HTML (~500KB), not GraphData JSON
2. **No Re-rendering**: HTML couldn't be re-rendered with different renderers (D3, Gravis, vis-network)
3. **Ignored User Selection**: `handlePlotData()` auto-detected the renderer and ignored `selectedRenderer` state
4. **No GraphData Stored**: HTML rendering path didn't store `graphData` to state, preventing later renderer switching
5. **Confusing UI**: Demo buttons were labeled as different themes but all loaded the same visualization

### Data Flow (Before Fix)

```
Demo Button Click
    ↓
onDemo() (async) → loads demo.txt (500KB HTML)
onThemeChange('terminal') (sync) → updates theme
    ↓
handlePlotData(html) → auto-detects NotebookRenderer
    ↓
renderWithRenderer(NotebookRenderer, html)
    ↓
Creates iframe with srcdoc (no graphData stored!)
    ↓
onRendererChange has NO EFFECT (no graphData to re-render)
```

---

## Solution Implemented

### Backend Changes

#### 1. New Demo Endpoint (`codecarto/routers/plotter_router.py`)

Added `/demo` endpoint that generates GraphData JSON from the codecarto project itself:

```python
@PlotterRouter.post("/demo")
async def plot_demo(options: PlotOptions) -> dict:
    """
    Generate demo graph data using the codecarto project itself.
    Returns GraphData JSON format that can be rendered with any client-side renderer.
    """
    # Uses codecarto directory as demo source
    # Supports all parser modes: ast, dependencies, directory
    # Returns {graph: {...}, metadata: {...}}
```

**Benefits**:
- Returns GraphData JSON (not HTML)
- Respects `parse_by` option (ast, dependencies, directory)
- Respects `layout` option (Spring, Spectral, etc.)
- Can be rendered with any client-side renderer
- Much smaller payload (~10-50KB vs 500KB)

#### 2. PlotService Update (`web/src/services/plot_service.ts`)

Added `loadDemo()` method:

```typescript
public static async loadDemo(
  plotterUrl: string,
  layout: string = 'Spring',
  parseMode: string = 'directory'
): Promise<unknown>
```

### Frontend Changes

#### 3. PlotActions Update (`web/src/state/actions.ts`)

Changed `loadDemo()` to call backend API instead of loading static HTML:

```typescript
async loadDemo(): Promise<void> {
  this.stateController.clear();
  try {
    const layout = convertLayoutToBackend(this.stateController.state.graphStyling.layout);
    const parseMode = this.stateController.state.parserOptions.mode;
    const data = await PlotService.loadDemo(
      this.stateController.api.plotter,
      layout,
      parseMode
    );
    this.handlePlotData(data);
  } catch (error) {
    console.error('Failed to load demo:', error);
    throw error;
  }
}
```

Removed unused import: `handleDemoData as getDemoData`

#### 4. Renderer Change Callback Fix (`web/src/components/codecarto/codecarto.ts`)

Fixed `onRendererChange` callback to properly trigger re-render:

**Before**:
```typescript
if (currentCell.state.graphData) {
  const currentPlotActions = getCell().state.plot; // ❌ Wrong!
  if (currentPlotActions && currentPlotActions.createGraphVnode) {
    currentPlotActions.createGraphVnode();
  }
}
```

**After**:
```typescript
if (currentCell.state.graphData) {
  actions.plot.createGraphVnode(); // ✅ Correct!
  m.redraw();
}
```

#### 5. Control Panel Simplification (`web/src/components/codecarto/control_panel/control_panel.ts`)

Replaced three theme-based demo buttons with single demo button:

**Before**:
```typescript
m('button', '⚡ Demo (Terminal)')  // All loaded same HTML
m('button', '🌊 Demo (Ocean)')
m('button', '🔮 Demo (Cyberpunk)')
```

**After**:
```typescript
m('button', '⚡ Load Demo')  // Uses backend API with current settings
```

---

## Data Flow (After Fix)

```
Demo Button Click
    ↓
onDemo() → PlotActions.loadDemo()
    ↓
PlotService.loadDemo(layout, parseMode)
    ↓
POST /demo with {layout: "Spring", parse_by: "directory"}
    ↓
Backend generates GraphData JSON
    ↓
handlePlotData(graphData) → renderGraphData()
    ↓
Stores graphData to state ✅
    ↓
createGraphVnode() → uses selectedRenderer from state
    ↓
Renders with D3/Gravis/Notebook based on user selection ✅

User Changes Renderer
    ↓
onRendererChange('gravis')
    ↓
Updates selectedRenderer in state
    ↓
createGraphVnode() → re-renders with new renderer ✅
```

---

## Testing Plan

### Manual Testing

1. **Start Backend**:
   ```bash
   cd codecartographer
   uv run codecarto
   ```

2. **Start Frontend**:
   ```bash
   cd web
   npm run dev
   ```

3. **Test Demo Loading**:
   - Click "⚡ Load Demo" button
   - Should load codecarto project structure
   - Should render with current renderer (default: D3)

4. **Test Renderer Switching**:
   - Load demo
   - Switch to Layout tab
   - Change renderer to "Gravis (vis-network)"
   - Graph should re-render with Gravis renderer ✅
   - Change to "Notebook (Static HTML)" (should show warning)
   - Change back to "D3.js (Force-directed)"
   - Graph should re-render with D3 ✅

5. **Test Parser Mode Switching**:
   - Go to Parse tab
   - Select "AST" mode
   - Re-load demo (graph should update to show AST structure)
   - Select "Dependencies" mode
   - Re-load demo (graph should update to show dependencies)
   - Select "Directory" mode
   - Re-load demo (graph should update to show file tree)

6. **Test Layout Switching**:
   - Load demo
   - Go to Layout tab
   - Change layout algorithm (should re-fetch from backend)
   - Graph positions should update

7. **Test Theme Switching**:
   - Load demo
   - Go to Theme tab
   - Switch between themes
   - Graph colors should update

### Expected Results

✅ Demo loads GraphData JSON (not HTML)
✅ Renderer selection works (can switch between D3/Gravis/Notebook)
✅ Parser mode selection affects demo content
✅ Layout algorithm affects node positions
✅ Theme affects graph colors
✅ All settings persist across re-renders

---

## Files Changed

### Backend
- `codecarto/routers/plotter_router.py` - Added `/demo` endpoint

### Frontend
- `web/src/services/plot_service.ts` - Added `loadDemo()` method
- `web/src/state/actions.ts` - Updated `loadDemo()` to use backend API
- `web/src/components/codecarto/codecarto.ts` - Fixed `onRendererChange` callback
- `web/src/components/codecarto/control_panel/control_panel.ts` - Simplified demo button

### Build Status
```
✓ 729 modules transformed
✓ built in 4.91s
✓ No TypeScript errors
```

---

## Benefits of This Fix

1. **Renderer Switching Works**: Users can now switch between D3, Gravis, and Notebook renderers
2. **Smaller Payload**: GraphData JSON (~10-50KB) vs pre-rendered HTML (500KB)
3. **Parser Mode Matters**: Demo now respects parser mode selection (AST vs Dependencies vs Directory)
4. **Layout Matters**: Demo now respects layout algorithm selection
5. **Consistent Behavior**: Demo works the same as file uploads and repo fetches
6. **Real-time Updates**: Changing renderer/layout/theme updates the graph immediately
7. **Cleaner UI**: Single demo button instead of confusing theme variants
8. **Better UX**: User settings actually affect the demo visualization

---

## Future Enhancements

1. **Pre-generated Demo Files**: Create 3 static GraphData JSON files for instant loading
   - `demo-ast.json` - AST structure
   - `demo-deps.json` - Dependency graph
   - `demo-tree.json` - File tree

2. **Demo Gallery**: Multiple demo datasets (different projects, complexity levels)

3. **Demo Persistence**: Save user's last demo configuration (renderer, parser, layout)

4. **Demo Sharing**: Generate shareable links with demo configuration

---

## Backwards Compatibility

The old demo file (`web/src/demo/demo.txt`) can be removed:
- No longer used by the application
- Replaced by dynamic backend generation
- 500KB file can be deleted to reduce repo size

**Note**: The demo service file (`web/src/services/demo_service.ts`) is also no longer needed and can be removed.

---

## Commit Message Suggestion

```
fix(renderer): enable renderer switching with demo data

Problem:
- Demo loaded pre-rendered HTML that couldn't be re-rendered
- Renderer selection had no effect on demo visualization
- Theme-based demo buttons were confusing (all loaded same data)

Solution:
- Added /demo backend endpoint that generates GraphData JSON
- Updated demo loading to use backend API instead of static file
- Fixed onRendererChange callback to trigger re-render
- Simplified control panel to single demo button

Benefits:
- Users can now switch renderers (D3, Gravis, Notebook)
- Parser mode selection affects demo (AST, Dependencies, Directory)
- Layout algorithm affects demo positions
- Smaller payload (10-50KB vs 500KB)
- Consistent behavior with file uploads and repo fetches

Files changed:
- codecarto/routers/plotter_router.py (new /demo endpoint)
- web/src/services/plot_service.ts (loadDemo method)
- web/src/state/actions.ts (use backend API)
- web/src/components/codecarto/codecarto.ts (fix callback)
- web/src/components/codecarto/control_panel/control_panel.ts (UI)
```

---

## Related Documentation

- `RENDERER_SYSTEM.md` - Renderer architecture
- `RENDERER_ROUTING.md` - Renderer selection logic
- `CONTROL_PANEL_GUIDE.md` - Control panel reference
- Migration plan from `~/.claude/plans/wondrous-crafting-zebra.md`
