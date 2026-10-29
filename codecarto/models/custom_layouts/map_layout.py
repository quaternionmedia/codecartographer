"""The Map layout: a code graph as each directory a ring of what it holds.

A layout a reader can pick for any graph, and the places the Showcase, which
a showgraph's code view opens in, starts from. The placing is
`show_layout.code_map`'s, which also says on which side of its node each name
goes. Its places are in the canvas's units, and
`graph_serializer.py` multiplies a layout's by 100, so they are given here a
hundredth as large.
"""

import networkx as nx


def map_layout(G: nx.DiGraph) -> dict:
    from codecarto.services.show_layout import code_map

    return {node: (x / 100.0, y / 100.0) for node, (x, y) in code_map(G).items()}
