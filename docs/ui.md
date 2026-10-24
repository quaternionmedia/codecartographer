# UI reference

This page says where everything in the browser window is and how to reach it:
the panels, the canvas, the radial menu and the header. Where it and the code
disagree, the code is right and this page is repaired; `tests/test_docs_routes.py`
reads the panel ids, the ring items and the menu keys against the code.

## The window

A header runs across the top, and under it a dock of panels
([Golden Layout](https://golden-layout.github.io/golden-layout/)). Each panel is
a tab: drag a tab to move it or stack it with others, drag a divider to resize,
and click a tab's ✕ to close it.

**The default arrangement** (`web/src/layout/default_layout.ts`) is the Graph
panel across the top and, below it, Files on the left beside a stack of Open (in
front), Graph Settings and Estate.

**The header's `+` button is the one way to add a window.** Its menu lists every
panel that is not in the layout, closed ones included, and under *Layout*
offers *Save current as default* and *Reset to built-in default*. A panel it
adds joins the stack whose tab was last clicked, or else the stack holding the
most panels, and never the Graph panel's own stack while another stack exists,
so the canvas stays in view.

A panel also comes forward when something loads data for it:

- a live row in the Estate panel opens the panel that draws its seam;
- View ▸ Compare in the [node ring](#node-ring) opens Chrestomathy;
- a bundled Cargo example in the [Open panel](#open) opens Cargo;
- the Topology, Capabilities, Overview, Cargo and Chrestomathy panels bring the
  Graph panel to the front when they have drawn.

**A saved layout** is kept in the browser (`localStorage`, key
`cc:gl-layout:default`). One that names a window this version does not have is
dropped, a toast says which, and the default loads. A layout saved with the
Upload, Repository and Actions windows loads with the Open window in their
place.

## Panels

`web/src/layout/panel_registry.ts` is the list of panels; each section below is
one of its entries, in the order the `+` menu lists them.

### Graph

Id `graph`. In the default arrangement.

The one canvas: every graph draws here, whichever panel asked for it. What it
does is under [The canvas](#the-canvas). With nothing drawn, it points at the
Open panel.

### Open

Id `open`. In the default arrangement, in front.

Where a graph starts. From top to bottom on the left, the quick starts first,
so that in the default arrangement they are in view without scrolling:

- **A GitHub URL or a local path**, then `→ Fetch` or Enter: draws it and loads
  its tree into the Files panel. Once loaded, a line names the repository and
  its size, and its ✕ clears the repository and any added files.
- **Local files**: drop them on the box or click it to browse. They are listed
  in the Files panel.
- **Demo and lexicons**: ⚡ Load Demo draws a sample graph, and each language
  with a lexicon has a 📖 button that draws it.
- **The examples**, by language, Rust first. A bundled example leads its group
  as a filled chip: it is read from this checkout with the documents its build
  recorded, so it needs no network, and a Cargo workspace's records go to the
  Cargo panel, which comes forward. A GitHub example draws the code map only;
  its tooltip says how much of the repository is drawn.

On the right, the parse options first, so a long Recent list leaves them in
view:

- **Parse options**, folded to one line that says what they are; click it to
  open them. *Extensions* (a chip per language, or a comma-separated list;
  empty means every language), *Parse Depth* (Files, Symbols, Deep) and
  *Annotate Lexicon*. Every parse of a repository or of files uses them.
- **Recent**: the graphs the server's cache holds, newest first. Click one to
  replay it without parsing; ☆ saves it in Graphbase when Graphbase is
  connected, and ★ marks one already saved; ✕ removes it from the cache.

Across the foot, the plot bar: **▶ Plot** draws the loaded repository; with
none, every added file; with neither, the URL in the field, as `→ Fetch` does.
**⏹ Cancel** stops a stream in flight. Beside them, the status line and the
progress of a stream.

### Estate

Id `estate-panel`. In the default arrangement.

Every seam this window reads, one row each: identified, with what it said about
itself, or down, with the sentence and the command that would change that. A
live row's **open …** button opens the panel that draws that seam, and a seam
nothing draws yet says *no panel yet*. **ask again** asks every seam again.

### Topology

Id `topology-panel`. Opens from the `+` menu or the Estate panel's topology row.

*Flows* lists the harness's topologies; click one to draw it. *What the archive
says about* takes a project name and draws what the harness's archive says about
it. The harness's caveat sits above the controls; a relation nobody measured is
drawn dashed.

### Capabilities

Id `capabilities-panel`. Opens from the `+` menu or the Estate panel's
capabilities row.

The corpus's capability registry: each declaration, the rung it claims and who
claimed it. **draw the registry** draws it.

### Overview

Id `overview-panel`. Opens from the `+` menu or the Estate panel's overview row.

dossier's reading of the estate: its masthead figures, its sections, and when the
reading was made. **draw the overview** draws it.

### Show

Id `show-panel`. Opens from the `+` menu, from the Estate panel's families row,
or by itself when the page is opened at a `?show=` address.

Every family and project the corpus names. The default is every family at once:
opened onto an empty canvas, or at a bare `?show`, the panel draws the index,
and **draw every family** draws it again over anything else. A family row
draws that family; a project's name draws its place in the
estate and offers its three views -- **estate**, **code map** and **system** --
with a view that cannot be drawn here disabled and its reason under it. The
legend above the controls says which edges are claims, which are declared seams
and which are measured. Each drawing rewrites the page's address, so
`?show=family:performing` or `?show=project:moat&view=system` reopens it.

### Cargo

Id `cargo-panel`. Opens from the `+` menu, or comes forward with a bundled
Cargo example.

Name a workspace (a directory holding `Cargo.toml`) and **read** it: which
engine read it, its crates and targets, the documents a recorded build left and
whether each is current, and the device target. Running
`codecarto cargo record <path>` in the workspace first adds cargo's own
resolution and the last check's diagnostics. *features* and *locked
dependencies of dependencies* widen **draw the workspace**.

### Chrestomathy

Id `chrestomathy-panel`. Opens from the `+` menu, or from View ▸ Compare.

*On the canvas* reads whatever graph is drawn as the constructs its nodes are,
in which languages, and names what the vocabulary could not place; it is read
again whenever a new graph is drawn. A construct's name sets it in the table
below; **show** frames its nodes and selects them for the
[selection ring](#selection-ring). *Construct* picks one construct and sets it
beside itself in every language: how each spells it, with the abstraction layer
of each token, what its parser calls it, and a note. A language with no
spelling is a row saying so. **draw the construct** draws it.

### Files

Id `file-tree`. In the default arrangement.

The loaded repository's tree, and the added files, one line each. A folder is
marked ▸, and ▾ while open, with what it holds indented under it; a file is
marked ·. Click a folder to open or close it, and a file to draw that file
alone. A file from GitHub has a *raw* link beside its name that opens its
contents in a new tab; a file read from disk has none, since the browser cannot
open it. In a large repository a folder marked … has not been read; click it to
read it, or **⊞ Expand All** to read them all. With nothing loaded, it points at
the Open panel.

### Graphbase

Id `graphbase-panel`. Opens from the `+` menu.

Graphs kept in MongoDB; it needs `MONGODB_URI`, and its header says whether it
is connected.

- **Snapshots**: name the drawn graph and 📸 keeps all of it; ▶ replays it
  without parsing.
- **Saved**: name the loaded URL and ☆ bookmarks it with its parse settings; ▶
  streams it again.
- **History**: the renders of the loaded URL; tick *Track* to record each one; ▶
  replays one.

✕ deletes an entry. Recent graphs are listed in the [Open panel](#open).

### Graph Settings

Id `graph-settings-panel`. In the default arrangement.

- **Renderer**: *D3.js (server layout)*, the canvas this page describes and the
  default; *Gravis (vis-network)*; *Notebook (Static HTML)*; *System Monitor*,
  which adds a *System* choice when there is more than one and a *Demo* or
  *Live* mode.
- **Layout**, open by default. *Algorithm* (D3 only) re-draws whatever is on the
  canvas with the chosen layout; *Compound* nests symbols around their files and
  files around their directories. *Physics*, *Repulsion* and *Link Distance*
  (Gravis only) drive vis-network's simulation. *Group Outlines* (D3 only)
  circles each directory and file group.
- **Visual**, folded: *Node Labels* (and per depth: Dir, File, Sym, Sub), *Node
  Size*, *Color By* (depth and kind, abstraction layer, or construct across
  languages), *Node Opacity*, *Border Width*, *Edge Labels*, *Edge Width*, *Edge
  Opacity*, *Label Size* and *Label Color*. Notebook and System Monitor take
  *Label Color* only.
- **Theme**, folded: Terminal, Light, Cyberpunk, Ocean, Sunset, Forest, Noir and
  Candy, which recolour the window and the canvas.

## The canvas

- **Zoom** with the scroll wheel; **pan** by dragging the background.
- **Drag a node** to move it; what is drawn inside it (a directory's files, a
  file's symbols) moves with it.
- **Hover** a node for its tooltip.
- **Double-click a node** that names a file to open its source: the file's page
  on GitHub at the node's line, or at the top of the file when it has none. For
  a file read from disk, which the browser cannot open, a badge beside the node
  names the file and line, kept inside the canvas. A path too long for the
  canvas is shortened in its middle, and the badge's tooltip has it whole. A
  double-click anywhere else zooms in.
- When a stream finishes, the view fits the whole graph: every node and every
  group outline, inside a margin, centred on what is drawn.
- **The legend** sits at the bottom left. Its header gives the totals; click it
  to list the node and edge kinds actually drawn, each with its swatch and
  count.
- **Right-click** opens the [radial menu](#the-radial-menu).

## The radial menu

A ring of choices around the pointer, for the node, the selection or the
canvas under it. Hide, Pin and Color are kept as state, so they survive
Relayout.

### Opening a ring

- **Right-click** opens a ring at the pointer that stays open. Click an item to
  choose it, click the centre to step out of a submenu or close the ring, and
  click outside it to close it.
- **Press and hold for 350 ms** with a finger or a pen opens a ring that follows
  the press. Slide to an item and lift to choose it; lift in the centre or
  outside the ring to cancel; slide out past an item with a ▸ to open its
  submenu.
- **`m`** on the focused canvas opens a ring at its centre.

A greyed item is offered but not available here; choosing it closes the ring.

### Which ring opens

| Opened | Nothing selected | One node selected | Several nodes selected |
|---|---|---|---|
| On a node | node ring, that node | node ring, the node under the pointer | selection ring |
| Off the nodes | canvas ring | canvas ring | canvas ring |
| With the key | canvas ring | selection ring | selection ring |

### Node ring

| | Item | Does |
|---|---|---|
| 1 | **Expand** | Asks the server for what lies under the node, using the directory the last parse read, and adds it. Greyed on a sub-symbol, which has nothing under it |
| 2 | **Collapse** | Removes what is drawn under the node. Greyed when nothing is |
| 3 | **Neighbors** | Selects the node and every node one edge away |
| 4 | **Pin** / **Unpin** | Marks the node with a gold outline |
| 5 | **Color** ▸ | The [Color submenu](#color-submenu) |
| 6 | **View** ▸ | **Source** opens the node's source, as a double-click does; greyed on a node that names no file. **Info** shows the node's name, what its parser called it, its construct and where it is. **Compare** opens the Chrestomathy panel at the node's construct; greyed when the vocabulary did not place it. **Focus** frames the node and everything inside it; greyed below files |
| 7 | **Hide** | Hides the node |
| 8 | **Delete** | Removes the node from the canvas; the source is untouched |

### Selection ring

| | Item | Does |
|---|---|---|
| 1 | **Expand** | Expands every selected node |
| 2 | **Neighbors** | Adds every node one edge away |
| 3 | **Spread** | Greyed: positions come from the server's layout |
| 4 | **Cluster** | Greyed, as Spread |
| 5 | **Color** ▸ | The [Color submenu](#color-submenu) |
| 6 | **Hide** | Hides the selected nodes |
| 7 | **Deselect** | Clears the selection |
| 8 | **Delete** *n* | Removes the selected nodes from the canvas |

### Canvas ring

| | Item | Does |
|---|---|---|
| 1 | **Fit** | Fits the view to the whole graph |
| 2 | **Relayout** | Draws the last graph again with the layout chosen in Graph Settings |
| 3 | **Spread** | Greyed: positions come from the server's layout |
| 4 | **Cluster** | Greyed, as Spread |
| 5 | **Physics** | Greyed: the D3 canvas runs no simulation |
| 6 | **Unhide** | Shows every hidden node. Greyed when none is hidden |
| 7 | **Deselect** | Clears the selection. Greyed when nothing is selected |

Spread, Cluster and Physics keep their places while greyed, so the items after
them do not move.

### Color submenu

**Sky**, **Calm**, **Royal**, **Gold** and **Signal**: named palette colours for
the chosen nodes.

### Keys in a ring

| Key | Does |
|---|---|
| `ArrowRight`, `ArrowDown` | Highlights the next item; from none, the first |
| `ArrowLeft`, `ArrowUp` | Highlights the previous item; from none, the last |
| `Enter` | Chooses the highlighted item, or opens its submenu |
| `Escape` | Steps out of a submenu, or closes the ring |

## The header

- **`+`**: the add-window menu, under [The window](#the-window).
- **GH**: whether the server reaches GitHub with a token. Green when it does,
  *GH?* when it does not, with a tooltip naming the token's source or how to
  give it one.
- **`?`**: the walkthrough. It opens by itself on a first visit; Escape, ×, or
  a click outside it closes it, and that is remembered in the browser.

## What the window does not have

There are no deep links or URL parameters, no menu on a right-click in the dock,
and no chords: the ring's chord words are defined and nothing listens for them.
