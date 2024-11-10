import os
import ast
import networkx as nx
from typing import Union
from collections import defaultdict
from models.source_data import File, Folder


class BaseASTVisitor(ast.NodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = nx.DiGraph()  # Unified DiGraph for all files
        self.current_parent_id = None
        self.current_function_args = {}
        self.current_module_name = ""
        self.functions = []

        # Cross-file tracking
        self.imports = {}  # Track imports {import_name: full_name}
        self.class_map = {}  # Global reference map {class_name: node_id}
        self.function_map = defaultdict(dict)  # {class_name: {method_name: node_id}}

    def parse(self, folder: Folder) -> nx.DiGraph:
        """Parse each file in the folder individually, then link across modules."""
        for file in folder.files:
            if file.name.endswith(".py"):
                self._parse_file(file)
        self._resolve_cross_module_links()
        return self.graph

    def _parse_file(self, file: File):
        """Parse each file and build its AST in the graph."""
        self.current_module_name = os.path.splitext(file.name)[0]
        self.current_parent_id = None
        self.current_function_args = {}

        tree = ast.parse(file.raw)
        self.visit(tree)

    def create_node(self, label, node_type, module, parent=None):
        """Helper to create a node in the graph with unique ID."""
        node_id = f"{module}.{label}"
        if not self.graph.has_node(node_id):
            self.graph.add_node(
                node_id,
                label=label,
                type=node_type,
                module=module,
                parent=parent,
            )
        if parent:
            self.graph.add_edge(parent, node_id)
        return node_id

    def _resolve_cross_module_links(self):
        """Link imports and resolve method calls across modules."""
        for import_name, full_name in self.imports.items():
            importing_module_id = (
                f"{self.current_module_name}.{self.current_module_name}"
            )
            if full_name in self.graph:
                import_node_id = self.create_node(
                    import_name,
                    "Import",
                    self.current_module_name,
                )
                self.graph.add_edge(importing_module_id, import_node_id)
                self.graph.add_edge(import_node_id, full_name)


class PythonCustomAST(BaseASTVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def visit_Module(self, node):
        module_id = self.create_node(
            self.current_module_name,
            "Module",
            self.current_module_name,
        )
        self.module = module_id
        previous_parent_id = self.current_parent_id
        self.current_parent_id = module_id
        self.generic_visit(node)
        self.current_parent_id = previous_parent_id
        return module_id

    def visit_ImportFrom(self, node):
        """Handles 'from module import name' statements."""
        for alias in node.names:
            import_name = alias.name
            full_name = f"{node.module}.{import_name}"
            self.imports[import_name] = full_name

            # Create an import node to track cross-file imports
            import_node_id = self.create_node(
                full_name,
                "Import",
                self.current_module_name,
                parent=self.current_parent_id,
            )
            self.graph.add_edge(
                f"{self.current_module_name}.{self.current_module_name}",
                import_node_id,
            )
            self.graph.add_edge(
                import_node_id,
                f"{node.module}.{node.module}",
            )

    def visit_ClassDef(self, node):
        class_id = self.create_node(
            node.name,
            "Class",
            self.current_module_name,
            parent=self.current_parent_id,
        )
        module_node_id = f"{self.current_module_name}.{self.current_module_name}"
        self.graph.add_edge(module_node_id, class_id)

        # Register class in global map
        self.class_map[node.name] = class_id

        previous_parent_id = self.current_parent_id
        self.current_parent_id = class_id

        # Handle inheritance links
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in self.imports:
                imported_class = self.imports[base.id]
                self.graph.add_edge(class_id, imported_class)
                self.class_map[node.name] = (
                    imported_class  # Avoid duplicating HelloWorld in Greetings
                )

        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                func_id = self.create_node(
                    child.name,
                    "Function",
                    self.current_module_name,
                    parent=class_id,
                )
                self.function_map[node.name][child.name] = func_id
            self.visit(child)

        self.current_parent_id = previous_parent_id
        return class_id

    def visit_FunctionDef(self, node):
        func_id = self.create_node(
            node.name,
            "Function",
            self.current_module_name,
            parent=self.current_parent_id,
        )
        self.functions.append(func_id)
        previous_parent_id = self.current_parent_id
        self.current_parent_id = func_id

        self.current_function_args = {}
        for arg in node.args.args:
            arg_id = self.visit(arg)
            self.current_function_args[arg.arg] = arg_id

        for stmt in node.body:
            self.visit(stmt)

        self.current_function_args = {}
        self.current_parent_id = previous_parent_id
        return func_id

    def visit_Expr(self, node):
        """Track calls within expressions."""
        if isinstance(node.value, ast.Call):
            call_name = ""
            if isinstance(node.value.func, ast.Attribute):
                # Attempt to resolve the class the method belongs to
                base_name = (
                    node.value.func.value.id
                    if isinstance(node.value.func.value, ast.Name)
                    else None
                )
                method_name = node.value.func.attr
                call_name = f"{base_name}.{method_name}" if base_name else method_name

                if base_name in self.imports:
                    imported_class_full_name = self.imports[base_name]
                    imported_method_full_name = (
                        f"{imported_class_full_name}.{method_name}"
                    )

                    if imported_class_full_name in self.class_map:
                        actual_method_id = self.function_map.get(
                            imported_class_full_name, {}
                        ).get(method_name)
                        if actual_method_id:
                            self.graph.add_edge(
                                self.current_parent_id, actual_method_id
                            )
                            return actual_method_id

            # Local or unresolved function call
            call_id = self.create_node(
                call_name,
                "Call",
                self.current_module_name,
                parent=self.current_parent_id,
            )
            previous_parent_id = self.current_parent_id
            self.current_parent_id = call_id
            for arg in node.value.args:
                self.visit(arg)
            self.current_parent_id = previous_parent_id
            return call_id

    def visit_Name(self, node):
        if node.id in self.imports:
            import_id = self.imports[node.id]
            self.graph.add_edge(self.current_parent_id, import_id)
            return import_id
        name_id = self.create_node(
            node.id,
            "Name",
            self.current_module_name,
            parent=self.current_parent_id,
        )
        return name_id

    def visit_arg(self, node):
        arg_id = self.create_node(
            node.arg,
            "Argument",
            self.current_module_name,
            parent=self.current_parent_id,
        )
        return arg_id

    def visit_JoinedStr(self, node):
        joined_str_id = self.create_node(
            "JoinedStr",
            "JoinedStr",
            self.current_module_name,
            parent=self.current_parent_id,
        )
        previous_parent_id = self.current_parent_id
        self.current_parent_id = joined_str_id
        for value in node.values:
            self.visit(value)
        self.current_parent_id = previous_parent_id
        return joined_str_id

    def visit_FormattedValue(self, node):
        formatted_value_id = self.create_node(
            "FormattedValue",
            "FormattedValue",
            self.current_module_name,
            parent=self.current_parent_id,
        )
        previous_parent_id = self.current_parent_id
        self.current_parent_id = formatted_value_id
        self.visit(node.value)
        self.current_parent_id = previous_parent_id
        return formatted_value_id

    def visit_For(self, node):
        for_id = self.create_node(
            "ForLoop",
            "For",
            self.current_module_name,
            parent=self.current_parent_id,
        )
        previous_parent_id = self.current_parent_id
        self.current_parent_id = for_id
        self.visit(node.target)
        self.visit(node.iter)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)
        self.current_parent_id = previous_parent_id
        return for_id

    def visit_Constant(self, node):
        label = f"Const: {repr(node.value)}"
        const_id = self.create_node(
            label,
            "Constant",
            self.current_module_name,
            parent=self.current_parent_id,
        )
        return const_id
