# State Consolidation Plan

**Status: COMPLETED**

## Problem Summary

The UI had **dual state** that must be kept in sync:
1. `panelState` (local in codecarto.ts) - controls UI display
2. `cell.state` (Meiosis global) - used by actions/renderers

Every change requires updating both, creating sync bugs and complexity.

## Current Flow Issues

### Parser Mode Change Flow
```
User clicks "Directory" mode
  -> onParserOptionsChange()
    -> updatePanelState({ parserOptions })     // local
    -> currentCell.update({ parserOptions })   // global
    -> lastPlotAction()                        // re-fetch
      -> actions.plot.loadDemo()
        -> reads stateController.state.parserOptions.mode  [ok] (uses global)
```
**Status**: Works, but dual-update is fragile.

### Layout Change Flow
```
User changes layout dropdown
  -> onGraphStylingChange()
    -> updatePanelState({ graphStyling })      // local
    -> currentCell.update({ graphStyling })    // global
    -> lastPlotAction()                        // re-fetch
      -> actions.plot.loadDemo()
        -> reads stateController.state.graphStyling.layout  [ok] (uses global)
```
**Status**: Works, but dual-update is fragile.

### Renderer Change Flow
```
User changes renderer dropdown
  -> onRendererChange()
    -> updatePanelState({ selectedRenderer })  // local
    -> currentCell.update({ selectedRenderer })// global
    -> actions.plot.createGraphVnode()
      -> reads stateController.state.selectedRenderer  [ok] (uses global)
```
**Status**: Works, but dual-update is fragile.

---

## Consolidation Plan

### Goal
Single source of truth: **cell.state** for all settings.
`panelState` only holds UI-specific ephemeral state (loading, messages, tab).

### Phase 1: Remove Duplicated State from panelState

**Before:**
```typescript
let panelState = {
  isOpen: false,
  activeTab: 'source',
  isLoading: false,
  statusMessage: 'Ready',
  // DUPLICATES - remove these:
  graphStyling: { ... },
  parserOptions: { ... },
  selectedRenderer: 'd3',
};
```

**After:**
```typescript
let panelState = {
  isOpen: false,
  activeTab: 'source',
  codeSourceMode: 'upload',
  repoUrl: '',
  currentTheme: 'forest',
  isLoading: false,
  statusMessage: 'Ready',
  panelHeight: 300,
  // NO graphStyling, parserOptions, selectedRenderer
};
```

### Phase 2: Update Callbacks to Use Single Source

**Before:**
```typescript
onParserOptionsChange: async (options) => {
  const oldMode = panelState.parserOptions.mode;  // reads local
  updatePanelState({ parserOptions: ... });       // updates local
  currentCell.update({ parserOptions: ... });     // updates global
  ...
}
```

**After:**
```typescript
onParserOptionsChange: async (options) => {
  const currentCell = getCell();
  const oldMode = currentCell.state.parserOptions.mode;  // reads global only
  currentCell.update({ parserOptions: { ...currentCell.state.parserOptions, ...options } });
  m.redraw();  // trigger UI update
  ...
}
```

### Phase 3: Update Control Panel to Read from cell.state

**Before:**
```typescript
// In control_panel.ts or codecarto.ts
const styling = panelState.graphStyling;
```

**After:**
```typescript
// Pass cell.state values to control panel
const getContent = (): ControlPanelContent => ({
  graphStyling: getCell().state.graphStyling,
  parserOptions: getCell().state.parserOptions,
  selectedRenderer: getCell().state.selectedRenderer,
  ...
});
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `web/src/components/codecarto/codecarto.ts` | Remove duplicated state from panelState, update callbacks |
| `web/src/components/codecarto/control_panel/control_panel.ts` | Read from content props instead of panelState |
| `web/src/components/codecarto/control_panel/types.ts` | Update ControlPanelState interface |

---

## Implementation Steps

1. **Update ControlPanelState interface** - remove graphStyling, parserOptions, selectedRenderer
2. **Update ControlPanelContent interface** - add graphStyling, parserOptions, selectedRenderer
3. **Update panelState initialization** - remove duplicated fields
4. **Update getContent()** - pass cell.state values
5. **Update all callbacks** - remove dual updates, use cell.state only
6. **Update control_panel.ts** - read from content props

---

## Verification

1. Load demo -> verify graph renders
2. Change parser mode -> verify graph re-renders with new mode
3. Change layout -> verify graph re-renders with new layout
4. Change renderer -> verify graph re-renders with new renderer
5. Change styling (node size, etc.) -> verify immediate update
6. Refresh page -> verify defaults are applied

---

## Idempotency Checklist

After consolidation, each setting change should be idempotent:
- [ ] Same input -> same output (deterministic)
- [ ] Multiple rapid changes -> no race conditions
- [ ] State always consistent between UI display and renderer behavior
- [ ] No stale closures capturing old state values
