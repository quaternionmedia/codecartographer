# Language Lexicon feature

A hand-authored ontology of a language's **reserved words and operators**,
arranged on a **hierarchy of abstraction layers** (machine-facing → abstract),
projected into codecarto's existing graph-visualization pipeline.

The first lexicon is **C**. The schema is language-agnostic; Go and Python are
meant to follow as additional YAML files.

## Why this is a distinct primitive

codecarto's existing graphs are *derived* by parsing a source file into an AST.
A lexicon is the opposite: reference data *about* a language, authored by hand.
It answers "what are this language's atoms and how do they stratify?" rather
than "what does this file do?". The two are designed to meet (see Option B).

## Files added

```
codecarto/
├── data/lexicons/c.yaml            # the hand-authored C taxonomy (data)
├── models/lexicon.py               # Pydantic schema (Lexicon/Layer/Group/Token)
├── services/lexicon_service.py     # load YAML → validate → project to graph
└── routers/lexicon_router.py       # GET /lexicon endpoints
tests/test_lexicon.py               # 8 tests incl. C89=32 keyword count
```

All paths follow codecarto's existing conventions: `BaseModel` models under
`models/`, a service class with `@staticmethod async`-compatible methods under
`services/`, and an `APIRouter` named `LexiconRouter`.

## Mounting

In `codecarto/main.py`, alongside the other `include_router` calls:

```python
from codecarto.routers.lexicon_router import LexiconRouter
app.include_router(LexiconRouter, prefix="/lexicon", tags=["lexicon"])
```

Endpoints:

| Endpoint | Returns |
|---|---|
| `GET /lexicon/` | available language ids |
| `GET /lexicon/{language}` | full validated lexicon JSON |
| `GET /lexicon/{language}/graph` | node-link graph for the plotter |
| `GET /lexicon/{language}/index` | token-spelling → contexts (Option B) |

The `/graph` payload uses the same node-link shape (`nodes` + `links`) the
plotter already consumes, so the C lexicon renders through the existing
frontend with no plotter changes. Token nodes carry `layer_ordinal` and `kind`
so the palette can color by abstraction level.

## Option A vs Option B

**Option A (shipped here):** the lexicon is static reference data projected to
a graph. It rides the existing pipeline today.

**Option B (scaffolded, not built):** when a real C parser lands (tree-sitter
or libclang — Python's `ast` module can't touch C), each lexed token can be
looked up via `Lexicon.index_by_token()` / `GET /lexicon/c/index` by its exact
source spelling to recover its abstraction layer. Generated C ASTs can then be
colored by the *same* `layer_ordinal` vocabulary as the lexicon graph, making
the two views visually consistent. The `token` field in the YAML is the join
key — keep it the exact source spelling for this to work.

## Adding a language

1. Copy `data/lexicons/c.yaml` to `data/lexicons/<lang>.yaml`.
2. Author its layers (ordinal 0 = most machine-facing) and groups.
3. That's it — `LexiconService.available()` discovers it; the router and tests
   are generic. Add a language-specific count test if the language has a clean
   invariant like C's 32 C89 keywords.

## Tests

```bash
pytest tests/test_lexicon.py
```

Covers load/validation, monotonic layer ordinals, the C89=32 keyword
invariant, single-root tree shape, node-link roundtrip, and that overloaded
operators (`*`, `&`) retain all their layer contexts in the index.
