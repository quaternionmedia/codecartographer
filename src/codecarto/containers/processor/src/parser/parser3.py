import ast
from networkx import DiGraph
from pprint import pprint

from src.parser.types.base_ast import BaseASTVisitor
from src.parser.types.python_ast import PythonAST


class Parser:
    graph = DiGraph()
    current_parent = None
    module_list = []

    @classmethod
    def parse(cls, source_dict: dict = None):
        """Parse the source code to a graph.

        Parameters:
        -----------
        source_dict : dict
            The source code to parse.

        Returns:
        --------
        DiGraph
            The parsed graph.
        """
        # Set the current parent to the source name
        cls.current_parent = id(source_dict["name"])

        # Add the source name to the module list
        cls.module_list.append(source_dict["name"])

        # Parse the Python code to AST
        parsed_ast = cls.parse_py_to_ast(source_dict["raw"])

        # Parse the AST to a graph
        graph = cls.parse_ast_to_graph(parsed_ast)

        return graph

    def parse_py_to_ast(python_code):
        # Parse the Python code to AST
        parsed_ast = ast.parse(python_code)

        return parsed_ast

    ###########################################################
    @classmethod
    def parse_ast_to_graph(cls, ast_node):
        visitor: BaseASTVisitor = PythonAST(cls.module_list)
        visitor.generic_visit(ast_node)
        # Add the parsed data to the graph
        cls.add_to_graph(visitor)
        return cls.graph

    @classmethod
    def add_to_graph(cls, visitor: BaseASTVisitor):
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

            # Add nodes and edges to the graph
            ast_with_names = ["function", "class", "import", "variables"]
            for node_type, nodes in node_types.items():
                for node in nodes:
                    # if node in ast_with_names, set label to the name of the node
                    if node_type in ast_with_names:
                        node_label = str(node)
                    else:
                        node_label = node_type

                    # need to pull out relavent info from the node
                    cls.create_node(
                        node_id=id(str(node)),
                        node_type=node_type,
                        node_label=node_label,
                        node_parent_id=id(cls.current_parent),
                    )
                    # add the edge to the parent
                    cls.graph.add_edge(id(cls.current_parent), id(str(node)))
        except Exception as ex:
            print(f"Failed to add to graph: {ex}")
            raise ex

    @classmethod
    def create_node(
        cls,
        node_id: int,
        node_type: str,
        node_label: str,
        node_parent_id: int | None,
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
        cls.graph.add_node(
            node_id,
            type=node_type,
            label=f"{node_label}: {node_type}",
            parent=node_parent_id,
        )
        # Add the edge
        cls.graph.add_edge(node_parent_id, node_id)
