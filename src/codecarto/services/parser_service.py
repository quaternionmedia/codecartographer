import networkx as nx

from models.source_data import Directory, Folder, File
from services.github_service import get_raw_from_url
from services.parsers.ASTs.python_custom_ast import PythonCustomAST
from services.parsers.directory_parser import DirectoryParser


class ParserService:

    @staticmethod
    async def parse_raw(url: str) -> nx.DiGraph:
        filename = url.split("/")[-1]
        raw = await get_raw_from_url(url)
        file = File(name=filename, size=0, raw=raw)
        folder = Folder(name="root", size=0, files=[file], folders=[])
        parser = PythonCustomAST()
        graph = parser.parse(folder)
        graph.name = file.name
        return graph

    @staticmethod
    async def parse_code(folder: Folder) -> nx.DiGraph:
        parser = PythonCustomAST()
        graph = parser.parse(folder)
        graph.name = folder.name
        return graph

    @staticmethod
    async def parse_directory(directory: Directory) -> nx.DiGraph:
        dir_parser = DirectoryParser()
        graph = dir_parser.parse(directory)
        graph.name = directory.info.name
        return graph
