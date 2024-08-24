from models.graph_data import GraphBase
from models.plot_data import DefaultPalette, Palette


class DatabaseContext:
    @staticmethod
    async def fetch_graph_by_id(graph_id: str) -> GraphBase:
        # Placeholder for DB fetch logic
        return GraphBase()

    @staticmethod
    async def fetch_palette_by_id(palette_id: str) -> Palette:
        # Placeholder for DB fetch logic
        return DefaultPalette
