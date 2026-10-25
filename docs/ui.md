# UI Reference Guide

Reference for CodeCartographer's shell, panels, canvas and menus. Where this page and the tree disagree, the tree is right and this page is repaired.

---

## Application Shell — Golden Layout

The app uses **Golden Layout 2.x** as its primary shell. Every panel is a
dockable tab that can be resized, rearranged, closed and re-opened. The list of
panels is `web/src/layout/panel_registry.ts`, and that file is the authority;
this table is a reading of it.

| Panel (menu label) | Registry id | What it is |
|---|---|---|
| Graph | `graph` | The one canvas. Every graph in the application draws here — code maps, lexicons, the estate views — through `StreamingGraphRenderer` |
| Files | `file-tree` | Repository and upload file browser |
| Upload | `upload-panel` | Local file dropzone, plus the source controls (Load Demo lives here) |
| Repository | `repo-panel` | GitHub URL or local path fetch, recent graphs, and the project selector: examples by language, Rust first. A bundled example (`examples/`, from `GET /repo/examples`) leads its group with a filled chip: it is read from this checkout with its recorded documents, so it needs no network, and a Cargo workspace's records are loaded into the Cargo panel as it opens. The GitHub examples draw the code map only -- a fetched repository brings no records of a build |
| Graphbase | `graphbase-panel` | Durable named bookmarks (needs `MONGODB_URI`) |
| Graph Settings | `graph-settings-panel` | Layout, physics, styling controls |
| Actions | `plotbar` | Plot, cancel, status |
| Estate | `estate-panel` | Every seam this window reads, live or not, with the way to the panel that draws it. In the default dock |
| Topology | `topology-panel` | Choose one of the harness's flows, or ask what the archive says about a project; the drawing goes to the canvas |
| Capabilities | `capabilities-panel` | The corpus's capability registry: each declaration and the rung it claims; draw them |
| Overview | `overview-panel` | dossier's reading of the estate: masthead figures and sections; draw them |
| Cargo | `cargo-panel` | A Rust workspace by path (the field follows the workspace shown, so a bundled example's click fills it): which engine read it, its crates, the recorded documents and whether each is current, the device target; draw the crate graph, with features or locked dependencies if asked |
| Chrestomathy | `chrestomathy-panel` | **On the canvas:** whatever graph is drawn -- a code map, a crate graph, a linker script -- read as the constructs its nodes are, in which languages, with what the vocabulary could not place, each said as what it is (a file the walk drew, a kind that is no construct and why); a row opens that construct below, and *show* frames and selects its nodes. Read again whenever a new graph is drawn, and never kept for one that has gone: a construct drawn from the vocabulary is not code and has no census. **Construct:** one construct set beside itself in each of C, Rust, Python, assembly and the linker script, every language `constructs.yaml` lists: each language's tokens with their abstraction layer, its parser kinds, and its note -- a language with no spelling is a row with its note, or one saying the vocabulary records none; draw it |

**Default layout** (`default_layout.ts`): Graph on top; below it Files on the
left and a tab stack of Upload (active), Repository, Graph Settings, Actions and
Estate. Topology, Capabilities, Overview, Cargo and Chrestomathy are opened
from the **`+`** menu in the header — or from a live row in the Estate panel — because each asks its seam
on open, and a fresh workstation has none up.

**Adding, restoring, saving.** The `+` button (and Ctrl+right-click on the dock) opens
the add-window menu listing every registered panel not currently open; closing a
tab and re-adding it goes through the same path. The menu's Layout section saves
the current arrangement as the default (`localStorage['cc:gl-layout:default']`)
and resets it.

### The estate panels share three pieces

`web/src/features/estate/`: **`seam_client.ts`** tells the four things a seam can answer
apart — this window's own API down, the seam unreachable, the seam present and
unreadable, a document — and is pure, tested under `npm run test:pure`;
**`problem_view.ts`** is the one way any panel says "nothing was drawn" (what,
remedy, where it tried, try again); **`provenance.ts`** renders the caveat and
source a seam put in its graph's metadata, above the controls, and only when the
canvas holds *that* seam's graph. A panel's problem view wears the panel's class
prefix (`.topology__problem`, `.capabilities__problem`, …) so its stylesheet and
its browser tests apply.

---

## Control Panel

The source and settings controls (`components/codecarto/control_panel/`) are
the bodies of three panels, one mode each (`ControlPanelMode`):

| Panel | Mode | Purpose |
|-------|------|---------|
| Upload | `upload` | Add local files; the parser options; Quick Start (Load Demo, a lexicon) |
| Repository | `repo` | Fetch a repository, recent graphs, the project selector; the same parser options and Quick Start |
| Graph Settings | `graph` | Layout, physics, styling, theme |

---

## Upload and Repository Panels

### Demo
- **Load Demo** (Quick Start, in either panel) — streams CodeCartographer's own source as a sample graph via `/parse/stream`.

### Repository
1. Paste a GitHub URL and press Enter or click **→ Fetch**.
2. The Files panel shows the tree. Click folders to expand, files to plot a single file.
3. **Plot** in the Actions panel, or **◈ Plot All** in the Files panel — streams the whole repo graph.
4. **✕** beside the repository's name — clears it, back to the URL field.

### Recent Graphs
Shown in the Repository panel when no repo is loaded. Lists previously parsed graphs from the filesystem cache (`~/.codecarto/cache/`). Clicking an entry replays it instantly (cache hit — no re-parse). The ✕ button evicts a single entry.

---

## Graph Settings Panel

### Layout Algorithm

Applies to whatever graph is on the canvas — a code map or an estate graph
(topology, capabilities, overview). Changing it re-draws the last thing drawn
with the new layout; the menu's names are the backend registry's, translated by
one rule in `web/src/features/graph/services/layout_names.ts`.

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
[rad's host-integration standard](https://github.com/quaternionmedia/rad/blob/main/adr/DRAFT-rad-host-integration-standard.md) for the contract it
conforms to.

Press-and-hold, right-click, or press the menu key on a focused canvas. Flick
toward a wedge to commit; release in the dead zone to cancel. Every item is
reachable by keyboard — arrow keys and Enter — and every verb also has a chord.

| Ring | Items |
|---|---|
| **Node** | Expand · Collapse · Neighbours · Pin · Color ▸ · View ▸ · Hide · Delete |
| **Canvas** | Fit · Relayout · Spread\* · Cluster\* · Physics\* · Unhide · Deselect · Color ▸ |
| **Selection** | Expand · Neighbours · Spread\* · Cluster\* · Color ▸ · Hide · Deselect · Delete *n* |
| **Edge** | Endpoints · Hide · Info |

**View ▸** holds Source · Info · Compare · Focus. *Compare* opens the
Chrestomathy panel at what the node *is* -- its construct, set beside every
language that writes it -- and is offered disabled on a node the vocabulary did
not place. *Info* says the node's name, its parser's kind, its construct and
facets, and where it is, every time it is used.

\* Shown but **disabled**: node positions come from the backend layout and
there is no force simulation to toggle. They keep their wedges so the other
items do not shift position between states. **A capability the host lacks is
offered disabled, never substituted** — three verbs once shared one `fitView()`
call while every test stayed green, which is the rule's whole origin.

`Expand` holds the 12 o'clock wedge — the one a straight-up flick reaches —
and calls `POST /parse/expand`, merging the returned subgraph into the live
scene. Hide, Pin and Color are held as application state, so they survive a
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

**It keys the colours on screen.** Under "Color By: Abstraction Layer" a row's
swatch takes the colour the canvas paints its nodes, and an *Abstraction layers*
section names each layer painted and counts its nodes — by language where the
graph holds more than one, since a layer's number is a rank within one
language's lexicon and the same number in two languages is two layers. Under
"Auto" a layer is named only where a node's own colour is its layer's, as the
chrestomathy's tokens are; a parsed node drawn in its own colour is no layer
row. "Color By: Construct" paints each node the vocabulary placed in its
construct's colour (`construct_color`), alike across languages, and a
*Constructs* section names each construct painted; under the other colourings
a construct is named only where a node's own colour is its construct's, so the
crate graph under "Auto" has no *Package* row in a colour nothing wears. The
canvas, the vis-network renderer and the key take the fill from one function,
`paintedColor`. A record (`ngon`) is a row per side count, and says it:
*Struct · 4 sides*.

Like rad, it is a `BaseExtension` mounted against the canvas, so it appears on
every path that draws a graph.

---

## Help Modal

- Click the **`?`** button (header) to open a 4-step walkthrough.
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
1. Upload or Repository panel → Quick Start → **Load Demo**.
2. Graph streams in progressively.
3. Adjust settings in the Graph Settings panel.

### Parse a GitHub Repo
1. Repository panel → paste GitHub URL → **→ Fetch**.
2. The Files panel shows the tree. Expand folders, click a file to plot it, or **Plot** for the whole repo.
3. Graph streams in. Graph Settings → Layout → **Compound** for a hierarchical view.

### Use Compound Layout
1. Graph Settings panel → Layout → **Compound**.
2. Plot (or re-plot). Dirs appear as large clusters, files orbit dirs, symbols orbit files.
3. Toggle **Group Outlines** to show/hide bounding circles.
4. Right-click a dir/file node → **View ▸ Focus** to zoom to that cluster.

### Re-open a Closed Panel
1. Close any dock tab (×).
2. Click **`+`** in the header and choose the panel from the list.

### See What Is Up
1. Click the **Estate** tab in the bottom dock.
2. Each seam is a row: identified (with what it said about itself) or down (with
   the command that would change that). **ask again** re-probes.
3. A live row's **open …** button opens the panel that draws that seam.
