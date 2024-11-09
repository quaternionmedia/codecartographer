import ast
from abc import abstractmethod


class ASTVisitor(ast.NodeVisitor):
    @abstractmethod
    def visit(self, node) -> ast.AST:
        pass


class BaseASTVisitor(ast.NodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """The base AST visitor"""
        # region AST objects
        self.module = ast.AST
        # define the type of list List<AST>
        self.variables: list[ast.AST] = []
        self.interactives: list[ast.AST] = []
        self.expressions: list[ast.AST] = []
        self.functiontypes: list[ast.AST] = []
        self.functions: list[ast.AST] = []
        self.asyncfunctions: list[ast.AST] = []
        self.classes: list[ast.AST] = []
        self.returns: list[ast.AST] = []
        self.deletes: list[ast.AST] = []
        self.assigns: list[ast.AST] = []
        self.typealiases: list[ast.AST] = []
        self.augassigns: list[ast.AST] = []
        self.annassigns: list[ast.AST] = []
        self.forloops: list[ast.AST] = []
        self.asyncforloops: list[ast.AST] = []
        self.whileloops: list[ast.AST] = []
        self.ifs: list[ast.AST] = []
        self.withs: list[ast.AST] = []
        self.asyncwiths: list[ast.AST] = []
        self.matches: list[ast.AST] = []
        self.raises: list[ast.AST] = []
        self.trys: list[ast.AST] = []
        self.trystars: list[ast.AST] = []
        self.asserts: list[ast.AST] = []
        self.imports: list[ast.AST] = []
        self.importfroms: list[ast.AST] = []
        self.globals: list[ast.AST] = []
        self.nonlocals: list[ast.AST] = []
        self.exprs: list[ast.AST] = []
        self.passes: list[ast.AST] = []
        self.breaks: list[ast.AST] = []
        self.continues: list[ast.AST] = []
        self.boolops: list[ast.AST] = []
        self.namedexprs: list[ast.AST] = []
        self.binops: list[ast.AST] = []
        self.uarynops: list[ast.AST] = []
        self.lambdas: list[ast.AST] = []
        self.ifexps: list[ast.AST] = []
        self.dicts: list[ast.AST] = []
        self.sets: list[ast.AST] = []
        self.listcomps: list[ast.AST] = []
        self.setcomps: list[ast.AST] = []
        self.dictcomps: list[ast.AST] = []
        self.generatorexps: list[ast.AST] = []
        self.awaits: list[ast.AST] = []
        self.yields: list[ast.AST] = []
        self.yieldfroms: list[ast.AST] = []
        self.comparisons: list[ast.AST] = []
        self.calls: list[ast.AST] = []
        self.formattedvalues: list[ast.AST] = []
        self.joinedstrs: list[ast.AST] = []
        self.constats: list[ast.AST] = []
        self.attribuetes: list[ast.AST] = []
        self.subscripts: list[ast.AST] = []
        self.starreds: list[ast.AST] = []
        self.names: list[ast.AST] = []
        self.lists: list[ast.AST] = []
        self.tuples: list[ast.AST] = []
        self.slices: list[ast.AST] = []
        self.loads: list[ast.AST] = []
        self.stores: list[ast.AST] = []
        self.dels: list[ast.AST] = []
        self.ands: list[ast.AST] = []
        self.ors: list[ast.AST] = []
        self.adds: list[ast.AST] = []
        self.subs: list[ast.AST] = []
        self.mults: list[ast.AST] = []
        self.matmults: list[ast.AST] = []
        self.divs: list[ast.AST] = []
        self.mods: list[ast.AST] = []
        self.pows: list[ast.AST] = []
        self.lshifts: list[ast.AST] = []
        self.rshifts: list[ast.AST] = []
        self.bitors: list[ast.AST] = []
        self.bitxors: list[ast.AST] = []
        self.bitands: list[ast.AST] = []
        self.floordivs: list[ast.AST] = []
        self.inverts: list[ast.AST] = []
        self.nots: list[ast.AST] = []
        self.uaddss: list[ast.AST] = []
        self.usubss: list[ast.AST] = []
        self.eqss: list[ast.AST] = []
        self.not_eqss: list[ast.AST] = []
        self.lts: list[ast.AST] = []
        self.ltes: list[ast.AST] = []
        self.gts: list[ast.AST] = []
        self.gtes: list[ast.AST] = []
        self.iss: list[ast.AST] = []
        self.isnots: list[ast.AST] = []
        self.ins: list[ast.AST] = []
        self.notins: list[ast.AST] = []
        self.excepthandlers: list[ast.AST] = []
        self.matchvalues: list[ast.AST] = []
        self.matchsingleton: list[ast.AST] = []
        self.matchsequences: list[ast.AST] = []
        self.matchmappings: list[ast.AST] = []
        self.matchclasses: list[ast.AST] = []
        self.matchstars: list[ast.AST] = []
        self.matchases: list[ast.AST] = []
        self.machors: list[ast.AST] = []
        self.typeignores: list[ast.AST] = []
        self.typevars: list[ast.AST] = []
        self.paramspecs: list[ast.AST] = []
        self.typevartuples: list[ast.AST] = []
        self.relations: list[ast.AST] = []
        # endregion

    def getNodeTypes(self) -> dict:
        return {
            "interactive": self.interactives,
            "expression": self.expressions,
            "function": self.functions,
            "asyncfunction": self.asyncfunctions,
            "class": self.classes,
            "return": self.returns,
            "delete": self.deletes,
            "assign": self.assigns,
            "typealias": self.typealiases,
            "augassign": self.augassigns,
            "annassign": self.annassigns,
            "forloop": self.forloops,
            "asyncforloop": self.asyncforloops,
            "whileloop": self.whileloops,
            "if": self.ifs,
            "with": self.withs,
            "asyncwith": self.asyncwiths,
            "match": self.matches,
            "raise": self.raises,
            "try": self.trys,
            "trystar": self.trystars,
            "assert": self.asserts,
            "import": self.imports,
            "importfrom": self.importfroms,
            "global": self.globals,
            "nonlocal": self.nonlocals,
            "expr": self.exprs,
            "pass": self.passes,
            "break": self.breaks,
            "continue": self.continues,
            "boolop": self.boolops,
            "namedexpr": self.namedexprs,
            "binop": self.binops,
            "unaryop": self.uarynops,
            "lambda": self.lambdas,
            "ifexp": self.ifexps,
            "dict": self.dicts,
            "set": self.sets,
            "listcomp": self.listcomps,
            "setcomp": self.setcomps,
            "dictcomp": self.dictcomps,
            "generatorexp": self.generatorexps,
            "await": self.awaits,
            "yield": self.yields,
            "yieldfrom": self.yieldfroms,
            "comparison": self.comparisons,
            "call": self.calls,
            "formattedvalue": self.formattedvalues,
            "joinedstr": self.joinedstrs,
            "constant": self.constats,
            "attribute": self.attribuetes,
            "subscript": self.subscripts,
            "starred": self.starreds,
            "name": self.names,
            "list": self.lists,
            "tuple": self.tuples,
            "slice": self.slices,
            "load": self.loads,
            "store": self.stores,
            "del": self.dels,
            "and": self.ands,
            "or": self.ors,
            "add": self.adds,
            "sub": self.subs,
            "mult": self.mults,
            "matmult": self.matmults,
            "div": self.divs,
            "mod": self.mods,
            "pow": self.pows,
            "lshift": self.lshifts,
            "rshift": self.rshifts,
            "bitor": self.bitors,
            "bitxor": self.bitxors,
            "bitand": self.bitands,
            "floordiv": self.floordivs,
            "invert": self.inverts,
            "not": self.nots,
            "uadd": self.uaddss,
            "usub": self.usubss,
            "eq": self.eqss,
            "not_eq": self.not_eqss,
            "lt": self.lts,
            "lte": self.ltes,
            "gt": self.gts,
            "gte": self.gtes,
            "is": self.iss,
            "isnot": self.isnots,
            "in": self.ins,
            "notin": self.notins,
            "excepthandler": self.excepthandlers,
            "matchvalue": self.matchvalues,
            "matchsingleton": self.matchsingleton,
            "matchsequence": self.matchsequences,
            "matchmapping": self.matchmappings,
            "matchclass": self.matchclasses,
            "matchstar": self.matchstars,
            "matchas": self.matchases,
            "machor": self.machors,
            "typeignore": self.typeignores,
            "typevar": self.typevars,
            "paramspec": self.paramspecs,
            "typevartuple": self.typevartuples,
            "relation": self.relations,
            "variables": self.variables,
        }

    # def visit(self, node):
    #     self.generic_visit(node)
    #     return self.module
