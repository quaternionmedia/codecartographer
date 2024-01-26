from operator import is_
import networkx as nx
from pprint import pprint
from src.database.gravis_db import insert_graph_into_database, get_gJGF_from_database


async def get_graph(
    demo: bool,
    file_path: str,
    db_graph: bool,
    url: str,
    graph_data: dict,
    is_repo: bool,
    gv: bool = False,
) -> tuple:
    """Get a graph.

    Parameters:
    -----------
        demo (bool):
            Whether to use the demo graph.
        file_path (str):
            The path to the file.
        db_graph (bool):
            Whether to use a graph from the database.
        url (str):
            The url to the file.
        graph_data (dict):
            The graph data.
        is_repo (bool):
            Whether the url is a repo.
        gv (bool):
            Whether to use the gravis repo.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    graph: nx.DiGraph = None
    graph_name: str = None
    is_in_db: bool = False

    # Clean the url if it is a repo
    if not demo and not file_path:
        if url and url != "":
            graph_name = url
            if is_repo:
                # remove trailing '/' if there
                if url.endswith("/"):
                    url = url[:-1]
                # get owner and repo name from url
                owner = url.split("/")[-2]
                repo = url.split("/")[-1]
                graph_name = f"{owner}/{repo}"

        # Check if graph is in database
        if graph_name and graph_name != "":
            pprint(f"graph_name: {graph_name}")

            try:
                graph_data, graph_name = await get_gJGF_from_database(graph_name)
            except Exception as exc:
                # If graph not in database, just igrnore error
                pass

            if graph_data:
                pprint("Graph found in database")
                db_graph = True
                is_in_db = True
            else:
                pprint("Graph not found in database")
                db_graph = False
                is_in_db = False

    # Use demo graph
    if demo:
        pprint("demo")
        graph, graph_name = demo_graph()

    # Get graph from demo_file
    elif file_path and file_path != "":
        pprint("file_path")
        graph, graph_name = file_graph(file_path)

    # Get graph from database
    elif db_graph and url:
        from src.polygraph.polygraph import gJGF_to_nxGraph

        pprint("db_graph")
        graph_data, graph_name = await get_gJGF_from_database(graph_name)
        graph_data["name"] = graph_name
        # graph_data = format_gJGF(graph_data)
        graph, graph_name = gJGF_to_nxGraph(graph_name, graph_data)

    # Get graph from repo url
    elif is_repo and url:
        pprint("is_repo")
        graph, graph_name = await repo_url_graph(url)
        # TODO: we have polygraph, why can't it just do graph_to_gJGF?
        db_results = await insert_graph_into_database(graph_name, graph)

        if gv:
            from src.polygraph.polygraph import gJGF_to_nxGraph

            pprint("gravis repo")
            pprint(graph_name)
            # If gv (gravis) we need the graph as a gJGF
            # simplest way is to just get it from the database
            # TODO: we have polygraph, why can't it just do graph_to_gJGF?
            graph_data, graph_name = await get_gJGF_from_database(graph_name)

    # Get graph from url
    elif url:
        pprint("url")
        graph, graph_name = await url_graph(url)

    # Get graph from json data
    elif graph_data and graph_data != {}:
        pprint("graph_data")
        # TODO: at some point user may be able to provide json data
        # TODO: will need to verify json data represents valid graph
        graph, graph_name = given_data_graph(graph_data)

    # If this is not a demo or file_graph
    if not demo and not file_path:
        # Insert graph into database if not already there
        if not is_in_db:
            try:
                pprint("Inserting graph into database")
                db_results = await insert_graph_into_database(graph_name, graph)
                pprint(f"Database results: {db_results}")
            except Exception as exc:
                # If graph already in database, ignore error
                pass
    else:
        pprint("Not inserting graph into database")

    return graph, graph_name


def demo_graph() -> tuple:
    """Create a demo graph.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    graph = nx.DiGraph()
    graph.add_nodes_from(
        [
            (1, {"type": "file", "label": "1"}),
            (2, {"type": "file", "label": "2"}),
            (3, {"type": "file", "label": "3"}),
            (4, {"type": "file", "label": "4"}),
            (5, {"type": "file", "label": "5"}),
            (6, {"type": "file", "label": "6"}),
            (7, {"type": "file", "label": "7"}),
            (8, {"type": "file", "label": "8"}),
        ]
    )
    graph.add_edges_from(
        [
            (1, 2),
            (1, 3),
            (2, 3),
            (2, 4),
            (3, 4),
            (5, 6),
            (5, 7),
            (6, 7),
            (6, 8),
            (7, 8),
        ]
    )
    return graph, "Fib Demo"


def file_graph(file_path) -> tuple:
    """Create a graph from a file path.

    Parameters:
    -----------
        file_path (str):
            The path to the file.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    import os
    from src.parser.parser import Parser

    if not os.path.exists(file_path):
        return {"error": "File not found."}
    parser: Parser = Parser(source_files=[file_path])
    filename = os.path.basename(file_path)

    return parser.graph, filename


def given_data_graph(data: dict) -> tuple:
    """Create a graph from given data.

    Parameters:
    -----------
        data (dict):
            The data to create the graph from.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    # Make sure graph has more than just 'name' key
    if len(data.keys()) == 1:
        return {"error": "Graph data must be a valid json graph."}

    # Create the graph
    graph = nx.DiGraph(data)

    # Return the graph and filename
    return graph, "Graph Data"


async def url_graph(url: str) -> tuple:
    """Create a graph from a url.

    Parameters:
    -----------
        url (str):
            The url to the file.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    from src.parser.parser import Parser
    from .import_source_url import get_raw_data_from_github_url

    filename = url.split("/")[-1]
    raw_data = await get_raw_data_from_github_url(url)
    parser: Parser = Parser(source_dict={"raw": raw_data, "name": filename})
    graph = parser.graph

    return graph, filename


async def repo_url_graph(url: str) -> tuple:
    """Create a graph from a repo url.

    Parameters:
    -----------
        url (str):
            The url to the file.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    from src.parser.parser_new import Parser
    from .import_source_url import get_raw_data_from_github_repo
    import networkx as nx

    pprint(f"repo_url_graph: {url}")
    filename = ""
    if url.endswith(".py"):
        # is a file
        filename = url.split("/")[-1]
    else:
        # is a repo
        # remove trailing '/' if there
        if url.endswith("/"):
            url = url[:-1]
        # get the owner and repo name from url
        owner = url.split("/")[-2]
        repo = url.split("/")[-1]
        filename = f"{owner}/{repo}"
    repo_struct = await get_raw_data_from_github_repo(url)
    parser: Parser = Parser(source_data=repo_struct, is_repo=True)
    graph = parser.graph

    json_graph = nx.readwrite.json_graph.node_link_data(graph)
    pprint(json_graph)

    return graph, filename
