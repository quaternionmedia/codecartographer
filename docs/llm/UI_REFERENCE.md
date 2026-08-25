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

**There is one, and every graph gets it.** rad is mounted against the canvas
rather than inside a renderer, so it reaches whatever drew the graph — Load
Demo, plot repo, plot file, cache recall, bookmark replay, a lexicon. Source is
`web/src/features/graph/rad/`; see
[`RAD_INTEGRATION_HANDOFF.md`](RAD_INTEGRATION_HANDOFF.md) for the contract it
conforms to.

Press-and-hold, right-click, or press the menu key on a focused canvas. Flick
toward a wedge to commit; release in the dead zone to cancel. Every item is
reachable by keyboard — arrow keys and Enter — and every verb also has a chord.

| Ring | Items |
|---|---|
| **Node** | Expand · Collapse · Neighbours · Pin · Colour ▸ · View ▸ · Hide · Delete |
| **Canvas** | Fit · Relayout · Spread\* · Cluster\* · Physics\* · Unhide · Deselect · Colour ▸ |
| **Selection** | Expand · Neighbours · Spread\* · Cluster\* · Colour ▸ · Hide · Deselect · Delete *n* |
| **Edge** | Endpoints · Hide · Info |

\* Shown but **disabled**: node positions come from the backend layout and
there is no force simulation to toggle. They keep their wedges so the other
items do not shift position between states. **A capability the host lacks is
offered disabled, never substituted** — three verbs once shared one `fitView()`
call while every test stayed green, which is the rule's whole origin.

`Expand` holds the 12 o'clock wedge — the one a straight-up flick reaches —
and calls `POST /parse/expand`, merging the returned subgraph into the live
scene. Hide, Pin and Colour are held as application state, so they survive a
re-render, a relayout and a cache replay.

---

## Graph Legend

A key in the bottom-left of the canvas, collapsed by default. Its header states
the totals; opening it lists the node kinds and edge kinds actually present,
with a swatch drawn by the same function the canvas draws nodes with, and a
count per row.

**It reads the graph rather than describing it.** There are no fixed rows: a
kind absent from the picture has no row, and every node is accounted for by
exactly one row. What each row means is decided in
`web/src/features/graph/extensions/legend_marks.ts`, which is pure and covered
by `npm run test:pure`.

Like rad, it is a `BaseExtension` mounted against the canvas, so it appears on
every path that draws a graph.

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
| Press-and-hold | Open radial menu (same, pointer-agnostic) |
| Menu key / Shift+F10 | Open radial menu at canvas centre — no pointer required |
| Arrow keys, Enter | Move the radial selection, commit it |
| Escape | Cancel the radial menu without committing |
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
