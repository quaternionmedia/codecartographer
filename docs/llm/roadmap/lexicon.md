# Language Lexicon feature

A hand-authored ontology of a language's **reserved words and operators**,
arranged on a **hierarchy of abstraction layers** (machine-facing → abstract),
projected into codecarto's existing graph-visualization pipeline.

Two lexicons exist: **C** (five layers) and **Python** (three layers,
deliberately more compact — the simpler onboarding example; see "Adding a
language" below). The schema is language-agnostic; more languages are meant
to follow as additional YAML files.

## Why this is a distinct primitive

codecarto's existing graphs are *derived* by parsing a source file into an AST.
A lexicon is the opposite: reference data *about* a language, authored by hand.
It answers "what are this language's atoms and how do they stratify?" rather
than "what does this file do?". The two meet in Option B (below).

## Files added

```
codecarto/
├── data/lexicons/c.yaml            # hand-authored C taxonomy (data)
├── data/lexicons/python.yaml       # hand-authored Python taxonomy (data)
├── models/lexicon.py               # Pydantic schema (Lexicon/Layer/Group/Token)
├── services/lexicon_service.py     # load YAML → validate → project to graph (Option A)
├── services/lexicon_bridge.py      # join real parsed graphs to layers (Option B)
└── routers/lexicon_router.py       # GET /lexicon endpoints
tests/test_lexicon.py               # Option A: per-lexicon + generic parametrized tests
tests/test_lexicon_router.py        # router envelope + gJGF shape tests
tests/test_unified_parser_service.py::TestLexiconAnnotation  # Option B tests
```

## Mounting

In `codecarto/main.py`, alongside the other `include_router` calls:

```python
from codecarto.routers.lexicon_router import LexiconRouter
app.include_router(LexiconRouter, prefix="/lexicon", tags=["lexicon"])
```

Endpoints — see `docs/api.md`'s "Lexicon Endpoints" section for the current,
authoritative shapes (the `/graph` endpoint's exact response shape changed
after this doc's original claim about it turned out to be wrong — see Option
A's own entry below).

## Option A: shipped, for both languages

The lexicon is static reference data projected to a graph via
`LexiconService.to_graph()` + `GraphSerializer.serialize_to_gjgf()` — the
*same* serialization pipeline (real layout positions, sizing) every
parsed-code graph uses. `GET /lexicon/{language}/graph` returns proper gJGF.

This corrects the original version of this doc, which claimed the graph
"rides the existing pipeline with no plotter changes" using
`LexiconService.to_json()`'s plain `{nodes, links}` node-link dump — verified
false once a real frontend caller was wired up: `D3GraphRenderer.canHandle`
requires `{graph: {nodes, edges}, metadata}` and doesn't recognize a flat
node-link payload as valid graph data at all. Fixed at the router, not
worked around on the frontend.

## Option B: shipped, first slice

`codecarto/services/lexicon_bridge.py`'s `annotate_graph_with_lexicon(graph,
language)` looks up each node's `kind` (via an explicit per-language
`_KIND_TOKEN_MAP`) and, where the language exposes one, each entry of a
tokenized qualifier/modifier list (`_QUALIFIER_META_KEY`) against
`Lexicon.index_by_token()`, stamping `layer_ordinal` + `meta['lexicon_layers']`
onto matches. Opt-in via `annotate_lexicon: true` on `POST /parse/unified`
(see `docs/api.md`) — off by default, no cost to existing callers.

**Coverage is real but narrower than "every node," on purpose**: Lexicon
tokens are keywords/operators, not identifiers — a node's `label` (a function
or variable name) essentially never matches. What matches:

- **C**: `struct`/`union`/`enum`/`typedef` by kind name (these unified kinds
  are themselves already the exact keyword spelling), plus `static`/`extern`/
  `register`/`const`/`volatile` via `meta['qualifiers']` (already tokenized
  by the parser).
- **Python**: `class`/`import` by kind name, `def` via kind `function` (the
  keyword is `def`, not `"function".lower()`), `for` via kind `loop` (not
  `"for"` — `python_language_parser.py` maps AST type `"For"` to unified kind
  `"loop"`). All at depth ≤ 2 except `loop`, which is depth 3.

**Do not add a language's kind-token map by assuming `kind.lower()` is a real
keyword.** Both Python traps above (`function`→`def`, `loop`→`for`) were
caught only by reading `_TYPE_MAP` in `python_language_parser.py` directly,
not by inspecting the raw AST visitor's own type names in
`python_custom_ast.py` — those two files use different vocabularies for the
same nodes, and only the *unified* one (the parser module's own mapping
table, not the AST visitor) is what actually reaches a graph's `kind` field.

## Adding a language

**Option A only** (the language's own reference-data graph; no real-parse
join): mechanical, unchanged from before Option B existed.

1. Copy `data/lexicons/c.yaml` or `data/lexicons/python.yaml` (Python is the
   shorter template) to `data/lexicons/<lang>.yaml`.
2. Author its layers (ordinal 0 = most machine-facing) and groups.
3. That's it — `LexiconService.available()` discovers it; `tests/
   test_lexicon.py`'s generic parametrized tests (`@pytest.mark.parametrize
   ("language", LexiconService.available())`) cover it automatically, no new
   test file needed.

**Also wiring Option B** (join real parsed code to this language's layers)
— a real, small, per-language step, not implied-free by step 1-3 above:

4. In `codecarto/services/lexicon_bridge.py`, add the language's entry to
   `_KIND_TOKEN_MAP`: for each of the language's unified `kind` values that
   corresponds to a real keyword, map `kind -> exact token spelling`. **Check
   the parser module's actual kind-mapping table first** (e.g.
   `python_language_parser.py`'s `_TYPE_MAP`, `c_parser.py`'s
   `_cursor_map`) — do not assume a kind's lowercase form is the keyword.
5. If the language's parser exposes an already-tokenized list of keyword
   modifiers on a node (like C's `meta['qualifiers']`), add the language to
   `_QUALIFIER_META_KEY` too. Most languages won't have an equivalent —
   that's fine, omit the entry.
6. Add test coverage in `tests/test_unified_parser_service.py`'s
   `TestLexiconAnnotation` class, following the existing C/Python cases —
   real parsed input, not just a hand-built graph, for at least one case per
   language (mark `@requires_libclang` if the language needs an optional
   parser dependency, matching the existing C tests in that file).

## Tests

```bash
pytest tests/test_lexicon.py tests/test_lexicon_router.py
pytest tests/test_unified_parser_service.py::TestLexiconAnnotation
```

`test_lexicon.py`: per-lexicon C-specific tests (C89=32 keyword invariant,
overloaded-operator index handling) plus generic tests parametrized over
every available language (load/validate, monotonic ordinals, connected-graph
projection) — a third language gets this coverage for free.
`test_lexicon_router.py`: response envelope + real gJGF shape.
`TestLexiconAnnotation`: Option B — per-language kind/qualifier matching,
non-matching nodes correctly left unannotated, mixed-language graphs.
