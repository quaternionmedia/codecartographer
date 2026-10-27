# UI reference

This page says where everything in the browser window is and how to reach it:
the steps, the panels, the canvas, the radial menu and the header. Where it and
the code disagree, the code is right and this page is repaired;
`tests/test_docs_routes.py` reads the steps, the panel ids, each ring's items in
order and the menu keys against the code.

## The window

A header runs across the top, and under it a dock of panels
([Golden Layout](https://golden-layout.github.io/golden-layout/)). Each panel is
a tab: drag a tab to move it or stack it with others, drag a divider to resize,
and click a tab's ✕ to close it. The dock fills the window under the header and
follows it as the window is resized, a maximised stack and the drawing on the
canvas with it. The dock has no menu of its own: a right-click on the canvas
opens the [radial menu](#the-radial-menu), and anywhere else it is the
browser's.

**The default arrangement** (`web/src/layout/default_layout.ts`) is the Graph
panel across the top and, below it, Files on the left beside a stack of Open (in
front), Graph Settings and Estate.

**The header's `+` button adds a window.** Its menu lists every panel that is
not in the layout, closed ones included, and under *Layout* offers *Save current
as default* and *Reset to built-in default*. A panel it adds joins the stack
whose tab was last clicked, or else the stack holding the most panels, and never
the Graph panel's own stack while another stack exists, so the canvas stays in
view. A window chosen from it moves the [step](#the-steps) to the one that owns
it; a step, in turn, opens its own windows again when they were closed. The menu
takes the focus when it opens, so a keyboard reader is on its first item; closed
with the focus inside it -- Escape, or one of its items -- it gives the focus
back to `+`, and a click outside it leaves the focus where that click put it.

A panel also opens, or comes forward, when something loads data for it:

- a live row in the Estate panel opens the panel that draws its seam;
- View ▸ Compare in the [node ring](#node-ring) opens Chrestomathy;
- a bundled Cargo example in the [Open panel](#open) opens Cargo;
- a `?show=` address opens [Show](#show);
- the Topology, Capabilities, Overview, Cargo and Chrestomathy panels bring the
  Graph panel to the front when they have drawn.

A panel that opens or comes forward while another stack is maximised -- step
4's canvas, or a stack maximised with its ▢ -- restores that stack, so the
panel is in view.

**A saved layout** is kept in the browser (`localStorage`, key
`cc:gl-layout:default`), saved as Golden Layout loads a layout; one kept as
Golden Layout resolves it, with its sizes as numbers, is read through Golden
Layout's own conversion. Its windows are read wherever Golden Layout reads
them: the layout's root, or a legacy layout's `content[0]`, and every open
popout's, a popout's own popouts included. One that names a window this version
does not have is dropped, a toast says which, and the default loads. A layout
saved with the Upload, Repository and Actions windows loads with the Open window
in their place; it is saved back so, and a toast says once which windows became
Open.

## The steps

Four numbered steps lead from opening source to reading its graph. The header's
rail shows all four, fills the one the reader is on, and ends with **Next**,
which names the step after it; the last step has no Next.
`web/src/layout/steps.ts` says what each step owns and brings forward.

| | Step | Brings forward | Owns |
|---|---|---|---|
| 1 | **Open** | Open, then the Graph panel | Open, Estate, Show, Topology, Capabilities, Overview, Cargo, Graphbase |
| 2 | **Browse** | Files, then the Graph panel | Files |
| 3 | **Tune** | Graph Settings, then the Graph panel | Graph Settings |
| 4 | **Read** | The Graph panel, maximised, which hides every other window | Graph, Chrestomathy |

- **A step on the rail enters it**, the step already on included. Its windows
  come to the front of their stacks and a closed one opens again; where two
  share a stack, the first one named is in front. A maximised stack is restored
  first, so any step after Read brings the windows back.
- **The canvas alone is Read, however it got that way.** Maximising the Graph
  panel's stack with its ▢ moves the rail to Read, and
  restoring the canvas from Read moves it back to the step the reader was on
  before. Either way the drawing is framed in the canvas's new size.
- **A step that resizes the canvas frames the drawing in it again**, as the
  ring's **Fit** does: entering Read, and leaving it. The fit waits until the
  canvas has its new size, not a fixed time. A step that leaves the canvas
  its size leaves the reader's zoom where it was.
- **Choosing a window moves the rail** to the step that owns it -- its tab, the
  `+` menu, or maximising another stack, which chooses the window in front of
  it -- and moves nothing else: the Graph panel's tab says Read without
  maximising the canvas. A window that comes forward by itself, as the canvas
  does after a draw, leaves the step where it is, and so does closing a tab.
- **A page opens on step 1**, and *Reset to built-in default* returns to it. The
  step is not kept anywhere: a reload has nothing drawn.
- **The walkthrough** (the header's `?`) is a page per step and shows the step
  the reader is on. Its ← Back, Next and dots enter a step, so the step's
  windows come forward behind it, and the rail moves, as it turns.

## Panels

`web/src/layout/panel_registry.ts` is the list of panels; each section below is
one of its entries, in the order the `+` menu lists them.

### Graph

Id `graph`. In the default arrangement.

The canvas: every graph draws here, whichever panel asked for it. What it
does is under [The canvas](#the-canvas). With nothing drawn, it points at step
1, Open, which the canvas hides on step 4.

**⧉**, among the Graph window's controls beside its maximise, shown while the
canvas's tab is in front, duplicates the graph into a window of its own
(`web/src/layout/panels/graph_copy_panel.ts`): a tab, `◈ Graph 2`, `◈ Graph 3`
and so on, added beside the canvas and dragged anywhere in the dock like any
other. A copy draws the graph as it was when it was made, pans and zooms apart
from the canvas, and carries its own key. The ring, the selection and the
panels that read the canvas stay with the canvas. A saved layout keeps its
copies; opened again, each draws what is on the canvas. With nothing drawn, ⧉
is disabled.

### Open

Id `open`. In the default arrangement, in front.

Where a graph starts. From top to bottom on the left, the quick starts first,
then the examples:

- **A GitHub URL or a local path**, then `→ Fetch` or Enter: draws it and loads
  its tree into the Files panel. Once loaded, a line names the repository and
  its size, and its ✕ clears the repository and any added files.
- **Demo and lexicons**: ⚡ Load Demo draws a sample graph, CodeCartographer's
  own source, from one `POST /plotter/demo` answer rather than a stream; each
  language with a lexicon has a 📖 button that draws it.
- **The examples**, by language, Rust first. A bundled example leads its group
  as a filled chip: it is read from this checkout with the documents its build
  recorded, so it needs no network, and a Cargo workspace's records go to the
  Cargo panel, which comes forward. A GitHub example draws the code map only;
  its tooltip says how much of the repository is drawn.

In the default arrangement in a 1600×1000 window, the URL, Load Demo and the
lexicons are in view without scrolling. Files and folders from disk are added
in the [Files](#files) panel. The panel is a share of
the window's height, so in a shorter window the column's fold rises, and the
lexicons are the first to fall below it.

On the right, the parse options first, so a long Recent list leaves them in
view:

- **Parse options**, folded to one line that says what they are; click it to
  open them. *Extensions* (a chip per language, or a comma-separated list;
  empty means every language), *Parse Depth* (Files, Symbols, Deep) and
  *Annotate Lexicon*. Every parse of a repository or of files uses them.
- **Recent**: the graphs the server's cache holds, newest first. Click one to
  replay it without parsing; ☆ saves it in Graphbase when Graphbase is
  connected, and ★ marks one already saved; ✕ removes it from the cache.

Across the foot, the plot bar: **▶ Plot** draws the loaded repository -- the
one the Files panel shows, from the URL its tree was read from, whatever the
field holds since; with none, every added file; with neither, the URL in the
field, as `→ Fetch` does. Plot's tooltip names what it will draw. **⏹ Cancel**
stops a stream in flight. Beside them, the status line and the progress of a
stream. Added files, the demo and a lexicon are drawn only while they are the
latest plot asked for: one whose answer arrives after another plot, or a
stream, was asked for is dropped (`web/src/state/latest_plot.ts`).

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

Every family and project the corpus names. *Families* lists each top-level
family and, indented under it, the families directly within it; a family nested
deeper is not listed, and is opened from its parent's drawing.
*Projects* lists every public project, and its field filters them by name or
family. The default is every family at once: opened with nothing on the canvas
and nothing being drawn there, or at a bare `?show`, the panel draws the index,
and **draw every family** draws it again over anything else. A family row
draws that family, and a project's name draws its place in the estate. A row
and a project's name are tab stops, and Enter or Space presses them as a click
does.

The panel opens on what is drawn. A trail runs from *every family* down to it
-- `every family › performing › instruments › carlos` -- and each step is a
link back. A project two families claim is reached from both
(`instruments · irl`). For every family, two buttons follow: **every family**
and **with each project's code**, the whole corpus in one graph: each family's
outline holding its projects, and each project its code map, from the show
document the corpus holds for it (`?show=index&view=code`, trail `every family ›
the whole corpus`). A project with no code map drawn yet is drawn alone, and
*What this drawing can say* names it. For a project, its three views follow: **estate**,
**code map** and **system**; the one drawn is pressed. A view that cannot be
drawn here is disabled, with its reason under it. Then the legend: which edges
are claims, which are declared seams and which are measured. *What this drawing
can say* holds the caveat and the corpus it was read from, folded. Its line
counts the seams nobody has declared and the members nothing measured.

On the canvas a showgraph is a map. Its nodes are drawn two and a half times
the size a code graph's are. Every name is drawn, outward from the ring
its group is packed on, and at least ten pixels high however far out the fit
frames it; an outline's name at least twelve, set inside or outside its outline
at the size it is drawn, and placed again when a zoom resizes it. The fit
frames the names at the size its own zoom draws them, so Fit again keeps the
frame. A name that would overlap another is hidden until a zoom gives it room,
and a node's hover always holds it. Names are ranked: families first, then
projects, then other repositories. Each outline takes its family's hue.
**Double-click** a family to open it, and a project to open its estate view.
A project's **code map** is drawn as a map too, in the Map layout: each
directory a disc of its files, its subdirectories packed around it. At the fit
that frames a whole repository each directory's outline name keeps its size,
where a code graph opened from the Open panel draws it a pixel high. A node is
named only while it is drawn at least four pixels across its middle on screen,
so a repository of hundreds of files is named by its directories' outlines,
and a file's name comes in as zooming in draws the file large enough to read.

Each drawing rewrites the page's address, so `?show=family:performing` or
`?show=project:moat&view=system` reopens it. A drawing opened by a click adds
an entry to the browser's history, so **Back** and **Forward** walk the
drawings, each drawn again. The address the page opened with, and the default,
do not add an entry. Back to an entry from before the first showgraph clears
the trail, and leaves the canvas as it is.

Only the latest drawing asked for is drawn: one whose answer comes after
another drawing, or another plot, was asked for is dropped, and a stream in
flight is ended when a showgraph opens. Another plot drawn over a showgraph --
a stream, the demo, a lexicon, added files, another panel's draw, or the system
monitor chosen in Graph Settings -- takes the address back to the bare page,
and the trail with it. A project's system view puts the system monitor on the
canvas, and the next draw that is not a system view puts back the renderer it
replaced.

To serve showgraphs from a corpus checkout other than the pin, set
`CODECARTO_CORPUS` before the server starts. Measured links and the system
view read clones beside this checkout, or under `CODECARTO_REPO_ROOTS`:

```sh
cd web && npm run build && cd ..
CODECARTO_CORPUS=../qm uv run codecarto serve --port 27190
```

Then open `http://localhost:27190/app?show`. The index is measured once per
commit of each clone, so a second drawing asks git nothing.

### Cargo

Id `cargo-panel`. Opens from the `+` menu, or comes forward with a bundled
Cargo example.

Name a workspace (a directory holding `Cargo.toml`) and **read** it -- the
field follows the workspace shown, so a bundled example's click fills it: which
engine read it, its crates and targets, the documents a recorded build left and
whether each is current, and the device target. Running
`codecarto cargo record <path>` in the workspace first adds cargo's own
resolution and the last check's diagnostics. *features* and *locked
dependencies of dependencies* widen **draw the workspace**.

### Chrestomathy

Id `chrestomathy-panel`. Opens from the `+` menu, or from View ▸ Compare.

*On the canvas* reads whatever graph is drawn as the constructs its nodes are,
in which languages, and names what the vocabulary could not place, each as what
it is (a file the walk drew, a kind that is no construct and why); it is read
again whenever a new graph is drawn, and never kept for one that has gone -- a
construct drawn from the vocabulary is not code and has no census. A construct's name sets it in the table
below; **show** frames its nodes and selects them, so a key opens the
[selection ring](#selection-ring) on them, or the [node ring](#node-ring) when
the construct is one node. *Construct* picks one construct and sets it
beside itself in every language: how each spells it, with the abstraction layer
of each token, what its parser calls it, and a note. Every language
`constructs.yaml` lists -- C, Rust, Python, assembly and the linker script -- is
a row: one with no spelling has its note, or one saying the vocabulary records
none. **draw the construct** draws it.

### Files

Id `file-tree`. In the default arrangement.

Files and folders from disk are added at its head. Drop files or a folder on
the box, or click it or press Enter or Space on it to choose files; **📂 Choose
a folder** chooses a folder, every file in it with its own folders kept. A
folder's version control, dependencies and build output (`.git`,
`node_modules`, `__pycache__`, `.venv`, `venv`, `.tox`, `.mypy_cache`,
`.pytest_cache`, `target`) are not read, nor a file over 2 MB, nor one of an
extension the parse options leave out when they name any; the status line
says how many were left out. An added file is known by its path, so two of one
name from two folders are both kept. The added files are listed by their paths,
and Plot draws them as the folders they were added in.

The loaded repository's tree, and the added files. A folder is marked ▸, and
▾ while open, with what it holds indented under it; a file is marked ·. Click
a folder to open or close it, and a file to draw that file alone. A file from
GitHub has a *raw* link beside its name that opens its contents in a new tab;
a file read from disk has none, since the browser cannot open it. With nothing
loaded, it points at the Open panel and the box above.

Each file and folder is a tab stop, and Enter or Space presses it as a click
does; a folder says whether it is open. A raw link is named for the file it
opens, "raw contents of" its path.

In a large repository a folder marked … has not been read; click it to read
it. It shows ↻ while it is read. A read that fails ends the ↻, leaves the folder
marked …, and says so in a toast; the next click reads it again. Several
folders can be read at once, each answer put into the tree as it comes.
**⊞ Expand All** reads every folder down to a fixed depth, and says in a toast
that it has begun, and again if it fails; a folder below that depth, or one
GitHub would not list, stays marked … and reads on a click. The tree it builds is shown,
though its root holds only folders. Every read is of the repository the tree
shows, whatever the Open panel's URL field has been typed to since, and an
answer that comes after another repository was fetched is dropped. A read
leaves the plot bar's ⏹ Cancel and progress to the stream they belong to.

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
  files around their directories; *Map* draws each directory as a disc of its
  files with its subdirectories packed around it, small enough to frame a
  whole repository ([Map layout](architecture.md#map-layout)), and a
  showgraph's code map opens in it. *Physics*, *Repulsion* and *Link Distance*
  drive vis-network's simulation and are offered on Gravis only, the one
  renderer that runs one; *Repulsion* and *Link Distance* show while *Physics*
  is on. `renderer_controls.rendererControls` says which controls each renderer
  takes. *Group Outlines* (D3 only) circles each group in a translucent dashed
  outline: grey around a directory's, teal around a file's.
- **Visual**, folded: *Node Labels* (and per depth: Dir, File, Sym, Sub), *Node
  Size*, *Color By* (depth and kind, abstraction layer, or construct across
  languages), *Node Opacity*, *Border Width*, *Edge Labels*, *Edge Width*, *Edge
  Opacity*, *Label Size* and *Label Color*. Notebook and System Monitor take
  *Label Color* only.
- **Theme**, folded: QM, the default, Terminal, Light, Cyberpunk, Ocean, Sunset,
  Forest, Noir and Candy, which recolour the window and the canvas. QM is the
  organisation's docs site's: a deep blue ground, its amber accent, and names in
  a light yellow. The canvas's names take the theme's font colour until *Label
  Color* is set to another.

## The canvas

- **Zoom** with the scroll wheel; **pan** by dragging the background.
- **Drag a node** to move it. Once a graph's group outlines have been drawn,
  what is drawn inside the node (a directory's files, a file's symbols) moves
  with it, and the outlines are drawn again where the drag ends, even after
  Group Outlines is turned off; a graph drawn with it off moves one node at a
  time ([Compound layout](architecture.md#compound-layout)).
- **Hover** a node for its tooltip.
- **Double-click a node** that names a file to open its source, as
  [A node's source](#a-nodes-source) says. On a showgraph, a family or a
  project node opens its own showgraph instead ([Show](#show)). A double-click
  anywhere else zooms in.
- When a stream finishes, the view fits the whole graph: every node, its label
  while labels are shown, and every group outline with its label, inside a
  margin, centred on what is drawn. A hidden node is left out, and so is an
  outline that holds only hidden nodes.
- **The legend** sits at the bottom left. Its header gives the totals; click it
  to list the node and edge kinds actually drawn, each with its swatch and
  count: a kind absent from the picture has no row, and every node is in exactly
  one. What each row means is decided in
  `web/src/features/graph/extensions/legend_marks.ts`, which is pure and covered
  by `npm run test:pure`. It keys the colours on screen. Under *Color By:
  Abstraction Layer* a row's swatch takes the colour the canvas paints its
  nodes, and an *Abstraction layers* section names each layer painted and counts
  its nodes -- by language where the graph holds more than one, since a layer's
  number is a rank within one language's lexicon. Under *Auto* a layer is named
  only where a node's own colour is its layer's, as the chrestomathy's tokens
  are. *Color By: Construct* paints each node the vocabulary placed in its
  construct's colour, alike across languages, and a *Constructs* section names
  each construct painted; under the other colourings a construct is named only
  where a node's own colour is its construct's, so the crate graph under *Auto*
  has no *Package* row. The canvas, the vis-network renderer and the key take
  the fill from one function, `paintedColor`. A record (`ngon`) is a row per
  side count, and says it: *Struct · 4 sides*.
- **Right-click** opens the [radial menu](#the-radial-menu).

### A node's source

A double-click on a node and View ▸ Source in the [node ring](#node-ring) open
the same place, by one rule: `node_info.sourceTarget` decides where, and
`streaming_renderer.openSource` opens it for both.

| The node | What opens |
|---|---|
| A file or a symbol from a GitHub repository | The file's page on GitHub in a new tab, at the node's line. A file, and a Python symbol, whose parser records no line, open at the top |
| A file or a symbol from a local checkout or an upload, which the browser cannot open | A badge beside the node for a few seconds, naming the node, the file's path and the line, on one line and kept inside the canvas, never over the point it was opened from. A path too long for the canvas is shortened in its middle, and a name that leaves no room for the file's own name is shortened first, so the file and the line stay; the badge's tooltip has the text whole |
| A node that names no file, such as a directory | Nothing: Source is greyed, and a double-click zooms in, as it does off the nodes; on a showgraph, a family's or a project's double-click opens its showgraph |

A C symbol names its file only by the file's stem, and a Python symbol by
`module.py`; both open where the file node they are drawn inside says the file
is.

## The radial menu

A ring of choices around the pointer, for the node, the selection or the
canvas under it. It is rad (`web/src/features/graph/rad/`), mounted against the
canvas rather than inside a renderer, so every graph gets it, whatever drew it;
[rad's host-integration standard](https://github.com/quaternionmedia/rad/blob/main/adr/DRAFT-rad-host-integration-standard.md)
is the contract it conforms to. Hide, Pin and Color are kept as state, so they
survive Relayout.

### Opening a ring

- **Right-click** opens a ring at the pointer that stays open. Click an item to
  choose it, click the centre to step out of a submenu or close the ring, and
  click outside it to close it.
- **Press and hold for 350 ms** with a finger or a pen opens a ring that follows
  the press. Slide to an item and lift to choose it; lift in the centre or
  outside the ring to cancel; slide out past an item with a ▸ to open its
  submenu.
- **`m`** on the focused canvas opens a ring at its centre. The context-menu key
  and Shift+F10 open the same ring as `m` does.

A greyed item is offered but not available here; choosing it closes the ring.

### Which ring opens

| Opened | Nothing selected | One node selected | Several nodes selected |
|---|---|---|---|
| On a node | node ring, that node | node ring, the node under the pointer | selection ring |
| Off the nodes: the background, an edge | canvas ring | canvas ring | canvas ring |
| With a key | canvas ring | node ring, the selected node | selection ring |

`web/src/features/graph/rad/host/menu_context.ts` decides this. A key has no
pointer and the nodes take no focus, so a key opens on the selection; with one
node selected it is the only way a key reaches Pin, Collapse and View. The node
ring has no Deselect, so `Escape` on the canvas with no ring open clears the
selection, as Deselect does, and every item is reachable without a pointer.

### Node ring

| | Item | Does |
|---|---|---|
| 1 | **Expand** | Asks the server (`POST /parse/expand`) for what lies under the node, using the directory the last parse read, and adds it. Greyed on a sub-symbol, which has nothing under it |
| 2 | **Collapse** | Removes what is drawn under the node. Greyed when nothing is |
| 3 | **Neighbors** | Selects the node and every node one edge away |
| 4 | **Pin** / **Unpin** | Marks the node with a gold outline |
| 5 | **Color** ▸ | The [Color submenu](#color-submenu) |
| 6 | **View** ▸ | **Source** opens the node's source, as a double-click does (see [A node's source](#a-nodes-source)); greyed on a node that names no file. **Info** shows the node's name, what its parser called it, its construct and where it is. **Compare** opens the Chrestomathy panel at the node's construct; greyed when the vocabulary did not place it. **Focus** frames the node and everything inside it; greyed below files |
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
them do not move. The ring acts on the canvas and the selection, never on one
node, so it has no Color; Color is on the node and selection rings.

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
- **1 Open, 2 Browse, 3 Tune, 4 Read** and **Next**: the step rail, under
  [The steps](#the-steps). The header is one line, of one height on every
  step. In a window 900 pixels wide or narrower, the steps the reader is not
  on, and Next, show their numbers alone, their names in their tooltips;
  narrower than the rail, the rail scrolls rather than run under the controls
  at the header's right end.
- **GH**: whether the server reaches GitHub with a token. Green when it does,
  *GH?* when it does not, with a tooltip naming the token's source or how to
  give it one.
- **`?`**: the walkthrough, a page per [step](#the-steps). It opens by itself on
  a first visit, on step 1; Escape, ×, *Got it!* on the last page, or a click
  outside it closes it, and that is remembered in the browser (`localStorage`,
  key `cc:help-dismissed`).

## What the window does not have

The page's address holds nothing but a Show drawing (`?show=`, under
[Show](#show)); the step is not in it. There is no menu on a right-click in the dock, and no ring for
an edge: a press on an edge opens the canvas ring. There are no chords: the
ring's chord words are defined in
`web/src/features/graph/rad/host/vocabulary.ts` and nothing listens for them,
so no typed word commits a verb.
