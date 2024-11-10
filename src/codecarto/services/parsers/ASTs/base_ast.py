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
        self.variables: list[str] = []
        self.relations: list[tuple[str, str]] = []
        # define the type of list List<AST>
        self.args: list[ast.arg] = []
        self.interactives: list[ast.Interactive] = []
        self.expressions: list[ast.Expression] = []
        self.functiontypes: list[ast.FunctionType] = []
        self.functions: list[ast.FunctionDef] = []
        self.asyncfunctions: list[ast.AsyncFunctionDef] = []
        self.classes: list[ast.ClassDef] = []
        self.returns: list[ast.Return] = []
        self.deletes: list[ast.Delete] = []
        self.assigns: list[ast.Assign] = []
        self.typealiases: list[ast.TypeAlias] = []
        self.augassigns: list[ast.AugAssign] = []
        self.annassigns: list[ast.AnnAssign] = []
        self.forloops: list[ast.For] = []
        self.asyncforloops: list[ast.AsyncFor] = []
        self.whileloops: list[ast.While] = []
        self.ifs: list[ast.If] = []
        self.withs: list[ast.With] = []
        self.asyncwiths: list[ast.AsyncWith] = []
        self.matches: list[ast.Match] = []
        self.raises: list[ast.Raise] = []
        self.trys: list[ast.Try] = []
        self.trystars: list[ast.TryStar] = []
        self.asserts: list[ast.Assert] = []
        self.imports: list[ast.Import] = []
        self.importfroms: list[ast.ImportFrom] = []
        self.globals: list[ast.Global] = []
        self.nonlocals: list[ast.Nonlocal] = []
        self.exprs: list[ast.Expr] = []
        self.passes: list[ast.Pass] = []
        self.breaks: list[ast.Break] = []
        self.continues: list[ast.Continue] = []
        self.boolops: list[ast.BoolOp] = []
        self.namedexprs: list[ast.NamedExpr] = []
        self.binops: list[ast.BinOp] = []
        self.uarynops: list[ast.UnaryOp] = []
        self.lambdas: list[ast.Lambda] = []
        self.ifexps: list[ast.IfExp] = []
        self.dicts: list[ast.Dict] = []
        self.sets: list[ast.Set] = []
        self.listcomps: list[ast.ListComp] = []
        self.setcomps: list[ast.SetComp] = []
        self.dictcomps: list[ast.DictComp] = []
        self.generatorexps: list[ast.GeneratorExp] = []
        self.awaits: list[ast.Await] = []
        self.yields: list[ast.Yield] = []
        self.yieldfroms: list[ast.YieldFrom] = []
        self.comparisons: list[ast.Compare] = []
        self.calls: list[ast.Call] = []
        self.formattedvalues: list[ast.FormattedValue] = []
        self.joinedstrs: list[ast.JoinedStr] = []
        self.constats: list[ast.Constant] = []
        self.attribuetes: list[ast.Attribute] = []
        self.subscripts: list[ast.Subscript] = []
        self.starreds: list[ast.Starred] = []
        self.names: list[ast.Name] = []
        self.lists: list[ast.List] = []
        self.tuples: list[ast.Tuple] = []
        self.slices: list[ast.Slice] = []
        self.loads: list[ast.Load] = []
        self.stores: list[ast.Store] = []
        self.dels: list[ast.Del] = []
        self.ands: list[ast.And] = []
        self.ors: list[ast.Or] = []
        self.adds: list[ast.Add] = []
        self.subs: list[ast.Sub] = []
        self.mults: list[ast.Mult] = []
        self.matmults: list[ast.MatMult] = []
        self.divs: list[ast.Div] = []
        self.mods: list[ast.Mod] = []
        self.pows: list[ast.Pow] = []
        self.lshifts: list[ast.LShift] = []
        self.rshifts: list[ast.RShift] = []
        self.bitors: list[ast.BitOr] = []
        self.bitxors: list[ast.BitXor] = []
        self.bitands: list[ast.BitAnd] = []
        self.floordivs: list[ast.FloorDiv] = []
        self.inverts: list[ast.Invert] = []
        self.nots: list[ast.Not] = []
        self.uaddss: list[ast.UAdd] = []
        self.usubss: list[ast.USub] = []
        self.eqss: list[ast.Eq] = []
        self.not_eqss: list[ast.NotEq] = []
        self.lts: list[ast.Lt] = []
        self.ltes: list[ast.LtE] = []
        self.gts: list[ast.Gt] = []
        self.gtes: list[ast.GtE] = []
        self.iss: list[ast.Is] = []
        self.isnots: list[ast.IsNot] = []
        self.ins: list[ast.In] = []
        self.notins: list[ast.NotIn] = []
        self.excepthandlers: list[ast.ExceptHandler] = []
        self.matchvalues: list[ast.MatchValue] = []
        self.matchsingleton: list[ast.MatchSingleton] = []
        self.matchsequences: list[ast.MatchSequence] = []
        self.matchmappings: list[ast.MatchMapping] = []
        self.matchclasses: list[ast.MatchClass] = []
        self.matchstars: list[ast.MatchStar] = []
        self.matchases: list[ast.MatchAs] = []
        self.matchors: list[ast.MatchOr] = []
        self.typeignores: list[ast.TypeIgnore] = []
        self.typevars: list[ast.TypeVar] = []
        self.paramspecs: list[ast.ParamSpec] = []
        self.typevartuples: list[ast.TypeVarTuple] = []
        # endregion

    def getNodeTypes(self) -> dict:
        return {
            "variables": self.variables,
            "relation": self.relations,
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
            "matchor": self.matchors,
            "typeignore": self.typeignores,
            "typevar": self.typevars,
            "paramspec": self.paramspecs,
            "typevartuple": self.typevartuples,
        }

    # def visit(self, node):
    #     self.generic_visit(node)
    #     return self.module
