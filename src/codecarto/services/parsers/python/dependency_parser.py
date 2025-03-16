# this will go through a directory,
# gather an import reference book and
# create a graph with nodes representing
# files and folders and edges between those
# that import each other

import ast
import sys
import networkx as nx
import importlib.util
from models.source_data import Directory, Folder, File


class DependencyParser:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.import_reference_book: dict[str, dict[str, list[str]]] = {}
        self.file_name_to_id: dict[str, str] = {}

    def parse(self, directory: Directory, remove_detached: bool = True) -> nx.DiGraph:
        """Parse a directory and return a dependency graph."""
        self._parse_folder(directory.root, "Root")
        self._create_import_edges()
        self._attach_detached_nodes()

        if remove_detached:
            self._remove_detached_nodes()

        return self.graph

    def _parse_folder(self, folder: Folder, parent: str):
        folder_id = self._add_folder_node(folder, parent)
        for item in folder.files + folder.folders:
            if isinstance(item, Folder):
                self._parse_folder(item, folder_id)
            elif isinstance(item, File):
                self._parse_file(item, folder_id)

    def _parse_file(self, file: File, parent: str):
        file_id = self._add_file_node(file, parent)

        # Compute the module name based on folder structure
        folder_path = self._get_folder_path(parent)
        module_name = f"{folder_path}.{file.name}" if folder_path else file.name

        self.file_name_to_id[module_name] = file_id
        if file.name.endswith(".py"):
            self.import_reference_book[file_id] = self._get_imports(file)

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
        return file_id

    def _get_folder_path(self, folder_id: str) -> str:
        path = []
        while folder_id and folder_id in self.graph.nodes:
            node = self.graph.nodes[folder_id]
            if "label" in node:
                path.insert(0, node["label"])
            folder_id = node.get("parent", None)
        return ".".join(path)

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
                found = False  # Track if we found a matching project file

                # 1️⃣ Check if module is a project file and connect it
                for other_module, other_id in self.file_name_to_id.items():
                    if other_module.endswith(".py") and (
                        other_module == module or other_module.endswith(f".{module}.py")
                    ):
                        self.graph.add_edge(file_id, other_id, imports=imported)
                        found = True  # Mark as resolved

                # 2️⃣ If not found in project, check if it's an external module
                if not found and self._is_external_module(module):
                    external_node = f"external.{module}"
                    if external_node not in self.graph:
                        self.graph.add_node(
                            external_node, type="external", label=module
                        )

                    self.graph.add_edge(file_id, external_node, imports=imported)

        return self.graph

    def _is_external_module(self, module: str) -> bool:
        """
        Determines if a module is external (not part of the project).
        It checks against:
        - Python standard library modules
        - Installed third-party packages (via importlib)
        """
        if module in sys.builtin_module_names:
            return True  # Standard library (e.g., "sys", "json")

        if importlib.util.find_spec(module) is not None:
            return True  # Third-party package (e.g., "pydantic", "fastapi")

        return False  # Project file

    def _attach_detached_nodes(self):
        """Find all nodes with no edges and attach them to a 'detached' node for debugging."""
        detached_nodes = {
            node
            for node in self.graph.nodes
            if not self.graph.in_edges(node) and not self.graph.out_edges(node)
        }

        if detached_nodes:
            self.graph.add_node("detached", type="debug", label="Detached Nodes")
            for node in detached_nodes:
                self.graph.add_edge("detached", node, relation="orphan")

    def _remove_detached_nodes(self):
        """Remove the 'detached' node and all orphan nodes it was connected to."""
        if "detached" in self.graph:
            # Get all nodes connected to "detached"
            orphan_nodes = list(self.graph.successors("detached"))

            # Remove orphan nodes first
            self.graph.remove_nodes_from(orphan_nodes)

            # Remove "detached" node itself
            self.graph.remove_node("detached")
