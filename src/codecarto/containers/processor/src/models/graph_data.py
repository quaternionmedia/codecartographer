from pydantic import BaseModel, Field


# This is a description of the Graph class accepted by the plotter.
# This way the client can send a general graph object and the server
# can convert it to a networkx graph object, the expected data.
# Doing so makes it easier to handle and validate the incoming data,
# as well as keeping the API purely HTTP/JSON without needing to
# serialize/deserialize complex objects.
class Edge(BaseModel):
    id: int = None
    type: str = ""
    source: int = None
    target: int = None


class Node(BaseModel):
    id: int = None
    type: str = ""
    label: str = ""
    base: str = ""
    parent: int = None
    children: list["Node"] = []
    edges: list[Edge] = []


Node.model_rebuild()


class GraphData(BaseModel):
    nodes: dict[str, Node] = Field(..., alias="nodes")
    edges: dict[str, Edge] = Field(..., alias="edges")


def get_graph_description() -> dict:
    """Returns a description of the GraphData class.

    Returns:
    --------
        dict: A description of the GraphData class.
    """
    return {
        "nodes": "Dictionary where each key is the ID of a node and the value is the node's data.",
        "edges": "Dictionary where each key is the ID of an edge and the value is the edge's data.",
        "node data": {
            "id": "The node's ID.",
            "type": "The type of the node.",
            "label": "The node's label.",
            "base": "The node's base.",
            "parent": "The ID of the node's parent, or null if the node has no parent.",
            "children": "List of the node's children. Each child is represented by its data.",
        },
        "edge data": {
            "id": "The edge's ID.",
            "type": "The type of the edge.",
            "source": "The ID of the edge's source node.",
            "target": "The ID of the edge's target node.",
        },
    }
