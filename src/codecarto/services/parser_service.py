import ast

from networkx import DiGraph
from models.graph_data import Node, Edge, GraphBuilder
from models.source_data import Folder, File, SourceData
from random import randint
from services.ASTs.base_ast import BaseASTVisitor


class ParserService:
    def __init__(
        self, visitor: BaseASTVisitor, graph_builder: GraphBuilder = GraphBuilder()
    ):
        self.visitor = visitor
        self.graph_builder = graph_builder
        self.module_list = []

    def parse(self, source: SourceData) -> DiGraph:
        """Parse the source code to a graph.

        Parameters:
        -----------
        source: SourceData
            The source code data to parse.

        Returns:
        --------
        DiGraph
            The parsed graph.
        """
        # Set the current parent to the source name
        self.current_parent = id(source.name)

        # Add the source name to the module list
        self.module_list.append(source.name)

        # Parse the Python code to AST
        if isinstance(source.source[0], File):
            parsed_ast = self.parse_py_to_ast(source.source[0].raw)
            self.visitor.generic_visit(parsed_ast)

        return self.create_graph()

    def parse_py_to_ast(self, python_code: str):
        return ast.parse(python_code)

    def create_graph(self) -> DiGraph:
        try:
            # Define types and corresponding attributes
            node_types = {
                "interactive": self.visitor.interactives,
                "expression": self.visitor.expressions,
                "function": self.visitor.functions,
                "asyncfunction": self.visitor.asyncfunctions,
                "class": self.visitor.classes,
                "return": self.visitor.returns,
                "delete": self.visitor.deletes,
                "assign": self.visitor.assigns,
                "typealias": self.visitor.typealiases,
                "augassign": self.visitor.augassigns,
                "annassign": self.visitor.annassigns,
                "forloop": self.visitor.forloops,
                "asyncforloop": self.visitor.asyncforloops,
                "whileloop": self.visitor.whileloops,
                "if": self.visitor.ifs,
                "with": self.visitor.withs,
                "asyncwith": self.visitor.asyncwiths,
                "match": self.visitor.matches,
                "raise": self.visitor.raises,
                "try": self.visitor.trys,
                "trystar": self.visitor.trystars,
                "assert": self.visitor.asserts,
                "import": self.visitor.imports,
                "importfrom": self.visitor.importfroms,
                "global": self.visitor.globals,
                "nonlocal": self.visitor.nonlocals,
                "expr": self.visitor.exprs,
                "pass": self.visitor.passes,
                "break": self.visitor.breaks,
                "continue": self.visitor.continues,
                "boolop": self.visitor.boolops,
                "namedexpr": self.visitor.namedexprs,
                "binop": self.visitor.binops,
                "unaryop": self.visitor.uarynops,
                "lambda": self.visitor.lambdas,
                "ifexp": self.visitor.ifexps,
                "dict": self.visitor.dicts,
                "set": self.visitor.sets,
                "listcomp": self.visitor.listcomps,
                "setcomp": self.visitor.setcomps,
                "dictcomp": self.visitor.dictcomps,
                "generatorexp": self.visitor.generatorexps,
                "await": self.visitor.awaits,
                "yield": self.visitor.yields,
                "yieldfrom": self.visitor.yieldfroms,
                "comparison": self.visitor.comparisons,
                "call": self.visitor.calls,
                "formattedvalue": self.visitor.formattedvalues,
                "joinedstr": self.visitor.joinedstrs,
                "constant": self.visitor.constats,
                "attribute": self.visitor.attribuetes,
                "subscript": self.visitor.subscripts,
                "starred": self.visitor.starreds,
                "name": self.visitor.names,
                "list": self.visitor.lists,
                "tuple": self.visitor.tuples,
                "slice": self.visitor.slices,
                "load": self.visitor.loads,
                "store": self.visitor.stores,
                "del": self.visitor.dels,
                "and": self.visitor.ands,
                "or": self.visitor.ors,
                "add": self.visitor.adds,
                "sub": self.visitor.subs,
                "mult": self.visitor.mults,
                "matmult": self.visitor.matmults,
                "div": self.visitor.divs,
                "mod": self.visitor.mods,
                "pow": self.visitor.pows,
                "lshift": self.visitor.lshifts,
                "rshift": self.visitor.rshifts,
                "bitor": self.visitor.bitors,
                "bitxor": self.visitor.bitxors,
                "bitand": self.visitor.bitands,
                "floordiv": self.visitor.floordivs,
                "invert": self.visitor.inverts,
                "not": self.visitor.nots,
                "uadd": self.visitor.uaddss,
                "usub": self.visitor.usubss,
                "eq": self.visitor.eqss,
                "not_eq": self.visitor.not_eqss,
                "lt": self.visitor.lts,
                "lte": self.visitor.ltes,
                "gt": self.visitor.gts,
                "gte": self.visitor.gtes,
                "is": self.visitor.iss,
                "isnot": self.visitor.isnots,
                "in": self.visitor.ins,
                "notin": self.visitor.notins,
                "excepthandler": self.visitor.excepthandlers,
                "matchvalue": self.visitor.matchvalues,
                "matchsingleton": self.visitor.matchsingleton,
                "matchsequence": self.visitor.matchsequences,
                "matchmapping": self.visitor.matchmappings,
                "matchclass": self.visitor.matchclasses,
                "matchstar": self.visitor.matchstars,
                "matchas": self.visitor.matchases,
                "machor": self.visitor.machors,
                "typeignore": self.visitor.typeignores,
                "typevar": self.visitor.typevars,
                "paramspec": self.visitor.paramspecs,
                "typevartuple": self.visitor.typevartuples,
                "relation": self.visitor.relations,
                "variables": self.visitor.variables,
            }

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
        node_parent_id: int | None,
    ):
        # Check params
        if not node_label or node_label == "":
            node_label = f"{node_type} (u)"

        # Add the node
        graph.add_node(
            node_id,
            type=node_type,
            label=f"{node_label}: {node_type}",
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
