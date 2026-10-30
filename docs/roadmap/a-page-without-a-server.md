# A page without a server

**State:** open — delete when `view.html` is published, opens every address
the corpus's pages link, and its messages are stated in `docs/api.md`.

One page, built with the window and served by any static host, that draws the
graphs other apps hand it, and the addresses they point it at, with no
codecarto running anywhere. The decision is the draft record *One page without
a server draws the graphs and addresses other apps hand it*, on
`project/codecartographer` (quaternionmedia/qm#291). It is Proposed, and waits
only on the origin the page is published from. This page is the order the
work lands in.

## Why

- **Rule 2's live window is a server on the reader's own machine.**
  [Scale](../scale.md) sends every view deeper than a page can hold to the
  live window, linked by its address. Followed from the corpus's site, that
  link opens nothing for a reader who is not running codecarto.
- **An app has no way to hand the window a graph.** The window takes no
  message, reads no graph document by URL and opens no file of graph data; it
  reads `?show=` and answers it from a route.

## What it builds on

Read on 2026-10-30, at `evolve/shared-imports`:

| seam | where | what it gives |
|---|---|---|
| a positioned document drawn with no network | `PlotActions.handlePlotData`, `D3GraphRenderer.canHandle` | the drawing, from gJGF's node map or a flat list |
| show documents | the corpus's site, `https://quaternionmedia.github.io/qm/show/<subject>/show.json` | every subject's views, served to any origin (`access-control-allow-origin: *`) |
| the address grammar | `web/src/features/show/show_address.ts` | `parseShow`, `formatShow` and the trail, pure and tested |
| one way into a showgraph | `openShow` in `layout_context.ts`, and the `codecarto:show-open` event | a double-click's next address |
| instructions as data | rad's `Intent` (`rad/core/types.ts`), `createIntentRouter` | fit, focus, hide, pin, colour, the ring's own verbs |
| a selection by id | `showOnCanvas(ids)` | frames the nodes and selects them |

And what stands in the way, largest first:

1. **Layout is Python's.** The canvas draws the positions it is given and
   places a node with none on a depth ring. The page draws positioned
   documents only; which views have one is the table below.
2. **Every way of getting a graph is a route.** `RequestHandler` and each
   service are wired to `api_base.ts`.
3. **The dock boots with its server.** Its boot asks several routes, the Show
   panel asks `/show/subjects`, and most panels need a route.
4. **The build names its assets from the root of an origin.** Its `base` sits
   inside `build:`, where Vite does not read it.

| view | positioned in its show document | opens in the page |
|---|---|---|
| a subject's estate (index, family, project) | yes, the route's own answer | from step 1 |
| a project's code | yes, every node | from step 1 |
| a project's system | composed; the system view lays it out in the browser | from step 1 |
| an imports view (index, family) | once it is exported | when it is |
| a family's code, the corpus's full view | no: a pointer to its projects' code views, packed again by `show_layout.pack` | refused by name until step 5 decides |

## The steps

Each step is a pull request, measured as its last section says.

### 1. A page that draws a document, with no server

- `view.html` and its script beside `web/src/index.html`, a second input of
  the build (`build.rollupOptions.input`). It imports the renderer and its legend, and
  none of the dock, the panels, `RequestHandler` or `api_base.ts`.
- One reading of a document, whatever brought it: a show document and the
  view asked for, or a gJGF document. A document that is neither is refused
  with a problem and a remedy, and so is a view the document holds as a
  pointer.
- `?doc=<url>`, a dropped or opened file, and a paste.
- A project's code view drawn as a map, as the window draws it. Its
  document lacks `kind: "show"` and its layout's name, which the window
  takes from the stream, so the export writes both into it.
- A project's system view drawn from its document's `composed`, which the
  system view is handed rather than asking `/system/compose`.
- The producer's caveat shown verbatim, with who handed it beside it.
- The build's `base` moved to where Vite reads it, relative to the page.
- Tests:
  - pure tests of the reading, for each shape and each refusal;
  - a browser test opens `view.html?doc=` on carlos's estate and code views,
    with every prefix in `API_PATHS` refused and the requests to them counted:
    none;
  - the built page opens from a subfolder of a plain static server.
- **Done when** carlos's estate and code views draw from their documents with
  no codecarto process running, at the positions the window draws them.

### 2. Addresses

- `?show=<address>` through `parseShow`, read from
  `<docs>/<folder>/show.json`: the corpus's published show folder, or the one
  `?docs=` names.
- A double-click opens the next address in the page, and Back returns
  (`popstate`).
- The breadcrumb is read from the index's document, not from
  `/show/subjects`.
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

### 4. Published

- Once the record's origin is chosen: a workflow builds `web/` and publishes
  the page and its assets. The adoption record's service inventory names the
  host.
- The corpus's pages link each subject's deeper view to the page
  (`view.html?show=<address>`). That change is the corpus's, in
  quaternionmedia/qm.
- **Done when** the published page opens each address the corpus's pages
  link, from the corpus's site.

### 5. The deep views

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

## Not in it

- Parsing, the lexicon, cargo, topologies, the estate's seams and graphbase.
  Each needs its server, and stays the dock's.
- Editing a graph, or saving one. The page stores nothing.
- Laying out a graph that arrives without positions. The record's first
  revision trigger reopens it.
