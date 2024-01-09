import networkx as nx
from fastapi import HTTPException


class GravisDBError(Exception):
    """Base class for gravis database exceptions."""

    def __init__(self, source, params, message):
        self.source = source
        self.params = params
        self.message = message


class GravisDBHttpError(GravisDBError):
    """Base class for gravis database http exceptions."""

    def __init__(self, source, params, message, status_code):
        super().__init__(source, params, message)
        self.status_code = status_code


async def get_gJGF_from_database(graph_name: str) -> tuple:
    """Get a gJGF from the database.

    Parameters:
    -----------
        graph_name (str):
            The name of the graph.

    Returns:
    --------
        tuple (str, str):
            The gJGF data and the filename.
    """
    from graphbase.src.main import read_graph

    # Check if graph name provided
    if not graph_name or graph_name == "":
        raise GravisDBError(
            "get_gJGF_from_database",
            {"graph_name": graph_name},
            "No graph name provided",
        )

    # Get the graph from database
    graph_data: dict = await read_graph(graph_name)

    # Check if graph data found
    if not graph_data or graph_data == {}:
        raise GravisDBError(
            "get_gJGF_from_database",
            {"graph_name": graph_name, "graph_data": graph_data},
            "Graph data not found in database",
        )

    # Return the graph data and filename
    return graph_data, graph_name


async def insert_graph_into_database(graph_name: str, graph: nx.DiGraph) -> dict:
    """Insert a graph into the database.

    Parameters:
    -----------
        graph_name (str):
            The name of the graph.
        graph (nx.DiGraph):
            The graph.

    Returns:
    --------
        results (dict):
            The results of the insert.
    """
    try:
        from graphbase.src.main import insert_graph

        # Check if graph provided
        if not graph:
            raise GravisDBError(
                "insert_graph_into_database",
                {"graph_name": graph_name, "graph": graph},
                "No graph provided",
            )

        # Convert graph to json
        nx_graph_json = nx.node_link_data(graph)

        # Insert the graph into the database
        result: dict = await insert_graph(graph_name, nx_graph_json)

        # return result
        return result

    except HTTPException as e:
        # If graph already exists (409), ignore error
        if e.status_code != 409:
            raise GravisDBHttpError(
                "insert_graph_into_database",
                {"graph_name": graph_name, "graph": graph},
                e.detail,
                e.status_code,
            )
