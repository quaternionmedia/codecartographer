import ast
from .base_ast import BaseASTVisitor


class PythonAST(BaseASTVisitor):
    def __init__(self, module_list: list = [], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.module_list = module_list

    # region Visits

    # region Mode
    def visit_Expression(self, node):
        self.generic_visit(node)
        self.expressions.append(node)

    def visit_FunctionType(self, node):
        self.generic_visit(node)
        self.functiontypes.append(node)

    def visit_Interactive(self, node):
        self.generic_visit(node)
        self.interactives.append(node)

    def visit_Module(self, node):
        """Visit the module node."""
        self.module = node
        # see if the module is in the module list
        # module list is a list of names of modules
        if self.module and self.module_list:
            self.generic_visit(node)

    # endregion

    # region Literals
    def visit_Constant(self, node):
        self.generic_visit(node)
        self.constats.append(node)

    def visit_Dict(self, node):
        """Visit the dict node."""
        self.generic_visit(node)
        self.dicts.append(node)

    def visit_FormattedValue(self, node):
        self.generic_visit(node)
        self.formattedvalues.append(node)

    def visit_Invert(self, node):
        self.generic_visit(node)
        self.inverts.append(node)

    def visit_JoinedStr(self, node):
        self.generic_visit(node)
        self.joinedstrs.append(node)

    def visit_List(self, node):
        """Visit the list node."""
        self.generic_visit(node)
        self.lists.append(node)

    def visit_Set(self, node):
        self.generic_visit(node)
        self.sets.append(node)

    def visit_Tuple(self, node):
        self.generic_visit(node)
        self.tuples.append(node)

    def visit_UAdd(self, node):
        self.generic_visit(node)
        self.uaddss.append(node)

    def visit_USub(self, node):
        self.generic_visit(node)
        self.usubss.append(node)

    # endregion

    # region Variables
    def visit_Name(self, node):
        self.generic_visit(node)
        self.names.append(node)

    def visit_Store(self, node):
        self.generic_visit(node)
        self.stores.append(node)

    def visit_Starred(self, node):
        self.generic_visit(node)
        self.starreds.append(node)

    def visit_arg(self, node: ast.arg):
        self.generic_visit(node)
        self.starreds.append(node)
        pass
        # """Visit the arg node.

        # Parameters:
        # -----------
        # node : ast.arg
        #     The arg node to visit.

        # Notes:
        # ------
        # In the following "def some_func(x):", the ast.arg node represents 'x'. \n
        # While ast.Name.id represents 'some_func'.
        # """

        # # Add the arg node to the graph
        # _type: str = None
        # if self.current_type:
        #     _type = self.current_type
        # else:
        #     _type = "Variable"
        # self.create_new_node(
        #     node_id=id(node),
        #     node_type=_type,
        #     node_label=node.arg,
        #     node_parent_id=id(self.current_parent),
        # )
        # # Set the current parent to the arg node
        # self.current_parent = node

    # endregion

    # region Expressions
    def visit_Attribute(self, node):
        self.generic_visit(node)
        self.attribuetes.append(node)

    def visit_BinOp(self, node):
        self.generic_visit(node)
        self.binops.append(node)

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        self.boolops.append(node)

    def visit_Call(self, node):
        self.generic_visit(node)
        self.calls.append(node)

    def visit_Compare(self, node):
        self.generic_visit(node)
        self.comparisons.append(node)

    def visit_Expr(self, node):
        self.generic_visit(node)
        self.exprs.append(node)

    def visit_IfExp(self, node):
        self.generic_visit(node)
        self.ifexps.append(node)

    def visit_NamedExpr(self, node):
        self.generic_visit(node)
        self.namedexprs.append(node)

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        self.uarynops.append(node)

    # endregion

    # region Expressions - Comprehensions
    def visit_DictComp(self, node):
        self.generic_visit(node)
        self.dictcomps.append(node)

    def visit_GeneratorExp(self, node):
        self.generic_visit(node)
        self.generatorexps.append(node)

    def visit_ListComp(self, node):
        self.generic_visit(node)
        self.listcomps.append(node)

    def visit_SetComp(self, node):
        self.generic_visit(node)
        self.setcomps.append(node)

    # endregion

    # region Expressions - Subscripting
    def visit_Slice(self, node):
        self.generic_visit(node)
        self.slices.append(node)

    def visit_Subscript(self, node):
        self.generic_visit(node)
        self.subscripts.append(node)

    # endregion

    # region Statements
    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        self.annassigns.append(node)

    def visit_Assert(self, node):
        self.generic_visit(node)
        self.asserts.append(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variables.append(target.id)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        self.augassigns.append(node)

    def visit_Delete(self, node):
        self.generic_visit(node)
        self.deletes.append(node)

    def visit_Pass(self, node):
        self.generic_visit(node)
        self.passes.append(node)

    def visit_Raise(self, node):
        self.generic_visit(node)
        self.raises.append(node)

    # endregion

    # region Statements - Imports
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        # see if any of the imports are in the module list
        for module in self.module_list:
            if module in self.imports:
                self.relations.append((self.module, module))
                self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        # see if any of the imports are in the module list
        for module in self.module_list:
            if module in self.imports:
                self.relations.append((self.module, module))
                self.generic_visit(node)

    # endregion

    # region Control Flow
    def visit_Break(self, node):
        self.generic_visit(node)
        self.breaks.append(node)

    def visit_Continue(self, node):
        self.generic_visit(node)
        self.continues.append(node)

    def visit_ExceptHandler(self, node):
        self.generic_visit(node)
        self.excepthandlers.append(node)

    def visit_For(self, node):
        self.generic_visit(node)
        self.forloops.append(node)

    def visit_If(self, node):
        self.generic_visit(node)
        self.ifs.append(node)

    def visit_Try(self, node):
        self.generic_visit(node)
        self.trys.append(node)

    def visit_TryStar(self, node):
        self.generic_visit(node)
        self.trystars.append(node)

    def visit_While(self, node):
        self.generic_visit(node)
        self.whileloops.append(node)

    def visit_With(self, node):
        self.generic_visit(node)
        self.withs.append(node)

    # endregion

    # region Pattern Matching
    def visit_Match(self, node):
        self.generic_visit(node)
        self.matches.append(node)

    def visit_MatchAs(self, node):
        self.generic_visit(node)
        self.matchases.append(node)

    def visit_MatchClass(self, node):
        self.generic_visit(node)
        self.matchclasses.append(node)

    def visit_MatchMapping(self, node):
        self.generic_visit(node)
        self.matchmappings.append(node)

    def visit_MatchOr(self, node):
        self.generic_visit(node)
        self.machors.append(node)

    def visit_MatchSequence(self, node):
        self.generic_visit(node)
        self.matchsequences.append(node)

    def visit_MatchSingleton(self, node):
        self.generic_visit(node)
        self.matchsingleton.append(node)

    def visit_MatchStar(self, node):
        self.generic_visit(node)
        self.matchstars.append(node)

    def visit_MatchValue(self, node):
        self.generic_visit(node)
        self.matchvalues.append(node)

    # endregion

    # region Functions and Class Definitions
    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.relations.append((base.id, node.name))
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_Global(self, node):
        self.generic_visit(node)
        self.globals.append(node)

    def visit_Lambda(self, node):
        self.generic_visit(node)
        self.lambdas.append(node)

    def visit_Nonlocal(self, node):
        self.generic_visit(node)
        self.nonlocals.append(node)

    def visit_Return(self, node):
        self.generic_visit(node)
        self.returns.append(node)

    def visit_Yield(self, node):
        self.generic_visit(node)
        self.yields.append(node)

    def visit_YieldFrom(self, node):
        self.generic_visit(node)
        self.yieldfroms.append(node)

    # endregion

    # region Async and Await
    def visit_AsyncFor(self, node):
        self.generic_visit(node)
        self.asyncforloops.append(node)

    def visit_AsyncFunctionDef(self, node):
        self.asyncfunctions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.generic_visit(node)
        self.asyncwiths.append(node)

    def visit_Await(self, node):
        self.generic_visit(node)
        self.awaits.append(node)

    # endregion

    # region Other - String Comparisons
    def visit_And(self, node):
        self.generic_visit(node)
        self.ands.append(node)

    def visit_In(self, node):
        self.generic_visit(node)
        self.ins.append(node)

    def visit_NotIn(self, node):
        self.generic_visit(node)
        self.notins.append(node)

    def visit_Is(self, node):
        self.generic_visit(node)
        self.iss.append(node)

    def visit_IsNot(self, node):
        self.generic_visit(node)
        self.isnots.append(node)

    def visit_Not(self, node):
        self.generic_visit(node)
        self.nots.append(node)

    def visit_Or(self, node):
        self.generic_visit(node)
        self.ors.append(node)

    # endregion

    # region Other - File Handling
    def visit_Load(self, node):
        self.generic_visit(node)
        self.loads.append(node)

    def visit_Del(self, node):
        self.generic_visit(node)
        self.dels.append(node)

    # endregion

    # region Other - Binary Operations
    def visit_Add(self, node):
        self.generic_visit(node)
        self.adds.append(node)

    def visit_BitAnd(self, node):
        self.generic_visit(node)
        self.bitands.append(node)

    def visit_BitOr(self, node):
        self.generic_visit(node)
        self.bitors.append(node)

    def visit_BitXor(self, node):
        self.generic_visit(node)
        self.bitxors.append(node)

    def visit_FloorDiv(self, node):
        self.generic_visit(node)
        self.floordivs.append(node)

    def visit_Div(self, node):
        self.generic_visit(node)
        self.divs.append(node)

    def visit_LShift(self, node):
        self.generic_visit(node)
        self.lshifts.append(node)

    def visit_MatMult(self, node):
        self.generic_visit(node)
        self.matmults.append(node)

    def visit_Mod(self, node):
        self.generic_visit(node)
        self.mods.append(node)

    def visit_Mult(self, node):
        self.generic_visit(node)
        self.mults.append(node)

    def visit_Pow(self, node):
        self.generic_visit(node)
        self.pows.append(node)

    def visit_RShift(self, node):
        self.generic_visit(node)
        self.rshifts.append(node)

    def visit_Sub(self, node):
        self.generic_visit(node)
        self.subs.append(node)

    # endregion

    # region Other - Binary Comparisons
    def visit_Eq(self, node):
        self.generic_visit(node)
        self.eqss.append(node)

    def visit_NotEq(self, node):
        self.generic_visit(node)
        self.not_eqss.append(node)

    def visit_Lt(self, node):
        self.generic_visit(node)
        self.lts.append(node)

    def visit_LtE(self, node):
        self.generic_visit(node)
        self.ltes.append(node)

    def visit_Gt(self, node):
        self.generic_visit(node)
        self.gts.append(node)

    def visit_GtE(self, node):
        self.generic_visit(node)
        self.gtes.append(node)

    # endregion

    # region Other - Type Aliases
    def visit_ParamSpec(self, node):
        self.generic_visit(node)
        self.paramspecs.append(node)

    def visit_TypeIgnore(self, node):
        self.generic_visit(node)
        self.typeignores.append(node)

    def visit_TypeVar(self, node):
        self.generic_visit(node)
        self.typevars.append(node)

    def visit_TypeVarTuple(self, node):
        self.generic_visit(node)
        self.typevartuples.append(node)

    # endregion

    # endregion
