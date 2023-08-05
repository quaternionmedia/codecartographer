import matplotlib.pyplot as plt
import networkx as nx

def arc_layout(G):
    pos = nx.spring_layout(G)  # To make the initial layout more interesting
    nodes = G.nodes()
    plt.figure(figsize=(8, 4))
    # Draw nodes
    for node in nodes:
        plt.scatter(pos[node][0], 0, s=100, c='blue')

    # Draw edges
    for edge in G.edges():
        start, end = pos[edge[0]], pos[edge[1]]
        x = [start[0], end[0]]
        y = [0, 0]
        plt.plot(x, y, c='red', alpha=0.5, zorder=1)

    # Remove y-axis
    plt.gca().axes.get_yaxis().set_visible(False)

    # Show the plot
    plt.show() 