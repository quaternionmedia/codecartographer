# Control Panel Quick Reference

## Tab Organization at a Glance

```
┌──────────────────────────────────────────────────────────────────┐
│ Control Panel Tabs (Left to Right Tutorial Flow)                │
├──────────────────────────────────────────────────────────────────┤
│ 1. Source 📁  │ 2. Parse 🔍  │ 3. Layout ◈  │ 4. Visual ✦  │ 5. Theme 🎨 │
│               │               │              │              │             │
│ Quick Start   │ Parser Mode   │ RENDERER     │ Node Style   │ Themes      │
│ ⚡🌊🔮        │ AST/Dir/Deps  │ D3/Gravis/NB │ Size/Opacity │ 8 presets   │
│               │               │              │              │             │
│ Status + Plot │ Extensions    │ Algorithm    │ Edge Style   │ About       │
│ ● Ready [▶]  │ .py, .js...   │ Spring/etc   │ Width/Labels │             │
│               │               │              │              │             │
│ Upload/Repo   │               │ Physics      │ Label Style  │             │
│ Files/URL     │               │ Force/Dist   │ Size/Color   │             │
└──────────────────────────────────────────────────────────────────┘
```

## Decision Tree

```
START
  │
  ├─ Want instant demo?
  │    └─ YES → Source tab → Click preset (⚡/🌊/🔮) → DONE
  │
  ├─ Have local files?
  │    └─ YES → Source tab → Upload → Click [▶ Plot] → Customize
  │
  ├─ Have GitHub URL?
  │    └─ YES → Source tab → Repository → Enter URL → Fetch → Plot
  │
  └─ Want to customize?
       │
       ├─ Step 1: Source → Choose data source
       ├─ Step 2: Parse → Pick parser mode
       ├─ Step 3: Layout → Select renderer + algorithm
       ├─ Step 4: Visual → Style appearance
       └─ Step 5: Theme → Set colors
```

## Context-Specific Options

### Layout Tab Options by Renderer

| Selected Renderer | Shows Algorithm? | Shows Physics? | Shows Sliders? |
|-------------------|------------------|----------------|----------------|
| D3.js             | ✅ Yes           | ✅ Yes         | ✅ If enabled  |
| Gravis            | ✅ Yes           | ✅ Yes         | ✅ If enabled  |
| Notebook          | ❌ **HIDDEN**    | ❌ **HIDDEN**  | ❌ **HIDDEN**  |

**Reason**: Notebook renderer displays pre-rendered HTML, so layout/physics don't apply.

## Quick Start Presets

| Button | Icon | Parser | Layout | Renderer | Theme | Physics |
|--------|------|--------|--------|----------|-------|---------|
| Demo 1 | ⚡   | AST    | Spring | D3       | Terminal | ON |
| Demo 2 | 🌊   | Directory | Spectral | Gravis | Ocean | OFF |
| Demo 3 | 🔮   | Dependencies | Kamada-Kawai | Notebook | Cyberpunk | N/A |

## Default Values

```typescript
const DEFAULTS = {
  // Source
  mode: 'upload',

  // Parse
  parserMode: 'ast',
  fileExtensions: [],

  // Layout
  renderer: 'd3',
  layout: 'spring_layout',
  enablePhysics: true,
  chargeStrength: -50,
  linkDistance: 100,

  // Visual
  nodeSize: 6,
  nodeOpacity: 0.8,
  nodeBorderWidth: 2,
  showNodeLabels: true,
  edgeWidth: 1.5,
  edgeOpacity: 0.7,
  showEdgeLabels: false,
  labelSize: 11,
  labelColor: '#00ff41',

  // Theme
  theme: 'terminal'
}
```

## Common Workflows

### Workflow 1: Quick Demo
1. Click **⚡ Demo (AST + D3)**
2. Done!

**Time**: < 1 second
**Clicks**: 1

---

### Workflow 2: Upload and Plot
1. Source tab → Upload mode
2. Drop/browse .py files
3. Click **[▶ Plot]** button
4. (Optional) Adjust theme

**Time**: ~5 seconds
**Clicks**: 2-3

---

### Workflow 3: GitHub Repository Analysis
1. Source tab → Repository mode
2. Enter GitHub URL
3. Click **Fetch**
4. Click **Directory Tree** or **Dependencies**
5. (Optional) Parse tab → Change parser mode
6. (Optional) Layout tab → Change renderer
7. (Optional) Visual tab → Adjust styling

**Time**: ~15-30 seconds
**Clicks**: 4-8

---

### Workflow 4: Full Customization
1. Source tab → Choose preset as starting point
2. Parse tab → Change parser mode
3. Layout tab → Change renderer, algorithm, physics
4. Visual tab → Adjust all visual properties
5. Theme tab → Select theme

**Time**: ~1-2 minutes
**Clicks**: 10-20

## Keyboard Shortcuts (Future)

```
Planned shortcuts:
- Ctrl+1 to Ctrl+5: Switch to tab 1-5
- Space: Plot (when files ready)
- D: Demo preset 1
- G: Demo preset 2
- N: Demo preset 3
- T: Cycle themes
```

## File Structure

```
web/src/components/codecarto/control_panel/
├── control_panel.ts          # Main component logic
├── control_panel.css          # All styles
└── README.md                  # (Create) Usage guide

Related files:
├── state/types.ts             # State interfaces
├── state/actions.ts           # Plot actions
└── codecarto.ts               # Parent component
```

