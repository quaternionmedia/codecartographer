"""The links between a Python file's functions and variables: what each calls, and how values flow.

The Python parser draws a file's classes and functions, and below them the
names, arguments, calls and constants each one holds. A function's use of a
module-level name is told apart from holding it in `PythonLanguageParser`; the
two links the source states and the tree does not are read here, with `ast`,
from the same source (`links`):

- **calls** -- a function or method to a function, method or class of the same
  module it calls: `f()`, `self.m()`, `Cls()`.
- **flows** -- a variable to each variable assigned from it: `y = f(x)`,
  `y += x`, `for y in x`, `with x as y` each give x -> y. Inside a function
  and at the module's top level alike.

**A VARIABLE IS ONE NODE PER MODULE.** The parser names a variable
`module.name`, whichever function it is in (`python_custom_ast.create_node`),
so a flow joins those names: two functions that each have an `x` share one
node, and a flow in either is drawn from it. A link is returned by those ids,
and kept only where both ends were parsed, to the depth asked for.
"""

from __future__ import annotations

import ast

_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _stored(target: ast.AST) -> list[str]:
    """The names an assignment target binds: `a`, `a, b`, `[a, *b]`."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for item in target.elts for name in _stored(item)]
    if isinstance(target, ast.Starred):
        return _stored(target.value)
    return []


def _loaded(value: ast.AST | None) -> list[str]:
    """The names an expression reads."""
    if value is None:
        return []
    return [node.id for node in ast.walk(value) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)]


def _flows(body: list[ast.stmt]) -> set[tuple[str, str]]:
    """(source, target) for each value assigned from another in `body`, not
    looking inside the functions and classes it defines."""
    out: set[tuple[str, str]] = set()

    def visit(statements: list[ast.stmt]) -> None:
        for stmt in statements:
            pairs: list[tuple[list[str], list[str]]] = []
            if isinstance(stmt, ast.Assign):
                pairs.append((_loaded(stmt.value), [n for t in stmt.targets for n in _stored(t)]))
            elif isinstance(stmt, ast.AnnAssign):
                pairs.append((_loaded(stmt.value), _stored(stmt.target)))
            elif isinstance(stmt, ast.AugAssign):
                pairs.append((_loaded(stmt.value), _stored(stmt.target)))
            elif isinstance(stmt, (ast.For, ast.AsyncFor)):
                pairs.append((_loaded(stmt.iter), _stored(stmt.target)))
            elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                for item in stmt.items:
                    if item.optional_vars is not None:
                        pairs.append((_loaded(item.context_expr), _stored(item.optional_vars)))
            for sources, targets in pairs:
                out.update((s, t) for s in sources for t in targets if s != t)
            for field in ("body", "orelse", "finalbody", "handlers"):
                inner = getattr(stmt, field, None)
                if isinstance(inner, list) and not isinstance(stmt, (*_FUNCTIONS, ast.ClassDef)):
                    visit([s for s in inner if isinstance(s, ast.stmt)] +
                          [s for h in inner if isinstance(h, ast.ExceptHandler) for s in h.body])

    visit(body)
    return out


def _calls(function: ast.AST, defined: set[str], methods: set[str]) -> set[str]:
    """The module's functions and classes, and its class's methods, `function` calls."""
    called: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in defined:
            called.add(func.id)
        elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
              and func.value.id in ("self", "cls") and func.attr in methods):
            called.add(func.attr)
    return called


def links(raw: str, module: str) -> set[tuple[str, str, str]]:
    """(source id, target id, kind) for each call and each flow `raw` states,
    by the ids `PythonLanguageParser` gives (`module.name`). A source that does
    not parse states none."""
    try:
        tree = ast.parse(raw)
    except (SyntaxError, ValueError):
        return set()
    node_id = lambda name: f"{module}.{name}"  # noqa: E731
    defined = {stmt.name for stmt in tree.body if isinstance(stmt, (*_FUNCTIONS, ast.ClassDef))}
    out: set[tuple[str, str, str]] = set()

    def function(fn: ast.AST, methods: set[str]) -> None:
        for callee in _calls(fn, defined, methods):
            if callee != fn.name:
                out.add((node_id(fn.name), node_id(callee), "calls"))
        out.update((node_id(s), node_id(t), "flows") for s, t in _flows(fn.body))
        for inner in fn.body:
            if isinstance(inner, _FUNCTIONS):
                function(inner, methods)

    for stmt in tree.body:
        if isinstance(stmt, _FUNCTIONS):
            function(stmt, set())
        elif isinstance(stmt, ast.ClassDef):
            methods = {item.name for item in stmt.body if isinstance(item, _FUNCTIONS)}
            for item in stmt.body:
                if isinstance(item, _FUNCTIONS):
                    function(item, methods)
    out.update((node_id(s), node_id(t), "flows") for s, t in _flows(tree.body))
    return out
