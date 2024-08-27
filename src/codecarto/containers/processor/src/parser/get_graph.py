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
    file_data: dict | str = None,
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
        file_data (dict | str):
            The file data.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    pprint("0       ############## GET GRAPH STARTING ##############")
    graph: nx.DiGraph = None
    graph_name: str = None
    is_in_db: bool = False

    # Clean the url if it is a repo
    if not demo and not file_path:
        if url and url != "":
            pprint(f"        url ")
            graph_name = url
            if is_repo:
                # remove trailing '/' if there
                if url.endswith("/"):
                    url = url[:-1]
                # get owner and repo name from url
                owner = url.split("/")[-2]
                repo = url.split("/")[-1]
                graph_name = f"{owner}/{repo}"
            else:
                # get filename from url
                graph_name = url.split("/")[-1]

        # Check if graph is in database
        if graph_name and graph_name != "":
            pprint(f"        graph_name: {graph_name}")

            try:
                graph_data, graph_name = await get_gJGF_from_database(graph_name)
            except Exception as exc:
                # If graph not in database, just igrnore error
                pass

            if graph_data:
                pprint(f"        Graph '{graph_name}' found in database")
                db_graph = True
                is_in_db = True
            else:
                pprint(f"        Graph '{graph_name}' not found in database")
                db_graph = False
                is_in_db = False

    # Use demo graph
    if demo:
        pprint("demo")
        graph, graph_name = demo_graph()

    # Get graph from demo_file
    elif file_path and file_path != "":
        pprint("file_path")
        graph, graph_name = file_path_graph(file_path)

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
        pprint("        is_repo")
        pprint("1       ############## GET REPO GRAPH ##############")
        graph, graph_name = await repo_url_graph(url)
        # TODO: we have polygraph, why can't it just do graph_to_gJGF?
        db_results = await insert_graph_into_database(graph_name, graph)

        if gv:
            from src.polygraph.polygraph import gJGF_to_nxGraph

            pprint(f"        gravis repo: {graph_name}")
            # If gv (gravis) we need the graph as a gJGF
            # simplest way is to just get it from the database
            # TODO: we have polygraph, why can't it just do graph_to_gJGF?
            graph_data, graph_name = await get_gJGF_from_database(graph_name)

    # Get graph from url
    elif url:
        pprint("graph from url")
        graph, graph_name = await file_url_graph(url)

    # Get graph from json data
    elif graph_data and graph_data != {}:
        pprint("        graph_data")
        pprint("1       ############## GIVEN GRAPH DATA ##############")
        # TODO: at some point user may be able to provide json data
        # TODO: will need to verify json data represents valid graph
        graph, graph_name = given_data_graph(graph_data)

    # Get graph from file data
    elif (
        file_data
        and (isinstance(file_data, str) and file_data != "")
        or (isinstance(file_data, dict) and file_data != {})
    ):
        pprint("        file_data")
        pprint("1       ############## GET FILE GRAPH ##############")
        graph, graph_name = await file_data_graph(file_data)
        # TODO: we have polygraph, why can't it just do graph_to_gJGF?
        db_results = await insert_graph_into_database(graph_name, graph)

        if gv:
            from src.polygraph.polygraph import gJGF_to_nxGraph

            pprint(f"        gravis file: {graph_name}")
            # If gv (gravis) we need the graph as a gJGF
            # simplest way is to just get it from the database
            # TODO: we have polygraph, why can't it just do graph_to_gJGF?
            graph_data, graph_name = await get_gJGF_from_database(graph_name)

    # Apply some styling to the graph
    # pprint("graph", graph)
    if graph:
        pprint("        gravis graph")

        pprint(
            f"graph num nodes: {graph.number_of_nodes()} num edges: {graph.number_of_edges()}"
        )
        pprint(f"graph nodes: {graph.nodes( data=True)}")
        graph = apply_styles(graph)

    # If this is not a demo or file_graph
    if not demo and not file_path:
        # Insert graph into database if not already there
        if not is_in_db:
            try:
                pprint("        Inserting graph into database")
                db_results = await insert_graph_into_database(graph_name, graph)
                pprint(f"        Database results: {db_results}")
            except Exception as exc:
                # If graph already in database, ignore error
                pass
    else:
        pprint("        Not inserting graph into database")

    pprint("2       ############## GET GRAPH FINISHED ##############")
    return graph, graph_name


