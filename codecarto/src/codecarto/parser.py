import ast
import networkx as nx
import os


class SourceParser(ast.NodeVisitor):
    """Parse a python source file into a networkx graph."""

    def __init__(self, file_path: str, source_files: list = None):
        """Initialize the parser.

        Parameters:
        -----------
        file_path : str
            The path to the file to parse.
        source_files : set
            A set of source files to parse.
        """
        self.file_path: str = file_path  # The path to the file to parse
        self.graph: nx.DiGraph = nx.DiGraph()  # The graph to populate
        self.current_parent = None  # To track the current parent node

        # Create root and python graphs
        # root is the representation of the process. It is the parent of all.
        # root will be a catch-all for top-level objects.
        # python is the representation of the python language. It is the parent of all python objects.
        # python will be a catch-all for all python objects that are not explicitly defined.
        # An edge exists from root to python.
        self.root: nx.DiGraph = nx.DiGraph(name="root")
        self.python: nx.DiGraph = nx.DiGraph(name="python")
        self.graph.add_node(
            id(self.root), type="Module", label="root", base="module", parent=None
        )
        self.graph.add_node(
            id(self.python), type="Module", label="python", base="module", parent="root"
        )
        self.graph.add_edge(id(self.root), id(self.python))

        # Keep track of parsed files
        self.parsed_files: list = []
        self.source_files: list = source_files or []

        # Parse the code & package files
        self.parse_code(file_path)

    def parse_code(self, file_path) -> nx.DiGraph:
        """Parse the code in the specified file path.

        Parameters:
        -----------
        file_path : str
            The path to the file to parse.
        """
        # Check if the file has already been parsed
        if file_path in self.parsed_files:
            return
        # Add the file to the parsed files
        self.parsed_files.append(file_path)
        # Parse the code
        print(f"Parsing: {file_path}")
        with open(file_path, "r") as f:
            source = f.read()
        tree = ast.parse(source)
        self.current_parent = self.root
        self.visit(tree)
        return self.graph

    def parse_package_files(self):
        """Parse all the files in the package."""
        for root, _, files in os.walk(self.package_root):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    self.parse_code(file_path)

    def get_imported_file_path(self, import_name) -> str | None:
        """Get the path to the file containing the imported module.

        Parameters:
        -----------
        import_name : str
            The name of the imported module.

        Returns:
        --------
        str|None
            The path to the file containing the imported module.
            None if the file is not found.
        """
        for file_path in self.source_files:
            file_name = os.path.basename(file_path)[:-3]  # Remove the .py extension
            if file_name == import_name:
                return file_path
        return None

    def create_node(self, node, type: str, label: str, base: str):
        """Creates a node and adds it to the graph.

        Parameters:
        ----------
        node : ast.AST
            The node to create.
        type : str
            The type of the node.
        label : str
            The label of the node.
        base : str
            The base of the node.
        """
        self.graph.add_node(
            id(node), type=type, label=label, base=base, parent=id(self.current_parent)
        )
        self.graph.add_edge(id(self.current_parent), id(node))

    # TODO: noticing a pattern here. Noting for future refactoring.
    # visits look like they can be broken down into 4 visits so far.
    # 1. visits without a parent, or the node is the top-level parent
    # 2. visits with a parent
    # 3. visits with multiple aliases
    # 4. visits with multiple targets

    def visit_Module(self, node: ast.Module):
        """Visit the module node.

        Parameters:
        -----------
        node : ast.Module
            The module node to visit.
        """
        # TODO: it looks like the current parent is None before create node is called
        # and then the current parent is set to the node id after create node is called
        # when is the current parent set to None again for other Module visits?
        # Does SourceParser.__init__ get called for each visit?
        self.create_node(node, "Module", os.path.basename(self.file_path), "module")
        self.current_parent = id(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit the class definition node.

        Parameters:
        -----------
        node : ast.ClassDef
            The class definition node to visit.
        """
        self.create_node(node, "ClassDef", node.name, "class")
        old_parent = self.current_parent
        self.current_parent = id(node)
        self.generic_visit(node)
        self.current_parent = old_parent

    def visit_FunctionDef(self, node : ast.FunctionDef):
        """Visit the function definition node.

        Parameters:
        -----------
        node : ast.FunctionDef
            The function definition node to visit.
        """
        self.create_node(node, "FunctionDef", node.name, "function")
        old_parent = self.current_parent
        self.current_parent = id(node)
        self.generic_visit(node)
        self.current_parent = old_parent

    def visit_Import(self, node : ast.Import):
        """Visit the import node.

        Parameters:
        -----------
        node : ast.Import
            The import node to visit.
        """
        # for alias in node.names:
        #     self.create_node(node, "Import", alias.name, "import")
        #     self.graph.add_edge(id(self.current_parent), id(node))
        for alias in node.names:
            imported_file_path = self.get_imported_file_path(alias.name)
            if (
                imported_file_path
                and imported_file_path not in self.parsed_files
                and imported_file_path in self.source_files
            ):
                imported_parser = SourceParser(imported_file_path, self.source_files)
                self.graph: nx.DiGraph = nx.compose(self.graph, imported_parser.graph)
                self.graph.add_edge(id(self.current_parent), id(imported_parser.root))
            self.create_node(node, "Import", alias.name, "import")
            self.graph.add_edge(id(self.current_parent), id(node))

    def visit_ImportFrom(self, node : ast.ImportFrom):
        """Visit the import from node.

        Parameters:
        -----------
        node : ast.ImportFrom
            The import from node to visit.
        """
        # for alias in node.names:
        #     self.create_node(node, "ImportFrom", alias.name, "import_from")
        #     self.graph.add_edge(id(self.current_parent), id(node))
        for alias in node.names:
            imported_file_path = self.get_imported_file_path(node.module)
            if (
                imported_file_path
                and imported_file_path not in self.parsed_files
                and imported_file_path in self.source_files
            ):
                imported_parser = SourceParser(imported_file_path, self.source_files)
                self.graph: nx.DiGraph = nx.compose(self.graph, imported_parser.graph)
                self.graph.add_edge(id(self.current_parent), id(imported_parser.root))
            self.create_node(node, "ImportFrom", alias.name, "import_from")
            self.graph.add_edge(id(self.current_parent), id(node))

    def visit_Assign(self, node : ast.Assign):
        """Visit the assignment node.

        Parameters:
        -----------
        node : ast.Assign
            The assignment node to visit.
        """
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.create_node(node, "var", target.id, "var")
                self.graph.add_edge(id(self.current_parent), id(node))

    def generic_visit(self, node: ast.AST):
        """Visit a node generically.

        Parameters:
        -----------
        node : ast.AST
            The node to visit.
        """ 
        super(SourceParser, self).generic_visit(node)
