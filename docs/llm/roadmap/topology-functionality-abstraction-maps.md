# Topology / functionality / abstraction maps: where this project is, and what's next

This is a direction document, not a feature spec — it names what
"useful, practical maps of code and the systems it represents" already
means concretely in this codebase, so that phrase has a checkable
referent instead of staying a vibe, and points at the one piece that's
already half-built and worth finishing first. No code changes ship with
this doc.

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

## The concrete next step: Lexicon Option B

`lexicon.md` already specifies this, precisely, as "scaffolded, not
built": once a real parser's token output can be looked up by exact
source spelling (`Lexicon.index_by_token()` / `GET /lexicon/{lang}/
index`), each token in a *real parsed graph* can be colored by the
*same* `layer_ordinal` vocabulary the standalone Lexicon graph uses.
Concretely, that means: parse a real C file, and for each token in the
resulting AST graph, look up which abstraction layer (machine-facing →
abstract) it belongs to via the Lexicon's index, then use that layer to
drive node color/grouping instead of (or alongside) the current
kind/depth heuristics.

This is the one place the two abstraction mechanisms above (structural
nesting, conceptual register) and real topology (an actual parsed
graph) would meet in a single view — not a new primitive, just wiring
together two things that already exist independently. It's named here,
not built here: per direction, this pass is cleanup and documentation
only. Picking it up is a separate piece of work, starting from
`lexicon.md`'s own "Option B" section and `docs/llm/2026-07-21-full-
review-cleanup-queue.md`'s discovery that `/lexicon/*` was mistaken for
dead code during this session's review — a sign the feature needs a
frontend surface (even a minimal one) to stop reading as orphaned.
