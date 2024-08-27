import networkx as nx

from models.graph_data import GraphBase

DemoGraph: GraphBase = GraphBase(
    nx.DiGraph(
        name="Demo",
        incoming_graph_data={
            "nodes": [
                (1, {"type": "module", "label": "module"}),
                (2, {"type": "function", "label": "function_a"}),
                (3, {"type": "class", "label": "class_a"}),
                (4, {"type": "variables", "label": "variables_a"}),
                (5, {"type": "import", "label": "import_a"}),
                (6, {"type": "function", "label": "function_b"}),
                (7, {"type": "class", "label": "class_b"}),
                (8, {"type": "variables", "label": "variables_b"}),
                (9, {"type": "function", "label": "function_c"}),
                (10, {"type": "function", "label": "function_d"}),
                (11, {"type": "class", "label": "class_c"}),
                (12, {"type": "variables", "label": "variables_c"}),
            ],
            "edges": [
                (1, 2),
                (1, 3),
                (1, 4),
                (1, 5),
                (2, 6),
                (3, 7),
                (4, 8),
                (6, 9),
                (7, 10),
                (9, 11),
                (10, 12),
            ],
        },
    )
)