## CSS Classes Reference

### Source Tab
```css
.panel-source__quickstart       /* Quick start section container */
.panel-source__status           /* Status bar with file count + plot button */
.panel-source__plot-btn         /* Dynamic plot button (appears when ready) */
.panel-source__mode-toggle      /* Upload/Repository toggle */
.panel-source__upload           /* Upload mode content */
.panel-source__repo             /* Repository mode content */
```

### Parse Tab
```css
.panel-settings__button-group   /* Horizontal button group */
.panel-settings__button-option  /* Individual parser mode button */
.panel-settings__input-compact  /* File extensions input */
```

### Layout Tab
```css
.panel-settings__select         /* Renderer + Algorithm dropdowns */
.panel-settings__toggle-compact /* Physics toggle */
.panel-settings__slider-group   /* Slider with label and value */
```

### Visual Tab
```css
.panel-visual__2col             /* 2-column grid container */
.panel-visual__column           /* Left/right column */
.panel-settings__color          /* Color picker */
```

### Theme Tab
```css
.panel-settings__options        /* Theme button grid */
.panel-settings__option         /* Individual theme button */
```

### Global
```css
.panel-settings__label-compact  /* All compact labels (0.75em) */
.panel-settings__group          /* Settings group container */
.panel-section                  /* Tab content wrapper */
.panel-section--active          /* Active tab (visible) */
```

## Conditional Rendering Patterns

### Pattern 1: Show if condition
```typescript
condition ? element : null
```

Example:
```typescript
state.selectedRenderer !== 'notebook'
  ? m('select.algorithm', ...)
  : null
```

### Pattern 2: Multiple conditions (AND)
```typescript
condition1 && condition2 ? element : null
```

Example:
```typescript
state.selectedRenderer !== 'notebook' && styling.enablePhysics
  ? m('slider.repulsion', ...)
  : null
```

### Pattern 3: Multiple conditions (OR)
```typescript
condition1 || condition2 ? element : null
```

Example:
```typescript
hasRepo || hasUploads
  ? m('button.plot', ...)
  : null
```

## State Updates

### Single setting
```typescript
callbacks.onRendererChange('d3')
```

### Multiple settings
```typescript
callbacks.onGraphStylingChange({
  layout: 'spring_layout',
  enablePhysics: true,
  chargeStrength: -100
})
```

### Preset configuration
```typescript
// Update multiple systems at once
callbacks.onDemo();                          // Load data
callbacks.onParserOptionsChange({ ... });    // Configure parser
callbacks.onGraphStylingChange({ ... });     // Configure layout
callbacks.onRendererChange('d3');            // Set renderer
callbacks.onThemeChange('terminal');         // Set theme
```

## Troubleshooting

### Plot button doesn't appear
✓ Check that files are loaded (`loadedFileCount > 0`)
✓ Verify status indicator is green

### Algorithm dropdown missing
✓ Check if Notebook renderer is selected
✓ Notebook hides algorithm (it's pre-rendered)

### Physics sliders hidden
✓ Check if Notebook renderer is selected
✓ Check if physics toggle is OFF
✓ Both conditions hide sliders

### Preset doesn't work
✓ Ensure all callbacks are wired up in codecarto.ts
✓ Check browser console for errors
✓ Verify state updates are triggering re-render

## Performance Tips

### Minimize re-renders
- Only update changed values
- Use `oninput` for live updates (sliders)
- Use `onchange` for discrete updates (selects, inputs)

### Reduce bundle size
- Import only needed components
- Use tree-shaking (already enabled via Vite)
- Consider code-splitting for large libraries

### Optimize rendering
- Use keys for list items
- Memoize expensive computations
- Batch state updates when possible

## Accessibility

### Current
- ✅ Keyboard navigable (tab order)
- ✅ Semantic HTML (labels, buttons, inputs)
- ✅ Color contrast (terminal theme)

### Future improvements
- ⏳ ARIA labels for controls
- ⏳ Screen reader announcements
- ⏳ Focus indicators
- ⏳ Keyboard shortcuts
- ⏳ High contrast mode

## Browser Compatibility

Tested on:
- ✅ Chrome 120+
- ✅ Firefox 121+
- ✅ Edge 120+
- ✅ Safari 17+ (macOS)

Known issues:
- None currently

## Change Log

### v1.0 - Initial tutorial flow
- Numbered tabs (1-5)
- Help text for each tab
- Progressive disclosure (required/optional)

### v2.0 - Compact refactor
- Horizontal button groups
- 2-column Visual tab grid
- Smaller sliders, toggles, labels
- 50% more compact overall

### v3.0 - Context-aware layout (CURRENT)
- Renderer moved to Layout tab
- Context-specific options (hide for notebook)
- Quick Start presets (3 demos)
- Dynamic Plot button
- Integrated tutorial philosophy

## Related Documentation

- [TUTORIAL_FLOW.md](./TUTORIAL_FLOW.md) - Original tutorial concept
- [CONTROL_PANEL_REFACTOR.md](./CONTROL_PANEL_REFACTOR.md) - Compact refactor details
- [FINAL_CONTROL_PANEL_ORGANIZATION.md](./FINAL_CONTROL_PANEL_ORGANIZATION.md) - Complete reference
- [RENDERER_SYSTEM.md](./RENDERER_SYSTEM.md) - Renderer architecture
- [RENDERER_ROUTING.md](./RENDERER_ROUTING.md) - Renderer selection logic
