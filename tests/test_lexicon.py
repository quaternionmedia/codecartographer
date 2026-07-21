"""Tests for the language lexicon feature.

Run: pytest tests/test_lexicon.py
"""

import networkx as nx
import pytest

from codecarto.models.lexicon import Lexicon
from codecarto.services.lexicon_service import LexiconService


def test_c_lexicon_loads_and_validates():
    lex = LexiconService.load("c")
    assert isinstance(lex, Lexicon)
    assert lex.language == "c"
    assert lex.keywords.layers and lex.operators.layers


def test_c_keyword_layers_are_machine_to_abstract():
    lex = LexiconService.load("c")
    ordinals = [layer.ordinal for layer in lex.keywords.layers]
    assert ordinals == sorted(ordinals)
    assert ordinals[0] == 0  # most machine-facing first


def test_c89_keyword_count():
    """C89 has 32 keywords; everything later carries a `since`."""
    lex = LexiconService.load("c")
    c89 = [
        t
        for layer in lex.keywords.layers
        for group in layer.groups
        for t in group.tokens
        if not t.since
    ]
    assert len(c89) == 32, f"expected 32 C89 keywords, got {len(c89)}"


def test_graph_is_connected_tree_from_language_root():
    lex = LexiconService.load("c")
    g = LexiconService.to_graph(lex)
    assert isinstance(g, nx.DiGraph)
    roots = [n for n, d in g.in_degree() if d == 0]
    assert roots == ["lang:c"]
    # every token node is reachable from the single root
    assert nx.number_weakly_connected_components(g) == 1


def test_every_token_node_has_layer_ordinal_and_kind():
    lex = LexiconService.load("c")
    g = LexiconService.to_graph(lex)
    tokens = [n for n, d in g.nodes(data=True) if d.get("type") == "token"]
    assert tokens
    for n in tokens:
        d = g.nodes[n]
        assert d["layer_ordinal"] >= 0
        assert d["kind"] in ("keywords", "operators")


def test_node_link_json_roundtrips():
    lex = LexiconService.load("c")
    data = LexiconService.to_json(lex)
    assert "nodes" in data
    assert "links" in data  # pinned key for frontend contract
    try:
        g2 = nx.node_link_graph(data, edges="links")
    except TypeError:
        g2 = nx.node_link_graph(data)
    assert g2.number_of_nodes() > 0


def test_index_handles_overloaded_operators():
    """`*`, `&` appear in multiple layers; the index must keep all contexts."""
    lex = LexiconService.load("c")
    idx = lex.index_by_token()
    star_kinds = {c["layer_name"] for c in idx["*"]}
    assert len(idx["*"]) >= 2  # dereference (mem) + multiply (arith)
    assert "Memory & address" in star_kinds


def test_missing_language_raises():
    with pytest.raises(FileNotFoundError):
        LexiconService.load("cobol")


# ── Generic structural tests over every available lexicon ──────────────────
# Parametrized over LexiconService.available() so a new language YAML gets
# this coverage for free — no per-language test needed, same "generic
# router/tests" property the language-agnostic parts of this feature already
# have. See docs/llm/roadmap/lexicon.md's "Adding a language" section.


@pytest.mark.parametrize("language", LexiconService.available())
def test_every_lexicon_loads_and_validates(language):
    lex = LexiconService.load(language)
    assert isinstance(lex, Lexicon)
    assert lex.language == language
    assert lex.keywords.layers or lex.operators.layers


@pytest.mark.parametrize("language", LexiconService.available())
def test_every_lexicon_layers_are_machine_to_abstract(language):
    lex = LexiconService.load(language)
    for kind in (lex.keywords, lex.operators):
        ordinals = [layer.ordinal for layer in kind.layers]
        assert ordinals == sorted(ordinals)
        if ordinals:
            assert ordinals[0] == 0


@pytest.mark.parametrize("language", LexiconService.available())
def test_every_lexicon_projects_to_a_connected_graph(language):
    lex = LexiconService.load(language)
    g = LexiconService.to_graph(lex)
    roots = [n for n, d in g.in_degree() if d == 0]
    assert roots == [f"lang:{language}"]
    assert nx.number_weakly_connected_components(g) == 1


def test_at_least_two_lexicons_available():
    """Guards against silently losing a language file."""
    assert set(LexiconService.available()) >= {"c", "python"}
