import ast
import networkx as nx
import os

# Walk through the steps
# Note: Not every visitor will add a node to the graph. They will do one more more of the following:
#       1. Add a node to the graph
#       2. Add an edge to the graph
#       4. Act as a helper node for other nodes
#       5. Visit the node's children
#       6. Do nothing
# 1. loop through source files
#   1. add file to parsed files
#   2. get a tree of each file
#   3. parse the tree, which visits each ast.node found for each item in the tree representing the file.
#      1. The first visit should be to a module for each file. Files are modules. Module parents will be the root graph.
#      2. When Module is visited, it will visit it's children with 'generic_visit'.
#      3. The immediate children are typically imports, functions, or classes.
#            - These would have a parent of the module.
#      4. Each child also calls the 'generic_visit' method, which will visit the child's children.
#            - Their parents would be the child of the module.
#      5. Some children have children, like functions and classes, and some do not like 'pass' and 'break'.
#         1. Typical containing children are classes, functions, collections
#         2. Typical non-containing children are variables and constants
#            - Imports will be considered barren, they do have children, but for this they act a connecting node to other module graphs
#            - ImportFroms are similar to imports, but they will be a connecting node from the current module to the from module's object
#              that we're importing
#            - They need to be nodes in the current module graph, but are not the imported module graph itself
#            - The imported obj will point to the import | importfrom node
#            - The module that is importing will point to the import | importfrom node as well
#            - The import | importfrom node will point to the obj using the imported obj in the module importing the obj
#            - So Graph(module).node(import|importfram) -> Graph(module).node(imported item)
#            - processor.py -> Processor -> main -> parser <- (from parser.py import Parser) <- processor.py
#            - processor.py -> from models import graph_data -> models module graph -> graph_data
#            - processor.py -> (from parser.py import Parser) <- Parser, a node in the parser module graph
#            - parser.py -> Parser -> (from parser.py import Parser) <- processor.py
#   4. once we get back to the module graph, we can mark it as complete and add it to the root graph
#   5. next file


