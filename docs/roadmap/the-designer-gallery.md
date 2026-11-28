# The Designer panel: the gallery

**State:** open — delete when the panel lands; `docs/ui.md` and `docs/api.md`
then describe it.

The first slice of the topology designer in
[the web window's plan](README.md#picking-up-the-web-window): a panel that
shows what the harness declares about each shape of collaboration, and which
of them could run with what the harness has. It reads and draws. Nothing in
it composes, saves or runs a shape.

## What it reads

Two documents the harness serves, each as given.

| Harness route | What the gallery takes from it |
|---|---|
| `/v1/orchestration/plane` | `capabilities`: one entry per shape with `status`, `can_run`, `spends`, `writes`, `decides`, `why` and `needs`, each need a `key`, a `because` and a `supplied_by`. `options`: a shape under a named setting, with the same fields. `statuses` and `needs`: the vocabulary. `attested`: the acts that are a person's. `drift`: shapes whose declaration and registration differ. `reading`: the harness's caveat |
| `/v1/orchestration/runnable` | `have`: the workers, budget, model and build the harness counts. `shapes`: each shape with `runnable` and its `unmet` needs. `never_supplied`: needs nothing supplies |

The vocabulary is the harness's. A status or a need key the gallery has not
seen is shown as written, with the harness's own sentence beside it; the
window holds no list of either.

## What this window serves

| Route | Answers |
|---|---|
| `GET /designer/data` | One document: each shape with its plane entry and its `runnable` entry joined by name, the options under the shape they vary, `have`, `drift`, `attested`, the caveat, and which harness answered |
| `GET /designer/gjgf?layout=&palette_id=` | The same as `GraphData`: a node per shape and per need, an edge from a shape to each need it states |

Both answer in the envelope every estate route uses. A harness that is not
answering is `unreachable`; one that answers a schema this window does not
read, or has no such route, is `unreadable`; each carries a `problem`, a
`remedy` and a `where`. The seam appears as a row of `/estate/seams` naming
the panel that draws it.

## The panel

Id `designer-panel`, under the **Harness** heading of the `+` menu.

- **Which harness.** The server that answered, as the Interactions panel
  states it.
- **What the harness has.** `have`, one line: workers, budget, model, build.
- **Shapes.** One row per shape, in the plane's order:
  - its name and its status, as the plane gives it;
  - three marks, each present or absent and never inferred: spends, writes,
    decides;
  - `why`, in full;
  - each need: the key, `because`, and `supplied_by`;
  - whether it could run now, from `runnable`, and when it could not, the
    needs still unmet. A shape the plane says runs and `runnable` says cannot
    shows both, since they answer different questions;
  - its options, each a variant row beneath it with the setting and value
    that make it.
- **Declared and registered.** `drift`, each list under the harness's name
  for it. An empty list is said to be empty.
- **A person's acts.** `attested`, as a list. A refused shape's need names the
  one it would take.
- **The caveat.** `reading`, verbatim, above the rows.
- **Draw.** One button sends the graph to the Graph panel.

The panel reads once when opened and again on a button. A declaration does
not change while a harness runs, so nothing here polls.

## The graph

Shapes in one column and needs in another, an edge from each shape to each
need it states. A need a shape states and `runnable` reports unmet is drawn
dashed, the mark this window already gives a relation nobody measured. A
shape's status is its node's kind, so the palette and the legend name it; the
three marks are on the node's hover with `why`. A need several shapes share
is one node, which is what the picture is for: it shows what supplying one
need would unblock.

## What is decided, and what is not

Decided here:

- The gallery joins the two documents by shape name and computes nothing
  else. It does not decide whether a shape could run; `runnable` does.
- Reading is not bounded to the machine the window runs on. Both harness
  routes are reads, and the gallery sends nothing.
- The panel belongs to the Harness group, since its data is the harness's.

Not decided, and read from the harness before the control is built:

- Whether `runnable` takes a hand other than the harness's own, which a
  "what could run with this hand" control would need.
- Whether `/v1/topologies`, the designs already saved, are listed in this
  panel or wait for authoring.

## Tests

- A stand-in harness at `qmcp_client.fetch` with a red case for each
  absence: not answering, no such route, a schema not read, a shape named in
  one document and missing from the other.
- The join as a pure function, with a shape present in only one document
  shown with what is missing said.
- The panel in a browser against a stubbed `/designer/data`: every field of
  a row shown, a mark absent when its field is false, an unknown status shown
  as written, and no request other than GET.
- `tests/test_boundaries.py` lists the new service, router and panel, and
  `tests/test_docs_routes.py` finds both routes in `docs/api.md`.
- Each test is broken once, seen red, and names the mutation.

## Done

The panel opens from the `+` menu, shows every shape the plane declares with
no field dropped, says which could run now and what each other lacks, draws
the shapes against their needs on the canvas, and reports an absent harness
as a sentence. `docs/ui.md` and `docs/api.md` describe it, and this page is
deleted.
