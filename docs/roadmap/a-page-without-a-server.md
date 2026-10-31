# A page without a server

**State:** open — delete when the published page opens every address the
corpus's pages link, and its messages are stated in `docs/api.md`.

One page, built with the window and served by any static host, that draws the
graphs other apps hand it, and the addresses they point it at, with no
codecarto running anywhere. The decision is the draft record *One page without
a server draws the graphs and addresses other apps hand it*, on
`project/codecartographer` (quaternionmedia/qm#291), Proposed. It is
published from this repository's GitHub Pages,
`https://quaternionmedia.github.io/codecartographer/view.html`. This page is
the order the rest of the work lands in.

The page draws a document now: [The page without a server](../view.md) is what
it does, and what it refuses.

## Why

- **Rule 2's live window is a server on the reader's own machine.**
  [Scale](../scale.md) sends every view deeper than a page can hold to the
  live window, linked by its address. Followed from the corpus's site, that
  link opens nothing for a reader who is not running codecarto.
- **An app has no way to hand the window a graph.** The window takes no
  message and reads no graph document by URL; it reads `?show=` and answers it
  from a route.

## What stands in the way

Largest first:

1. **Layout is Python's.** The canvas draws the positions it is given and
   places a node with none on a depth ring. The page draws positioned
   documents only; which views have one is the table below.
2. **The system monitor asks its routes.** It reads `/system/compose` and
   `/system/events` and opens a replay socket, where a show document already
   holds the composed system.
3. **The breadcrumb is the Show panel's**, and the Show panel asks
   `/show/subjects`; the index's show document holds every subject it names.

| view | positioned in its show document | opens in the page |
|---|---|---|
| a subject's estate (index, family, project) | yes, the route's own answer | now |
| a project's code | yes, every node | now |
| an imports view (index, family) | yes, as exported | now |
| a project's system | composed; the system monitor lays it out in the browser | from step 2 |
| a family's code, the corpus's full view | no: a pointer to its projects' code views, packed again by `show_layout.pack` | refused by name until step 4 decides |

## The steps

Each step is a pull request, measured as its last section says.

### 1. Published

- A workflow builds the page (`npm run build:view`) on every push to `main`
  that changes `web/`, and deploys its folder to this repository's GitHub
  Pages. Pages is enabled with **GitHub Actions** as its source, by the
  repository's owner.
- The record names the host in its service inventory entry: GitHub Pages
  serves static files, and any static host serves the same folder, so its
  withdrawal is a change of host and of the links to it, not an engineering
  project.
- **Done when** the published page draws carlos's code view from the corpus's
  site: `view.html?doc=../qm/show/project/carlos/show.json&view=code`.

### 2. Addresses, and the system view

- `?show=<address>` through `parseShow`, read from
  `<docs>/<folder>/show.json`: the corpus's published show folder, or the one
  `?docs=` names.
- A double-click opens the next address in the page (the canvas's
  `codecarto:show-open` event), and Back returns (`popstate`).
- The breadcrumb is read from the index's document, not from
  `/show/subjects`.
- A project's system view drawn from its document's `composed`, the monitor
  handed it rather than asking `/system/compose`, with no replay.
- The corpus's pages link each subject's deeper view to the page
  (`view.html?show=<address>`). That change is the corpus's, in
  quaternionmedia/qm.
- **Done when** every address the export draws opens in the page from a copy
  of the published folder, and each pointer view is refused by name.

### 3. Messages

- The envelope, the ops (`load`, `show`, `select`, `intent`) and the events
  (`ready`, `drawn`, `selected`, `opened`, `refused`), as the record states
  them, and `?from=<origin>`.
- `intent` runs through the same `GraphOps` the ring uses. They are built in
  `layout_context.ts` today, so their construction moves to where the dock and
  the page both build them the same way.
- Two host pages among the browser tests' fixtures: one embeds the page in an
  iframe, one opens it with `window.open`. Each drives every op and is
  answered with every refusal.
- `docs/api.md` states the messages, and a test reads them against the page's
  own table of ops and events.
- **Done when** both host pages drive every op and see every event, and a
  message from an origin `?from=` leaves out changes nothing.

### 4. The deep views

A family to its symbols, the corpus's full view, and
[the corpus at every depth](the-corpus-at-every-depth.md) are composed and
packed by the backend. Either the export writes each one positioned, which
adds its bytes to the corpus's history at every redraw (rules 5 and 6), or
the page packs them in the browser, a second definition of
`show_layout.pack`. Both are measured first, for the document's gzipped bytes
and the time to a first drawing at a 4× slowdown, and a record decides
between them.

## Measures

`codecarto show measure` measures pictures. The page's own figures are
measured in each step's pull request, on the machine `docs/scale.md` names:

- its script, gzipped, against the window's;
- the time to a first drawing, unslowed and at a 4× slowdown, of carlos's
  code view and core's family estate;
- the requests it makes to codecarto: none.

Measured on 2026-10-31, from a static copy of the published folder, median of
five:

| measured | the page drawing its first documents |
|---|---|
| its script, gzipped | 34.5 KB, d3 included; the window loads 145.8 KB at once |
| carlos's code view, 1,232 nodes | 3.2 s, and 5.4 s at a 4× slowdown: mostly the canvas's pacing, a hundredth of the nodes a frame, as the window draws it |
| core's family estate, 8 nodes | 0.24 s, and 0.51 s at a 4× slowdown |
| its requests | the page, its two assets and the document; none to codecarto |

## Not in it

- Parsing, the lexicon, cargo, topologies, the estate's seams and graphbase.
  Each needs its server, and stays the dock's.
- Editing a graph, or saving one. The page stores nothing.
- Laying out a graph that arrives without positions. The record's first
  revision trigger reopens it.
