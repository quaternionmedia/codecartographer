import networkx as nx

def sorted_square_layout(G: nx.Graph):
    """Position nodes in a grid.

    Parameters
    ----------
    G : NetworkX graph or list of nodes
        A position will be assigned to every node in G.

    Returns
    -------
    pos : dict
        A dictionary of positions keyed by node
    """
    import math
    import numpy as np 

    num_nodes = len(G.nodes())
    sqrt_num_nodes = math.sqrt(num_nodes)
    grid_size = math.ceil(sqrt_num_nodes) 

    # Sort nodes by their 'type', when they have one. A layout is a position
    # calculation and must not presume a styling attribute: a graph whose nodes
    # carried no `type` -- any graph not built from a parse -- raised KeyError
    # from inside the layout and reached a route as a 500. Untyped nodes sort
    # first, by id, so the grid is still a deterministic order.
    sorted_nodes = sorted(G.nodes(data=True),
                          key=lambda x: (str(x[1].get("type", "")), str(x[0])))

    # Create a grid of positions
    positions = np.array([(x, y) for x in range(grid_size) for y in range(grid_size)])

    # Create a mapping from node to position
    pos = {node: pos for (node, _attr), pos in zip(sorted_nodes, positions)}

    return pos 