def fib_demo_graph() -> tuple:
    """Create a demo graph.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    pprint("fib_demo_graph")

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


def demo_graph() -> tuple:
    """Create a demo graph.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    pprint("demo_graph")

    graph = nx.DiGraph()

    # create a demo graph about a simple python program
    # Add nodes representing different AST objects in a Python program
    graph.add_nodes_from(
        [
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
        ]
    )

    # Add edges to create a more complex graph with multiple branching clusters
    graph.add_edges_from(
        [
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
        ]
    )

    return graph, "Demo"


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


def file_path_graph(file_path) -> tuple:
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
    from src.parser.parser_new import Parser

    if not os.path.exists(file_path):
        return {"error": "File not found."}

    parser: Parser = Parser(source_data=[file_path])
    filename = os.path.basename(file_path)

    return parser.graph, filename


async def file_data_graph(file_data: dict | str) -> tuple:
    """Create a graph from file data.

    Parameters:
    -----------
        file_data (str):
            The file data.

    Returns:
    --------
        tuple (nx.DiGraph, str):
            The graph and the filename.
    """
    from src.parser.parser_new import Parser

    name = "uploaded_file"
    data = file_data
    if isinstance(file_data, dict):
        data = file_data["data"]
        name = file_data["filename"]

    repo_struct = {
        "owner": "user",
        "repo": "uploaded_file",
        "size": "123",
        "raw": data,
    }
    pprint("#####################  FILE DATA GRAPH  #####################")
    parser: Parser = Parser(source_data=repo_struct, is_repo=True)
    graph = parser.graph

    return graph, name


async def file_url_graph(url: str) -> tuple:
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
    from src.parser.parser_new import Parser
    from .import_source_url import get_raw_data_from_github_url

    filename = url.split("/")[-1]
    raw_data = await get_raw_data_from_github_url(url)
    pprint("#####################  FILE URL GRAPH  #####################")

    parser: Parser = Parser(source_data={"raw": raw_data, "name": filename})
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

    pprint("      REPO URL GRAPH ")
    pprint(f"        repo_url_graph ")
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
    # print the struct with proper indentation and newlines, if raw is code, just print 'code'
    # pp(repo_struct)

    pprint("      PARSER STARTING ")
    parser: Parser = Parser(source_data=repo_struct, is_repo=True)
    graph = parser.graph
    pprint("      PARSER COMPLETED ")

    # prints out the graph as json
    # print(nx.readwrite.json_graph.node_link_data(graph))

    return graph, filename


