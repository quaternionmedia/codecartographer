# Topology / functionality / abstraction maps: where this project is, and what's next

This is a direction document, not a feature spec — it names what
"useful, practical maps of code and the systems it represents" already
means concretely in this codebase, so that phrase has a checkable
referent instead of staying a vibe. It originally named Lexicon Option B
as the concrete next step to build; that's since shipped (see the
update below) — this doc is kept as the map of what exists and what's
still open, not rewritten to erase what it predicted correctly.

## What already exists, by kind of map

**Topology** — structural relationships between real code, derived by
parsing:
- `UnifiedParserService` (`codecarto/services/unified_parser_service.py`)
  produces call graphs, import/dependency edges (`depends_on`,
  `external_module` nodes), and directory hierarchy, across every
  language `ParserRegistry` knows (Python via `PythonCustomAST`, C via
  libclang with cross-file `calls`/`FIELD_OF`/`POINTS_TO` resolution,
  12 more languages via `regex_language_parser.py`).
- Known gap, already scoped, not started: naive per-file directory
  walking misses real build context for C (generated headers,
  per-file compiler flags) — see
  [`c_parser_phase3_compile_commands.md`](c_parser_phase3_compile_commands.md)
  for using a real `compile_commands.json` instead. Deliberately kept
  separate: it needs a sandboxed-execution security pass (running an
  arbitrary repo's build system), a materially different risk profile
  than parsing.

**Abstraction** — organizing what topology produces into layers a
person can reason about, rather than one flat graph:
- The compound hierarchical layout (`codecarto/models/custom_layouts/
  compound_layout.py`, `web/src/features/graph/services/
  compound_layout.ts`) — a structural abstraction: dirs → files →
  symbols, three passes, each level collapsible.
- The Lexicon (`codecarto/services/lexicon_service.py`, `/lexicon/*`,
  [`lexicon.md`](lexicon.md)) — a *different* kind of abstraction: not
  derived from parsing, but a hand-authored ontology of a language's
  reserved words and operators, arranged on a hierarchy of abstraction
  layers (machine-facing → abstract). Where compound layout abstracts
  by *structural nesting*, the Lexicon abstracts by *conceptual
  register* — what kind of thing a token is, independent of where it
  sits in a file tree.

**Functionality** — what a system actually *does* at runtime, not just
how its code is shaped:
- PAM (`codecarto/routers/pam_router.py`) visualizes live Linux
  authentication activity (auth.log tailing, session replay) — a real
  runtime/behavioral map, of a *system* rather than of source code. It
  already fits "the systems they represent" half of the brief; it's
  just a different data source (log events, not parsed source) feeding
  the same graph-rendering pipeline.

## Update: Lexicon Option B — shipped, first slice

The above named this as the concrete next step; it's since been built.
`codecarto/services/lexicon_bridge.py` joins real parsed C and Python
graphs to their Lexicon's abstraction layers (opt-in via
`annotate_lexicon` on `POST /parse/unified`), the standalone Lexicon
graph now actually renders (its `/graph` endpoint emitted a shape the
frontend didn't recognize until this pass fixed it — see `lexicon.md`),
and a `colorBy: 'layer'` styling option colors nodes by the result. See
`lexicon.md` for exactly what's covered (narrower than "every node" —
keywords/operators, not identifiers, and only where a language's parser
exposes a matchable kind or qualifier list) and its "Adding a language"
section for extending to a third language.

**What's still not done, named honestly rather than left implicit:**

- `annotate_lexicon` isn't exposed as a toggle in the main repo/demo
  parse flow — only the standalone Lexicon graph (which has its own
  `layer_ordinal` from Option A) is switchable from the UI today.
  Wiring a checkbox into the real-parse path is a small, separate
  follow-up.
- Only C and Python have a Lexicon; only 4 Python keywords and 8 C
  keyword-shaped kinds are reachable by Option B's join (see
  `lexicon.md`'s coverage notes) — most of both languages' full
  keyword lists exist for Option A only.
- C's `meta['type_str']` (e.g. `"struct Foo *"`) contains embedded
  keywords/operators but isn't tokenized — joining it would need real
  tokenization, not attempted.
- `c_parser_phase3_compile_commands.md`'s topology-accuracy gap is
  unrelated and still fully open.
