"""Lexicon service: load language lexicons and project them to graphs.

Loads ``codecarto/data/lexicons/<language>.yaml`` into a :class:`Lexicon`, and
projects it to a networkx graph in the same node-link shape codecarto already
produces for ASTs — so the existing ``/plotter`` pipeline and frontend render
it for free (Option A).

The graph hierarchy is::

    language -> kind (keywords|operators) -> layer -> group -> token

Each node carries ``layer_ordinal`` and ``kind`` attributes so the plotter can
color by abstraction level. This same attribute vocabulary is what a future C
parser would stamp onto AST nodes (Option B), keeping the two views visually
consistent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import networkx as nx
import yaml

from codecarto.models.lexicon import Lexicon

LEXICON_DIR = Path(__file__).resolve().parent.parent / "data" / "lexicons"


class LexiconService:
    @staticmethod
    def available() -> list[str]:
        """List language ids that have a lexicon file."""
        if not LEXICON_DIR.is_dir():
            return []
        return sorted(p.stem for p in LEXICON_DIR.glob("*.yaml"))

    @staticmethod
    def load(language: str) -> Lexicon:
        """Load and validate a lexicon by language id (e.g. ``'c'``)."""
        path = LEXICON_DIR / f"{language.lower()}.yaml"
        if not path.is_file():
            raise FileNotFoundError(
                f"No lexicon for '{language}'. Available: {LexiconService.available()}"
            )
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        return Lexicon.model_validate(raw)

    @staticmethod
    def to_graph(lexicon: Lexicon) -> nx.DiGraph:
        """Project a lexicon to a directed graph (language -> ... -> token)."""
        g = nx.DiGraph()
        lang_id = f"lang:{lexicon.language}"
        g.add_node(
            lang_id,
            label=lexicon.display_name or lexicon.language,
            type="language",
            layer_ordinal=-1,
            kind="root",
        )

        for kind_name, kind in (("keywords", lexicon.keywords), ("operators", lexicon.operators)):
            kind_id = f"kind:{lexicon.language}:{kind_name}"
            g.add_node(kind_id, label=kind_name, type="kind", layer_ordinal=-1, kind=kind_name)
            g.add_edge(lang_id, kind_id, relation="has_kind")

            for layer in kind.layers:
                layer_id = f"{kind_id}:L{layer.ordinal}"
                g.add_node(
                    layer_id,
                    label=f"L{layer.ordinal} {layer.name}",
                    type="layer",
                    layer_ordinal=layer.ordinal,
                    kind=kind_name,
                    gloss=layer.gloss.strip(),
                )
                g.add_edge(kind_id, layer_id, relation="has_layer")

                for group in layer.groups:
                    group_id = f"{layer_id}:{group.name}"
                    g.add_node(
                        group_id,
                        label=group.name,
                        type="group",
                        layer_ordinal=layer.ordinal,
                        kind=kind_name,
                    )
                    g.add_edge(layer_id, group_id, relation="has_group")

                    for tok in group.tokens:
                        # token spellings are not globally unique (overloads),
                        # so scope the node id by its group context.
                        tok_id = f"{group_id}:{tok.token}"
                        g.add_node(
                            tok_id,
                            label=tok.token,
                            type="token",
                            layer_ordinal=layer.ordinal,
                            kind=kind_name,
                            role=tok.role,
                            since=tok.since,
                        )
                        g.add_edge(group_id, tok_id, relation="has_token")
        return g

    @staticmethod
    def to_json(lexicon: Lexicon) -> Dict:
        """Node-link JSON matching codecarto's graph serialization.

        ``edges="links"`` is pinned so the payload uses the ``links`` key on
        every networkx version (3.x changed the default to ``edges``), keeping
        the frontend contract stable.
        """
        graph = LexiconService.to_graph(lexicon)
        try:
            return nx.node_link_data(graph, edges="links")
        except TypeError:
            # older networkx without the `edges` kwarg already emits "links"
            return nx.node_link_data(graph)
