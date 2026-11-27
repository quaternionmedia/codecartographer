"""The Reading Order layout: a graph left to right, the way its arrows read.

The layout the harness's interactions are drawn in, and one any graph can be
asked for by name. The placing is `reading_order.place`'s. Its places are in
the canvas's units, and `graph_serializer.py` multiplies a layout's by 100, so
they are given here a hundredth as large.
"""

import networkx as nx


def reading_order_layout(G: nx.DiGraph) -> dict:
    from codecarto.services.reading_order import place

    return {node: (x / 100.0, y / 100.0) for node, (x, y) in place(G).items()}
