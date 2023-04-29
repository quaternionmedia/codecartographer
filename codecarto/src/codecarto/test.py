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
        self.graph: nx.DiGraph = nx.DiGraph()  # The graph to populate
        self.current_parent = None  # To track the current parent node
        self.current_file = None  # To track the current file

        # Create root and python graphs
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
        self.source_files: list = source_files

        # Parse the code & package files
        self.parse_list(source_files)

    def parse_list(self, source_files:list) -> nx.DiGraph:
        """Parse the codes in the list.

        Parameters:
        -----------
        source_files : list
            A list of source files to parse.
        """ 
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
        with open(file_path, "r") as f:
            code = f.read()
        tree = ast.parse(code, filename=file_path)
        self.visit(tree) 
  
# Mode
    # def visit_Expression(self, node : ast.Expression):
    # def visit_FunctionType(self, node: ast.FunctionType): 
    # def visit_Interactive(self, node : ast.Interactive):  
    def visit_Module(self, node : ast.Module):
        """Visit the module node.

        Parameters:
        -----------
        node : ast.Module
            The module node to visit.
        """
        # Add the module node to the graph
        self.graph.add_node(
            id(node), type="Module", label=os.path.basename(self.current_file), base="module", parent=id(self.root)
        )
        # Add an edge from the current parent to the module node
        self.graph.add_edge(id(self.current_parent), id(node))
        # Set the current parent to the module node
        self.current_parent = node
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
 
# Literals
    # def visit_Constant(self, node : ast.Constant):
    # def visit_Dict(self, node : ast.Dict):
    # def visit_FormattedValue(self, node : ast.FormattedValue):
    # def visit_JoinedStr(self, node : ast.JoinedStr):
    # def visit_List(self, node : ast.List):
    # def visit_Set(self, node : ast.Set):
    # def visit_Tuple(self, node : ast.Tuple):
 
# Variables
    # def visit_Name(self, node : ast.Name):
    # def visit_Store(self, node : ast.Store):
    # def visit_Starred(self, node : ast.Starred):
 
# Expressions 
    # def visit_Attribute(self, node : ast.Attribute):
    # def visit_BinOp(self, node : ast.BinOp):
    # def visit_BoolOp(self, node : ast.BoolOp):
    def visit_Call(self, node : ast.Call):
        """Visit the call node.

        Parameters:
        -----------
        node : ast.Call
            The call node to visit.
        """
        # Add the call node to the graph
        self.graph.add_node(
            id(node), type="Call", label="Call", base="call", parent=id(self.current_parent)
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
    # def visit_Compare(self, node : ast.Compare):
    # def visit_Expr(self, node : ast.Expr):
    # def visit_IfExp(self, node : ast.IfExp):
    # def visit_NamedExpr(self, node : ast.NamedExpr):
    # def visit_UnaryOp(self, node : ast.UnaryOp):
#   Subscripting
        # def visit_Slice(self, node : ast.Slice):
        # def visit_Subscript(self, node : ast.Subscript): 
#   Comprehensions
        # def visit_DictComp(self, node : ast.DictComp):
        # def visit_GeneratorExp(self, node : ast.GeneratorExp):
        # def visit_ListComp(self, node : ast.ListComp):
        # def visit_SetComp(self, node : ast.SetComp): 
 
# Statements
    # def visit_AnnAssign(self, node : ast.AnnAssign):
    # def visit_Assert(self, node : ast.Assert):
    # def visit_Assign(self, node : ast.Assign): 
    # def visit_AugAssign(self, node : ast.AugAssign):
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
    # def visit_For(self, node : ast.For):
    # def visit_If(self, node : ast.If):
    # def visit_Try(self, node : ast.Try):
    # def visit_TryStar(self, node : ast.TryStar):
    # def visit_While(self, node : ast.While):
    # def visit_With(self, node : ast.With):
 
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
    def visit_ClassDef(self, node : ast.ClassDef):
        """Visit the class node.

        Parameters:
        -----------
        node : ast.ClassDef
            The class node to visit.
        """
        # Add the class node to the graph
        self.graph.add_node(
            id(node), type="Class", label=node.name, base="class", parent=id(self.current_parent)
        )
        # Add an edge from the current parent to the class node
        self.graph.add_edge(id(self.current_parent), id(node))
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the class node
        self.current_parent = node
        # Visit the class' children
        self.generic_visit(node)
        # Set the current parent back to the class' parent
        self.current_parent = old_parent  
    def visit_FunctionDef(self, node : ast.FunctionDef):
        """Visit the function node.

        Parameters:
        -----------
        node : ast.FunctionDef
            The function node to visit.
        """
        # Add the function node to the graph
        self.graph.add_node(
            id(node), type="Function", label=node.name, base="function", parent=id(self.current_parent)
        )
        # Add an edge from the current parent to the function node
        self.graph.add_edge(id(self.current_parent), id(node))
        # Set the old parent to the current parent
        old_parent = self.current_parent
        # Set the current parent to the function node
        self.current_parent = node
        # Visit the function's children
        self.generic_visit(node)
        # Set the current parent back to the function's parent
        self.current_parent = old_parent
    # def visit_Global(self, node : ast.Global):
    # def visit_Lambda(self, node : ast.Lambda): 
    # def visit_Nonlocal(self, node : ast.Nonlocal):
    # def visit_Return(self, node : ast.Return): 
    # def visit_Yield(self, node : ast.Yield): 
    # def visit_YieldFrom(self, node : ast.YieldFrom): 
 
# Async and Await
    # def visit_AsyncFor(self, node : ast.AsyncFor): 
    # def visit_AsyncFunction(self, node : ast.AsyncFunction): 
    # def visit_AsyncWith(self, node : ast.AsyncWith): 
    # def visit_Await(self, node : ast.Await):  