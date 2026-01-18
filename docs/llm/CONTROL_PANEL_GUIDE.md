# Control Panel Guide

**Status**: Current (2026-01-18)
**Version**: 3.1 - Tutorial Flow with Theme-Based Demos

## Overview

The control panel is organized into 5 tabs that follow a tutorial flow from left to right:

```
1. Source 📁 → 2. Parse 🔍 → 3. Layout ◈ → 4. Visual ✦ → 5. Theme 🎨
```

Each tab represents a step in the visualization creation process.

---

## Tab 1: Source 📁

**Purpose**: Load data (files, repositories, or demos)

### Quick Start Demos

Three preset buttons load demo visualizations with different themes:

| Button | Icon | Theme | Description |
|--------|------|-------|-------------|
| Demo (Terminal) | ⚡ | Terminal | Green matrix-style theme |
| Demo (Ocean) | 🌊 | Ocean | Blue underwater theme |
| Demo (Cyberpunk) | 🔮 | Cyberpunk | Purple neon theme |

**Note**: All demos load the same pre-rendered visualization (Gravis HTML). They differ only in color theme.

### Status Indicator

Shows file readiness:
- **Gray dot**: No files loaded
- **Green dot**: Files ready to plot
- **Text**: File count or instructions

### Dynamic Plot Button

When files are loaded, a **[▶ Plot]** button appears that:
- Automatically detects source type (repo or uploads)
- Calls the appropriate plot method
- Provides clear call-to-action

### Upload Mode

- Drag and drop files
- Browse for files
- Shows uploaded file list
- Filters Python files

### Repository Mode

- Enter GitHub URL
- Fetch repository
- Select parsing method (Directory Tree or Dependencies)
- Shows repository info

---

## Tab 2: Parse 🔍

**Purpose**: Choose how to parse source code

### Parser Modes

Horizontal button group with 3 options:

| Icon | Mode | Description |
|------|------|-------------|
| 🔍 | AST | Parse Abstract Syntax Tree (code structure) |
| 📁 | Directory | Parse directory structure (file tree) |
| ◈ | Dependencies | Parse import dependencies |

**Active state**: Button highlights with secondary color and glow.

### File Extensions (Optional)

- Input field for comma-separated extensions
- Default: `.py, .js, .ts`
- Leave blank to parse all files

---

## Tab 3: Layout ◈

**Purpose**: Configure spatial arrangement and physics

### Renderer Selection

**Position**: First option at top of Layout tab

Dropdown with 3 options:
- **D3.js (Force-directed)**: Interactive D3 force simulation
- **Gravis (vis-network)**: Gravis physics engine
- **Notebook (Static HTML)**: Pre-rendered static HTML

