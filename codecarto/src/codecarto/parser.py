import ast
import networkx as nx
import os


class SourceParser(ast.NodeVisitor):
    def __init__(self, file_path):
        self.graph = nx.DiGraph()
        self.file_path = file_path
        self.current_parent = None

        # Create root and python graphs
        self.graph.add_node(
            "root", type="Module", label="root", base="module", parent=None
        )
        self.graph.add_node(
            "python", type="Module", label="python", base="module", parent="root"
        )
        self.graph.add_edge("root", "python")

        self._graph = self.parse_code(file_path)

    def create_node(self, node, type, label, base):
        self.graph.add_node(
            id(node), type=type, label=label, base=base, parent=self.current_parent
        )
        self.graph.add_edge(self.current_parent, id(node))

    def parse_code(self, file_path):
        with open(file_path, "r") as f:
            source = f.read()
        tree = ast.parse(source)
        self.current_parent = "root"
        self.visit(tree)
        return self.graph

    def visit_Module(self, node):
        self.create_node(node, "Module", os.path.basename(self.file_path), "module")
        self.current_parent = id(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.create_node(node, "ClassDef", node.name, "class")
        old_parent = self.current_parent
        self.current_parent = id(node)
        self.generic_visit(node)
        self.current_parent = old_parent

    def visit_FunctionDef(self, node):
        self.create_node(node, "FunctionDef", node.name, "function")
        old_parent = self.current_parent
        self.current_parent = id(node)
        self.generic_visit(node)
        self.current_parent = old_parent

    def visit_Import(self, node):
        for alias in node.names:
            self.create_node(node, "Import", alias.name, "import")
            self.graph.add_edge(self.current_parent, id(node))

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.create_node(node, "ImportFrom", alias.name, "import_from")
            self.graph.add_edge(self.current_parent, id(node))

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.create_node(node, "var", target.id, "var")
                self.graph.add_edge(self.current_parent, id(node))

    def generic_visit(self, node):
        super(SourceParser, self).generic_visit(node)
