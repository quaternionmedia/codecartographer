import networkx as nx


class NotebookError(Exception):
    """Base class for notebook exceptions."""

    def __init__(self, source, params, message):
        self.source = source
        self.params = params
        self.message = message


async def run_notebook(
    graph_name: str, graph: nx.DiGraph, title: str = "Sprial", type: str = "d3"
) -> list:
    """Extract the outputs from a notebook.

    Parameters:
    -----------
    graph_name : str
        The name of the graph to read from database.
    graph : nx.DiGraph
        The graph to plot.
    title : str
        The name of the layout to plot.
    type : str
        The type of graph to plot in the notebook.

    Returns:
    --------
    list
        The list of outputs.
    """
    import nbformat
    import gravis as gv
    from nbconvert.preprocessors import ExecutePreprocessor
    from src.plotter.plotter import Plotter
    from src.plotter.positions import Positions

    # Check if graph provided
    if not graph:
        raise NotebookError(
            "run_notebook",
            {"graph_name": graph_name, "graph": graph},
            "No graph provided",
        )

    # make possible multigraphs into a digraph
    graph = nx.DiGraph(graph)

    # Set and scale up the postiions
    plot = Plotter(graph=graph)
    pos = plot.get_node_positions(graph=graph, layout_name=f"{title.lower()}_layout")
    for id, (x, y) in pos.items():
        node = graph.nodes[id]
        node["x"] = float(x) * 100
        node["y"] = float(y) * 100

    # Scale nodes based on edges
    for node, data in graph.nodes(data=True):
        # Set size based on the number of outgoing edges
        data["size"] = (
            1 + (len(graph.out_edges(node)) * 10) + (len(graph.in_edges(node)) * 10)
        )

    # Convert the graph to gJGF for the notebook
    gJFG = gv.convert.any_to_gjgf(graph)

    # Read in the notebook
    nb_path = f"src/notebooks/gravis_{type}.ipynb"
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

        # Create a new code cell with the graph_data (g)
        param_cell = nbformat.v4.new_code_cell(f"g = {gJFG}")

        # Insert the cell at the beginning of the notebook
        nb.cells.insert(0, param_cell)

    # Execute the notebook
    ep = ExecutePreprocessor(timeout=600)
    ep.preprocess(nb, {"metadata": {"path": "src/notebooks/"}})

    # Extract the outputs
    outputs = []
    for cell in nb.cells:
        if cell.cell_type == "code":
            for output in cell.outputs:
                if output.output_type == "execute_result":
                    outputs.append(output.data)

    # Return the outputs
    return outputs