# TOOD: this is temporary until we define more in palette.py
def apply_styles(graph: nx.DiGraph) -> nx.DiGraph:
    node_styles = {
        # "interactive": visitor.interactives,
        # "expression": visitor.expressions,
        "function": {"color": "#99ff99", "shape": "rectangle"},
        "asyncfunction": {"color": "#99ff99", "shape": "rectangle"},
        "class": {"color": "#ff9999", "shape": "ellipse"},
        # "return": visitor.returns,
        # "delete": visitor.deletes,
        # "assign": visitor.assigns,
        # "typealias": visitor.typealiases,
        # "augassign": visitor.augassigns,
        # "annassign": visitor.annassigns,
        # "forloop": visitor.forloops,
        # "asyncforloop": visitor.asyncforloops,
        # "whileloop": visitor.whileloops,
        # "if": visitor.ifs,
        # "with": visitor.withs,
        # "asyncwith": visitor.asyncwiths,
        # "match": visitor.matches,
        # "raise": visitor.raises,
        # "try": visitor.trys,
        # "trystar": visitor.trystars,
        # "assert": visitor.asserts,
        "import": {"color": "#9999ff", "shape": "diamond"},
        "importfrom": {"color": "#9999ff", "shape": "diamond"},
        # "global": visitor.globals,
        # "nonlocal": visitor.nonlocals,
        # "expr": visitor.exprs,
        # "pass": visitor.passes,
        # "break": visitor.breaks,
        # "continue": visitor.continues,
        # "boolop": visitor.boolops,
        # "namedexpr": visitor.namedexprs,
        # "binop": visitor.binops,
        # "unaryop": visitor.uarynops,
        # "lambda": visitor.lambdas,
        # "ifexp": visitor.ifexps,
        # "dict": visitor.dicts,
        # "set": visitor.sets,
        # "listcomp": visitor.listcomps,
        # "setcomp": visitor.setcomps,
        # "dictcomp": visitor.dictcomps,
        # "generatorexp": visitor.generatorexps,
        # "await": visitor.awaits,
        # "yield": visitor.yields,
        # "yieldfrom": visitor.yieldfroms,
        # "comparison": visitor.comparisons,
        # "call": visitor.calls,
        # "formattedvalue": visitor.formattedvalues,
        # "joinedstr": visitor.joinedstrs,
        # "constant": visitor.constats,
        # "attribute": visitor.attribuetes,
        # "subscript": visitor.subscripts,
        # "starred": visitor.starreds,
        # "name": visitor.names,
        # "list": visitor.lists,
        # "tuple": visitor.tuples,
        # "slice": visitor.slices,
        # "load": visitor.loads,
        # "store": visitor.stores,
        # "del": visitor.dels,
        # "and": visitor.ands,
        # "or": visitor.ors,
        # "add": visitor.adds,
        # "sub": visitor.subs,
        # "mult": visitor.mults,
        # "matmult": visitor.matmults,
        # "div": visitor.divs,
        # "mod": visitor.mods,
        # "pow": visitor.pows,
        # "lshift": visitor.lshifts,
        # "rshift": visitor.rshifts,
        # "bitor": visitor.bitors,
        # "bitxor": visitor.bitxors,
        # "bitand": visitor.bitands,
        # "floordiv": visitor.floordivs,
        # "invert": visitor.inverts,
        # "not": visitor.nots,
        # "uadd": visitor.uaddss,
        # "usub": visitor.usubss,
        # "eq": visitor.eqss,
        # "not_eq": visitor.not_eqss,
        # "lt": visitor.lts,
        # "lte": visitor.ltes,
        # "gt": visitor.gts,
        # "gte": visitor.gtes,
        # "is": visitor.iss,
        # "isnot": visitor.isnots,
        # "in": visitor.ins,
        # "notin": visitor.notins,
        # "excepthandler": visitor.excepthandlers,
        # "matchvalue": visitor.matchvalues,
        # "matchsingleton": visitor.matchsingleton,
        # "matchsequence": visitor.matchsequences,
        # "matchmapping": visitor.matchmappings,
        # "matchclass": visitor.matchclasses,
        # "matchstar": visitor.matchstars,
        # "matchas": visitor.matchases,
        # "machor": visitor.machors,
        # "typeignore": visitor.typeignores,
        # "typevar": visitor.typevars,
        # "paramspec": visitor.paramspecs,
        # "typevartuple": visitor.typevartuples,
        # "relation": visitor.relations,
        "variables": {"color": "#009999", "shape": "rectangle"},
        "module": {"color": "#ffff99", "shape": "rectangle"},
        "default": {"color": "#0c0c44", "shape": "circle"},
    }

    edge_styles = {
        "inheritance": {"color": "#990066", "line_style": "solid"},
        "import": {"color": "#005500", "line_style": "dashed"},
        "variable": {"color": "#000055", "line_style": "dotted"},
        "function": {"color": "#550000", "line_style": "dotted"},
        "default": {"color": "#000000", "line_style": "dotted"},
    }

    for node, data in graph.nodes(data=True):
        node_type = data.get("type", "default")
        style = node_styles.get(node_type.lower(), node_styles["default"])
        data.update(style)
        data["opacity"] = 0.5

    for _, _, data in graph.edges(data=True):
        edge_type = data.get("type", "default")
        style = edge_styles.get(edge_type, edge_styles["default"])
        data.update(style)

    return graph
