"""The Showcase layout: a code map whose symbols and members are tight clusters of dots.

The layout a reader picks to see what a repository holds rather than only how
it is filed: its directories and files as the Map draws them, and below them
every function, class, variable and call a dot, packed tight round what holds
it (`show_layout.showcase`). Its settings ride on its name --
`Showcase(dot=2,gap=0.5,nest=true,sized=true)` (`position_service.layout_spec`) -- and
the window sets them from the Graph Settings panel. Its places are in the
canvas's units, and `graph_serializer.py` multiplies a layout's by 100, so they
are given here a hundredth as large, as the Map's are.
"""

import networkx as nx


def showcase_layout(G: nx.DiGraph, dot: float = 2.0, gap: float = 0.5, nest: bool = True,
                    sized: bool = True) -> dict:
    from codecarto.services.show_layout import showcase

    return {node: (x / 100.0, y / 100.0) for node, (x, y) in showcase(G, dot=dot, gap=gap, nest=nest, sized=sized).items()}