class Parser(ast.NodeVisitor):
    """Parse a python source file into a networkx graph."""

    # TODO: when we eventually add import and importFrom, they need to be the id of the Module they represent
    # TODO: when this gets updated, do logic of option 'uno'
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
        self.current_type: str = None  # type
        # self.current_module: nx.DiGraph = None  # module
        # self.current_class: nx.DiGraph = None  # class
        # self.current_function: nx.DiGraph = None  # function
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
        # add the root node
        self.graph.add_node(
            id(self.root), type="Module", label="root", base="module", parent=None
        )
        # add the python node
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
        test = False
        if test:
            # TODO: for local testing purpose
            _files = ["plotter.py"]
            # loop through the list of source files
            for file_path in source_files:
                # TODO: testing purpose: check if base name of file_path in _files
                if os.path.basename(file_path) in _files:
                    # Check if the file has already been parsed
                    if file_path in self.parsed_files:
                        continue
                    # Add the file to the parsed files
                    self.parsed_files.append(file_path)
                    # Parse the code
                    self.current_file = file_path
                    self.parse_code(file_path)
        else:
            # check if graph only has root and python nodes
            if not source_files or len(source_files) == 0:
                if len(self.graph.nodes) == 2:
                    # remove the root and python nodes
                    self.graph.remove_node(id(self.root))
                    self.graph.remove_node(id(self.python))
                return None

            # loop through the list of source files
            for file_path in source_files:
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
        with open(file_path, "r") as with_file:
            code = with_file.read()
        tree = ast.parse(code, filename=file_path)
        # self.pretty_ast_dump(tree)
        # Visit the tree
        # this starts the decent through the file's code objects
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

    # Deprecated
    # def visit_Bytes(self, node : ast.Bytes):
    # def visit_Ellipsis(self, node : ast.Ellipsis):
    # def visit_ExtSlice(self, node : ast.ExtSlice):
    # def visit_Index(self, node : ast.Index):
    # def visit_NameConstant(self, node : ast.NameConstant):
    # def visit_Num(self, node : ast.Num):
    # def visit_Str(self, node : ast.Str):
    # def visit_Param(self, node: ast.Param):

    # region Mode
    def visit_Expression(self, node: ast.Expression):
        """Visit the expression node.

        Parameters:
        -----------
        node : ast.Expression
            The expression node to visit.

        Notes:
        ------
        In the following "xsqur = x * x", the ast.Expression node represents "x * x". \n
        While ast.Name.id represents 'xsqur'.
        """
        return
        # Add the expression node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Expression",
            node_label=None,
            node_parent_id=id(self.current_parent),
        )
        # Visit the children
        self.generic_visit(node)

    def visit_FunctionType(self, node: ast.FunctionType):
        """Visit the function type node.

        Parameters:
        -----------
        node : ast.FunctionType
            The function type node to visit.

        Notes:
        ------
        In the following "def foo(x: int) -> int:", the ast.FunctionType node represents "x: int -> int". \n
        While ast.Name.id represents 'foo'.
        """
        return
        # Add the function type node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="FunctionType",
            node_label=None,
            node_parent_id=id(self.current_parent),
        )
        # Visit the children
        self.generic_visit(node)

    def visit_Interactive(self, node: ast.Interactive):
        """Visit the interactive node.

        Parameters:
        -----------
        node : ast.Interactive
            The interactive node to visit.

        Notes:
        ------
        In the following "python -i", the ast.Interactive node represents "python -i".
        """
        return
        # Add the interactive node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Interactive",
            node_label=None,
            node_parent_id=id(self.current_parent),
        )
        # Visit the children
        self.generic_visit(node)

    def visit_Module(self, node: ast.Module):
        """Visit the module node.

        Parameters:
        -----------
        node : ast.Module
            The module node to visit.

        Notes:
        ------
        ast.Module represents the entire python file.
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
        # self.current_module = node
        # Visit the children of the Module
        self.generic_visit(node)

    # endregion

    # region Literals
    def visit_Constant(self, node: ast.Constant):
        """Visit the constant node.

        Parameters:
        -----------
        node : ast.Constant
            The constant node to visit.

        Notes:
        ------
        In the following "x = 1", the ast.Constant node represents "1". \n
        While ast.Name.id represents 'x'.
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

        Notes:
        ------
        In the following "x = {1: 2}", the ast.Dict node represents "{1: 2}". \n
        While ast.Name.id represents 'x'.
        """
        # I don't really want the 'Dict' node in the graph,
        # but to say that it's children are of type Dict
        # so set the current_type to Dict, visit children,
        # then unset the current_type

        # Set the current type to Dict
        self.current_type = "Dict"
        # Visit the children
        self.generic_visit(node)
        # Unset the current type
        self.current_type = None

        # # Add the dict node to the graph
        # self.create_new_node(
        #     node_id=id(node),
        #     node_type="Dict",
        #     node_label="dict",
        #     node_parent_id=id(self.current_parent),
        # )
        # # Set the current parent to the dict node
        # self.current_parent = node
        # # Visit the children
        # self.generic_visit(node)

    def visit_FormattedValue(self, node: ast.FormattedValue):
        """Visit the formatted value node.

        Parameters:
        -----------
        node : ast.FormattedValue
            The formatted value node to visit.

        Notes:
        ------
        In the following "x = f'{1}'", the ast.FormattedValue node represents "'{1}'". \n
        While ast.Name.id represents 'x'.
        """
        return
        # Add the formatted value node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="FormattedValue",
            node_label=None,
            node_parent_id=id(self.current_parent),
        )
        # Visit the children
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        """Visit the joined string node.

        Parameters:
        -----------
        node : ast.JoinedStr
            The joined string node to visit.

        Notes:
        ------
        In the following "x = f'{1}'", the ast.JoinedStr node represents "f'{1}'". \n
        While ast.Name.id represents 'x'.
        """
        return
        # Add the joined string node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="JoinedStr",
            node_label=None,
            node_parent_id=id(self.current_parent),
        )
        # Visit the children
        self.generic_visit(node)

    def visit_List(self, node: ast.List):
        """Visit the list node.

        Parameters:
        -----------
        node : ast.List
            The list node to visit.

        Notes:
        ------
        In the following "x = [1, 2]", the ast.List node represents "[1, 2]". \n
        While ast.Name.id represents 'x'.
        """
        # I don't really want the 'List' node in the graph,
        # but to say that it's children are of type List
        # so set the current_type to List, visit children,
        # then unset the current_type

        # Set the current type to List
        self.current_type = "List"
        # Visit the children
        self.generic_visit(node)
        # Unset the current type
        self.current_type = None

        # # Add the list node to the graph
        # self.create_new_node(
        #     node_id=id(node),
        #     node_type="List",
        #     node_label="list",
        #     node_parent_id=id(self.current_parent),
        # )
        # # Set the current parent to the list node
        # self.current_parent = node
        # # Visit the children
        # self.generic_visit(node)

    def visit_Set(self, node: ast.Set):
        """Visit the set node.

        Parameters:
        -----------
        node : ast.Set
            The set node to visit.

        Notes:
        ------
        In the following "x = {1, 2}", the ast.Set node represents "{1, 2}". \n
        While ast.Name.id represents 'x'.
        """
        # I don't really want the 'Set' node in the graph,
        # but to say that it's children are of type Set
        # so set the current_type to Set, visit children,
        # then unset the current_type

        # Set the current type to Set
        self.current_type = "Set"
        # Visit the children
        self.generic_visit(node)
        # Unset the current type
        self.current_type = None

        # # Add the set node to the graph
        # self.create_new_node(
        #     node_id=id(node),
        #     node_type="Set",
        #     node_label="set",
        #     node_parent_id=id(self.current_parent),
        # )
        # # Set the current parent to the set node
        # self.current_parent = node
        # # Visit the children
        # self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple):
        """Visit the tuple node.

        Parameters:
        -----------
        node : ast.Tuple
            The tuple node to visit.

        Notes:
        ------
        In the following "x = (1, 2)", the ast.Tuple node represents "(1, 2)". \n
        While ast.Name.id represents 'x'.
        """
        # I don't really want the 'Tuple' node in the graph,
        # but to say that it's children are of type Tuple
        # so set the current_type to Tuple, visit children,
        # then unset the current_type

        # Set the current type to Tuple
        self.current_type = "Tuple"
        # Visit the children
        self.generic_visit(node)
        # Unset the current type
        self.current_type = None

        # # Add the tuple node to the graph
        # self.create_new_node(
        #     node_id=id(node),
        #     node_type="Tuple",
        #     node_label="tuple",
        #     node_parent_id=id(self.current_parent),
        # )
        # # Set the current parent to the tuple node
        # self.current_parent = node
        # # Visit the children
        # self.generic_visit(node)

    # endregion

    # region Variables
    def visit_Name(self, node: ast.Name):
        """Visit the name node.

        Parameters:
        -----------
        node : ast.Name
            The name node to visit.

        Notes:
        ------
        In the following "x = 1", the ast.Name node represents 'x'. \n
        While ast.Constant.value represents 1.
        """
        # Add the name node to the graph
        _type: str = None
        if self.current_type:
            _type = self.current_type
        else:
            _type = "Variable"
        self.create_new_node(
            node_id=id(node),
            node_type=_type,
            node_label=node.id,
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the name node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_Store(self, node: ast.Store):
        """Visit the store node.

        Parameters:
        -----------
        node : ast.Store
            The store node to visit.

        Notes:
        ------
        The ast.Store node indicates that this is a store context (i.e., the var is being assigned a value). \n
        ast.Name.id represents the name of the variable being assigned. \n
        ast.Constant.value represents the value being assigned to the variable.
        """
        return
        # Add the store node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Store",
            node_label=None,
            node_parent_id=id(self.current_parent),
        )
        # Visit the children
        self.generic_visit(node)

    def visit_Starred(self, node: ast.Starred):
        """Visit the starred node.

        Parameters:
        -----------
        node : ast.Starred
            The starred node to visit.

        Notes:
        ------
        In the following "x = [*range(10)]", the ast.Starred node represents "*range(10)". \n
        While ast.Name.id represents 'x'.
        """
        return
        # Add the starred node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Starred",
            node_label=None,
            node_parent_id=id(self.current_parent),
        )
        # Visit the children
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg):
        """Visit the arg node.

        Parameters:
        -----------
        node : ast.arg
            The arg node to visit.

        Notes:
        ------
        In the following "def some_func(x):", the ast.arg node represents 'x'. \n
        While ast.Name.id represents 'some_func'.
        """
        # Add the arg node to the graph
        _type: str = None
        if self.current_type:
            _type = self.current_type
        else:
            _type = "Variable"
        self.create_new_node(
            node_id=id(node),
            node_type=_type,
            node_label=node.arg,
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the arg node
        self.current_parent = node

    # endregion

    # region Expressions
    def visit_Attribute(self, node: ast.Attribute):
        """Visit the attribute node.

        Parameters:
        -----------
        node : ast.Attribute
            The attribute node to visit.

        Notes:
        ------
        In the following "x = some_obj.some_attr" : \n
            ast.Attribute.value node represents 'some_obj'. \n
            ast.Attribute.attr node represents 'some_attr'. \n
        While ast.Name.id represents 'x'.
        """
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

        Notes:
        ------
        In the following "x = 1 + 2", the ast.BinOp node represents Binary Operation itself. \n
        ast.BinOp.value outputs "BinOp(left=Num(n=1), op=Add(), right=Num(n=2))" : \n
            ast.BinOp.left node represents '1'. \n
            ast.BinOp.op node represents 'Add()'. \n
            ast.BinOp.right node represents '2'. \n
        While ast.Name.id represents 'x'.
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

        Notes:
        ------
        In the following "x = True and False", the ast.BoolOp node represents Boolean Operation itself. \n
        ast.BoolOp.values outputs "BoolOp(values=[NameConstant(value=True), NameConstant(value=False)])" : \n
            ast.BoolOp.values[0] node represents 'True'. \n
            ast.BoolOp.values[1] node represents 'False'. \n
        While ast.Name.id represents 'x'.
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

        Notes:
        ------
        In the following "x = some_func(1, 2)", the ast.Call node represents the function call itself. \n
        ast.Call.func outputs "Name(id='some_func', ctx=Load())" : \n
            ast.Call.func.id node represents 'some_func'. \n
            ast.Call.args[0] node represents '1'. \n
            ast.Call.args[1] node represents '2'. \n
        While ast.Name.id represents 'x'.
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

        Notes:
        ------
        In the following "x = 1 < 2", the ast.Compare node represents the comparison itself. \n
        ast.Compare.left outputs "Num(n=1)" : \n
            ast.Compare.left node represents '1'. \n
            ast.Compare.ops[0] node represents 'Lt()'. \n
            ast.Compare.comparators[0] node represents '2'. \n
        While ast.Name.id represents 'x'.
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

        Notes:
        ------
        In the following "x = 1", the ast.Expr node represents the expression itself. \n
        ast.Expr.value outputs "Num(n=1)" : \n
            ast.Expr.value node represents '1'. \n
        While ast.Name.id represents 'x'.\n \n
        The difference between ast.Expr and ast.Expression is that ast.Expr is a statement, while ast.Expression is an expression. \n
        For example, "x = 1" is a statement, while "1" is an expression.
        """
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

        Notes:
        ------
        In the following "x = 1 if True else 2", the ast.IfExp node represents the if expression itself. \n
        ast.IfExp.body outputs "Num(n=1)" : \n
            ast.IfExp.body node represents '1'. \n
            ast.IfExp.test node represents 'True'. \n
            ast.IfExp.orelse node represents '2'. \n
        While ast.Name.id represents 'x'.
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

    def visit_NamedExpr(self, node: ast.NamedExpr):
        """Visit the namedexpr node.

        Parameters:
        -----------
        node : ast.NamedExpr
            The namedexpr node to visit.

        Notes:
        ------
        In the following "x := 1", the ast.NamedExpr node represents the named expression itself. \n
        ast.NamedExpr.value outputs "Num(n=1)" : \n
            ast.NamedExpr.value node represents '1'. \n
        While ast.Name.id represents 'x'.
        """
        return
        # Add the namedexpr node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="NamedExpr",
            node_label="NamedExpr",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the namedexpr node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        """Visit the unaryop node.

        Parameters:
        -----------
        node : ast.UnaryOp
            The unaryop node to visit.

        Notes:
        ------
        In the following "-x", the ast.UnaryOp node represents the unary operation itself. \n
        ast.UnaryOp.operand outputs "Name(id='x')" : \n
            ast.UnaryOp.operand node represents 'x'. \n
            ast.UnaryOp.op node represents 'USub()'. \n
        While ast.Name.id represents 'x'.
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

    # endregion

    # region Expression - Comprehensions
    def visit_DictComp(self, node: ast.DictComp):
        """Visit the dictcomp node.

        Parameters:
        -----------
        node : ast.DictComp
            The dictcomp node to visit.

        Notes:
        ------
        In the following "squares = {x: x**2 for x in range(1, 6)}", the ast.DictComp node represents the dictionary comprehension itself. \n
        ast.DictComp.key outputs "Name(id='x')" : \n
            ast.DictComp.key node represents 'x'. \n
            ast.DictComp.value node represents an ast.BinOp node 'BinOp()'. \n
            ast.DictComp.generators node represents 'comprehension()'. \n
        While ast.Name.id represents 'squares'.
        """
        return
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

        Notes:
        ------
        In the following "squares = (x**2 for x in range(1, 6))", the ast.GeneratorExp node represents the generator expression itself. \n
        ast.GeneratorExp.elt outputs "BinOp()" : \n
            ast.GeneratorExp.elt node represents 'BinOp()'. \n
            ast.GeneratorExp.generators node represents 'comprehension()'. \n
        While ast.Name.id represents 'squares'.
        """
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

        Notes:
        ------
        In the following "squares = [x**2 for x in range(1, 6)]", the ast.ListComp node represents the list comprehension itself. \n
        ast.ListComp.elt outputs "BinOp()" : \n
            ast.ListComp.elt node represents a ast.BinOp node 'BinOp()'. \n
            ast.ListComp.generators node represents 'comprehension()'. \n
        While ast.Name.id represents 'squares'.
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

        Notes:
        ------
        In the following "squares = {x**2 for x in range(1, 6)}", the ast.SetComp node represents the set comprehension itself. \n
        ast.SetComp.elt outputs "BinOp()" : \n
            ast.SetComp.elt node represents a ast.BinOp node 'BinOp()'. \n
            ast.SetComp.generators node represents 'comprehension()'. \n
        While ast.Name.id represents 'squares'.
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

    # endregion

    # region Expression - Subscripting
    def visit_Slice(self, node: ast.Slice):
        """Visit the slice node.

        Parameters:
        -----------
        node : ast.Slice
            The slice node to visit.

        Notes:
        ------
        In the following "x[1:2]", the ast.Slice node represents the slice itself. \n
        ast.Slice.lower outputs "Constant(value=1)" : \n
            ast.Slice.lower node represents 'Constant(value=1)'. \n
            ast.Slice.upper node represents 'Constant(value=2)'. \n
            ast.Slice.step node represents 'None'. \n
        While ast.Name.id represents 'x'.
        """
        return
        # Add the slice node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Slice",
            node_label="Slice",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the slice node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        """Visit the subscript node.

        Parameters:
        -----------
        node : ast.Subscript
            The subscript node to visit.

        Notes:
        ------
        In the following "x[1:2]", the ast.Subscript node represents the subscript itself. \n
        ast.Subscript.value outputs "Name(id='x')" : \n
            ast.Subscript.value node represents an ast.Name node Name(id='x'). \n
            ast.Subscript.slice node represents an ast.Slice node 'Slice()'. \n
        While ast.Name.id represents 'x'.
        """
        return
        # Add the subscript node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Subscript",
            node_label="Subscript",
            node_parent_id=id(self.current_parent),
        )
        # Set the current parent to the subscript node
        self.current_parent = node
        # Visit the children
        self.generic_visit(node)

    # endregion

    # region Statements
    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit the annotated assignment node.

        Parameters:
        -----------
        node : ast.AnnAssign
            The annotated assignment node to visit.

        Notes:
        ------
        In the following "x: int = 1", the ast.AnnAssign node represents the annotated assignment itself. \n
        ast.AnnAssign.target outputs "Name(id='x')" : \n
            ast.AnnAssign.target node represents an ast.Name node Name(id='x'). \n
            ast.AnnAssign.annotation node represents 'Name(id='int')'. \n
            ast.AnnAssign.value node represents 'Constant(value=1)'. \n
        While ast.Name.id represents 'x'.
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

    def visit_Assert(self, node: ast.Assert):
        """Visit the assert node.

        Parameters:
        -----------
        node : ast.Assert
            The assert node to visit.

        Notes:
        ------
        In the following "assert x == 1", the ast.Assert node represents the assert itself. \n
        ast.Assert.test outputs "Compare()" : \n
            ast.Assert.test node represents a ast.Compare node 'Compare()'. \n
            ast.Assert.msg node represents 'None'. \n
        While ast.Name.id represents 'x'.
        """
        self.generic_visit(node)
        return
        # Add the assert node to the graph
        self.graph.add_node(
            id(node),
            type="Assert",
            label="Assert",
            parent=id(self.current_parent),
        )
        # Add an edge from the current parent to the assert node
        self.graph.add_edge(id(self.current_parent), id(node))
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the assert node
        self.current_parent = node
        # Visit the assert's children
        self.generic_visit(node)
        # Set the current parent back to the assert's parent
        self.current_parent = old_parent

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

        Notes:
        ------
        In the following "x = 1", the ast.Assign node represents the assignment itself. \n
        ast.Assign.targets outputs "Name(id='x')" : \n
            ast.Assign.targets node represents an ast.Name node Name(id='x'). \n
            ast.Assign.value node represents 'Constant(value=1)'. \n
        While ast.Name.id represents 'x'.
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

        Notes:
        ------
        In the following "x += 1", the ast.AugAssign node represents the augmented assignment itself. \n
        ast.AugAssign.target outputs "Name(id='x')" : \n
            ast.AugAssign.target node represents an ast.Name node Name(id='x'). \n
            ast.AugAssign.op node represents an ast.Add node 'Add()'. \n
            ast.AugAssign.value node represents an ast.Constant node 'Constant(value=1)'. \n
        While ast.Name.id represents 'x'.
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

    def visit_Delete(self, node: ast.Delete):
        """Visit the delete node.

        Parameters:
        -----------
        node : ast.Delete
            The delete node to visit.

        Notes:
        ------
        In the following "del x", the ast.Delete node represents the delete itself. \n
        ast.Delete.targets outputs "Name(id='x')" : \n
            ast.Delete.targets node represents an ast.Name node Name(id='x'). \n
        While ast.Name.id represents 'x'.
        """
        # Add the delete node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Delete",
            node_label="del",
            node_parent_id=id(self.current_parent),
        )

    def visit_Pass(self, node: ast.Pass):
        """Visit the pass node.

        Parameters:
        -----------
        node : ast.Pass
            The pass node to visit.

        Notes:
        ------
        In the following "def my_func(): pass", the ast.Pass node represents the pass itself. \n
        ast.Pass has no children.
        """

    def visit_Raise(self, node: ast.Raise):
        """Visit the raise node.

        Parameters:
        -----------
        node : ast.Raise
            The raise node to visit.

        Notes:
        ------
        In the following "raise Exception()", the ast.Raise node represents the raise itself. \n
        ast.Raise.exc outputs "Name(id='Exception')" : \n
            ast.Raise.exc node represents an ast.Name node Name(id='Exception'). \n
        While ast.Name.id represents 'Exception'.
        """
        # Add the raise node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Raise",
            node_label="raise",
            node_parent_id=id(self.current_parent),
        )

    # endregion

    # region Statements - Imports
    def visit_Import(self, node: ast.Import):
        """Visit the import node.

        Parameters:
        -----------
        node : ast.Import
            The import node to visit.

        Notes:
        ------
        In the following "import os", the ast.Import node represents the import itself. \n
        ast.Import.names outputs "alias(name='os')" : \n
            ast.Import.names node represents an ast.alias node alias(name='os'). \n
        While ast.alias.name represents 'os'.
        """
        return
        # Add the import node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Import",
            node_label="import",
            node_parent_id=id(self.current_parent),
        )

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit the import from node.

        Parameters:
        -----------
        node : ast.ImportFrom
            The import from node to visit.

        Notes:
        ------
        In the following "from os import path", the ast.ImportFrom node represents the import from itself. \n
        ast.ImportFrom.module outputs "os" : \n
            ast.ImportFrom.module node represents an ast.Module node for os. \n
        """
        return
        # Add the import from node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="ImportFrom",
            node_label="import from",
            node_parent_id=id(self.current_parent),
        )

    # endregion

    # region Control Flow
    def visit_Break(self, node: ast.Break):
        """Visit the break node.

        Parameters:
        -----------
        node : ast.Break
            The break node to visit.

        Notes:
        ------
        In the following "while True: break", the ast.Break node represents the break itself. \n
        ast.Break has no children.
        """
        return
        # Add the break node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Break",
            node_label="break",
            node_parent_id=id(self.current_parent),
        )

    def visit_Continue(self, node: ast.Continue):
        """Visit the continue node.

        Parameters:
        -----------
        node : ast.Continue
            The continue node to visit.

        Notes:
        ------
        In the following "while True: continue", the ast.Continue node represents the continue itself. \n
        ast.Continue has no children.
        """
        return
        # Add the continue node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Continue",
            node_label="continue",
            node_parent_id=id(self.current_parent),
        )

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Visit the except handler node.

        Parameters:
        -----------
        node : ast.ExceptHandler
            The except handler node to visit.

        Notes:
        ------
        In the following "try: except Exception as e: pass", the ast.ExceptHandler node represents the except handler itself. \n
        ast.ExceptHandler.type outputs "Name(id='Exception')" : \n
            ast.ExceptHandler.type node represents an ast.Name node Name(id='Exception'). \n
        While ast.Name.id represents 'Exception'.
        """
        # Add the except handler node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="ExceptHandler",
            node_label="except",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the except handler node
        self.current_parent = node
        # Visit the except handler's children
        self.generic_visit(node)
        # Set the current parent back to the except handler's parent
        self.current_parent = old_parent

    def visit_For(self, node: ast.For):
        """Visit the for node.

        Parameters:
        -----------
        node : ast.For
            The for node to visit.

        Notes:
        ------
        In the following "for i in range(10): pass", the ast.For node represents the for itself. \n
            ast.For.target node represents an ast.Name node Name(id='i'). \n
            ast.For.iter node represents an ast.Call node Call(func=Name(id='range'), args=[Num(n=10)], keywords=[]).
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

        Notes:
        ------
        In the following "if x==z: pass", the ast.If node represents the if itself. \n
            ast.If.test node represents an ast.Compare node Compare(left=Name(id='x'), ops=[Eq()], comparators=[Name(id='z')]).
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

        Notes:
        ------
        In the following "try: x += 5" except: pass else: print(worked) finally: print(done), the ast.Try node represents the try itself. \n
            ast.Try.body represents the contents of try, in this case an ast.Assign node. \n
            ast.Try.handlers represents the except handlers, in this case an ast.ExceptHandler node. \n
            ast.Try.orelse represents the else clause of the try, in this case an ast.Expr node. \n
            ast.Try.finalbody represents the finally clause of the try, in this case an ast.Expr node.
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

        Notes:
        ------
        In the following "while x < 10: y + 5", the ast.While node represents the while itself. \n
            ast.While.test node represents an ast.Compare node for 'x < 10'. \n
            ast.While.body represents the contents of the while, in this case an ast.Expr node.
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

        Notes:
        ------
        In the following "with open('file.txt', 'r') as f: f.read()", the ast.With node represents the with itself. \n
            ast.With.items represents the context managers, in this case an ast.withitem node. \n
            ast.With.body represents the contents of the with, in this case an ast.Expr node.
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

    # endregion

    # region Pattern Matching
    def visit_Match(self, node: ast.Match):
        """Visit the match node.

        Parameters:
        -----------
        node : ast.Match
            The match node to visit.

        Notes:
        ------
        In the following "match x: case 1: pass", the ast.Match node represents the match itself. \n
            ast.Match.cases represents the cases of the match, in this case an ast.MatchCase node.
        """
        return
        # Add the match node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Match",
            node_label="match",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the match node
        self.current_parent = node
        # Visit the match's children
        self.generic_visit(node)
        # Set the current parent back to the match's parent
        self.current_parent = old_parent

    def visit_MatchAs(self, node: ast.MatchAs):
        """Visit the match as node.

        Parameters:
        -----------
        node : ast.MatchAs
            The match as node to visit.

        Notes:
        ------
        In the following "match x: case 1 as y: pass", the ast.MatchAs node represents the match as itself. \n
            ast.MatchAs.pattern represents the pattern of the match as, in this case an ast.Name node. \n
            ast.MatchAs.name represents the name of the match as, in this case an ast.Name node.
        """
        return
        # Add the match as node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="MatchAs",
            node_label="match as",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the match as node
        self.current_parent = node
        # Visit the match as's children
        self.generic_visit(node)
        # Set the current parent back to the match as's parent
        self.current_parent = old_parent

    def visit_MatchClass(self, node: ast.MatchClass):
        """Visit the match class node.

        Parameters:
        -----------
        node : ast.MatchClass
            The match class node to visit.

        Notes:
        ------
        In the following "match x: case A(y): pass", the ast.MatchClass node represents the match class itself. \n
            ast.MatchClass.pattern represents the pattern of the match class, in this case an ast.Call node.
        """
        return
        # Add the match class node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="MatchClass",
            node_label="match class",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the match class node
        self.current_parent = node
        # Visit the match class's children
        self.generic_visit(node)
        # Set the current parent back to the match class's parent
        self.current_parent = old_parent

    def visit_MatchMapping(self, node: ast.MatchMapping):
        """Visit the match mapping node.

        Parameters:
        -----------
        node : ast.MatchMapping
            The match mapping node to visit.

        Notes:
        ------
        In the following "match x: case {1: y}: pass", the ast.MatchMapping node represents the match mapping itself. \n
            ast.MatchMapping.pattern represents the pattern of the match mapping, in this case an ast.Dict node.
        """
        return
        # Add the match mapping node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="MatchMapping",
            node_label="match mapping",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the match mapping node
        self.current_parent = node
        # Visit the match mapping's children
        self.generic_visit(node)
        # Set the current parent back to the match mapping's parent
        self.current_parent = old_parent

    def visit_MatchOr(self, node: ast.MatchOr):
        """Visit the match or node.

        Parameters:
        -----------
        node : ast.MatchOr
            The match or node to visit.

        Notes:
        ------
        In the following "match x: case 1 | 2: pass", the ast.MatchOr node represents the match or itself. \n
            ast.MatchOr.left represents the left side of the match or, in this case an ast.Constant node. \n
            ast.MatchOr.right represents the right side of the match or, in this case an ast.Constant node.
        """
        return
        # Add the match or node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="MatchOr",
            node_label="match or",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the match or node
        self.current_parent = node
        # Visit the match or's children
        self.generic_visit(node)
        # Set the current parent back to the match or's parent
        self.current_parent = old_parent

    def visit_MatchSequence(self, node: ast.MatchSequence):
        """Visit the match sequence node.

        Parameters:
        -----------
        node : ast.MatchSequence
            The match sequence node to visit.

        Notes:
        ------
        In the following "match x: case [1, 2]: pass", the ast.MatchSequence node represents the match sequence itself. \n
            ast.MatchSequence.pattern represents the pattern of the match sequence, in this case an ast.List node.
        """
        return
        # Add the match sequence node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="MatchSequence",
            node_label="match sequence",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the match sequence node
        self.current_parent = node
        # Visit the match sequence's children
        self.generic_visit(node)
        # Set the current parent back to the match sequence's parent
        self.current_parent = old_parent

    def visit_MatchSingleton(self, node: ast.MatchSingleton):
        """Visit the match singleton node.

        Parameters:
        -----------
        node : ast.MatchSingleton
            The match singleton node to visit.

        Notes:
        ------
        In the following "match x: case 1: pass", the ast.MatchSingleton node represents the match singleton itself. \n
            ast.MatchSingleton.pattern represents the pattern of the match singleton, in this case an ast.Constant node.
        """
        return
        # Add the match singleton node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="MatchSingleton",
            node_label="match singleton",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the match singleton node
        self.current_parent = node
        # Visit the match singleton's children
        self.generic_visit(node)
        # Set the current parent back to the match singleton's parent
        self.current_parent = old_parent

    def visit_MatchStar(self, node: ast.MatchStar):
        """Visit the match star node.

        Parameters:
        -----------
        node : ast.MatchStar
            The match star node to visit.

        Notes:
        ------
        In the following "match x: case [1, *y]: pass", the ast.MatchStar node represents the match star itself. \n
            ast.MatchStar.pattern represents the pattern of the match star, in this case an ast.List node.
        """
        return
        # Add the match star node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="MatchStar",
            node_label="match star",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the match star node
        self.current_parent = node
        # Visit the match star's children
        self.generic_visit(node)
        # Set the current parent back to the match star's parent
        self.current_parent = old_parent

    def visit_MatchValue(self, node: ast.MatchValue):
        """Visit the match value node.

        Parameters:
        -----------
        node : ast.MatchValue
            The match value node to visit.

        Notes:
        ------
        In the following "match x: case 1: pass", the ast.MatchValue node represents the match value itself. \n
            ast.MatchValue.pattern represents the pattern of the match value, in this case an ast.Constant node.
        """
        return
        # Add the match value node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="MatchValue",
            node_label="match value",
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the match value node
        self.current_parent = node
        # Visit the match value's children
        self.generic_visit(node)
        # Set the current parent back to the match value's parent
        self.current_parent = old_parent

    # endregion

    # region Functions and Class Definitions
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit the class node.

        Parameters:
        -----------
        node : ast.ClassDef
            The class node to visit.

        Notes:
        ------
        In the following "class A(baseClass): def __init__(self, a:int=5): self.x=a*2", the ast.ClassDef node represents the class itself. \n
            ast.ClassDef.name represents the name of the class, in this case 'A'. \n
            ast.ClassDef.bases represents the base classes, in this case 'baseClass'. \n
            ast.ClassDef.keywords represents the keyword arguments, in this case an ast.arg node to represent 'self' and 'a'. \n
            ast.ClassDef.body represents the contents of the class, in this case an ast.FunctionDef node for '__init__'.
        """
        # Add the class node to the graph
        # current_parent should be a module node, unless it's a sub class
        self.create_new_node(
            node_id=id(node),
            node_type="ClassDef",
            node_label=node.name,
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the class node
        # because now we'll be visiting the class' children
        self.current_parent = node
        # # Save the previous current_class
        # previous_class = self.current_class
        # # Set the current_class
        # self.current_class = node
        # Visit the class' children
        self.generic_visit(node)
        # Set the current parent back to the class' parent
        # we've finished visiting the class' children, so go back to class' parent
        self.current_parent = old_parent
        # # Restore the previous current_class
        # self.current_class = previous_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit the function node.

        Parameters:
        -----------
        node : ast.FunctionDef
            The function node to visit.

        Notes:
        ------
        In the following "def func(a:int=5): b = a*2 return b", the ast.FunctionDef node represents the function itself. \n
            ast.FunctionDef.name represents the name of the function, in this case 'func'. \n
            ast.FunctionDef.args represents the arguments, in this case an ast.arg node to represent 'a'. \n
            ast.FunctionDef.body represents the contents of the function, in this case an ast.Assign node for 'b = a*2' and an ast.Return node.
        """
        # function_parent: nx.DiGraph
        # if self.current_class:
        #     function_parent = self.current_class
        # else:
        #     if self.current_module:
        #         function_parent = self.current_module
        #     else:
        #         function_parent = self.current_parent
        # Add the function node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="FunctionDef",
            node_label=node.name,
            node_parent_id=id(self.current_parent),
        )
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the function node
        self.current_parent = node
        # # Save the previous current_function
        # previous_function = self.current_function
        # # Set the current_function
        # self.current_function = node
        # Visit the function's children
        self.generic_visit(node)
        # Set the current parent back to the function's parent
        self.current_parent = old_parent
        # # Restore the previous current_function
        # self.current_function = previous_function

    def visit_Global(self, node: ast.Global):
        """Visit the global node.

        Parameters:
        -----------
        node : ast.Global
            The global node to visit.

        Notes:
        ------
        In the following "global a b", the ast.Global node represents the global itself. \n
        ast.Global doesn't have any children nodes to represent 'a' and 'b'.
        """
        # Add the global node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Global",
            node_label="global",
            node_parent_id=id(self.current_parent),
        )

    def visit_Lambda(self, node: ast.Lambda):
        """Visit the lambda node.

        Parameters:
        -----------
        node : ast.Lambda
            The lambda node to visit.

        Notes:
        ------
        In the following "lambda a: a*2", the ast.Lambda node represents the lambda itself. \n
            ast.Lambda.args represents the arguments, in this case an ast.arg node to represent 'a'. \n
            ast.Lambda.body represents the contents of the lambda, in this case an ast.BinOp node for 'a*2'.
        """
        return
        # Add the lambda node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Lambda",
            node_label="lambda",
            node_parent_id=id(self.current_parent),
        )

    def visit_Nonlocal(self, node: ast.Nonlocal):
        """Visit the nonlocal node.

        Parameters:
        -----------
        node : ast.Nonlocal
            The nonlocal node to visit.

        Notes:
        ------
        In the following "nonlocal a b", the ast.Nonlocal node represents the nonlocal itself. \n
        ast.Nonlocal doesn't have any children nodes to represent 'a' and 'b'.
        """
        return
        # Add the nonlocal node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Nonlocal",
            node_label="nonlocal",
            node_parent_id=id(self.current_parent),
        )

    def visit_Return(self, node: ast.Return):
        """Visit the return node.

        Parameters:
        -----------
        node : ast.Return
            The return node to visit.

        Notes:
        ------
        In the following "return a", the ast.Return node represents the return itself. \n
            ast.Return.value represents the value to return, in this case an ast.Name node for 'a'.
        """
        # Add the return node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Return",
            node_label="return",
            node_parent_id=id(self.current_parent),
        )

    def visit_Yield(self, node: ast.Yield):
        """Visit the yield node.

        Parameters:
        -----------
        node : ast.Yield
            The yield node to visit.

        Notes:
        ------
        In the following "yield a", the ast.Yield node represents the yield itself. \n
            ast.Yield.value represents the value to yield, in this case an ast.Name node for 'a'.
        """
        return
        # Add the yield node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Yield",
            node_label="yield",
            node_parent_id=id(self.current_parent),
        )

    def visit_YieldFrom(self, node: ast.YieldFrom):
        """Visit the yield from node.

        Parameters:
        -----------
        node : ast.YieldFrom
            The yield from node to visit.

        Notes:
        ------
        In the following "yield from a", the ast.YieldFrom node represents the yield from itself. \n
            ast.YieldFrom.value represents the value to yield from, in this case an ast.Name node for 'a'.
        """
        return
        # Add the yield from node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="YieldFrom",
            node_label="yield from",
            node_parent_id=id(self.current_parent),
        )

    # endregion

    # region Async and Await
    def visit_AsyncFor(self, node: ast.AsyncFor):
        """Visit the async for node.

        Parameters:
        -----------
        node : ast.AsyncFor
            The async for node to visit.

        Notes:
        ------
        In the following "async for a in b: a+5", the ast.AsyncFor node represents the async for itself. \n
            ast.AsyncFor.target represents the target of the async for, in this case an ast.Name node for 'a'. \n
            ast.AsyncFor.iter represents the iterable of the async for, in this case an ast.Name node for 'b'. \n
            ast.AsyncFor.body represents the contents of the async for, in this case an ast.BinOp node for 'a+5'.
        """
        return
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

        Notes:
        ------
        In the following "async def a(b): b+5", the ast.AsyncFunctionDef node represents the async function itself. \n
            ast.AsyncFunctionDef.name represents the name of the async function, in this case an ast.Name node for 'a'. \n
            ast.AsyncFunctionDef.args represents the arguments of the async function, in this case an ast.arguments node for 'b'. \n
            ast.AsyncFunctionDef.body represents the contents of the async function, in this case an ast.BinOp node for 'b+5'.
        """
        return
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

        Notes:
        ------
        In the following "async with a as b: b+5", the ast.AsyncWith node represents the async with itself. \n
            ast.AsyncWith.items represents the items of the async with, in this case an ast.withitem node for 'a as b'. \n
            ast.AsyncWith.body represents the contents of the async with, in this case an ast.BinOp node for 'b+5'.
        """
        return
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

    def visit_Await(self, node: ast.Await):
        """Visit the await node.

        Parameters:
        -----------
        node : ast.Await
            The await node to visit.

        Notes:
        ------
        In the following "await a", the ast.Await node represents the await itself. \n
            ast.Await.value represents the value to await, in this case an ast.Name node for 'a'.
        """
        return
        # Add the await node to the graph
        self.create_new_node(
            node_id=id(node),
            node_type="Await",
            node_label="await",
            node_parent_id=id(self.current_parent),
        )

    # endregion
