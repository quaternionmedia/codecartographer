import networkx as nx

def grid_layout(G: nx.Graph):
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
    grid_size = math.ceil(math.sqrt(num_nodes))

    # Sort nodes by 'value' attribute
    sorted_nodes = sorted(G.nodes(data=True), key=lambda x: x[1]["type"])

    # Create a grid of positions
    positions = np.array([(x, y) for x in range(grid_size) for y in range(grid_size)])

    # Create a mapping from node to position
    pos = {node: pos for (node, _attr), pos in zip(sorted_nodes, positions)}

    return pos 