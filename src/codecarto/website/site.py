import os
import mpld3
from mpld3 import plugins, utils

import networkx as nx
from networkx import DiGraph
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

from ..parser.parser import Parser
from ..plotter.plotter import Plotter
from ..plotter.palette import Palette
from ..config.directory.package_dir import PROCESSOR_FILE_PATH
import matplotlib.pyplot as plt
from matplotlib import image, patches, colors
from matplotlib.colors import colorConverter
import numpy as np
import mpld3


def test_site():
    imsize = np.array([319, 217])
    center = [108.5, 108.5]
    max_radius = 108.5
    radii = np.linspace(16, max_radius, 5)
    angles = np.arange(0, 360, 45)

    fig = plt.figure(figsize=imsize / 50.0)
    ax = fig.add_axes([0, 0, 1, 1], frameon=False, xticks=[], yticks=[])

    # Create a clip path for the elements
    clip_path = patches.Rectangle((0, 0), imsize[0], imsize[1], transform=ax.transData)

    # Create the background gradient
    x = np.array([0, 104, 196, 300])
    y = np.linspace(150, 450, 86)[:, None]

    c = np.cos(-np.pi / 4)
    s = np.sin(-np.pi / 4)
    X, Y = (c * x - s * y) - 116, (s * x + c * y)
    C = np.arange(255).reshape((3, 85)).T
    C = C[::-1, :]
    cmap = colors.LinearSegmentedColormap.from_list(
        "mpld3",
        [
            [0.97, 0.6, 0.29],
            [0.97, 0.59, 0.27],
            [0.97, 0.58, 0.25],
            [0.95, 0.44, 0.34],
            [0.92, 0.51, 0.29],
            [0.68, 0.21, 0.20],
        ],
    )
    mesh = ax.pcolormesh(X, Y, C, cmap=cmap, shading="auto", zorder=0)
    mesh.set_clip_path(clip_path)

    # cut-off the background to form the "D" and "3" using white patches
    # (this could also be done with a clip path)
    kwargs = dict(fc="white", ec="none", zorder=1)
    ax.add_patch(patches.Rectangle([0, 0], center[0], imsize[1], **kwargs))

    ax.add_patch(patches.Circle(center, radii[2], **kwargs))
    ax.add_patch(patches.Wedge(center, 127, -90, 90, width=18.5, **kwargs))

    ax.add_patch(patches.Circle((252, 66), 18, **kwargs))
    ax.add_patch(patches.Rectangle([216, 48], 36, 36, **kwargs))
    ax.add_patch(patches.Wedge((252, 66), 101, -90, 40.1, width=35, **kwargs))

    ax.add_patch(patches.Circle((252, 151), 18, **kwargs))
    ax.add_patch(patches.Rectangle([216, 133], 36, 36, **kwargs))
    ax.add_patch(patches.Wedge((252, 151), 101, -40.1, 90, width=35, **kwargs))

    ax.add_patch(patches.Rectangle([-200, -200], 719, 200, **kwargs))
    ax.add_patch(patches.Rectangle([-200, -200], 200, 617, **kwargs))
    ax.add_patch(patches.Rectangle([-200, imsize[1]], 719, 200, **kwargs))
    ax.add_patch(patches.Rectangle([imsize[0], -200], 200, 617, **kwargs))

    # plot circles and lines
    for radius in radii:
        ax.add_patch(
            patches.Circle(center, radius, lw=0.5, ec="gray", fc="none", zorder=2)
        )
    for angle in angles:
        dx, dy = np.sin(np.radians(angle)), np.cos(np.radians(angle))
        ax.plot(
            [max_radius * (1 - dx), max_radius * (1 + dx)],
            [max_radius * (1 - dy), max_radius * (1 + dy)],
            "-",
            color="gray",
            lw=0.5,
            zorder=2,
        )

    # plot wedges within the graph
    wedges = [
        (98, 231, 258, "#FF6600"),
        (85, 170, 205, "#FFC500"),
        (60, 80, 103, "#7DFF78"),
        (96, 45, 58, "#FD7C1A"),
        (73, 291, 308, "#CCFF28"),
        (47, 146, 155, "#28FFCC"),
        (25, 340, 360, "#004AFF"),
    ]

    for radius, theta1, theta2, color in wedges:
        ax.add_patch(
            patches.Wedge(
                center,
                radius,
                theta1,
                theta2,
                fc=color,
                ec="black",
                alpha=0.6,
                zorder=3,
            )
        )

    for patch in ax.patches:
        patch.set_clip_path(clip_path)

    ax.set_xlim(0, imsize[0])
    ax.set_ylim(imsize[1], 0)

    # plt.savefig('mpld3.png')
    mpld3.show()


