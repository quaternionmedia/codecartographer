"""What a parsed node *is*, said once for every language -- and the chrestomathy
that sets one construct beside itself across them.

**A KIND IS WHAT A LANGUAGE CALLS SOMETHING; A CONSTRUCT IS WHAT IT IS.** Each
parser keeps its own `kind` vocabulary, because that is what its source says
(`enum_constant`, `impl`, `label`). `codecarto/data/constructs.yaml` maps those
kinds onto one language-neutral set, so a C `struct` and a Rust `struct` are the
same construct drawn the same way, and a Rust `enum` whose variants carry data
is a *sum type* while C's `enum` is an *enumeration* -- one keyword, two things,
which is exactly what a reader comparing the two needs to see.

**STAMPED, NEVER GUESSED.** `annotate` writes `construct` only where the
vocabulary maps a node's language and kind, and `meta.facets` only for the
qualifiers, attributes, macros and body facts the vocabulary names. A node of
a language the vocabulary does not list is left exactly as it arrived.

**A LOOK IS A DEFAULT, NOT AN OVERRIDE.** A parser that set `shape` or `color`
knew something -- C's adapter carries the c-visualizer reference design, and a
test holds that design and the vocabulary to each other. A node with no look
of its own gets its construct's, which is how Rust nodes are drawn with C's
grammar wherever the two have the same construct.

**THE CHRESTOMATHY IS A READING OF TWO HAND-AUTHORED FILES.** `spelled:` in the
vocabulary names the tokens each language uses; the lexicons say which layer
and group each token sits on. Nothing here parses code to find out how a
construct is used -- it says how each language *writes* one, and a language
that has no spelling is drawn with its note rather than left out, because that
absence is often the lesson.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import networkx as nx

from codecarto.models.construct import Construct, LanguageMap, Vocabulary

VOCABULARY = Path(__file__).resolve().parent.parent / "data" / "constructs.yaml"

# Abstraction layers, machine-facing (0) to abstract, as one sequential ramp.
# Every lexicon numbers its layers from 0, so a token on C's layer 2 and one on
# Rust's layer 2 are the same colour -- the colour says "how far from the
# machine", never which language. Carried on nodes as `layer_color` so the
# canvas draws what it is sent and the ramp has one home.
LAYER_RAMP = ("#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6", "#8b5cf6", "#ec4899")

# The shapes the canvas draws are `KNOWN_SHAPES` in
# web/src/features/graph/services/node_shapes.ts, and only there: the test that
# holds every look to them reads that file rather than a copy kept here.

# How many sides a record's polygon (`shape: ngon`, `meta.sides`) may have:
# three is where a polygon starts, and past ten one reads as a circle. The one
# statement of the range -- every parser that derives `sides` clamps with
# `ngon_sides`, and the canvas draws the count it is sent.
NGON_SIDES = (3, 10)


def ngon_sides(count: int | None) -> int | None:
    """A record's side count from how many parts it has, within `NGON_SIDES`;
    None when the parser counted nothing, so the canvas draws its default
    rather than a number invented here. Zero is a count -- a unit struct --
    and draws with the fewest sides."""
    if count is None:
        return None
    low, high = NGON_SIDES
    return min(max(int(count), low), high)


def layer_color(ordinal: int) -> str:
    """The ramp colour for an abstraction layer; beyond the ramp, its last."""
    if ordinal < 0:
        return "#94a3b8"
    return LAYER_RAMP[min(ordinal, len(LAYER_RAMP) - 1)]


@lru_cache(maxsize=1)
def load() -> Vocabulary:
    """The vocabulary, validated. Cached: it is data shipped with the package."""
    import yaml

    with VOCABULARY.open("r", encoding="utf-8") as fh:
        return Vocabulary.model_validate(yaml.safe_load(fh))


def construct_for(language: str, kind: str, meta: dict | None = None) -> str | None:
    """The construct a node of *language* and *kind* is, or None."""
    mapping = load().languages.get(language)
    if mapping is None:
        return None
    return _construct(mapping, kind, meta or {})


def _construct(mapping: LanguageMap, kind: str, meta: dict) -> str | None:
    for rule in mapping.refine:
        if rule.kind == kind and meta.get(rule.meta):
            return rule.target
    return mapping.kinds.get(kind)


def attribute_name(attr: str) -> str:
    """The name an attribute is known by, as written in source:
    `cortex_m_rt::entry` -> `entry`, `repr(C)` -> `repr`,
    `unsafe(no_mangle)` -> `no_mangle`, `link_section = ".x"` -> `link_section`."""
    import re

    head = re.split(r"[(=\s]", attr, maxsplit=1)[0]
    if head == "unsafe" and "(" in attr:
        return attribute_name(attr[attr.index("(") + 1:].rstrip(")"))
    return head.rsplit("::", 1)[-1]


def _facets(mapping: LanguageMap, meta: dict, construct: str | None) -> list[str]:
    found: list[str] = []
    for token in meta.get("qualifiers") or []:
        facet = mapping.qualifiers.get(str(token))
        if facet:
            found.append(facet)
    for attr in meta.get("attributes") or []:
        facet = mapping.attributes.get(attribute_name(str(attr)))
        if facet:
            found.append(facet)
    for key, facet in mapping.meta.items():
        if meta.get(key):
            found.append(facet)
    for macro in meta.get("macros") or []:
        facet = mapping.macros.get(str(macro))
        if facet:
            found.append(facet)
    # A facet that repeats the construct says nothing the construct did not.
    return sorted({f for f in found if f != construct})


def annotate(graph: nx.Graph) -> int:
    """Stamp `construct`, `meta.facets` and a default look. Returns how many
    nodes the vocabulary recognised.

    Idempotent: running it twice gives the same graph, so a parser may call it
    and the pipeline may call it again over the merged graph.
    """
    vocabulary = load()
    recognised = 0
    for _, data in graph.nodes(data=True):
        mapping = vocabulary.languages.get(str(data.get("language", "")))
        if mapping is None:
            continue
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        construct_id = _construct(mapping, str(data.get("kind", "")), meta)
        facets = _facets(mapping, meta, construct_id)
        if construct_id is None and not facets:
            continue
        recognised += 1
        if construct_id:
            data["construct"] = construct_id
        if facets:
            data.setdefault("meta", {})["facets"] = facets
        construct = vocabulary.get(construct_id) if construct_id else None
        if construct is None or construct.look is None:
            continue
        data.setdefault("shape", construct.look.shape)
        data.setdefault("color", construct.look.color)
        if data.get("shape") == "ngon" and "sides" not in meta:
            # The first count the parser gave, zero included: `or` read a unit
            # struct's zero fields as no count and drew it with four sides.
            count = next((meta[k] for k in ("field_count", "variant_count", "member_count")
                          if meta.get(k) is not None), None)
            sides = ngon_sides(count)
            if sides is not None:
                data.setdefault("meta", {})["sides"] = sides
    return recognised


# ── The chrestomathy ──────────────────────────────────────────────────────────


def _display_name(language: str) -> str:
    from codecarto.services.lexicon_service import LexiconService

    if language in LexiconService.available():
        return LexiconService.load(language).display_name or language
    return {"assembly": "Assembly", "linker": "Linker script"}.get(language, language)


def _languages(vocabulary: Vocabulary, construct: Construct) -> list[str]:
    """Every language with something to say about *construct*: a spelling, or a
    parser kind that realises it. Vocabulary order first, then the rest."""
    named = list(vocabulary.languages)
    named += [lang for lang in construct.spelled if lang not in named]
    return [lang for lang in named
            if lang in construct.spelled or _kinds_for(vocabulary, lang, construct.id)]


def _kinds_for(vocabulary: Vocabulary, language: str, construct_id: str) -> list[str]:
    mapping = vocabulary.languages.get(language)
    if mapping is None:
        return []
    kinds = {k for k, c in mapping.kinds.items() if c == construct_id}
    kinds |= {r.kind for r in mapping.refine if r.target == construct_id}
    return sorted(kinds)


def _facet_sources(vocabulary: Vocabulary, language: str, construct_id: str) -> list[str]:
    """What, in source, carries a facet: `qualifier unsafe`, `#[link_section]`."""
    mapping = vocabulary.languages.get(language)
    if mapping is None:
        return []
    found = [f"qualifier {k}" for k, v in mapping.qualifiers.items() if v == construct_id]
    found += [f"#[{k}]" for k, v in mapping.attributes.items() if v == construct_id]
    found += [f"{k}!" for k, v in mapping.macros.items() if v == construct_id]
    return found


def reading(construct_id: str) -> dict[str, Any] | None:
    """One construct across every language, as rows. None when nobody named it."""
    from codecarto.services.lexicon_service import LexiconService

    vocabulary = load()
    construct = vocabulary.get(construct_id)
    if construct is None:
        return None
    available = set(LexiconService.available())
    rows = []
    for language in _languages(vocabulary, construct):
        spelling = construct.spelled.get(language)
        index = LexiconService.load(language).index_by_token() if language in available else {}
        tokens = [{"token": tok, "contexts": index.get(tok, [])}
                  for tok in (spelling.tokens if spelling else [])]
        rows.append({
            "language": language,
            "display_name": _display_name(language),
            "has_lexicon": language in available,
            "tokens": tokens,
            "kinds": _kinds_for(vocabulary, language, construct.id),
            "carried_by": _facet_sources(vocabulary, language, construct.id),
            "note": spelling.note if spelling else "",
        })
    return {
        "construct": {
            "id": construct.id,
            "name": construct.name,
            "gloss": construct.gloss,
            "facet": construct.facet,
            "look": construct.look.model_dump() if construct.look else None,
        },
        "languages": rows,
        "source": _source(),
        "caveat": caveat(),
    }


def table() -> dict[str, Any]:
    """Every construct, with the languages that spell or parse it -- the
    index a panel chooses from."""
    vocabulary = load()
    rows = []
    for construct in vocabulary.constructs:
        rows.append({
            "id": construct.id,
            "name": construct.name,
            "gloss": construct.gloss,
            "facet": construct.facet,
            "languages": _languages(vocabulary, construct),
        })
    return {
        "constructs": rows,
        "languages": list(vocabulary.languages),
        "source": _source(),
        "caveat": caveat(),
    }


def caveat() -> str:
    return ("Each language's tokens come from its hand-authored lexicon and each "
            "parser kind from what that language's parser emits; the join is "
            "codecarto/data/constructs.yaml. It compares how languages *write* a "
            "construct, not what their compilers do with it, and a language with "
            "no spelling is drawn with its note rather than left out.")


def _source() -> str:
    return "codecarto/data/constructs.yaml"


def as_graph(construct_id: str) -> nx.DiGraph | None:
    """The construct at the centre, each language around it, each language's
    tokens and parser kinds around that. Tokens carry their lexicon layer and
    are coloured by it, so the same distance from the machine reads the same
    in every language."""
    found = reading(construct_id)
    if found is None:
        return None
    construct = found["construct"]
    look = construct["look"] or {"shape": "hexagon", "color": "#94a3b8"}
    graph = nx.DiGraph(kind="chrestomathy", construct=construct["id"])
    root = f"construct:{construct['id']}"
    graph.add_node(root, label=construct["name"], kind="construct", depth=0,
                   shape=look["shape"], color=look["color"], size=34,
                   meta={"sides": 6},
                   hover=f"{construct['name']} — {construct['gloss']}",
                   click=f"<p><b>{construct['name']}</b> <code>{construct['id']}</code></p>"
                         f"<p>{construct['gloss']}</p>")
    for row in found["languages"]:
        language = row["language"]
        lang_id = f"language:{language}"
        silent = not row["tokens"] and not row["kinds"] and not row["carried_by"]
        graph.add_node(lang_id, label=row["display_name"], kind="language", depth=1,
                       shape="square", color="#64748b" if silent else "#cbd5e1", size=22,
                       hover=row["note"] or row["display_name"],
                       click=f"<p><b>{row['display_name']}</b></p><p>{row['note']}</p>")
        graph.add_edge(root, lang_id, kind="spelled_in", label="spelled in",
                       style="dashed" if silent else "solid")
        for tok in row["tokens"]:
            contexts = tok["contexts"]
            ordinal = min((c["layer_ordinal"] for c in contexts), default=-1)
            where = "; ".join(sorted({f"L{c['layer_ordinal']} {c['layer_name']} · {c['group']}"
                                      for c in contexts})) or "not in this language's lexicon"
            tok_id = f"token:{language}:{tok['token']}"
            graph.add_node(tok_id, label=tok["token"], kind="token", depth=2, language=language,
                           layer_ordinal=ordinal, layer_color=layer_color(ordinal),
                           shape="circle", color=layer_color(ordinal), size=14,
                           hover=f"{tok['token']} — {where}",
                           click=f"<p><code>{tok['token']}</code></p><p>{where}</p>")
            graph.add_edge(lang_id, tok_id, kind="token", label="token")
        for kind in row["kinds"]:
            kind_id = f"kind:{language}:{kind}"
            graph.add_node(kind_id, label=f"{kind} (parsed)", kind="parser_kind", depth=2,
                           shape="diamond", color="#e2e8f0", size=12,
                           hover=f"The {row['display_name']} parser emits kind '{kind}' for this")
            graph.add_edge(lang_id, kind_id, kind="parsed_as", label="parsed as")
        for source in row["carried_by"]:
            src_id = f"carried:{language}:{source}"
            graph.add_node(src_id, label=source, kind="carrier", depth=2,
                           shape="triangle", color="#e2e8f0", size=12,
                           hover=f"In {row['display_name']}, {source} marks this")
            graph.add_edge(lang_id, src_id, kind="carried_by", label="carried by")
    return graph


def metadata(construct_id: str, options: Any = None) -> dict[str, Any]:
    found = reading(construct_id) or {"languages": []}
    return {
        "kind": "chrestomathy",
        "construct": construct_id,
        "source": _source(),
        "layout": getattr(options, "layout", "Kamada Kawai"),
        "type": getattr(options, "type", None),
        "palette_id": getattr(options, "palette_id", "0"),
        "languages": [row["language"] for row in found["languages"]],
        "layers": [{"ordinal": n, "color": c} for n, c in enumerate(LAYER_RAMP)],
        "caveat": caveat(),
    }
