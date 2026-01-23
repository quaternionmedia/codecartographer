import networkx as nx

from codecarto.models.source_data import Directory, Folder, File
from codecarto.services.github_service import get_raw_from_url
from codecarto.services.parsers.ASTs.python_custom_ast import PythonCustomAST
from codecarto.services.parsers.python.directory_parser import DirectoryParser
from codecarto.services.parsers.python.dependency_parser import DependencyParser


class ParserService:

    @staticmethod
    async def parse_local_directory(path: str) -> Directory:
        """Read a local directory from filesystem and convert to Directory model"""
        from pathlib import Path
        import os

        dir_path = Path(path)

        def read_directory_recursive(directory: Path) -> Folder:
            """Recursively read directory structure"""
            files = []
            folders = []

            for item in directory.iterdir():
                if item.is_file():
                    # Read file content (only for Python files for now)
                    if item.suffix == '.py':
                        try:
                            with open(item, 'r', encoding='utf-8') as f:
                                raw_content = f.read()
                            files.append(File(
                                url=str(item),
                                name=item.name,
                                size=item.stat().st_size,
                                raw=raw_content
                            ))
                        except (UnicodeDecodeError, PermissionError):
                            # Skip files that can't be read
                            pass

                elif item.is_dir():
                    # Recursively read subdirectory
                    subfolder = read_directory_recursive(item)
                    folders.append(subfolder)

            folder_size = sum(f.size for f in files) + sum(f.size for f in folders)
            return Folder(
                name=directory.name,
                size=folder_size,
                files=files,
                folders=folders
            )

        root_folder = read_directory_recursive(dir_path)
        total_size = root_folder.size

        from codecarto.models.source_data import RepoInfo
        return Directory(
            info=RepoInfo(owner="local", name=dir_path.name, url=str(dir_path)),
            size=total_size,
            root=root_folder
        )

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
    async def parse_code_directory(directory: Directory) -> nx.DiGraph:
        """Parse entire directory using AST (code structure) parser"""
        parser = PythonCustomAST()
        # Use the root folder from directory structure
        root_folder = directory.root
        graph = parser.parse(root_folder)
        graph.name = directory.info.name
        return graph

    @staticmethod
    async def parse_directory(directory: Directory) -> nx.DiGraph:
        """Parse directory structure (filesystem hierarchy)"""
        dir_parser = DirectoryParser()
        graph = dir_parser.parse(directory)
        graph.name = directory.info.name
        return graph

    @staticmethod
    async def parse_dependancy(directory: Directory) -> nx.DiGraph:
        """Parse dependencies (import relationships)"""
        dep_parser = DependencyParser()
        graph = dep_parser.parse(directory)
        graph.name = directory.info.name
        return graph
