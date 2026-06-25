"""Language lexicon models.

A *lexicon* is a hand-authored ontology of a language's lexical atoms
(reserved words and operators) arranged on a hierarchy of abstraction layers,
from machine-facing (ordinal 0) to abstract (higher ordinals).

This is reference data *about* a language, distinct from the per-file ASTs
codecarto derives by parsing source. The two are designed to meet: every
``Token`` carries the exact source ``token`` spelling, so a future C parser
(Option B) can look a lexed token up by spelling and recover its ``layer`` and
``group`` to color/group generated graphs by abstraction level.

Data lives in ``codecarto/data/lexicons/<language>.yaml`` and is loaded by
``LexiconService``.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    """A single lexical atom (a reserved word or an operator).

    ``token`` is the exact source spelling and the join key for parser
    enrichment. ``role`` disambiguates overloaded spellings (e.g. ``*`` as
    dereference vs. multiply, ``&`` as address-of vs. bitwise-and).
    """

    token: str = Field(..., description="Exact source spelling; the join key.")
    role: str = Field("", description="Disambiguating sense for overloaded tokens.")
    since: str = Field("", description="Standard of first appearance, e.g. 'c99'. Empty = base standard.")


class Group(BaseModel):
    """A functional cluster of tokens within a single abstraction layer."""

    name: str
    tokens: List[Token] = []


class Layer(BaseModel):
    """One abstraction layer. ``ordinal`` 0 is the most machine-facing."""

    ordinal: int
    name: str
    gloss: str = ""
    groups: List[Group] = []


class TokenKind(BaseModel):
    """A stratification of one *kind* of token (keywords or operators).

    Keywords and operators stratify differently, so each owns its own layer
    stack with independently-numbered ordinals.
    """

    layers: List[Layer] = []


class Lexicon(BaseModel):
    """A complete language lexicon: keywords and operators, each stratified."""

    language: str = Field(..., description="Lowercase language id, e.g. 'c'.")
    display_name: str = ""
    standards: List[str] = []
    keywords: TokenKind = TokenKind()
    operators: TokenKind = TokenKind()

    # -- convenience for Option B (parser enrichment) -----------------------

    def index_by_token(self) -> dict[str, List[dict]]:
        """Map every source spelling to the layer/group/kind contexts it
        appears in. A spelling may map to several contexts (overloaded
        operators), so values are lists. This is the lookup a C parser would
        use to enrich a lexed token with its abstraction layer.
        """
        idx: dict[str, List[dict]] = {}
        for kind_name, kind in (("keyword", self.keywords), ("operator", self.operators)):
            for layer in kind.layers:
                for group in layer.groups:
                    for tok in group.tokens:
                        idx.setdefault(tok.token, []).append(
                            {
                                "kind": kind_name,
                                "layer_ordinal": layer.ordinal,
                                "layer_name": layer.name,
                                "group": group.name,
                                "role": tok.role,
                                "since": tok.since,
                            }
                        )
        return idx
