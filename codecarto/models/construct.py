"""The construct vocabulary's shape.

Data lives in ``codecarto/data/constructs.yaml`` and is loaded by
``construct_service``. A *construct* is what a parsed node is, independent of
the language that spelled it; a *language map* says which of a parser's
``kind`` values (and which qualifiers, attributes and body facts) realise which
construct.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Look(BaseModel):
    """How a construct is drawn when the node carries no look of its own."""

    shape: str
    color: str


class Spelling(BaseModel):
    """How one language writes a construct.

    ``tokens`` are lexicon spellings -- a test holds every one to that
    language's lexicon, when it has one. ``groups`` names, for a token the
    lexicon files in more than one place, the group of the sense that spells
    *this* construct (Rust's ``for`` is ``iteration`` in a loop and
    ``behaviour`` in ``impl Trait for Type``); the token is drawn on that
    group's layer, and a test requires the choice wherever there is one.
    ``note`` says what the tokens cannot, including that a language has no
    spelling at all.
    """

    tokens: List[str] = []
    groups: Dict[str, str] = {}
    note: str = ""


class Construct(BaseModel):
    id: str = Field(..., description="Dotted, language-neutral: `type.product`.")
    name: str
    gloss: str = ""
    look: Optional[Look] = None
    spelled: Dict[str, Spelling] = {}

    @property
    def facet(self) -> bool:
        """A construct with no look is something a node can *also* be, never
        what it is."""
        return self.look is None


class Refinement(BaseModel):
    """`kind` with a truthy `meta` key is `construct` instead of the default.

    Read from YAML as `construct:`; held as `target` because `construct` is a
    method every pydantic model already has."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str
    meta: str
    target: str = Field(..., alias="construct")


class LanguageMap(BaseModel):
    """One language's parser kinds and facet sources, against the constructs.

    ``kinds`` and ``not_constructs`` together name every kind the language's
    parsers can emit, and nothing else: a kind is a construct, or it is listed
    with the reason it is not one (an expression inside a body, say, is what
    code does rather than a thing it declares). A node of a kind listed there
    carries no ``construct``.
    """

    kinds: Dict[str, str] = {}
    not_constructs: Dict[str, str] = {}
    refine: List[Refinement] = []
    qualifiers: Dict[str, str] = {}
    attributes: Dict[str, str] = {}
    meta: Dict[str, str] = {}
    macros: Dict[str, str] = {}


class Vocabulary(BaseModel):
    version: int
    constructs: List[Construct]
    languages: Dict[str, LanguageMap] = {}

    def get(self, construct_id: str) -> Optional[Construct]:
        return next((c for c in self.constructs if c.id == construct_id), None)