**Context-Aware Behavior**: When Notebook is selected, layout options are hidden (pre-rendered HTML doesn't support dynamic layout).

### Algorithm (Conditional)

**Shows when**: Renderer ≠ Notebook

Dropdown with layout algorithms:
- Spring Layout
- Spectral Layout
- Kamada-Kawai Layout
- Circular Layout
- Spiral Layout
- Random Layout
- Shell Layout
- Sorted Square Layout

### Physics Simulation (Conditional)

**Shows when**: Renderer ≠ Notebook

**Toggle**: Enable/disable physics simulation

**Sliders** (only when physics enabled AND renderer ≠ Notebook):
- **Repulsion Force**: -500px to -10px (node separation)
- **Link Distance**: 10px to 300px (edge length)

---

## Tab 4: Visual ✦

**Purpose**: Style nodes, edges, and labels

### 2-Column Grid Layout

**Left Column: Node Settings**
- **Node Labels**: Toggle visibility
- **Node Size**: 2-30px
- **Node Opacity**: 10-100%
- **Border Width**: 0-8px

**Right Column: Edge & Label Settings**
- **Edge Labels**: Toggle visibility
- **Edge Width**: 0.5-10px
- **Edge Opacity**: 10-100%
- **Label Size**: 6-24px
- **Label Color**: Color picker

**Benefits**: 70% less vertical space than previous single-column layout.

---

## Tab 5: Theme 🎨

**Purpose**: Choose color scheme

### Theme Grid

8 theme options in 4×2 grid:

| Theme | Colors |
|-------|--------|
| Terminal | Green matrix |
| Cyberpunk | Purple neon |
| Ocean | Blue aquatic |
| Forest | Green nature |
| Sunset | Orange/pink |
| Monochrome | Grayscale |
| Solarized | Solarized palette |
| Dracula | Dark purple |

### About Section

Link to documentation and version info.

---

## Design Philosophy

### Tutorial Flow

Tabs are numbered 1-5 to guide users through the process:
1. **Load** data
2. **Parse** it
3. **Arrange** layout
4. **Style** appearance
5. **Theme** colors

### Progressive Disclosure

- Required options shown first
- Optional settings revealed as needed
- Context-specific options (hide irrelevant controls)

### Compact Design

- Horizontal button groups (not vertical stacks)
- 2-column grids (more screen space)
- Smaller labels, sliders, toggles
- Minimal spacing

### Context-Aware UI

Options change based on selections:
- **Notebook renderer**: Hides layout and physics (pre-rendered)
- **Physics disabled**: Hides force sliders
- **Files loaded**: Shows plot button

---

## Common Workflows

### Workflow 1: Quick Demo
1. Click **⚡ Demo (Terminal)**
2. Done!

**Time**: < 1 second
**Clicks**: 1

---

### Workflow 2: Upload and Plot
1. Source tab → Drop files
2. Click **[▶ Plot]** button
3. (Optional) Adjust theme

**Time**: ~5 seconds
**Clicks**: 2-3

---

### Workflow 3: GitHub Analysis
1. Source tab → Repository mode
2. Enter GitHub URL
3. Click **Fetch**
4. Click **Directory Tree** or **Dependencies**
5. (Optional) Customize in other tabs

**Time**: ~15-30 seconds
**Clicks**: 4-8

---

### Workflow 4: Full Customization
1. Source tab → Load demo/files
2. Parse tab → Choose parser mode
3. Layout tab → Select renderer, algorithm, physics
4. Visual tab → Adjust styling
5. Theme tab → Choose theme

**Time**: ~1-2 minutes
**Clicks**: 10-20

---

## Technical Implementation

### File Structure

```
web/src/components/codecarto/control_panel/
├── control_panel.ts          # Main component
└── control_panel.css          # All styles
```

### Key CSS Classes

#### Compact Elements
```css
.panel-settings__label-compact       /* Small uppercase labels */
.panel-settings__button-option       /* Horizontal button group items */
.panel-settings__input-compact       /* Smaller input fields */
.panel-settings__toggle-compact      /* Smaller toggle switches */
```

#### Layout
```css
.panel-settings__button-group        /* Horizontal button container */
.panel-visual__2col                  /* 2-column grid for Visual tab */
.panel-source__quickstart            /* Quick start demo section */
```

#### Dynamic Elements
```css
.panel-source__plot-btn              /* Dynamic plot button */
.panel-source__status-indicator      /* Status dot (gray/green) */
.panel-settings__button-option--active  /* Active button state */
```

### Conditional Rendering Pattern

```typescript
// Hide element when condition is false
condition ? element : null

// Example: Hide algorithm for notebook renderer
state.selectedRenderer !== 'notebook'
  ? m('select.algorithm', ...)
  : null
```

### State Management

All state is managed in `StateController`:
- `parserOptions`: Parser mode and extensions
- `graphStyling`: Layout, physics, visual settings
- `selectedRenderer`: D3, Gravis, or Notebook
- `currentTheme`: Selected color theme

Callbacks update state and trigger re-renders:
```typescript
callbacks.onParserOptionsChange({ mode: 'ast' });
callbacks.onGraphStylingChange({ layout: 'spring_layout' });
callbacks.onRendererChange('d3');
callbacks.onThemeChange('terminal');
```

---

## Known Limitations

### Demo Presets

**Current**: All three demo buttons load the same pre-rendered Gravis HTML, differing only in theme.

**Future**: Generate different demo data for each renderer type:
- D3 demo: Interactive force-directed graph
- Gravis demo: vis-network physics
- Notebook demo: Static HTML

**Workaround**: Use real repository data to test different renderers.

### Notebook Renderer

**Limitation**: Pre-rendered HTML cannot be re-styled or re-arranged client-side.

**Impact**: Layout and physics options are hidden when Notebook is selected.

**Solution**: Use D3 or Gravis renderers for interactive, customizable visualizations.

---

## Migration History

### v3.1 - Theme-Based Demos (2026-01-18)
- Simplified demo buttons to reflect theme-only differences
- Removed misleading renderer/parser options from demo presets
- All demos now accurately labeled as theme variants

### v3.0 - Context-Aware Layout
- Moved renderer from Visual to Layout tab
- Added context-specific option hiding
- Added quick start presets
- Added dynamic plot button

### v2.0 - Compact Refactor
- Horizontal button groups
- 2-column Visual tab grid
- Smaller sliders, toggles, labels
- 50% more compact overall

### v1.0 - Initial Tutorial Flow
- Numbered tabs (1-5)
- Help text for each tab
- Progressive disclosure

---

## Related Documentation

- `RENDERER_SYSTEM.md` - Renderer architecture
- `RENDERER_ROUTING.md` - Renderer selection logic
- `ADDING_NEW_RENDERER.md` - How to add renderers
- `PARSER_UI_INTEGRATION.md` - Parser integration

---

## Future Enhancements

### Priority 1: GraphData Format Demos
Generate structured JSON demos that can be rendered with any client-side renderer:
```json
{
  "graph": {
    "nodes": [...],
    "edges": [...]
  },
  "metadata": {
    "type": "d3",
    "layout": "spring_layout"
  }
}
```

### Priority 2: Keyboard Shortcuts
```
Ctrl+1 to Ctrl+5: Switch tabs
Space: Plot (when ready)
T: Cycle themes
```

### Priority 3: Preset Management
- Save custom presets
- Export/import configurations
- Share preset URLs

### Priority 4: Responsive Design
- Mobile-friendly layouts
- Touch-friendly controls
- Adaptive grid columns

---

## Browser Compatibility

**Tested on:**
- ✅ Chrome 120+
- ✅ Firefox 121+
- ✅ Edge 120+
- ✅ Safari 17+ (macOS)

**Known issues:** None currently
