import ast
import networkx as nx
import os


class SourceParser(ast.NodeVisitor):
    """Parse a python source file into a networkx graph."""

    def __init__(self, source_files: list):
        """Initialize the parser.

        Parameters:
        -----------
        source_files : set
            A set of source files to parse.
        """
        # The graph to populate
        self.source_files: list = source_files
        self.graph: nx.DiGraph = nx.DiGraph()
        # To track current elements
        self.current_file: str = None  # file
        self.current_node: nx.DiGraph = None  # node
        self.current_module: nx.DiGraph = None  # module
        self.current_class: nx.DiGraph = None  # class
        self.current_function: nx.DiGraph = None  # function
        self.current_parent: nx.DiGraph = None  # for, while, if, etc.
        # Create root and python nodes
        self.root: nx.DiGraph = nx.DiGraph(name="root")
        self.python: nx.DiGraph = nx.DiGraph(name="python")
        self.add_start_nodes()
        # Parse the source code
        self.parsed_files: list = []
        self.parse_list(source_files)

    def add_start_nodes(self):
        """Add root and python node to the graph."""
        # Add the python node
        self.graph.add_node(
            id(self.root), type="Module", label="root", base="module", parent=None
        )
        self.graph.add_node(
            id(self.python),
            type="Module",
            label="python",
            base="module",
            parent=id(self.root),
        )
        self.graph.add_edge(id(self.root), id(self.python))

    def parse_list(self, source_files: list) -> nx.DiGraph:
        """Parse the codes in the list.

        Parameters:
        -----------
        source_files : list
            A list of source files to parse.
        """
        _files = ["test.py"]
        # loop through the list of source files
        for file_path in source_files:
            # check if base name of file_pathh in _files
            if os.path.basename(file_path) in _files:
                # Check if the file has already been parsed
                if file_path in self.parsed_files:
                    continue
                # Add the file to the parsed files
                self.parsed_files.append(file_path)
                # Parse the code
                self.current_file = file_path
                self.parse_code(file_path)

    def parse_code(self, file_path) -> nx.DiGraph:
        """Parse the code in the specified file path.

        Parameters:
        -----------
        file_path : str
            The path to the file to parse.
        """
        # Parse the code
        with open(file_path, "r") as with_fileh:
            code = with_fileh.read()
        tree = ast.parse(code, filename=file_path)
        # self.pretty_ast_dump(tree)
        self.visit(tree)

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

    def create_new_node(
        self, node_id: int, node_type: str, node_label: str, node_parent_id: int
    ) -> nx.DiGraph:
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
        if not node_label:
            node_label = f"{node_type} (u)"
        _node = self.graph.add_node(
            node_id, type=node_type, label=node_label, parent=node_parent_id
        )
        self.graph.add_edge(node_parent_id, node_id)
        return _node

    # Walk through the steps
    # 1. loop through source files
    #   -  each file is a module
    #   -  each module has a parent of root
    #   -  each module is a graph
    #   1. add file to parsed files
    #   2. get a tree of each file
    #   3. parse the tree, which sends visits for each item in the tree
    #      1. each item is a node to the module graph
    #      2. each item has a parent of the module graph
    #      3. some items are graphs as well and some are not
    #         1. graph items are classes, functions, collections
    #         2. non-graph items are items that have no children, like variables, literals, expressions
    #            - Imports are non-graphs, but they act as an edge to other module graphs
    #            - ImportFroms are nodes in the imported module graph
    #            - They need to be nodes in the current module graph, but are not the imported module graph itself
    #            - So Graph(module).node(Froms items) -> Graph(module).node(Imported item)
    #            - processor.py -> Processor -> main -> parser <- from parser.py import Parser
    #            - processor.py -> from parser.py import Parser -> Parser
    #            - parser.py -> Parser -> from parser.py import Parser -> processor.py
    #   4. once we get back to the module graph, we can park it as complete and add it to the root graph
    #   5. next file

    # Mode
    # def visit_Expression(self, node : ast.Expression):
    # def visit_FunctionType(self, node: ast.FunctionType):
    # def visit_Interactive(self, node : ast.Interactive):
    def visit_Module(self, node: ast.Module):
        """Visit the module node.

        Parameters:
        -----------
        node : ast.Module
            The module node to visit.
        """
        # Add the module node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Module",
            node_label=os.path.basename(self.current_file),
            node_parent_id=id(self.root),
        )
        # Set the current parent to the module node
        self.current_parent = node
        self.current_module = node
        # Visit the children
        self.generic_visit(node)

    # Deprecated
    # def visit_Bytes(self, node : ast.Bytes):
    # def visit_Ellipsis(self, node : ast.Ellipsis):
    # def visit_ExtSlice(self, node : ast.ExtSlice):
    # def visit_Index(self, node : ast.Index):
    # def visit_NameConstant(self, node : ast.NameConstant):
    # def visit_Num(self, node : ast.Num):
    # def visit_Str(self, node : ast.Str):
    # def visit_Param(self, node: ast.Param):

    # Literals
    def visit_Constant(self, node: ast.Constant):
        """Visit the constant node.

        Parameters:
        -----------
        node : ast.Constant
            The constant node to visit.
        """ 
        return
        # Add the constant node to the graph
        self.graph.add_node(
            id(node),
            type="Constant",
            label=node.value,
            base="literal",
            parent=id(self.current_parent),
        )
        # Add an edge from the current parent to the constant node
        self.graph.add_edge(id(self.current_parent), id(node))
        # Set the current parent to the constant node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict):
        """Visit the dict node.

        Parameters:
        -----------
        node : ast.Dict
            The dict node to visit.
        """
        # Add the dict node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Dict",
            node_label="dict",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the dict node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    # def visit_FormattedValue(self, node : ast.FormattedValue):
    # def visit_JoinedStr(self, node : ast.JoinedStr):
    def visit_List(self, node: ast.List):
        """Visit the list node.

        Parameters:
        -----------
        node : ast.List
            The list node to visit.
        """
        # Add the list node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="List",
            node_label="list",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the list node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_Set(self, node: ast.Set):
        """Visit the set node.

        Parameters:
        -----------
        node : ast.Set
            The set node to visit.
        """
        # Add the set node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Set",
            node_label="set",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the set node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple):
        """Visit the tuple node.

        Parameters:
        -----------
        node : ast.Tuple
            The tuple node to visit.
        """
        # Add the tuple node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Tuple",
            node_label="tuple",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the tuple node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    # Variables
    def visit_Name(self, node: ast.Name):
        """Visit the name node.

        Parameters:
        -----------
        node : ast.Name
            The name node to visit.
        """
        # Add the name node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Variable",
            node_label=node.id,
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the name node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    # def visit_Store(self, node : ast.Store):
    # def visit_Starred(self, node : ast.Starred): 

    def visit_arg(self, node: ast.arg):
        """Visit the arg node.

        Parameters:
        -----------
        node : ast.arg
            The arg node to visit.
        """
        # Add the arg node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Variable",
            node_label=node.arg,
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the arg node
        self.current_parent = node 

        # TODO: This will add the typing to the arg names in the graph
        # Visit the children
        #self.generic_visit(node)

    # Expressions
    def visit_Attribute(self, node: ast.Attribute):
        """Visit the attribute node.

        Parameters:
        -----------
        node : ast.Attribute
            The attribute node to visit.
        """ 
        # possibly for comment nodes
        return
        # Add the attribute node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Attribute",
            node_label=node.attr,
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the attribute node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        """Visit the binop node.

        Parameters:
        -----------
        node : ast.BinOp
            The binop node to visit.
        """
        return
        # Add the binop node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="BinOp",
            node_label="BinOp",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the binop node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        """Visit the boolop node.

        Parameters:
        -----------
        node : ast.BoolOp
            The boolop node to visit.
        """
        return
        # Add the boolop node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="BoolOp",
            node_label="BoolOp",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the boolop node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Visit the call node.

        Parameters:
        -----------
        node : ast.Call
            The call node to visit.
        """ 
        return
        # Add the call node to the graph
        self.graph.add_node(
            id(node), type="Call", label="Call", parent=id(self.current_parent)
        )
        # Add an edge from the current parent to the call node
        self.graph.add_edge(id(self.current_parent), id(node))
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the call node
        self.current_parent = node
        # Visit the call's children
        self.generic_visit(node)
        # Set the current parent back to the call's parent
        self.current_parent = old_parent

    def visit_Compare(self, node: ast.Compare):
        """Visit the compare node.

        Parameters:
        -----------
        node : ast.Compare
            The compare node to visit.
        """
        return
        # Add the compare node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Compare",
            node_label="Compare",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the compare node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr):
        """Visit the expression node.

        Parameters:
        -----------
        node : ast.Expr
            The expression node to visit.
        """ 
        # possibly for comment nodes
        return
        # Add the expression node to the graph
        self.graph.add_node(
            id(node), type="Expr", label="Expr", parent=id(self.current_parent)
        )
        # Add an edge from the current parent to the expression node
        self.graph.add_edge(id(self.current_parent), id(node))
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the expression node
        self.current_parent = node
        # Visit the expression's children
        self.generic_visit(node)
        # Set the current parent back to the expression's parent
        self.current_parent = old_parent

    def visit_IfExp(self, node: ast.IfExp):
        """Visit the ifexp node.

        Parameters:
        -----------
        node : ast.IfExp
            The ifexp node to visit.
        """
        # Add the ifexp node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="IfExp",
            node_label="IfExp",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the ifexp node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    # def visit_NamedExpr(self, node : ast.NamedExpr):
    def visit_UnaryOp(self, node: ast.UnaryOp):
        """Visit the unaryop node.

        Parameters:
        -----------
        node : ast.UnaryOp
            The unaryop node to visit.
        """
        return
        # Add the unaryop node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="UnaryOp",
            node_label="UnaryOp",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the unaryop node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    #   Comprehensions
    def visit_DictComp(self, node: ast.DictComp):
        """Visit the dictcomp node.

        Parameters:
        -----------
        node : ast.DictComp
            The dictcomp node to visit.
        """
        # Add the dictcomp node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="DictComp",
            node_label="DictComp",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the dictcomp node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        """Visit the generatorexp node.

        Parameters:
        -----------
        node : ast.GeneratorExp
            The generatorexp node to visit.
        """
        # possibly for comment nodes
        return
        # Add the generatorexp node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="GeneratorExp",
            node_label="GenExp",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the generatorexp node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp):
        """Visit the listcomp node.

        Parameters:
        -----------
        node : ast.ListComp
            The listcomp node to visit.
        """
        # Add the listcomp node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="ListComp",
            node_label="ListComp",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the listcomp node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp):
        """Visit the setcomp node.

        Parameters:
        -----------
        node : ast.SetComp
            The setcomp node to visit.
        """
        # Add the setcomp node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="SetComp",
            node_label="SetComp",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the setcomp node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    #   Subscripting
    # def visit_Slice(self, node : ast.Slice):
    # def visit_Subscript(self, node : ast.Subscript):

    # Statements
    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit the annotated assignment node.

        Parameters:
        -----------
        node : ast.AnnAssign
            The annotated assignment node to visit.
        """ 
        self.generic_visit(node)
        return
        # Add the annotated assignment node to the graph
        self.graph.add_node(
            id(node),
            type="AnnAssign",
            label="AnnAssign",
            parent=id(self.current_parent),
        )
        # Add an edge from the current parent to the annotated assignment node
        self.graph.add_edge(id(self.current_parent), id(node))
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the annotated assignment node
        self.current_parent = node
        # Visit the annotated assignment's children
        self.generic_visit(node)
        # Set the current parent back to the annotated assignment's parent
        self.current_parent = old_parent

    # def visit_Assert(self, node : ast.Assert):

    # def infer_type(self, node):
    #     if isinstance(node, ast.Constant):
    #         # For Python 3.8+
    #         return type(node.value).__name__
    #     elif isinstance(node, ast.Num):
    #         return type(node.n).__name__
    #     elif isinstance(node, ast.Str):
    #         return "str"
    #     # Add other cases if needed
    #     else:
    #         return "var"

    def visit_Assign(self, node: ast.Assign):
        """Visit the assignment node.

        Parameters:
        -----------
        node : ast.Assign
            The assignment node to visit.
        """
        # Assuming the target is a single variable
        # check if the target has an id attribute
        self.generic_visit(node)
        return
        _name = ""
        parent_id = id(self.current_parent)

        if hasattr(node.targets[0], "id"):
            _name = node.targets[0].id
        elif hasattr(node.targets[0], "attr"):
            _name = node.targets[0].attr
            if (
                isinstance(node.targets[0].value, ast.Name)
                and node.targets[0].value.id == "self"
            ):
                # If the attribute is assigned to `self`, set the parent to the current class
                parent_id = id(self.current_class)
        elif hasattr(node.targets[0], "value"):
            _name = node.targets[0].value
        else:
            _name = node.value

        # # Infer the type of the assigned value
        # var_type = self.infer_type(node.value)

        # Now you can create a node with the label as the variable name and base as the inferred type
        self.create_new_node(
            node_id=id(node),
            node_type="Variable",
            node_label=_name,
            node_parent_id=id(self.current_parent),
        ) 

    def visit_AugAssign(self, node: ast.AugAssign):
        """Visit the augmented assignment node.

        Parameters:
        -----------
        node : ast.AugAssign
            The augmented assignment node to visit.
        """ 
        self.generic_visit(node)
        return
        # Add the augmented assignment node to the graph
        self.graph.add_node(
            id(node),
            type="AugAssign",
            label="AugAssign",
            parent=id(self.current_parent),
        )
        # Add an edge from the current parent to the augmented assignment node
        self.graph.add_edge(id(self.current_parent), id(node))
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the augmented assignment node
        self.current_parent = node
        # Visit the augmented assignment's children
        self.generic_visit(node)
        # Set the current parent back to the augmented assignment's parent
        self.current_parent = old_parent

    # def visit_Delete(self, node : ast.Delete):
    # def visit_Pass(self, node : ast.Pass):
    # def visit_Raise(self, node : ast.Raise):
    #   Imports
    # def visit_Import(self, node : ast.Import):
    # def visit_ImportFrom(self, node : ast.ImportFrom):

    # Control Flow
    # def visit_Break(self, node : ast.Break):
    # def visit_Continue(self, node : ast.Continue):
    # def visit_ExceptHandler(self, node : ast.ExceptHandler):
    def visit_For(self, node: ast.For):
        """Visit the for node.

        Parameters:
        -----------
        node : ast.For
            The for node to visit.
        """
        # Add the for node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="For",
            node_label="for",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the for node
        self.current_parent = node
        # Visit the for's children
        self.generic_visit(node)
        # Set the current parent back to the for's parent
        self.current_parent = old_parent

    def visit_If(self, node: ast.If):
        """Visit the if node.

        Parameters:
        -----------
        node : ast.If
            The if node to visit.
        """
        # Add the if node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="If",
            node_label="if",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the if node
        self.current_parent = node
        # Visit the if's children
        self.generic_visit(node)
        # Set the current parent back to the if's parent
        self.current_parent = old_parent

    def visit_Try(self, node: ast.Try):
        """Visit the try node.

        Parameters:
        -----------
        node : ast.Try
            The try node to visit.
        """
        # Add the try node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Try",
            node_label="try",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the try node
        self.current_parent = node
        # Visit the try's children
        self.generic_visit(node)
        # Set the current parent back to the try's parent
        self.current_parent = old_parent

    # def visit_TryStar(self, node : ast.TryStar):
    def visit_While(self, node: ast.While):
        """Visit the while node.

        Parameters:
        -----------
        node : ast.While
            The while node to visit.
        """
        # Add the while node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="While",
            node_label="while",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the while node
        self.current_parent = node
        # Visit the while's children
        self.generic_visit(node)
        # Set the current parent back to the while's parent
        self.current_parent = old_parent

    def visit_With(self, node: ast.With):
        """Visit the with node.

        Parameters:
        -----------
        node : ast.With
            The with node to visit.
        """
        # Add the with node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="With",
            node_label="with",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the with node
        self.current_parent = node
        # Visit the with's children
        self.generic_visit(node)
        # Set the current parent back to the with's parent
        self.current_parent = old_parent

    # Pattern Matching
    # def visit_Match(self, node : ast.Match):
    # def visit_MatchAs(self, node : ast.MatchAs):
    # def visit_MatchClass(self, node : ast.MatchClass):
    # def visit_MatchMapping(self, node : ast.MatchMapping):
    # def visit_MatchOr(self, node : ast.MatchOr):
    # def visit_MatchSequence(self, node : ast.MatchSequence):
    # def visit_MatchSingleton(self, node : ast.MatchSingleton):
    # def visit_MatchStar(self, node : ast.MatchStar):
    # def visit_MatchValue(self, node : ast.MatchValue):

    # Functions and Class Definitions
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit the class node.

        Parameters:
        -----------
        node : ast.ClassDef
            The class node to visit.
        """
        # Add the class node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="ClassDef",
            node_label=node.name,
            node_parent_id=id(self.current_module),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the class node
        self.current_parent = node
        # Save the previous current_class
        previous_class = self.current_class
        # Set the current_class
        self.current_class = node
        # Visit the class' children
        self.generic_visit(node)
        # Set the current parent back to the class' parent
        self.current_parent = old_parent
        # Restore the previous current_class
        self.current_class = previous_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit the function node.

        Parameters:
        -----------
        node : ast.FunctionDef
            The function node to visit.
        """
        function_parent: nx.DiGraph
        if self.current_class:
            function_parent = self.current_class
        else:
            if self.current_module:
                function_parent = self.current_module
            else:
                function_parent = self.current_parent
        # Add the function node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="FunctionDef",
            node_label=node.name,
            node_parent_id=id(function_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the function node
        self.current_parent = node
        # Save the previous current_function
        previous_function = self.current_function
        # Set the current_function
        self.current_function = node
        # Visit the function's children
        self.generic_visit(node)
        # Set the current parent back to the function's parent
        self.current_parent = old_parent
        # Restore the previous current_function
        self.current_function = previous_function

    def visit_Global(self, node: ast.Global):
        """Visit the global node.

        Parameters:
        -----------
        node : ast.Global
            The global node to visit.
        """
        # Add the global node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Global",
            node_label="global",
            node_parent_id=id(self.current_parent),
        )

    # def visit_Lambda(self, node : ast.Lambda):
    def visit_Nonlocal(self, node: ast.Nonlocal):
        """Visit the nonlocal node.

        Parameters:
        -----------
        node : ast.Nonlocal
            The nonlocal node to visit.
        """
        # Add the nonlocal node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Nonlocal",
            node_label="nonlocal",
            node_parent_id=id(self.current_parent),
        )

    # def visit_Return(self, node : ast.Return):
    # def visit_Yield(self, node : ast.Yield):
    # def visit_YieldFrom(self, node : ast.YieldFrom):

    # Async and Await
    def visit_AsyncFor(self, node: ast.AsyncFor):
        """Visit the async for node.

        Parameters:
        -----------
        node : ast.AsyncFor
            The async for node to visit.
        """
        # Add the async for node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="AsyncFor",
            node_label="async for",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the async for node
        self.current_parent = node
        # Visit the async for's children
        self.generic_visit(node)
        # Set the current parent back to the async for's parent
        self.current_parent = old_parent

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit the async function node.

        Parameters:
        -----------
        node : ast.AsyncFunctionDef
            The async function node to visit.
        """
        # Add the async function node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="AsyncFunctionDef",
            node_label=node.name,
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the async function node
        self.current_parent = node
        # Visit the async function's children
        self.generic_visit(node)
        # Set the current parent back to the async function's parent
        self.current_parent = old_parent

    def visit_AsyncWith(self, node: ast.AsyncWith):
        """Visit the async with node.

        Parameters:
        -----------
        node : ast.AsyncWith
            The async with node to visit.
        """
        # Add the async with node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="AsyncWith",
            node_label="async with",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the async with node
        self.current_parent = node
        # Visit the async with's children
        self.generic_visit(node)
        # Set the current parent back to the async with's parent
        self.current_parent = old_parent

    # def visit_Await(self, node : ast.Await):
