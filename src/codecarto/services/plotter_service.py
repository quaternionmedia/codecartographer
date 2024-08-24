from models.graph_data import GraphBase
from models.plot_data import PlotOptions, Palette, RawData


class PlotterService:
    @staticmethod
    def plot_raw(graph: RawData, palette: Palette, options: PlotOptions):
        return

    @staticmethod
    def plot_graph(graph: GraphBase, palette: Palette, options: PlotOptions):
        return "plotting"
