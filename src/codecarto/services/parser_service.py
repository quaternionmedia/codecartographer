import ast

from networkx import DiGraph
from models.graph_data import Node, Edge, GraphBuilder
from models.source_data import Directory, Folder, File
from random import randint
from services.parsers.ASTs.base_ast import BaseASTVisitor
from util.utilities import Log


class ParserService:
    def __init__(
        self, visitor: BaseASTVisitor, graph_builder: GraphBuilder = GraphBuilder()
    ):
        self.visitor = visitor
        self.graph_builder = graph_builder
        self.current_parent = None
        self.module_list = []
        self.graph = DiGraph()

    def parse(self, source: Directory, linkImports: bool = False) -> DiGraph:
        """Parse the entire repository and link imports between files.

        Parameters:
        -----------
        source: Directory
            The source code data to parse (including multiple files).

        Returns:
        --------
        DiGraph
            The parsed graph.
        """
        file_nodes = {}

        for file in source.root.files:
            if file.name.endswith(".py"):
                self.parse_file(file)
                file_nodes[file.name] = self.visitor.imports

        for folder in source.root.folders:
            self.parse_folder(folder, file_nodes)

        if linkImports:
            self.link_imports(file_nodes)

        return self.graph

    def parse_folder(self, folder: Folder, file_nodes: dict):
        for file in folder.files:
            self.parse_file(file)
            file_nodes[file.name] = (
                self.visitor.imports
            )  # Store the imports for later linking

        for sub_folder in folder.folders:
            if isinstance(sub_folder, Folder):
                self.parse_folder(sub_folder, file_nodes)

    def parse_file(self, file: File):
        """Parse a single file and add the nodes to the graph."""
        if not file.name.endswith(".py"):
            return
        parsed_ast = self.parse_py_to_ast(file.raw)
        self.visitor.generic_visit(parsed_ast)
        # self.build_graph(file.name)
        self.create_graph()

    def build_graph(self, filename: str):
        """Add the parsed nodes from the visitor to the graph."""
        # node_types = {
        #     "interactive": self.visitor.interactives,
        #     "expression": self.visitor.expressions,
        #     "function": self.visitor.functions,
        #     "asyncfunction": self.visitor.asyncfunctions,
        #     "class": self.visitor.classes,
        #     "import": self.visitor.imports,
        # }

        node_types = self.visitor.getNodeTypes()
        Log.pprint(node_types)

        for node_type, nodes in node_types.items():
            for node in nodes:
                node_label = (
                    str(node)
                    if node_type in ["function", "class", "import"]
                    else node_type
                )
                self.create_node(
                    graph=self.graph,
                    node_id=id(str(node)),
                    node_type=node_type,
                    node_label=node_label,
                    node_parent_id=id(self.current_parent),
                    filename=filename,
                )

    def link_imports(self, file_nodes: dict):
        """Link imports in one file to the corresponding class/function in another file."""
        Log.pprint("####################  LINKING  ########################")

        for filename, imports in file_nodes.items():
            Log.info(f"Checking imports in {filename}")
            for import_node in imports:
                imported_module_name = str(import_node)

                # Check if any file matches the imported module name
                for other_filename, other_imports in file_nodes.items():
                    if other_filename != filename and other_filename.endswith(
                        f"{imported_module_name}.py"
                    ):
                        Log.info(f"Found {imported_module_name} in {other_filename}")
                        # Create an edge between the import in `filename`
                        # and the corresponding module in `other_filename`

                        d: dict
                        for n, d in self.graph.nodes(data=True):
                            import_node_id = []
                            other_node_id = []
                            node_filename = d.get("filename")
                            if (
                                node_filename
                                and node_filename == filename
                                and d["label"].startswith(imported_module_name)
                            ):
                                import_node_id.append(n)
                                break
                            elif node_filename == other_filename:
                                other_node_id.append(n)

                        if import_node_id and other_node_id:
                            Log.info(
                                f"Adding edge between {imported_module_name} in {filename} and {other_filename}"
                            )
                            self.graph.add_edge(import_node_id[0], other_node_id[0])

    # def parse(self, source: Directory) -> DiGraph:
    #     """Parse the source code to a graph.

    #     Parameters:
    #     -----------
    #     source: Directory
    #         The source code data to parse.

    #     Returns:
    #     --------
    #     DiGraph
    #         The parsed graph.
    #     """
    #     # Set the current parent to the source name
    #     self.current_parent = id(source.name)

    #     # Add the source name to the module list
    #     self.module_list.append(source.name)

    #     # Parse the Python code to AST
    #     file_nodes = {}
    #     for item in source.source:
    #         if isinstance(item, File):
    #             self.parse_file(item)
    #             file_nodes[item.name] = (
    #                 self.visitor.imports
    #             )  # Store the imports for later linking
    #         elif isinstance(item, Folder):
    #             self.parse_folder(item, file_nodes)

    #         parsed_ast = self.parse_py_to_ast(source.source[0].raw)
    #         self.visitor.generic_visit(parsed_ast)

    #     return self.create_graph()

    def parse_py_to_ast(self, python_code: str) -> ast.AST:
        return ast.parse(python_code)

    def create_graph(self) -> DiGraph:
        try:
            # Define types and corresponding attributes
            node_types = self.visitor.getNodeTypes()

            # Add nodes and edges to the graph
            graph = DiGraph()
            ast_with_names = ["function", "class", "import", "variables"]
            for node_type, nodes in node_types.items():
                for node in nodes:
                    # if node in ast_with_names, set label to the name of the node
                    if node_type in ast_with_names:
                        node_label = str(node)
                    else:
                        node_label = node_type

                    # need to pull out relavent info from the node
                    self.create_node(
                        graph=graph,
                        node_id=id(str(node)),
                        node_type=node_type,
                        node_label=node_label,
                        node_parent_id=id(self.current_parent),
                        filename=node,
                    )
                    # add the edge to the parent
                    graph.add_edge(id(self.current_parent), id(str(node)))

            return graph
        except Exception as ex:
            print(f"Failed to add to graph: {ex}")
            raise ex

    def create_node(
        self,
        graph: DiGraph,
        node_id: int,
        node_type: str,
        node_label: str,
        node_parent_id: int,
        filename: str,
    ):
        # Check params
        if not node_label or node_label == "":
            node_label = f"{node_type} (u)"

        # Add the node
        label = f"{node_label}"  #: {node_type}"
        graph.add_node(
            node_id,
            filename=filename,
            type=node_type,
            label=label,
            parent=node_parent_id,
        )
        # Add the edge
        graph.add_edge(node_parent_id, node_id)

    # def parse(self, source_data: SourceData):
    #     for item in source_data.source:
    #         if isinstance(item, File):
    #             self._parse_file(item)
    #         elif isinstance(item, Folder):
    #             self._parse_folder(item)
    #         else:
    #             raise ValueError("Unsupported source type")
    #     return self.graph_builder.get_graph()

    # def _parse_file(self, file: File):
    #     parsed_ast = self.parse_py_to_ast(file.raw)
    #     module = self.visitor.visit(parsed_ast)
    #     self.build_graph(module, file.name)

    # def _parse_folder(self, folder: Folder):
    #     for file in folder.files:
    #         self._parse_file(file)
    #     for sub_folder in folder.folders:
    #         self._parse_folder(sub_folder)

    # def build_graph(self, module: dict, source_name: str):
    #     for node_type, nodes in module.items():
    #         for node in nodes:
    #             node_label = (
    #                 str(node)
    #                 if node_type in ["function", "class", "import"]
    #                 else node_type
    #             )
    #             self.graph_builder.add_node(
    #                 Node(
    #                     id=id(node),
    #                     type=node_type,
    #                     label=node_label,
    #                     parent=id(source_name),
    #                 )
    #             )
    #             self.graph_builder.add_edge(
    #                 Edge(
    #                     id=randint(0, 1000),
    #                     source=id(source_name),
    #                     target=id(node),
    #                 )
    #             )
