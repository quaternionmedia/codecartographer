# this will go through a directory,
# gather an import reference book and
# create a graph with
# nodes representing files and folders and
# edges between those that import each other

import ast
import networkx as nx
from models.source_data import Directory, Folder, File


class DirectoryParser:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.import_reference_book: dict[str, dict[str, list[str]]] = {}
        self.file_name_to_id: dict[str, str] = {}

    def parse(self, directory: Directory) -> nx.DiGraph:
        """Parse a directory and return a graph with nodes representing
        files and folders and edges between those that import each other"""
        self._parse_folder(directory.root, "Root")
        self._create_import_edges()
        return self.graph

    def _parse_folder(self, folder: Folder, parent: str):
        folder_id = self._add_folder_node(folder, parent)
        # print(f"Parsing folder: {folder.name} (Parent: {parent}, ID: {folder_id})")
        for item in folder.files + folder.folders:
            if isinstance(item, Folder):
                self._parse_folder(item, folder_id)
            elif isinstance(item, File):
                self._parse_file(item, folder_id)

    def _parse_file(self, file: File, parent: str):
        file_id = self._add_file_node(file, parent)
        # print(f"Parsing file: {file.name} (Parent: {parent}, ID: {file_id})")
        self.file_name_to_id[file.name] = file_id
        if file.name.endswith(".py"):
            self.import_reference_book[file_id] = self._get_imports(file)

    def _add_folder_node(self, folder: Folder, parent: str) -> str:
        """Add a folder node to the graph"""
        folder_id = f"folder_{folder.name}_{id(folder)}"  # Use unique ID based on name and memory ID
        self.graph.add_node(
            folder_id,
            type="default",
            label=folder.name,
            parent=parent,
        )

        if parent:
            # print(f"Adding edge from {parent} to {folder_id}")
            self.graph.add_edge(parent, folder_id)

        return folder_id

    def _add_file_node(self, file: File, parent: str) -> str:
        """Add a file node to the graph"""
        file_id = (
            f"file_{file.name}_{id(file)}"  # Use unique ID based on name and memory ID
        )
        self.graph.add_node(
            file_id,
            filename=file.name,
            type="default",
            label=file.name,
            parent=parent,
        )

        if parent:
            # print(f"Adding edge from {parent} to {file_id}")
            self.graph.add_edge(parent, file_id)

        return file_id

    def _get_imports(self, file: File) -> dict[str, list[str]]:
        """Get imports from a file"""
        imports: dict[str, list[str]] = {}
        tree = ast.parse(file.raw)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):  # import module
                for alias in node.names:
                    imports[alias.name] = [alias.name]
            elif isinstance(node, ast.ImportFrom):  # from module import something
                if node.module:
                    importList = [alias.name for alias in node.names]
                    imports[node.module] = importList
        return imports

    def _create_import_edges(self):
        """Create edges between files that import each other"""
        for file_id, imports in self.import_reference_book.items():
            for module, imported in imports.items():
                # Check if the imported module is in our file_name_to_id mapping
                for other_file, other_id in self.file_name_to_id.items():
                    # Assuming module matches the filename without extension
                    if other_file.endswith(f"{module}.py"):
                        self.graph.add_edge(file_id, other_id, imports=imported)
        return self.graph
