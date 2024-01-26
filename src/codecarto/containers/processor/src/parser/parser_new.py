import os
import ast
from platform import node
from matplotlib.pylab import f
import networkx as nx
from operator import contains, index
from pprint import pprint

from .types.base_ast import BaseASTVisitor
from .types.python_ast import PythonAST

# from .types.python_ast import PythonAST

ast_types = {
    "py": PythonAST,
}


class Parser:
    """Parse source file(s) into a networkx graph."""

    def __init__(self, source_data: list | dict = None, is_repo: bool = False):
        """Initialize the parser.

        Parameters:
        -----------
        source_data : list | dict
            The source data to parse.
        is_repo : bool
            Whether the source is a repo.
        """
        # The graph to populate
        self.graph: nx.DiGraph = nx.DiGraph()
        # The source data
        self.source_data: list | dict = source_data
        # To track current elements
        self.current_dir: str = None  # dir
        self.current_file: str = None  # file
        self.current_node: nx.DiGraph = None  # node
        self.current_type: str = None  # node type
        self.current_parent: nx.DiGraph = None  # module, for, while, if, etc.
        # Parse the source code
        self.parsed_files: list = []
        self.module_list: list = []
        self.add_start_nodes(is_repo)
        self.parse_source_data()

    ########## GRAPH ##########
    def add_start_nodes(self, is_repo: bool = False):
        """Add root and python node to the graph."""
        # Create root and python nodes
        if is_repo:
            # Repo source data
            root_label: str = f"{self.source_data['owner']}/{self.source_data['repo']}"
            self.root: nx.DiGraph = nx.DiGraph(name=root_label)
            self.graph.add_node(
                id(self.root),
                type="Module",
                label=root_label,
                parent=None,
            )
            self.current_parent = id(self.root)
        else:
            # File source data
            self.root: nx.DiGraph = nx.DiGraph(name="root")
            self.python: nx.DiGraph = nx.DiGraph(name="python")
            # add the root node
            self.graph.add_node(
                id(self.root),
                type="Module",
                label="root",
                parent=None,
            )
            # add the python node
            self.graph.add_node(
                id(self.python),
                type="Module",
                label="python",
                parent=id(self.root),
            )
            self.graph.add_edge(id(self.root), id(self.python))

    def add_to_graph(self, visitor: BaseASTVisitor):
        """Add the parsed data to the graph.

        Parameters:
        -----------
        visitor : BaseASTVisitor
            The visitor object.
        """
        try:
            # Get the module
            module = visitor.module
            # Define types and corresponding attributes
            node_types = {
                "interactive": visitor.interactives,
                "expression": visitor.expressions,
                "function": visitor.functions,
                "asyncfunction": visitor.asyncfunctions,
                "class": visitor.classes,
                "return": visitor.returns,
                "delete": visitor.deletes,
                "assign": visitor.assigns,
                "typealias": visitor.typealiases,
                "augassign": visitor.augassigns,
                "annassign": visitor.annassigns,
                "forloop": visitor.forloops,
                "asyncforloop": visitor.asyncforloops,
                "whileloop": visitor.whileloops,
                "if": visitor.ifs,
                "with": visitor.withs,
                "asyncwith": visitor.asyncwiths,
                "match": visitor.matches,
                "raise": visitor.raises,
                "try": visitor.trys,
                "trystar": visitor.trystars,
                "assert": visitor.asserts,
                "import": visitor.imports,
                "importfrom": visitor.importfroms,
                "global": visitor.globals,
                "nonlocal": visitor.nonlocals,
                "expr": visitor.exprs,
                "pass": visitor.passes,
                "break": visitor.breaks,
                "continue": visitor.continues,
                "boolop": visitor.boolops,
                "namedexpr": visitor.namedexprs,
                "binop": visitor.binops,
                "unaryop": visitor.uarynops,
                "lambda": visitor.lambdas,
                "ifexp": visitor.ifexps,
                "dict": visitor.dicts,
                "set": visitor.sets,
                "listcomp": visitor.listcomps,
                "setcomp": visitor.setcomps,
                "dictcomp": visitor.dictcomps,
                "generatorexp": visitor.generatorexps,
                "await": visitor.awaits,
                "yield": visitor.yields,
                "yieldfrom": visitor.yieldfroms,
                "comparison": visitor.comparisons,
                "call": visitor.calls,
                "formattedvalue": visitor.formattedvalues,
                "joinedstr": visitor.joinedstrs,
                "constant": visitor.constats,
                "attribute": visitor.attribuetes,
                "subscript": visitor.subscripts,
                "starred": visitor.starreds,
                "name": visitor.names,
                "list": visitor.lists,
                "tuple": visitor.tuples,
                "slice": visitor.slices,
                "load": visitor.loads,
                "store": visitor.stores,
                "del": visitor.dels,
                "and": visitor.ands,
                "or": visitor.ors,
                "add": visitor.adds,
                "sub": visitor.subs,
                "mult": visitor.mults,
                "matmult": visitor.matmults,
                "div": visitor.divs,
                "mod": visitor.mods,
                "pow": visitor.pows,
                "lshift": visitor.lshifts,
                "rshift": visitor.rshifts,
                "bitor": visitor.bitors,
                "bitxor": visitor.bitxors,
                "bitand": visitor.bitands,
                "floordiv": visitor.floordivs,
                "invert": visitor.inverts,
                "not": visitor.nots,
                "uadd": visitor.uaddss,
                "usub": visitor.usubss,
                "eq": visitor.eqss,
                "not_eq": visitor.not_eqss,
                "lt": visitor.lts,
                "lte": visitor.ltes,
                "gt": visitor.gts,
                "gte": visitor.gtes,
                "is": visitor.iss,
                "isnot": visitor.isnots,
                "in": visitor.ins,
                "notin": visitor.notins,
                "excepthandler": visitor.excepthandlers,
                "matchvalue": visitor.matchvalues,
                "matchsingleton": visitor.matchsingleton,
                "matchsequence": visitor.matchsequences,
                "matchmapping": visitor.matchmappings,
                "matchclass": visitor.matchclasses,
                "matchstar": visitor.matchstars,
                "matchas": visitor.matchases,
                "machor": visitor.machors,
                "typeignore": visitor.typeignores,
                "typevar": visitor.typevars,
                "paramspec": visitor.paramspecs,
                "typevartuple": visitor.typevartuples,
                "relation": visitor.relations,
                "variables": visitor.variables,
            }
            # Add nodes and edges
            for node_type, nodes in node_types.items():
                nodes = [str(node) for node in nodes]
                for node in nodes:
                    self.create_node(
                        node_id=id(node),
                        node_type=node_type,
                        node_label=node_type,
                        node_parent_id=id(self.current_parent),
                    )
        except Exception as ex:
            print(f"Failed to add to graph: {ex}")
            raise ex

    def create_node(
        self,
        node_id: int,
        node_type: str,
        node_label: str,
        node_parent_id: int,
    ):
        """Create new node.

        Parameters:
        -----------
        node_id : int
            The id of the new node.
        node_type : str
            The type of the new node.
        node_label : str
            The label of the new node.
        node_parent_id : int
            The id of the parent new node.
        """
        # Check params
        if not node_label or node_label == "":
            node_label = f"{node_type} (u)"
        # Add the node
        self.graph.add_node(
            node_id,
            type=node_type,
            label=node_label,
            parent=node_parent_id,
        )
        # Add the edge
        self.graph.add_edge(node_parent_id, node_id)

    ########## PARSE CODE ##########
    def parse_source_data(self):
        """Parse the source data."""
        try:
            if isinstance(self.source_data, dict):
                # parse the repo
                print("Parsing repo...")
                self.parse_repo(self.source_data["raw"])
                # parse the raw for accepted file types
                # self.parse_raw()
            elif isinstance(self.source_data, list):
                # loop through the list of source files
                print("Parsing files...")
                self.module_list = self.source_data
                for file in self.source_data:
                    self.parse_file(file)
            else:
                # invalid source data type
                raise TypeError("Invalid source data type.")
        except Exception as ex:
            print(f"Failed to parse source data: {ex}")
            raise ex

    def parse_repo(self, source_dict: dict = None):
        """Parse the codes in the list.

        Parameters:
        -----------
        source_dict : dict
            A dict of source files to parse.
        """
        try:
            self.get_repo_modules(source_dict)
            # loop through the list of source files
            for key, value in source_dict.items():
                # key is the name of the dir or 'files'
                if key == "files":
                    # value is a list of dicts with name and raw
                    for file in value:
                        # file attributes
                        file_idx: int = value.index(file) - 1
                        filename: str = file["name"]
                        node_id: int = id(filename)
                        # save the node id to the source_data
                        # TODO: This is breaking because these don't all exist on every node
                        # self.source_data["raw"][self.current_dir]["files"][file_idx][
                        #     "node_id"
                        # ] = node_id
                        self.create_node(
                            node_id=node_id,
                            node_type="File",
                            node_label=filename,
                            node_parent_id=id(self.current_parent),
                        )
                else:
                    # add a node for the dir
                    self.create_node(
                        node_id=id(key),
                        node_type="Dir",
                        node_label=key,
                        node_parent_id=id(self.root),
                    )
                    self.current_parent = key
                    self.current_dir = key
                    self.parse_repo(value)
        except Exception as ex:
            print(f"Failed to parse repo: {ex}")
            raise ex

    def parse_raw(self, source_raw: str, filename: str):
        """Parse the passed raw source code.

        Parameters:
        -----------
        source_raw : str
            The source text to parse.
        filename : str
            The name of the file.
        """
        # Check params
        if not source_raw:
            raise ValueError("Parser.parse_text: source_raw is None")
        if not filename:
            raise ValueError("Parser.parse_text: filename is None")

        # TODO: this is adding the raw elements wrong
        # TODO: Could just add the id of file to the source_data
        # TODO: and then parse the raw for the files after
        # TODO: one of the problems is that the raw data is
        # TODO: being linked off other files instead of the dir
        # TODO: This came from the parse_repo function
        # check if the file contains one of the allowed type
        # file_type: str = filename.split(".")[-1]
        # if contains(ast_types.keys(), file_type):
        #     raw: str = file["raw"]
        #     if not raw or raw == "":  # empty file
        #         self.create_node(
        #             node_id=id(filename),
        #             node_type="File",
        #             node_label=filename,
        #             node_parent_id=id(self.current_parent),
        #         )
        #     else:  # non-empty file
        #         self.create_node(
        #             node_id=id(filename),
        #             node_type="File",
        #             node_label=filename,
        #             node_parent_id=id(self.current_parent),
        #         )
        #         self.current_parent = filename
        #         self.parse_raw(raw, filename)
        # else:  # other files
        #     self.create_node(
        #         node_id=id(filename),
        #         node_type="File",
        #         node_label=filename,
        #         node_parent_id=id(self.current_parent),
        #     )

        # Parse the code
        node = ast.parse(source_raw, filename)
        if node:
            # Visit the node
            file_ext = filename.split(".")[-1]
            visitor = ast_types[file_ext](self.module_list)
            visitor.visit(node)
            # Add the parsed data to the graph
            self.add_to_graph(visitor)
        else:
            print(f"Parser.parse_text: tree is None for {filename}")
            raise ValueError(f"Parser.parse_text: tree is None for {filename}")

    def parse_file(self, filepath: str):
        """Parse the passed file.

        Parameters:
        -----------
        filepath : str
            The path to the file to parse.
        """
        try:
            # Read the file content
            with open(filepath, "r", encoding="utf-8") as file:
                file_content = file.read()
            # Parse the content using AST
            filename = os.path.basename(filepath)
            node = ast.parse(file_content, filename=filename)
            # Visit the node
            file_ext = filepath.split(".")[-1]
            visitor: BaseASTVisitor = ast_types[file_ext](self.module_list)
            visitor.visit(node)
            # Add the parsed data to the graph
            self.add_to_graph(visitor)
        except SyntaxError as ex:
            # Log or print error message if needed
            print(f"SyntaxError in file {filepath}: {ex}")
            pass  # Simply skip the file
        except UnicodeDecodeError as ex:
            # Log or print error message if needed
            print(f"UnicodeDecodeError in file {filepath}: {ex}")
            pass  # Simply skip the file
        except Exception as ex:
            # Log or print error message if needed
            print(f"Failed to parse {filepath}: {ex}")
            pass  # Simply skip the file

    ########## REPO ##########
    def get_repo_modules(self, source_raw: dict):
        """Get the modules from the repo.

        Parameters:
        -----------
        source_raw : dict
            A dict of source files to parse.
        """
        # pull out the file names from the source_raw
        for key, value in source_raw.items():
            if key == "files":
                for file in value:
                    self.module_list.append(file["name"])

    ########## DEBUG ##########
    def pretty_ast_dump(self, node, indent=0):
        """Pretty print the ast tree.

        Parameters:
        -----------
        node : ast.AST
            The ast node to print.
        indent : int
            The indent level.
        """
        if isinstance(node, ast.AST):
            node_name = node.__class__.__name__
            print("  " * indent + node_name)

            for field_name, field_value in ast.iter_fields(node):
                print("  " * (indent + 1) + field_name + ":")
                self.pretty_ast_dump(field_value, indent + 2)
        elif isinstance(node, list):
            for item in node:
                self.pretty_ast_dump(item, indent)
        else:
            print("  " * indent + repr(node))
