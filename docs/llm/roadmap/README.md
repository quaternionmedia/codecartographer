# Roadmap

Forward-looking design docs for work that's been scoped but not fully
built — distinct from `docs/llm/archive/legacy/`, which holds
completed-and-shipped survey/implementation write-ups.

| Doc | What it's about |
|---|---|
| [`topology-functionality-abstraction-maps.md`](topology-functionality-abstraction-maps.md) | What "useful, practical maps of code and the systems it represents" already means concretely in this codebase, and the next concrete step toward more of it |
| [`lexicon.md`](lexicon.md) | The Language Lexicon feature: hand-authored per-language ontologies on a hierarchy of abstraction layers, for C and Python. Option A (static reference graph) and a first slice of Option B (joining real parsed code to abstraction layers) are both shipped; extending `annotate_lexicon` into the main parse UI and adding a third language are natural next steps, not yet done |
| *the web window* (in the corpus: `plans/the-web-window.md`) | The estate frame, the topology designer on it, and the chrestomathy of code -- the plan the estate panels, `web/src/features/estate/` and `/estate/seams` are built to. Kept in the corpus because it decides things for three repositories; this table points at it rather than copying it. Its first two phases are on `main`; the pickup for the rest is the section below |
| [`c_parser_phase3_compile_commands.md`](c_parser_phase3_compile_commands.md) | Using a real `compile_commands.json` (or a sandboxed build to generate one) instead of naive directory-walking, for more accurate C parse graphs on the GitHub-example flow |

## Picking up the web window

The plan's phases 0 and 1 -- the estate frame -- are what `main` carries. The
phases that remain are stated once, in the corpus, as
`handbook/handoffs/the-web-window.md`: what each builds, where in this
repository it lands, what to read first, and what "done" is. Read that page
before the plan, because it was stamped after the merges and the plan was
written before them. What falls to this repository, in the order the handoff
gives it:

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
- **Cartography and chrestomathy.** `annotate_lexicon` into the main parse
  flow, layer colouring as legend rows, a Chrestomathy panel across the
  languages with a lexicon (`lexicon.md`, *Adding a language*), and the panel
  the Estate table's prose row lacks -- a thread's topics drawn with the same
  caveat discipline as every other seam.

What does not move: the window calculates layout and palette vocabulary and
nothing else, stores nothing, and shows a producer's caveat verbatim --
`docs/architecture.md`, *Calculated, stored, displayed*, and
`tests/test_boundaries.py`, which stays green through every phase above.
