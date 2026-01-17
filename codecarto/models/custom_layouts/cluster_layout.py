import numpy as np

def cluster_layout(G, root, radius=1):
    positions = {root: np.array([0, 0])}  # Initialize the positions dictionary with the root at the center
    unvisited = set(G.nodes()) - {root}  # Nodes that haven't been visited yet

    stack = [(root, 0, 2*np.pi, radius)]  # Initialize the stack with the root, start_angle, end_angle, and depth

    while stack:
        node, angle, d_angle, depth = stack.pop()  # Pop a node from the stack
        children = list(G.neighbors(node))
        num_children = len(children)
        for i, child in enumerate(children):
            child_angle = angle - d_angle/2 + i*d_angle/num_children  # calculate the angle for the child
            positions[child] = depth * np.array([np.cos(child_angle), np.sin(child_angle)])  # calculate the position for the child
            stack.append((child, child_angle, d_angle/num_children, depth+radius))  # add the child to the stack

    # Process unvisited nodes, if any
    while unvisited:
        node = unvisited.pop()
        if node in positions:  # If we've already visited the node, continue
            continue
        parents = list(G.predecessors(node))  # Get the node's parents
        if parents:  # If the node has parents
            parent = parents[0]  # Assume that the node has only one parent
            if parent in positions:  # If the parent has been visited
                positions[node] = positions[parent]  # Position the node at the parent's position
                # Layout the subgraph rooted at the node, iteratively
                stack.append((node, 0, 2*np.pi, radius))

    return positions
















# import math 

# def create_clusters(G, root):
#     clusters = {}
#     visited = set()

#     def dfs(node):
#         visited.add(node)
#         clusters[node] = []
#         for child in G.neighbors(node):
#             if child not in visited:
#                 clusters[node].append(child)
#                 dfs(child)
    
#     dfs(root)
#     return clusters

# def cluster_layout(G, root):
#     clusters = create_clusters(G, root)
#     positions = {root: (0, 0)}

#     def count_nodes(node):
#         return 1 + sum(count_nodes(child) for child in clusters[node])

#     node_sizes = {node: count_nodes(node) for node in clusters}

#     def layout_clusters(node, radius, start_angle, end_angle):
#         children = clusters[node]
#         if not children:
#             return
#         total_size = sum(node_sizes[child] for child in children)
#         angle_step = (end_angle - start_angle) / max(total_size, 1)
#         angle = start_angle
#         for child in children:
#             child_size = node_sizes[child]
#             mid_angle = angle + angle_step * child_size / 2
#             x = radius * math.cos(mid_angle)
#             y = radius * math.sin(mid_angle)
#             positions[child] = (x, y)
#             layout_clusters(child, radius + 1, angle, angle + angle_step * child_size)
#             angle += angle_step * child_size

#     layout_clusters(root, 1, 0, 2 * math.pi)
#     return positions
