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

    # Check if graph provided
    if not graph:
        raise NotebookError(
            "run_notebook",
            {"graph_name": graph_name, "graph": graph},
            "No graph provided",
        )

    # Set and scale up the postiions
    pos = Plotter.get_node_positions(graph, f"{title.lower()}_layout")
    for id, (x, y) in pos.items():
        node = graph.nodes[id]
        node["x"] = float(x) * 100
        node["y"] = float(y) * 100

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