"""Joins real parsed-graph nodes to a language's Lexicon abstraction layers.

The join to parsed code (see ``docs/architecture.md``, "Lexicons and the
construct vocabulary"): a
:class:`~codecarto.models.lexicon.Lexicon` token's spelling is the join key,
but only keywords/operators actually appear as node ``kind`` values or
tokenized qualifier lists — a node's ``label`` (a declared identifier like
``main``) is essentially never a lexicon token, so no automatic string match
is attempted there.

Adding a language here (beyond Option A, which needs nothing but a new YAML
file — see ``LexiconService``) means adding its entry below:

- ``_KIND_TOKEN_MAP[language]``: maps a unified node's ``kind`` string to the
  exact keyword spelling it represents, where that mapping is not a trivial
  lowercase of the kind name. **Do not assume ``kind.lower()`` is a real
  keyword** — e.g. Python's ``"Function"`` node kind is not the keyword
  ``"function"``, it is ``"def"``.
- ``_QUALIFIER_META_KEY[language]``: the ``meta`` key (if any) holding an
  already-tokenized list of keyword spellings attached to a node (e.g. C's
  ``meta["qualifiers"]`` — ``static``/``extern``/``register``/``const``/
  ``volatile``). Omit the language entirely if its parser has no such list.
"""

from __future__ import annotations

import networkx as nx

from codecarto.services.construct_service import layer_color
from codecarto.services.lexicon_service import LexiconService

# kind -> token spelling, explicit per language (not derived from casing —
# see module docstring for why that would be wrong). Keys are the *unified*
# node kind (lowercase, post-language-parser mapping), not the raw AST type
# name a language's own parser module uses internally - e.g. Python's
# python_language_parser.py maps AST type "For" to unified kind "loop", not
# "for", and "Function" to "function", not the keyword "def" - both traps
# this map was initially written wrong against before being verified against
# that mapping table directly.
_KIND_TOKEN_MAP: dict[str, dict[str, str]] = {
    "c": {
        "struct": "struct",
        "union": "union",
        "enum": "enum",
        "typedef": "typedef",
    },
    "python": {
        "class": "class",
        "function": "def",
        "import": "import",
        "loop": "for",  # depth 3 only
    },
    # rust_language_parser.py's kinds are its own names for items, and four
    # of them are not the keyword: `function`/`method` are `fn`, `module` is
    # `mod`, `macro` is `macro_rules`, an extern block is `extern`.
    "rust": {
        "function": "fn",
        "method": "fn",
        "struct": "struct",
        "enum": "enum",
        "union": "union",
        "trait": "trait",
        "impl": "impl",
        "module": "mod",
        "type": "type",
        "const": "const",
        "static": "static",
        "use": "use",
        "extern_crate": "crate",
        "extern_block": "extern",
        "macro": "macro_rules",
    },
}

# language -> meta key holding an already-tokenized keyword/qualifier list.
_QUALIFIER_META_KEY: dict[str, str] = {
    "c": "qualifiers",
    "rust": "qualifiers",  # pub, unsafe, async, const, extern, mut, static
}


def annotate_graph_with_lexicon(graph: nx.DiGraph, language: str) -> None:
    """Mutate ``graph`` in place, stamping lexicon abstraction layers onto
    nodes whose ``kind`` or tokenized qualifiers match a keyword/operator in
    ``language``'s Lexicon.

    No-op if ``language`` has no lexicon, or has neither a kind-token map nor
    a qualifier meta key registered above. Nodes with no match are left
    untouched — no ``layer_ordinal`` key is added, matching the existing
    convention that ``shape``/``color`` are absent rather than null when a
    parser doesn't set them.
    """
    kind_map = _KIND_TOKEN_MAP.get(language)
    qualifier_key = _QUALIFIER_META_KEY.get(language)
    if not kind_map and not qualifier_key:
        return
    if language not in LexiconService.available():
        return

    index = LexiconService.load(language).index_by_token()

    for _, data in graph.nodes(data=True):
        if data.get("language") != language:
            continue

        candidates: list[str] = []
        if kind_map:
            token = kind_map.get(data.get("kind", ""))
            if token:
                candidates.append(token)
        if qualifier_key:
            meta = data.get("meta") or {}
            candidates.extend(meta.get(qualifier_key, []))

        matches = [ctx for tok in candidates for ctx in index.get(tok, [])]
        if not matches:
            continue

        meta = data.setdefault("meta", {})
        meta["lexicon_layers"] = matches
        data["layer_ordinal"] = min(m["layer_ordinal"] for m in matches)
        # The colour "Color By: Abstraction Layer" draws, decided here so the
        # canvas has one ramp to read rather than one of its own.
        data["layer_color"] = layer_color(data["layer_ordinal"])
