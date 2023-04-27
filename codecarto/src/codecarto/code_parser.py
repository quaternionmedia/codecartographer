import os
import ast
import networkx as nx
from .utils.dirs import get_package_dir

code_objects = [
    "code_analyzer",
    "code_graph",
    "code_parser",
    "code_visualizer",
    "themes",
    "python",
]


class CodeParser(ast.NodeVisitor):
    """A class to parse code and create a graph from it."""

    def __init__(self, file_path: str = None):
        """Initialize the CodeParser class.

        Parameters:
        -----------
        file_path : str
            The path to the file to parse.
        """
        # parameters
        self.graph: nx.DiGraph = nx.DiGraph()
        self.current_class = None
        self.current_function = None

        # directory and file names
        if file_path:
            self.file_path = file_path
        else:
            self.file_path = self.find_module_path(file_path)
        self.src_dir = get_package_dir()
        self.module_name = os.path.splitext(os.path.basename(file_path))[0]
        self.project_root = self.src_dir

        # parse code
        tree = self.parse_code(file_path)
        self.visit(tree)

        # TODO: this should be the graph_json.json file
        # code = load_json_data(file_path)

        # graph
        _graph = self.graph
        _graph.add_node(self.module_name, node_type="module", parent=None)
        self.graph = self.add_python_node(_graph)

    def find_module_path(self, module_name: str) -> str:
        """Find the path to a module.

        Parameters:
        -----------
        module_name : str
            The name of the module for which to find the path.

        Returns:
        --------
        str
            The path to the module or None if the module was not found.
        """
        for root, _, files in os.walk(self.project_root):
            if f"{module_name}.py" in files:
                module_path = os.path.join(root, f"{module_name}.py")
                if module_path.startswith(self.project_root):
                    return module_path
        raise ValueError(
            f"Module '{module_name}' not found in project root directory: {self.project_root}"
        )

    def parse_code(self, file_path: str) -> ast.AST:
        """Parse code from a file.

        Parameters:
        -----------
        file_path : str
            The path to the file to parse.

        Returns:
        --------
        ast.AST
            The parsed code.
        """
        try:
            with open(file_path, "r") as f:
                code = f.read()
                tree = ast.parse(code)
                return tree
        except SyntaxError as e:
            raise ValueError(f"Invalid code syntax: {e}") from e

    def parse_json_data(self, json_code_data):
        """Parse code from a json data.

        Parameters:
        -----------
        json_code_data : dict
            The json code data to parse.

        Returns:
        --------
        tree
            The parsed code.
        """
        try:
            tree = ast.parse(json_code_data)
            return tree
        except SyntaxError as e:
            raise ValueError(f"Invalid code syntax: {e}") from e

    def add_python_node(self, graph):
        """Add the python node to the graph and set the parent of all nodes without a parent to the python node.

        Parameters:
        -----------
        graph : nx.DiGraph
            The graph to which to add the python node.

        Returns:
        --------
        nx.DiGraph
            The graph with the python node added.
        """
        graph.add_node("python", node_type="module", label="python", parent=None)
        # find all the nodes in G that do not have a parent
        for node in graph.nodes:
            if graph.nodes[node].get("parent") is None:
                if node not in code_objects:
                    graph.nodes[node]["parent"] = "python"
                    # check if nodes[node] has a ["label"] attribute
                    # if not, add the node (node_id) as the label
                    if graph.nodes[node].get("label") is None:
                        graph.nodes[node]["label"] = node
        return graph

    def visit_Module(self, node):
        """Visit a module node and add it to the graph.

        Parameters:
        -----------
        node : ast.Module
            The module node to visit.
        """
        self.graph.add_node(
            self.module_name, node_type="module", label=self.module_name
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Visit a class node and add it to the graph.

        Parameters:
        -----------
        node : ast.ClassDef
            The class node to visit.
        """
        self.graph.add_node(
            node.name,
            node_type="class",
            label=node.name,
            typing=node.bases,
            parent=self.module_name,
        )
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        """Visit a function node and add it to the graph.

        Parameters:
        -----------
        node : ast.FunctionDef
            The function node to visit.
        """
        parent = self.current_class if self.current_class else self.module_name
        self.graph.add_node(
            node.name, node_type="function", label=node.name, parent=parent
        )
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = None

    def visit_Assign(self, node):
        """Visit an assignment node and add it to the graph.

        Parameters:
        -----------
        node : ast.Assign
            The assignment node to visit.
        """
        parent = (
            self.current_function
            if self.current_function
            else (self.current_class if self.current_class else self.module_name)
        )
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.graph.add_node(
                    target.id, node_type="variable", label=target.id, parent=parent
                )
                self.graph.add_edge(parent, target.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        """Visit a call node and add it to the graph.

        Parameters:
        -----------
        node : ast.Call
            The call node to visit.
        """
        parent = (
            self.current_function
            if self.current_function
            else (self.current_class if self.current_class else self.module_name)
        )
        if isinstance(node.func, ast.Name):
            function_name = node.func.id
            self.graph.add_edge(parent, function_name)
        self.generic_visit(node)

    def visit_import_common(self, node, parent):
        """Visit an import node and add it to the graph.

        Parameters:
        -----------
        node : ast.Import | ast.ImportFrom
            The import node to visit.
        parent : str
            The parent of the import node.
        """
        module_name = node.module.split(".")[0]
        imported_module_path = os.path.join(self.src_dir, module_name + ".py")
        # Add the import node
        import_node_name = f"import {module_name}"
        self.graph.add_node(
            import_node_name,
            node_type="import",
            label=import_node_name,
            parent=parent,
        )
        # Connect the import node to the current function or class, if any
        self.graph.add_edge(parent, import_node_name)
        if os.path.isfile(imported_module_path):
            # Analyze the imported module and add its nodes and edges to the graph
            analyzer = CodeParser(imported_module_path)
            analyzer.visit(
                ast.parse(open(imported_module_path, "r", encoding="utf-8").read())
            )
            self.graph = nx.compose(self.graph, analyzer.graph)

    # def visit_Import(self, node, parent = None):
    def visit_Import(self, node):
        """Visit an import node and add it to the graph.

        Parameters:
        -----------
        node : ast.Import
            The import node to visit.
        """
        for alias in node.names:
            self.graph.add_node(alias.name, node_type="import", label=alias.name)
            if self.current_function:
                self.graph.add_edge(self.current_function, alias.name)
            elif self.current_class:
                self.graph.add_edge(self.current_class, alias.name)
        self.generic_visit(node)

        # parent = (
        #     self.current_function
        #     if self.current_function
        #     else (self.current_class if self.current_class else self.module_name)
        # )
        # for alias in node.names:
        #     module_name = alias.name.split(".")[0]
        #     imported_module_path = os.path.join(self.src_dir, module_name + ".py")

        #     # Add the import node
        #     import_node_name = f"import {module_name}"
        #     self.graph.add_node(
        #         import_node_name,
        #         node_type="import",
        #         label=import_node_name,
        #         parent=parent,
        #     )

        #     # Connect the import node to the current function or class, if any
        #     self.graph.add_edge(parent, import_node_name)

        #     if os.path.isfile(imported_module_path):
        #         # Analyze the imported module and add its nodes and edges to the graph
        #         analyzer = CodeParser(imported_module_path)
        #         analyzer.visit(
        #             ast.parse(open(imported_module_path, "r", encoding="utf-8").read())
        #         )
        #         self.graph = nx.compose(self.graph, analyzer.graph)
        # self.generic_visit(node)

        # parent = (
        #     self.current_function
        #     if self.current_function
        #     else (self.current_class if self.current_class else self.module_name)
        # )
        # for alias in node.names:
        #     self.visit_import_common(node=alias, parent=parent)
        # self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Visit an import_from node and add it to the graph.

        Parameters:
        -----------
        node : ast.ImportFrom
            The import_from node to visit.
        """
        module_name = node.module
        self.graph.add_node(module_name, node_type="import_from", label=module_name)
        if self.current_function:
            self.graph.add_edge(self.current_function, module_name)
        elif self.current_class:
            self.graph.add_edge(self.current_class, module_name)
        self.generic_visit(node)

        # parent = (
        #     self.current_function
        #     if self.current_function
        #     else (self.current_class if self.current_class else self.module_name)
        # )
        # module_name = node.module.split(".")[0]
        # imported_module_path = os.path.join(self.src_dir, module_name + ".py")

        # # Add the import_from node
        # import_from_node_name = f"import_from {module_name}"
        # self.graph.add_node(
        #     import_from_node_name,
        #     node_type="import_from",
        #     label=import_from_node_name,
        #     parent=parent,
        # )

        # # Connect the import_from node to the current function or class, if any
        # self.graph.add_edge(parent, import_from_node_name)

        # if os.path.isfile(imported_module_path):
        #     # Analyze the imported module and add its nodes and edges to the graph
        #     analyzer = CodeParser(imported_module_path)
        #     analyzer.visit(
        #         ast.parse(open(imported_module_path, "r", encoding="utf-8").read())
        #     )
        #     self.graph = nx.compose(self.graph, analyzer.graph)
        # self.generic_visit(node)

        # parent = (
        #     self.current_function
        #     if self.current_function
        #     else (self.current_class if self.current_class else self.module_name)
        # )
        # self.visit_import_common(node=node, parent=parent)
        # self.generic_visit(node)
