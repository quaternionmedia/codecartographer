# UI Reference Guide

Reference for CodeCartographer's control panel and user interface.

---

## Application Shell — Golden Layout

The app uses **Golden Layout 2.x** as its primary shell. All panels are dock tabs that can be freely resized, rearranged, and popped in/out.

| Panel | Default position | Purpose |
|-------|-----------------|---------|
| Graph | Main area (top) | D3 graph canvas |
| Source / Info | Bottom dock tab | File tree, repo info |
| Actions | Bottom dock tab | Plot/re-plot controls |

When a panel tab is closed, a **Restore** button appears in the header so it can be re-opened without a page reload. Panels are independently resizable — drag the divider between dock areas.

---

## Control Panel

The control panel is a collapsible sidebar with **two tabs**:

| Tab | Purpose |
|-----|---------|
| Source | Load data — demo, GitHub repo, cached graphs |
| Graph | Graph settings — layout, physics, styling, compound groups |

---

## Source Tab

### Demo
- **Load Demo** — streams CodeCartographer's own source as a sample graph via `/parse/stream`.

### Repository Mode
1. Paste a GitHub URL and press Enter or click **Fetch**.
2. The file tree populates. Click folders to expand, files to plot a single file.
3. **Plot** — streams the whole repo graph.
4. **Clear** — resets back to the URL input screen.

### Recent Graphs (cache panel)
Shown when no repo is loaded. Lists previously parsed graphs from the filesystem cache (`~/.codecarto/cache/`). Clicking an entry replays it instantly (cache hit — no re-parse). The ✕ button evicts a single entry.

---

## Graph Tab

### Layout Algorithm

| Value | Description |
|-------|-------------|
| `spring_layout` | Force-directed (default) |
| `compound_layout` | **Hierarchical**: dirs → files → symbols in nested orbits |
| `circular_layout` | Nodes on a circle |
| `kamada_kawai_layout` | Energy-minimization spring |
| `spectral_layout` | Graph Laplacian eigenvectors |

### Physics Controls
- **Enable Physics** — toggle force simulation (spring_layout only)
- **Repulsion Force** — how strongly nodes repel (chargeStrength, negative values)
- **Link Distance** — target edge length in px

### Node Appearance
| Option | Description |
|--------|-------------|
| Node Size | Base radius in px |
| Node Opacity | 0.0–1.0 fill transparency |
| Border Width | Stroke width in px |

### Edge Appearance
| Option | Description |
|--------|-------------|
| Edge Width | Line thickness in px |
| Edge Opacity | 0.0–1.0 |

### Label Appearance
| Option | Description |
|--------|-------------|
| Show Node Labels | Toggle label visibility |
| Label Size | Font size in px |
| Label Color | Hex color |

### Group Outlines (Compound Layout)
**Group Outlines** toggle — shows translucent SVG bounding circles per directory/file group (most meaningful with `compound_layout`):
- **Grey dashed** circles = directory clusters (depth 0)
- **Purple dashed** circles = file clusters (depth 1)

---

## Streaming Graph Renderer

The default renderer is `StreamingGraphRenderer` — nodes and edges arrive progressively over an SSE stream and are added to the canvas in real time.

- **Loading overlay** — shown until the first `meta` event arrives.
- **Progress bar + status** — "Streaming N/M nodes" with a cancel ✕ button.
- **Pop-in animation** — each node fades/scales in as it arrives (rAF drain loop).
- **Batch pacing** — `setTotal(n)` tunes how many nodes render per frame (small repos: 1/frame; large repos: up to `ceil(N/100)` per frame).
- **Fit view** — after the stream completes, the viewport auto-fits to contain all nodes.
- **Drag** — nodes can be dragged to reposition; edges follow in real time.

---

## Radial Context Menu

Right-click anywhere on the graph canvas to open the radial menu.

### Node Menu (right-click a node)
| Item | Action |
|------|--------|
| Expand | Load depth-2 symbols for a file node |
| Collapse | Remove child nodes |
| Neighbors | Highlight direct connections |
| Pin | Lock node position |
| Style | Open per-node style override |
| Hide | Remove node from view |
| Delete | Remove node + its edges |
| Info | Show node metadata panel |
| **Focus Group** | Zoom/pan to the bounding circle of this node's cluster (depth 0 and 1 only) |

### Canvas Menu (right-click empty space)
| Submenu / Item | Action |
|----------------|--------|
| **Zoom** | Fit to screen, reset zoom, zoom in/out |
| **Select** | Select all nodes, clear selection |
| **Layout → Spring** | Apply spring_layout |
| **Layout → Compound** | Apply compound_layout |
| **Layout → Circular** | Apply circular_layout |
| **Layout → Kamada-Kawai** | Apply kamada_kawai_layout |
| **Layout → Spectral** | Apply spectral_layout |
| **Organize → Apply Layout** | Re-run the currently selected layout |

---

## Help Modal

- Click the **`?`** button (header) to open a 3-step walkthrough.
- Auto-shows on first visit (dismissed state stored in `localStorage: cc:help-dismissed`).
- `HelpModal.open()` / `HelpModal.close()` API.

---

## Themes

Available themes (top-right dropdown):
- Terminal · Forest · Cyberpunk · Ocean · Sunset · Light · Noir · Candy

Themes drive CSS custom properties (`--c-primary`, `--c-secondary`, `--c-accent`, etc.) consumed by both the UI and the graph renderer's default color palette.

---

## Keyboard Shortcuts

| Key / Action | Effect |
|-------------|--------|
| Scroll | Zoom in/out on graph canvas |
| Drag background | Pan |
| Drag node | Reposition node; edges follow |
| Right-click | Open radial menu |
| Enter (URL field) | Submit GitHub URL |

---

## State Flow

```
User action (click, input, toggle)
    ↓
Control Panel callback (onDemo, onGraphStylingChange, onPlotWholeRepo, …)
    ↓
cell_state.update() — Meiosis patch
    ↓
m.redraw() — Mithril re-renders control panel
    ↓
PlotActions / StreamingGraphRenderer — graph updates
```

---

## Common Workflows

### View Demo
1. Open control panel → Source tab → **Load Demo**.
2. Graph streams in progressively.
3. Adjust settings in the Graph tab.

### Parse a GitHub Repo
1. Source tab → paste GitHub URL → **Fetch**.
2. File tree loads. Expand folders, click a file to plot it, or **Plot** for the whole repo.
3. Graph streams in. Use radial menu → Layout → Compound for hierarchical view.

### Use Compound Layout
1. Graph tab → Layout → **Compound**.
2. Plot (or re-plot). Dirs appear as large clusters, files orbit dirs, symbols orbit files.
3. Toggle **Group Outlines** to show/hide bounding circles.
4. Right-click a dir/file node → **Focus Group** to zoom to that cluster.

### Re-open a Closed Panel
1. Close any dock tab (×).
2. Click the **Restore** button that appears in the header.