async def site():
    from ..plotter.plotter import Plotter

    file_path: str = PROCESSOR_FILE_PATH
    print(file_path)
    parser: Parser = Parser(source_files=[file_path])
    data: DiGraph = parser.graph
    plotter = Plotter()
    plotter.grid = True
    plotter.json = False
    plotter.file_path = file_path
    plotter.api = True
    plotter.show_plot = True

    if data:
        pl = await plotter.plot(graph=data)
        # pl = await plot(data, grid=True, json=False, show=True)
        # print(pl)

        # fig = plt.figure(figsize=50.0)
        # ax = fig.add_axes([0, 0, 1, 1], frameon=False, xticks=[], yticks=[])

        # # Initialize figure, axes (w, h), title, and position on monitor
        # fig, ax = plt.subplots(figsize=(15, 15))
        # fig.canvas.manager.window.wm_geometry("+0+0")
        # _title: str = f"Spiral Layout"
        # _file_name: str = os.path.basename(file_path)
        # _title = f"{_title} for '{_file_name}'"
        # ax.set_title(_title)
        # ax.axis("off")

        # # Collect nodes and their attributes
        # palette: Palette = Palette()
        # node_styles = palette.get_node_styles()
        # node_data: dict[str, list] = {node_type: [] for node_type in node_styles.keys()}
        # unique_node_types = set()
        # for _, node_type in data.nodes(data="type"):
        #     if node_type is not None:
        #         unique_node_types.add(node_type)
        # for n, a in data.nodes(data=True):
        #     node_type = a.get("type", "Unknown")
        #     if node_type not in node_styles.keys():
        #         node_type = "Unknown"
        #     node_data[node_type].append(n)
        # try:
        #     from ..plotter.positions import Positions

        #     layout_pos = Positions(
        #         include_networkx=True,
        #         include_custom=False,
        #     )
        #     pos = layout_pos.get_positions("spiral_layout", **data)
        # except Exception as e:
        #     print()  # needs an extra line
        # # draw nodes

        # for node_type, nodes in node_data.items():
        #     nx.drawing.draw_networkx_nodes(
        #         data,
        #         pos,
        #         nodelist=nodes,
        #         node_color=node_styles[node_type]["color"],
        #         node_shape=node_styles[node_type]["shape"],
        #         node_size=node_styles[node_type]["size"],
        #         alpha=node_styles[node_type]["alpha"],
        #     )

        #     # Draw edges
        #     nx.drawing.draw_networkx_edges(data, pos, alpha=0.2)

        #     # Draw legend
        #     _colors: dict = {}
        #     _shapes: dict = {}
        #     for node_type in unique_node_types:
        #         _colors[node_type] = node_styles[node_type]["color"]
        #         _shapes[node_type] = node_styles[node_type]["shape"]
        #     legend_elements = [
        #         mlines.Line2D(
        #             [0],
        #             [0],
        #             color=color,
        #             marker=shape,
        #             linestyle="None",
        #             markersize=10,
        #             label=theme,
        #         )
        #         for theme, color, shape in zip(
        #             _colors, _colors.values(), _shapes.values()
        #         )
        #     ]
        #     ax.legend(handles=legend_elements, loc="upper right", fontsize=10)

        # # Here we connect the linked brush plugin
        # plugins.connect(fig)

        # mpld3.show()
    else:
        print("No data found.")
