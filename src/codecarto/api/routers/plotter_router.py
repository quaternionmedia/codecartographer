from fastapi import APIRouter
from codecarto import GraphData, Plotter, PolyGraph

router: APIRouter = APIRouter()
GraphPlotter: Plotter = Plotter()


@router.get("/plotter/plot")
async def plot(
    graph_data: GraphData, layout: str = "", _grid: bool = False, _json: bool = False
) -> str:
    """Plots a networkx graph.

    Args:
    -----
        graph_data (nx.DiGraph): The networkx graph to plot.
        layout (str): The layout to use for the plot.
        _grid (bool): Whether or not plot all layouts in a grid.
        _json (bool): Whether or not to return the json data.

    Returns:
    --------
        str: The output directory of the plots.
    """
    if graph_data is None:
        raise ValueError("No graph data provided.")
    else:
        # Convert the GraphData object to a networkx graph
        graph = PolyGraph.convert_to_nx(graph_data)
        # Set the plotter options
        Plotter.do_grid = _grid
        Plotter.do_json = _json
        # Plot the graph
        Plotter.plot(graph, layout)
        # Return the output directory of the plots
        return Plotter.dirs["output_dir"]


# # This is for local CLI use only
# @router.get("/plotter/set_output_dir")
# async def set_output_dir(output_dir: str) -> None:
#     """Sets the plot output directory.

#     Parameters:
#     -----------
#         output_dir (str) Default = None:
#             The directory to use.
#     """
#     Plotter.set_plot_output_dir(output_dir)


# # This is for local CLI use only
# @router.get("/plotter/reset_output_dir")
# def reset_plot_output_dir():
#     """Resets the plot output directory to the default output directory."""
#     Plotter.reset_plot_output_dir()


# # This is for local lib use only
# # Not used in typical use cases. All other methods are available
# # through the returned Plotter object.
# @router.get("/plotter/new")
# async def new(
#     dirs: dict[str, str] = None,
#     file_path: str = "",
#     do_labels: bool = False,
#     do_grid: bool = False,
#     do_json: bool = False,
#     do_show: bool = False,
#     do_single_file: bool = False,
#     do_ntx: bool = True,
#     do_custom: bool = True,
# ) -> Plotter:
#     """Returns a new Plotter object to use in projects."""
#     return Plotter(
#         dirs,
#         file_path,
#         do_labels,
#         do_grid,
#         do_json,
#         do_show,
#         do_single_file,
#         do_ntx,
#         do_custom,
#     )
