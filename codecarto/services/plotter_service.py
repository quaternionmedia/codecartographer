import networkx as nx

from codecarto.models.graph_data import GraphBase
from codecarto.models.plot_data import PlotOptions, Palette, RawData
from codecarto.notebooks.notebook import run_notebook
from codecarto.services.palette_service import apply_styles
from codecarto.util.utilities import Log


class PlotterService:

    @staticmethod
    async def plot_nx_graph(
        graph_name: str,
        graph: nx.DiGraph,
        options: PlotOptions,
        isDependencyPlot: bool = False,
    ):
        Log.pprint("######################  NODES  ######################")
        Log.pprint(graph.nodes(data=True))
        Log.pprint("######################  EDGES  ######################")
        Log.pprint(graph.edges(data=True))

        return await run_notebook(
            graph_name=graph_name,
            graph=apply_styles(graph),
            title=options.layout,
            type=options.type,
            isDependencyPlot=isDependencyPlot,
        )

    @staticmethod
    def plot_raw_json(graph: RawData, palette: Palette, options: PlotOptions):
        return "plotting"

    @staticmethod
    def plot_graphbase(graph: GraphBase, palette: Palette, options: PlotOptions):
        return "plotting"
