import networkx as nx
from models.graph_data import GraphBase
from models.plot_data import PlotOptions, Palette, RawData
from notebooks.notebook import run_notebook
from services.palette_service import apply_styles
from util.utilities import Log


class PlotterService:

    @staticmethod
    async def plot_nx_graph(graph_name: str, graph: nx.DiGraph, options: PlotOptions):
        Log.pprint("######################  GRAPH  ######################")
        Log.pprint(graph.nodes(data=True))

        return await run_notebook(
            graph_name=graph_name,
            graph=apply_styles(graph),
            title=options.layout,
            type=options.type,
        )

    @staticmethod
    def plot_raw_json(graph: RawData, palette: Palette, options: PlotOptions):
        return "plotting"

    @staticmethod
    def plot_graphbase(graph: GraphBase, palette: Palette, options: PlotOptions):
        return "plotting"
