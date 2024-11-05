import ast
import uuid
import networkx as nx
from abc import abstractmethod


class ASTVisitor(ast.NodeVisitor):
    @abstractmethod
    def visit(self, node) -> ast.AST:
        pass


class BaseASTVisitor(ast.NodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """The base AST visitor"""
        # Define the base lists for node types
        self.module = None
        self.variables = []
        self.interactives = []
        self.expressions = []
        self.functiontypes = []
        self.functions = []
        self.asyncfunctions = []
        self.classes = []

        # Initialize the DiGraph
        self.graph = nx.DiGraph()

    def getNodeTypes(self) -> dict:
        return {
            "interactive": self.interactives,
            "expression": self.expressions,
            "function": self.functions,
            "asyncfunction": self.asyncfunctions,
            "class": self.classes,
            "variables": self.variables,
            "functiontype": self.functiontypes,
        }

    def create_node(self, label, node_type, module, parent=None, args=None):
        """Helper function to create a node in the graph."""
        node_id = str(uuid.uuid4())
        self.graph.add_node(
            node_id,
            label=label,
            type=node_type,
            module=module,
            parent=parent,
            args=args or [],
        )
        if parent:
            self.graph.add_edge(parent, node_id)
        return node_id


class PythonAST(BaseASTVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def visit_Module(self, node):
        module_id = self.create_node("HelloWorld.py", "Module", None)
        self.module = module_id
        self.generic_visit(node)  # Continue traversing child nodes
        return module_id

    def visit_ClassDef(self, node):
        class_id = self.create_node(node.name, "Class", self.module, parent=self.module)
        self.classes.append(class_id)
        for child in node.body:
            self.visit(child)  # Continue traversing child nodes
        return class_id

    def visit_FunctionDef(self, node):
        func_id = self.create_node(
            node.name,
            "Function",
            self.module,
            parent=self.graph.nodes[self.module]["id"],
        )
        self.functions.append(func_id)
        for arg in node.args.args:
            self.visit(arg)  # Traverse function arguments
        for child in node.body:
            self.visit(child)  # Continue traversing child nodes
        return func_id

    def visit_arg(self, node):
        arg_id = self.create_node(
            node.arg,
            "Argument",
            self.module,
            parent=self.graph.nodes[self.module]["id"],
        )
        self.variables.append(arg_id)
        return arg_id

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call):
            call_id = self.create_node(
                "print", "Call", self.module, parent=self.graph.nodes[self.module]["id"]
            )
            for arg in node.value.args:
                self.visit(arg)  # Traverse arguments of the call
            return call_id

    def visit_JoinedStr(self, node):
        joined_str_id = self.create_node(
            "format_str",
            "JoinedStr",
            self.module,
            parent=self.graph.nodes[self.module]["id"],
        )
        for value in node.values:
            self.visit(value)  # Traverse values in the formatted string
        return joined_str_id

    def visit_FormattedValue(self, node):
        formatted_value_id = self.create_node(
            "FormattedValue",
            "FormattedValue",
            self.module,
            parent=self.graph.nodes[self.module]["id"],
        )
        self.visit(node.value)  # Traverse the value inside the formatted string
        return formatted_value_id

    def visit_Name(self, node):
        name_id = self.create_node(
            node.id, "Name", self.module, parent=self.graph.nodes[self.module]["id"]
        )
        return name_id

    def visit_Constant(self, node):
        const_id = self.create_node(
            "Constant",
            "Constant",
            self.module,
            parent=self.graph.nodes[self.module]["id"],
        )
        return const_id
