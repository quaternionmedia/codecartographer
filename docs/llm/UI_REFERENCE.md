# UI Reference Guide

Reference for CodeCartographer's control panel and user interface.

---

## Control Panel Overview

The control panel is a collapsible sidebar with five tabs:

| Tab | Purpose |
|-----|---------|
| Source | Load data (Demo, Upload, GitHub URL) |
| Parse | Configure parser mode and file extensions |
| Layout | Select renderer, layout algorithm, physics |
| Visual | Styling options (nodes, edges, labels) |
| Theme | Color themes |

### Resize Behavior

- The panel height slider updates the plot area height.
- Graph renderers observe container size changes and resize the canvas/iframe accordingly.

---

## Source Tab

### Quick Start
- **Load Demo**: Loads CodeCartographer's own source as a sample graph

### Upload Mode
- Drag & drop Python files
- Click to browse and select files
- Plot individual files or all uploads

### Repository Mode
- Enter GitHub repository URL
- Fetch repository structure
- Navigate file tree
- Plot whole repo or individual files

---

## Parse Tab

### Parser Modes

| Mode | Description |
|------|-------------|
| AST (Code Structure) | Full Python abstract syntax tree analysis |
| Directory Tree | Filesystem hierarchy |
| Dependencies | Import relationships |

### File Extensions
Configure which file extensions to parse (default: `.py`).

### Behavior
- Changing parser mode triggers re-fetch if data is loaded
- Shows status message if no data is loaded yet

---

## Layout Tab

### Renderer Selection

| Renderer | Description |
|----------|-------------|
| D3.js (Force-directed) | Interactive physics simulation |
| Gravis (vis-network) | Alternative physics engine |
| Notebook (Static HTML) | Pre-rendered visualizations |

### Layout Algorithms

| Layout | Description |
|--------|-------------|
| Spring | Force-directed (default) |
| Spectral | Eigenvector-based positioning |
| Kamada-Kawai | Energy minimization |
| Circular | Nodes in a circle |
| Spiral | Nodes in a spiral |
| Random | Random positions |
| Shell | Concentric circles |
| Sorted Square | Grid arrangement |

### Physics Controls
- **Enable Physics**: Toggle force simulation
- **Repulsion Force**: How strongly nodes repel (negative values)
- **Link Distance**: Target distance between connected nodes

---

## Visual Tab

### Node Options
| Option | Range | Description |
|--------|-------|-------------|
| Node Size | 1-30 | Base radius in pixels |
| Node Opacity | 0.1-1.0 | Fill transparency |
| Border Width | 0-5 | Stroke width |
| Color Override | color | Override automatic colors |

### Edge Options
| Option | Range | Description |
|--------|-------|-------------|
| Edge Width | 0.5-5 | Line thickness |
| Edge Opacity | 0.1-1.0 | Line transparency |
| Edge Color | color | Line color |
| Edge Style | solid/dashed/dotted | Line style |

### Label Options
| Option | Description |
|--------|-------------|
| Show Node Labels | Toggle node label visibility |
| Show Edge Labels | Toggle edge label visibility |
| Label Size | Font size in pixels |
| Label Color | Text color |

### Canvas Options
| Option | Description |
|--------|-------------|
| Background | Graph canvas background color |

---

## Theme Tab

Available themes:
- Terminal (default green)
- Forest (nature green)
- Cyberpunk (neon)
- Ocean (blue)
- Sunset (warm)
- Light (bright)
- Noir (dark)
- Candy (colorful)

Themes affect the overall UI colors and default graph styling.

---

## Keyboard Shortcuts

### Graph Interaction
| Key | Action |
|-----|--------|
| Scroll | Zoom in/out |
| Drag background | Pan |
| Drag node | Move node |
| Click node | Select |
| Ctrl+Click | Multi-select |
| Right-click | Radial menu |

### Control Panel
| Key | Action |
|-----|--------|
| Enter (in URL field) | Submit URL |

---

## Status Messages

The control panel displays status feedback:

| Message | Meaning |
|---------|---------|
| Ready | No operation in progress |
| Loading demo... | Fetching demo data |
| Fetching repository... | Loading GitHub repo |
| Applying X parser... | Re-parsing with new mode |
| Parser: X. Load source to apply. | Parser changed but no data |
| Renderer: X. Load source to apply. | Renderer changed but no data |
| Error... | Operation failed |

---

## Graph Interaction

### Radial Menu
Right-click on graph to open radial menu with options:
- Zoom controls (fit, reset, in, out)
- Selection (select all, clear)
- Layout refresh
- Export options

### Node Dragging
- Drag nodes to reposition
- Node stays pinned after drag
- Edges update in real-time

### Selection
- Click to select single node
- Ctrl/Cmd+Click for multi-select
- Selected nodes show highlight

### Tooltips
Hover over nodes to see:
- Node label/ID
- Node type
- Connection count

---

## Callbacks Flow

```
User Action → Control Panel Callback → State Update → Re-render

Examples:
- onDemo() → loadDemo() → handlePlotData() → createGraphVnode()
- onParserOptionsChange() → update state → lastPlotAction() if data exists
- onRendererChange() → update state → createGraphVnode() if data exists
- onGraphStylingChange() → update state → createGraphVnode() or re-fetch
```

---

## State Flow

```
User changes setting
    ↓
updatePanelState() - local component state for UI
    ↓
cellState.update() - global Meiosis state
    ↓
m.redraw() - Mithril re-renders
    ↓
Graph updates based on new state
```

---

## Common Workflows

### View Demo
1. Click "Load Demo" in Source tab
2. Graph appears with default settings
3. Adjust styling in Visual tab
4. Change theme in Theme tab

### Parse GitHub Repository
1. Enter GitHub URL in Source tab
2. Click "Fetch"
3. Navigate file tree
4. Click "Plot" on whole repo or specific files

### Change Parser Mode
1. Load some data first (demo or upload)
2. Go to Parse tab
3. Select different parser mode
4. Graph re-renders with new structure

### Switch Renderers
1. Load graph data
2. Go to Layout tab
3. Select different renderer
4. Graph re-renders with new engine
