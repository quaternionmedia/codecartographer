# this will go through a directory
# create a graph with
# nodes representing files and folders and
# edges between parents and children in the directory

import networkx as nx
from models.source_data import Directory, Folder, File


class DirectoryParser:
    def __init__(self):
        self.graph = nx.DiGraph()

    def parse(self, directory: Directory) -> nx.DiGraph:
        """Parse a directory and return a graph with nodes representing
        files and folders and edges between those that import each other"""
        self._parse_folder(directory.root, "Root")
        return self.graph

    def _parse_folder(self, folder: Folder, parent: str):
        folder_id = self._add_folder_node(folder, parent)
        for item in folder.files + folder.folders:
            if isinstance(item, Folder):
                self._parse_folder(item, folder_id)
            elif isinstance(item, File):
                self._add_file_node(item, parent)

    def _add_folder_node(self, folder: Folder, parent: str) -> str:
        """Add a folder node to the graph"""
        # Use unique ID based on name and memory ID
        folder_id = f"folder_{folder.name}_{id(folder)}"
        self.graph.add_node(
            folder_id,
            type="default",
            label=folder.name,
            parent=parent,
        )

        if parent:
            print(f"Adding edge from {parent} to {folder_id}")
            self.graph.add_edge(parent, folder_id)

        return folder_id

    def _add_file_node(self, file: File, parent: str) -> str:
        """Add a file node to the graph"""
        # Use unique ID based on name and memory ID
        file_id = f"file_{file.name}_{id(file)}"
        self.graph.add_node(
            file_id,
            filename=file.name,
            type="default",
            label=file.name,
            parent=parent,
        )

        if parent:
            print(f"Adding edge from {parent} to {file_id}")
            self.graph.add_edge(parent, file_id)

        return file_id
