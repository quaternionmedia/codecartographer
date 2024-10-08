import ast
from abc import abstractmethod


class ASTVisitor(ast.NodeVisitor):
    @abstractmethod
    def visit(self, node) -> ast.AST:
        pass


class BaseASTVisitor(ast.NodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """The base AST visitor."""
        self.module = ast.AST
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

    # def visit(self, node):
    #     self.generic_visit(node)
    #     return self.module
