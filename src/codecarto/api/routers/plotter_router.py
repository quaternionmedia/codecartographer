import networkx as nx
import matplotlib.pyplot as plt
import mpld3
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates

# import redis

# from ..depends import get_redis_conn

PlotterRoute: APIRouter = APIRouter()
templates = Jinja2Templates(directory="src/codecarto/api/static/templates")


@PlotterRoute.get(
    "/plot",
)
async def plot(
    request: Request,
    # redis_conn: redis.StrictRedis = Depends(get_redis_conn),
    grid: bool = False,
):
    from ...polygraph.polygraph import PolyGraph
    from ...plotter.palette import Palette

    # Make sure to clear the cancel flag at the start of a new plotting task
    # redis_conn.delete("plotting_cancel_flag")

    grid_test = grid
    labels_test = False
    output: str = "Output: <br> "

    # Load the graph
    file_path: str = "src/codecarto/api/static/parse_files/graph_data.json"
    poly: PolyGraph = PolyGraph()
    graph: nx.Graph = poly.json_file_to_graph(file_path)

    # Collect nodes and their attributes
    pal: Palette = Palette()
    node_styles = pal.get_node_styles()
    node_data: dict[str, list] = {node_type: [] for node_type in node_styles.keys()}
    for n, a in graph.nodes(data=True):
        node_type = a.get("type", "Unknown")
        if node_type not in node_styles.keys():
            node_type = "Unknown"
        node_data[node_type].append(n)

    output += f"Starting plot. Do grid? {grid_test} <br> "
    if not grid_test:
        # Create a simple plot
        output += f"Number of nodes: {graph.number_of_nodes()} <br>"
        fig, ax = plt.subplots(figsize=(5, 5))
        fig.canvas.manager.window.wm_geometry("+0+0")
        _title: str = f"Spiral Layout"
        _file_name: str = "graph_data.json"
        _title = f"{_title} for '{_file_name}'"
        ax.set_title(_title)
        ax.axis("off")
        pos = nx.spiral_layout(graph)

        # Draw Nodes with positions and styles
        for node_type, nodes in node_data.items():
            nx.drawing.draw_networkx_nodes(
                graph,
                pos,
                nodelist=nodes,
                node_color=node_styles[node_type]["color"],
                node_shape=node_styles[node_type]["shape"],
                node_size=node_styles[node_type]["size"],
                alpha=node_styles[node_type]["alpha"],
            )
    else:
        import math
        import matplotlib.lines as mlines
        from ...plotter.positions import Positions

        # compute grid
        posi: Positions = Positions()
        layouts = posi.get_layouts()
        num_layouts = len(layouts)
        output += f"Number of layouts: {num_layouts} <br> "
        grid_size = math.ceil(math.sqrt(num_layouts))

        # Set the figure size
        figsize = (5, 5)
        fig, axes = plt.subplots(
            grid_size,
            grid_size,
            figsize=(figsize[0] * grid_size, figsize[1] * grid_size),
        )
        fig.set_size_inches(5, 5)

        # Set the figure position to the top-left corner of the screen plus the margin
        mng = plt.get_current_fig_manager()
        mng.window.wm_geometry("+0+0")

        # Loop through all layouts
        idx = 0

        for layout_name, layout_info in layouts.items():
            # Inside the loop or appropriate place in your plotting code
            # cancel_flag = redis_conn.get("plotting_cancel_flag")
            # if cancel_flag:
            #     # Handle cancellation, e.g., clean up and return a response
            #     output += "Plotting canceled by user."
            #     return templates.TemplateResponse(
            #         "plot.html", {"request": request, "output": output}
            #     )

            output += f"Layout name: {layout_name} <br> "
            layout, layout_params = layout_info

            # Set up ax
            ax = axes[idx // grid_size, idx % grid_size] if grid_size > 1 else axes
            ax.set_title(f"{layout_name}")
            ax.axis("off")

            # Collect nodes and their attributes
            node_styles = pal.get_node_styles()
            node_data: dict[str, list] = {
                node_type: [] for node_type in node_styles.keys()
            }
            for n, a in graph.nodes(data=True):
                node_type = a.get("type", "Unknown")
                if node_type not in node_styles.keys():
                    node_type = "Unknown"
                node_data[node_type].append(n)

            # Get layout parameters
            seed = -1
            layout_kwargs = {"G": graph}
            for param in layout_params:
                if param == "seed":
                    # import random

                    seed = 856  # random.randint(0, 1000)
                    layout_kwargs["seed"] = seed
                elif param == "nshells" and layout_name == "shell_layout":
                    # Group nodes by parent
                    grouped_nodes: dict[str, list] = {}
                    for node, data in graph.nodes(data=True):
                        parent = data.get("parent", "Unknown")
                        if parent not in grouped_nodes:
                            grouped_nodes[parent] = []
                        grouped_nodes[parent].append(node)

                    # Create the list of lists (shells)
                    shells = list(grouped_nodes.values())
                    layout_kwargs["nshells"] = shells
                elif param != "G":
                    # TODO: Handle other parameters here
                    pass

            # Compute Layout
            try:
                pos = posi.get_positions(layout_name, **layout_kwargs)
            except Exception as e:
                output += f"Skipping {layout_name} due to an error: {e} <br> "
                continue

            # Draw nodes with different shapes
            for node_type, nodes in node_data.items():
                nx.drawing.draw_networkx_nodes(
                    graph,
                    pos,
                    nodelist=nodes,
                    node_color=node_styles[node_type]["color"],
                    node_shape=node_styles[node_type]["shape"],
                    node_size=node_styles[node_type]["size"],
                    alpha=node_styles[node_type]["alpha"],
                    ax=ax,
                )

            # Draw edges and labels
            nx.drawing.draw_networkx_edges(graph, pos, alpha=0.2, ax=ax)
            if labels_test:
                nx.drawing.draw_networkx_labels(
                    graph,
                    pos,
                    labels=nx.classes.get_node_attributes(graph, "label"),
                    font_size=10,
                    ax=ax,
                    font_family="sans-serif",
                )

            # # Create legend
            # unique_node_types = set(
            #     node_type
            #     for _, node_type in graph.nodes(data="type")
            #     if node_type is not None
            # )
            # _colors = {
            #     node_type: node_styles[node_type]["color"]
            #     for node_type in unique_node_types
            # }
            # _shapes = {
            #     node_type: node_styles[node_type]["shape"]
            #     for node_type in unique_node_types
            # }
            # legend_elements = [
            #     mlines.Line2D(
            #         [0],
            #         [0],
            #         color=color,
            #         marker=shape,
            #         linestyle="None",
            #         markersize=10,
            #         label=theme,
            #     )
            #     for theme, color, shape in zip(_colors, _colors.values(), _shapes.values())
            # ]
            # axes.legend(handles=legend_elements, loc="upper right", fontsize=10)

            idx += 1

    output += f"Converting fig to html <br> "

    # Convert the Matplotlib plot to D3.js HTML representation
    plot_html = mpld3.fig_to_html(fig)

    output += f"Done"
    return templates.TemplateResponse(
        "plot.html",
        {
            "request": request,
            "output": output,
            "plot_html": plot_html,
            "status": "completed",
        },
    )


# @PlotterRoute.get("/cancel")
# async def cancel_plotting(redis_conn: redis.StrictRedis = Depends(get_redis_conn)):
#     redis_conn.set("plotting_cancel_flag", "1")
#     return {"status": "canceled"}
