# Roadmap

**State:** open — delete when every page it lists has been deleted and its
own sections are empty.

Work that is scoped and not built. A page here is deleted when its work lands;
what has landed is described in the reference pages under `docs/`.

| Page | What is open |
|---|---|
| [`rust.md`](rust.md) | Rust and the firmware languages: semantic resolution through SCIP, peripherals, C firmware at parity, the build, running firmware |
| [`lexicon.md`](lexicon.md) | More lexicons and constructs for the chrestomathy |
| [`c_parser_phase3_compile_commands.md`](c_parser_phase3_compile_commands.md) | Parsing C from a real `compile_commands.json` instead of walking the directory |
| [`large-repos.md`](large-repos.md) | A repository the size of linux, parsed whole and explored on the canvas |
| *the web window* (in the corpus: `plans/the-web-window.md`) | The estate frame, the topology designer on it, and the chrestomathy of code. Kept in the corpus because it decides things for three repositories; the pickup for this repository is the section below |

## Picking up the web window

The phases of the plan that remain are stated once, in the corpus, as
`handbook/handoffs/the-web-window.md`: what each builds, where in this
repository it lands, what to read first, and what "done" is. Read that page
before the plan. What falls to this repository, in the order the handoff gives
it:

- **The live flow on the shape.** Run state from the harness's invocations and
  human queue, joined to the drawn boxes by address, as a
  `web/src/features/graph/extensions/` extension and a Harness panel beside
  the estate panels -- read-only, polling before any event stream. An address
  no box carries is reported in the panel, never dropped.
- **The topology designer.** First a Designer panel that lists what
  `/v1/orchestration/plane` declares; then authoring, saved through
  `/v1/topologies` and shown with the plane's verdict as given. The authored
  verbs for the ring begin with this repository's own record naming `rad` in
  its `Pends on` row, on `project/codecartographer`, before anything is built.
- **Cartography and chrestomathy.** The panel the Estate table's prose row
  lacks -- a thread's topics drawn with the same caveat discipline as every
  other seam -- and the looksatwords bridge both ways.

What does not move: the window calculates layout and palette vocabulary and
nothing else, stores nothing, and shows a producer's caveat verbatim --
`docs/architecture.md`, *Calculated, stored, displayed*, and
`tests/test_boundaries.py`.

## Maps of code

- **A wider lexicon join.** The join to parsed code reaches only the keywords
  a parser exposes as a kind or a qualifier, so most of each lexicon is
  reachable only in its own graph.
- **C's type strings.** `meta['type_str']` (`"struct Foo *"`) holds keywords
  and operators that are not tokenized, so the join cannot reach them.

## Smaller open work

- **`DefaultPalette` is a literal** in `codecarto/models/plot_data.py`. As
  `data/palettes/default.yaml`, beside the lexicons, it could be edited without
  touching Python; `Palette` is built at import time by several callers.
- **Nothing validates a palette.** One missing `unknown` resolves every
  unmatched base to `palette_service`'s fallbacks without a message; a
  `Palette.validate()` naming missing keys would say so.
- **The palette's shapes are matplotlib markers** (`o`, `s`, `^`), translated
  to the canvas's shape names in one tested table. Canvas-neutral names with a
  table per renderer would be a data migration.
- **The lexicon and the palette describe one language twice**, as abstraction
  layers and as dotted bases, and neither reads the other.
- **`plotter_router.render_graph_to_html` reads gJGF by hand**, about a
  hundred lines, where `GraphSerializer` and the models already describe it.
- **`Positions._layouts` is read from outside** by `topology_router.py` and
  `estate_service.py`; a public `names()` would end that.
- **`StateController.update` does not repaint.** A caller reached from a DOM
  event is repainted by Mithril; one that awaits in `oninit` is not, so it must
  redraw itself. Either `update` redraws, with a way to batch, or its name says
  it does not.
