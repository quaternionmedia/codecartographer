"""
Lean Language Parser
====================
Reads Lean 4 source at the declaration level -- what a tokenizer and a bracket
matcher can know without the elaborator -- and emits the unified node schema.

A Lean file is a sequence of commands. Each declaration starts at a keyword
(`theorem`, `def`, `structure`, `inductive`, ...) and runs to the next command,
so a tokenizer finds every declaration, its name, its statement and the names
its statement and proof mention. What it cannot find is anything Lean decides
by elaborating: which instance a class argument resolves to, what `x.f` means
for a local `x`, what a notation or a macro expands to, which names
`to_additive` or `alias` generate. Those belong to Lean, and this module does
not imitate it. Each relation says how it was resolved, so nothing drawn from
a spelling reads as checked.

What is read
------------
theorem      `theorem` and Mathlib's `lemma`; `meta.keyword` says which.
             `meta.statement` is the proposition as written, `meta.proof` is
             `tactic` when the proof opens with `by` and `term` otherwise.
def          `def`; `abbrev` and `opaque` are kinds of their own.
axiom        `axiom`: a proposition taken without proof.
structure    with each field as a child; `class` likewise.
inductive    with each constructor as a child. `meta.enumeration` is set when
             no constructor takes an argument.
instance     named or anonymous; an anonymous one is labelled by its type.
example      an anonymous declaration.
macro        `macro`, `macro_rules`, `syntax`, `notation`, `infix`, `infixl`,
             `infixr`, `prefix`, `postfix`, `elab`, `elab_rules` and
             `declare_syntax_cat`; `meta.keyword` says which.

`meta.sorry` counts the `sorry` and `admit` a declaration holds: a statement
with one is not proved. `meta.qualifiers` keeps the modifiers a declaration
was written with (`private`, `protected`, `noncomputable`, `partial`,
`unsafe`, ...) and `meta.attributes` each `@[..]` entry as written.

A namespace is not a node. Lean reopens one name in any file, so it is a
prefix of the names inside it rather than a thing one place declares:
`meta.qualified` is a declaration's full name, `meta.namespace` the prefix.

Relations, and how each is found
--------------------------------
contains     structure or class -> its fields; inductive -> its constructors.
uses         declaration -> a declaration its statement or body names.
             `part` is `statement`, `body` or `both`: what a theorem is about,
             and what its proof cites. A name is looked up the way Lean
             scopes it -- as written, then through each enclosing namespace
             (`resolution: namespace`), then through each `open`
             (`resolution: open`) -- and a dotted name is tried whole and then
             by its prefixes, so `Nat.succ_le.mp` reaches `Nat.succ_le`. A
             name two declarations in the batch could be draws nothing, unless
             exactly one of them is in the same file.
inherits     structure or class -> each parent after `extends`.
implements   instance -> the class its type begins with.
depends_on   file -> file, from `import A.B.C`, when exactly one file in the
             batch has a path ending in `A/B/C.lean` (`resolution:
             module-path`); file -> an external module named for the import's
             first component otherwise.

What a name inside a declaration is not
---------------------------------------
A binder of the declaration, a `variable` in scope, or a name a `fun`,
`intro`, `have`, `obtain`, `let` or quantifier introduces on its own line is
local, and a reference that begins with one is not looked up. This is a
reading of spellings, not of scopes: a local introduced any other way that
shares a declaration's name is drawn as a use of it.

Where a declaration ends
------------------------
At the next command keyword that begins a line, or follows only a doc
comment, attributes and modifiers that do. A command this module does not
know reads as part of the declaration above it. `open` and `set_option`
indented under a declaration are that declaration's own (`open Classical in`
inside a proof).

Node ID format
--------------
``lean::{file}::{kind}::{qualified name}::{line}`` -- ``file`` is the File's
``url`` or ``name``. A second declaration of one kind and name on one line
takes ``#2`` after its line, and so on.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from typing import ClassVar

import networkx as nx

from codecarto.models.source_data import File
from codecarto.services import construct_service
from codecarto.services.parsers.language_parser import (
    ParserRegistry,
    make_edge,
    make_node,
)

# ── Tokens ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Tok:
    kind: str  # 'ident' | 'literal' | 'punct' | 'doc'
    text: str
    line: int
    col: int
    pos: int
    first: bool  # the first token on its line


# One component of a name: `add_comm'`, `get?`, `x₁`, `«a name»`.
_PART = r"(?:[^\W\d][\w']*[!?]?|«[^»\n]*»)"

_TOKEN = re.compile(
    rf"""
     (?P<ws>\s+)
    |(?P<block>/-)
    |(?P<comment>--[^\n]*)
    |(?P<rawstr>r(?P<hashes>\#+)")
    |(?P<str>"(?:[^"\\]|\\.)*")
    |(?P<char>'(?:[^'\\\n]|\\(?:x[0-9a-fA-F]{{2}}|u[0-9a-fA-F]{{4}}|.))')
    |(?P<binder>[λΠΣ])
    |(?P<hash>\#[a-z_]+)
    |(?P<ident>{_PART}(?:\.{_PART})*)
    |(?P<number>\d\w*(?:\.\d+)?)
    |(?P<punct>:=|=>|::|->|<-|@\[|[^\s\w])
    """,
    re.VERBOSE | re.DOTALL,
)


def tokenize(src: str) -> list[Tok]:
    """Lean source -> tokens. Comments and module docs (`/-! .. -/`) are
    dropped; a doc comment (`/-- .. -/`) is kept as its first line.

    Total on any input: a quote that never closes becomes one punct token and
    reading carries on after it; an unterminated block comment or raw string
    runs to the end of the text.
    """
    toks: list[Tok] = []
    pos, n, line, line_start, last_line = 0, len(src), 1, 0, 0

    def add(kind: str, text: str) -> None:
        nonlocal last_line
        toks.append(Tok(kind, text, line, pos - line_start, pos, line != last_line))
        last_line = line

    while pos < n:
        m = _TOKEN.match(src, pos)
        if m is None:  # a word character no alternative begins with
            add("punct", src[pos])
            end = pos + 1
        else:
            kind, end = m.lastgroup, m.end()
            if kind == "block":
                depth = 1
                while end < n and depth:
                    if src.startswith("/-", end):
                        depth, end = depth + 1, end + 2
                    elif src.startswith("-/", end):
                        depth, end = depth - 1, end + 2
                    else:
                        end += 1
                text = src[pos:end]
                if text.startswith("/--"):
                    body = text[3:-2].strip() if text.endswith("-/") else text[3:].strip()
                    add("doc", body.splitlines()[0].strip() if body else "")
            elif kind == "rawstr":
                closing = src.find('"' + m.group("hashes"), end)
                end = n if closing < 0 else closing + 1 + len(m.group("hashes"))
                add("literal", src[pos:end])
            elif kind in ("str", "char", "number"):
                add("literal", m.group())
            elif kind in ("ident", "hash"):
                add("ident", m.group())
            elif kind in ("punct", "binder"):
                add("punct", m.group())
        newlines = src.count("\n", pos, end)
        if newlines:
            line += newlines
            line_start = src.rfind("\n", pos, end) + 1
        pos = end
    return toks


# ── Commands ──────────────────────────────────────────────────────────────────

# keyword -> the kind its declaration is drawn as.
_DECLARATIONS = {
    "theorem": "theorem", "lemma": "theorem",
    "def": "def", "irreducible_def": "def",
    "abbrev": "abbrev", "opaque": "opaque", "axiom": "axiom",
    "structure": "structure", "class": "class", "inductive": "inductive",
    "instance": "instance", "example": "example",
}
_MACROS = {"macro", "macro_rules", "syntax", "notation", "infix", "infixl", "infixr",
           "prefix", "postfix", "elab", "elab_rules", "declare_syntax_cat"}
_SCOPES = {"namespace", "section", "mutual", "end"}
# Commands that declare nothing drawn here, and end the declaration above them.
_OTHER = {"import", "open", "export", "variable", "universe", "set_option", "attribute",
          "alias", "initialize", "builtin_initialize", "omit", "include", "add_decl_doc",
          "library_note", "assert_not_exists", "run_cmd", "run_meta", "suppress_compilation",
          "unseal", "seal", "register_simp_attr", "register_option",
          "initialize_simps_projections", "compile_inductive", "unif_hint"}
_COMMANDS = set(_DECLARATIONS) | _MACROS | _SCOPES | _OTHER
_MODIFIERS = {"private", "protected", "noncomputable", "partial", "unsafe", "nonrec",
              "local", "scoped", "public", "meta"}
# Indented under a declaration, these are a term's or a tactic's (`open X in`).
_ALSO_TERMS = {"open", "set_option", "omit", "include"}

_OPEN = {"(": ")", "[": "]", "{": "}", "⟨": "⟩", "⦃": "⦄", "@[": "]"}
_CLOSE = set(_OPEN.values())

# After one of these, the names up to the first token that is not a name or a
# bracket, on the same line, are local to the declaration.
_INTRODUCERS = {"fun", "λ", "∀", "∃", "∃!", "Σ", "Π", "∑", "∏", "⋃", "⋂", "intro", "intros",
                "rintro", "obtain", "have", "let", "set", "with", "case", "next", "assume",
                "for", "generalize", "induction", "cases", "rcases"}
_NAME_GLUE = {"(", ")", "⟨", "⟩", ",", "_", "@", "|", "{", "}", "⦃", "⦄"}


@dataclass
class Decl:
    kind: str
    keyword: str
    name: str            # as written; "" for an anonymous instance or an example
    qualified: str       # the full name; "" when there is none
    namespace: tuple[str, ...]
    line: int
    line_end: int = 0
    label: str = ""
    doc: str = ""
    qualifiers: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    statement: str = ""
    proof: str = ""
    sorry: int = 0
    opens: tuple[str, ...] = ()
    locals: frozenset[str] = frozenset()
    refs_statement: set[str] = field(default_factory=set)
    refs_body: set[str] = field(default_factory=set)
    extends: list[str] = field(default_factory=list)
    class_name: str = ""
    children: list["Decl"] = field(default_factory=list)
    enumeration: bool = False
    type_str: str = ""


@dataclass
class _Scope:
    kind: str  # 'file' | 'namespace' | 'section' | 'mutual'
    name: tuple[str, ...] = ()
    opens: list[str] = field(default_factory=list)
    locals: set[str] = field(default_factory=set)


@dataclass
class FileRead:
    decls: list[Decl] = field(default_factory=list)
    imports: list[tuple[str, int]] = field(default_factory=list)


def _parts(name: str) -> tuple[str, ...]:
    return tuple(p for p in name.split(".") if p)


def _squeeze(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class _Reader:
    """One file's tokens, read command by command."""

    def __init__(self, src: str) -> None:
        self.src = src
        self.toks = tokenize(src)

    # -- finding commands -------------------------------------------------------

    def _prefix(self, i: int) -> tuple[int, str, list[str], list[str]]:
        """From *i*, past a doc comment, attributes and modifiers: where the
        keyword would be, and what was passed."""
        toks, n = self.toks, len(self.toks)
        doc, attrs, quals = "", [], []
        while i < n:
            t = toks[i]
            if t.kind == "doc":
                doc = t.text
                i += 1
            elif t.text == "@[":
                j = self._group_end(i, n)
                attrs += self._split_text(i + 1, j - 1)
                i = j
            elif t.kind == "ident" and t.text in _MODIFIERS:
                quals.append(t.text)
                i += 1
                if t.text == "scoped" and i < n and toks[i].text == "[":
                    i = self._group_end(i, n)  # `scoped[NS] notation`
            else:
                break
        return i, doc, attrs, quals

    def _group_end(self, i: int, end: int) -> int:
        """*i* at an opening bracket: the index just past its closing one."""
        toks, stack = self.toks, []
        for k in range(i, end):
            text = toks[k].text
            if text in _OPEN:
                stack.append(_OPEN[text])
            elif stack and text == stack[-1]:
                stack.pop()
                if not stack:
                    return k + 1
        return end

    def _split_text(self, i: int, j: int) -> list[str]:
        """The source between tokens *i* and *j*, split at top-level commas."""
        out, start, depth = [], i, 0
        for k in range(i, j + 1):
            text = self.toks[k].text if k < j else ","
            if k < j and text in _OPEN:
                depth += 1
            elif k < j and text in _CLOSE:
                depth -= 1
            elif text == "," and depth <= 0:
                if k > start:
                    out.append(self._text(start, k, 80))
                start = k + 1
        return out

    def _text(self, i: int, j: int, limit: int = 160) -> str:
        """The source from token *i* up to token *j*, on one line."""
        if i >= j or i >= len(self.toks):
            return ""
        end = self.toks[j].pos if j < len(self.toks) else len(self.src)
        return _squeeze(self.src[self.toks[i].pos:end], limit)

    def commands(self) -> list[tuple[int, int, str, str, list[str], list[str]]]:
        """(start, keyword index, keyword, doc, attributes, qualifiers) for
        each command, in order."""
        toks, n = self.toks, len(self.toks)
        found = []
        decl_col: int | None = None
        i = 0
        while i < n:
            t = toks[i]
            if t.first or (i and toks[i - 1].text == "in"):
                j, doc, attrs, quals = self._prefix(i)
                word = toks[j].text if j < n and toks[j].kind == "ident" else ""
                if word in _COMMANDS or (word.startswith("#") and j == i):
                    inside = decl_col is not None and t.col > decl_col
                    if word in _ALSO_TERMS and inside:
                        i += 1
                        continue
                    found.append((i, j, word, doc, attrs, quals))
                    is_decl = word in _DECLARATIONS or word in _MACROS
                    decl_col = t.col if is_decl else None
                    i = j + 1
                    continue
            i += 1
        return found

    # -- reading a file ---------------------------------------------------------

    def read(self) -> FileRead:
        toks, n = self.toks, len(self.toks)
        out = FileRead()
        scopes = [_Scope("file")]
        pending: list[str] = []  # `open X in`, for the next declaration only
        cmds = self.commands()
        for k, (start, kw, word, doc, attrs, quals) in enumerate(cmds):
            a, b = kw + 1, cmds[k + 1][0] if k + 1 < len(cmds) else n
            namespace = tuple(p for s in scopes for p in s.name)
            if word == "import":
                out.imports += [(t.text, t.line) for t in toks[a:b]
                                if t.kind == "ident" and t.text not in ("all", "public", "meta")]
            elif word == "open":
                names, one_shot = self._opened(a, b)
                # `open B` inside `namespace A` may mean `A.B` or `B`.
                wide = [".".join(namespace[:d] + (name,))
                        for name in names for d in range(len(namespace), -1, -1)]
                if one_shot:
                    pending += wide
                else:
                    scopes[-1].opens += wide
            elif word == "variable":
                scopes[-1].locals |= self._binder_names(a, b)
            elif word == "namespace":
                name = toks[a].text if a < b and toks[a].kind == "ident" else ""
                scopes.append(_Scope("namespace", _parts(name)))
            elif word in ("section", "mutual"):
                scopes.append(_Scope(word))
            elif word == "end":
                if len(scopes) > 1:
                    scopes.pop()
            elif word in _DECLARATIONS or word in _MACROS:
                decl = self._declaration(word, toks[kw].line, a, b, namespace)
                if decl is not None:
                    decl.doc, decl.attributes = doc, attrs
                    decl.qualifiers = quals + decl.qualifiers
                    decl.opens = tuple(o for s in scopes for o in s.opens) + tuple(pending)
                    decl.locals |= frozenset(x for s in scopes for x in s.locals)
                    out.decls.append(decl)
                pending = []
        return out

    def _opened(self, a: int, b: int) -> tuple[list[str], bool]:
        """The namespaces an `open` names, and whether it ends in `in`."""
        toks, names = self.toks, []
        one_shot = b > a and toks[b - 1].text == "in"
        for t in toks[a:b]:
            if t.text == "scoped":
                continue
            if t.kind != "ident" or t.text in ("in", "hiding", "renaming"):
                break
            names.append(t.text)
        return names, one_shot

    def _binder_names(self, a: int, b: int, stop: int | None = None) -> set[str]:
        """The names bound by the bracketed binders in tokens [a, b), read up
        to *stop*: `(x y : T)` and `{α}` bind theirs, `[Foo α]` binds none."""
        toks, names = self.toks, set()
        i, end = a, b if stop is None else stop
        while i < end:
            if toks[i].text in ("(", "{", "⦃", "["):
                j = self._group_end(i, b)
                inner = toks[i + 1:j - 1]
                colon = next((x for x, t in enumerate(inner) if t.text in (":", ":=")), None)
                if colon is not None:
                    inner = inner[:colon]
                elif toks[i].text == "[":
                    inner = []
                names |= {t.text for t in inner if t.kind == "ident" and "." not in t.text}
                i = j
            else:
                i += 1
        return names

    # -- reading one declaration ------------------------------------------------

    def _declaration(self, word: str, line: int, a: int, b: int,
                     namespace: tuple[str, ...]) -> Decl | None:
        toks = self.toks
        if word in _MACROS:
            literal = next((t.text.strip('"').strip() for t in toks[a:b]
                            if t.kind == "literal" and t.text.startswith('"')), "")
            name = toks[a].text if word == "declare_syntax_cat" and a < b else ""
            decl = Decl("macro", word, "", "", namespace, line, label=name or literal or word)
            self._body(decl, a, a, b)
            return decl

        kind, quals = _DECLARATIONS[word], []
        if word == "class" and a < b and toks[a].text in ("inductive", "abbrev"):
            if toks[a].text == "inductive":
                kind = "inductive"
                quals.append("class")
            a += 1

        i, name = a, ""
        if kind == "instance" and i < b and toks[i].text == "(":
            i = self._group_end(i, b)  # `(priority := low)`
        if kind != "example" and i < b and toks[i].kind == "ident" and toks[i].text not in ("where", "extends"):
            name, i = toks[i].text, i + 1
        if not name and kind not in ("instance", "example"):
            return None

        depth = self._depths(a, b)
        heads = (":=", "where", "|") if kind in ("inductive", "structure", "class") else (":=", "where")
        sig_end = next((k for k in range(i, b) if depth[k - a] == 0 and (
            toks[k].text in heads or (toks[k].text == "|" and toks[k].first))), b)
        colon = next((k for k in range(i, sig_end) if depth[k - a] == 0 and toks[k].text == ":"), None)

        rooted = name.startswith("_root_.")
        written = _parts(name[7:] if rooted else name)
        full = written if rooted else namespace + written
        decl = Decl(kind, word, name, ".".join(full) if name else "",
                    full[:-1] if name else namespace, line, qualifiers=quals)
        decl.line_end = toks[b - 1].line if b > a else line
        decl.statement = self._text(colon + 1, sig_end) if colon is not None else ""
        decl.label = name or (_squeeze(decl.statement, 60) if kind == "instance" else kind)
        decl.locals = frozenset(self._binder_names(i, b, colon if colon is not None else sig_end))
        if kind in ("theorem", "example", "instance") and sig_end < b:
            after = toks[sig_end + 1].text if sig_end + 1 < b else ""
            decl.proof = "tactic" if toks[sig_end].text == ":=" and after == "by" else "term"
        self._body(decl, i, sig_end, b)

        if kind in ("structure", "class"):
            at = next((k for k in range(i, sig_end) if depth[k - a] == 0 and toks[k].text == "extends"), None)
            if at is not None:
                stop = colon if colon is not None and colon > at else sig_end
                decl.extends = self._heads(at + 1, stop, depth, a)
            if sig_end < b and toks[sig_end].text != "|":
                decl.children = self._fields(sig_end + 1, b, depth, a, decl)
        if kind == "inductive" or (kind in ("structure", "class") and sig_end < b and toks[sig_end].text == "|"):
            decl.children = self._constructors(sig_end, b, depth, a, decl)
            decl.enumeration = bool(decl.children) and not any(c.type_str for c in decl.children)
        if kind == "instance" and colon is not None and colon + 1 < sig_end:
            head = toks[colon + 1]
            decl.class_name = head.text if head.kind == "ident" else ""
        return decl

    def _depths(self, a: int, b: int) -> list[int]:
        """Bracket depth of each token in [a, b); a bracket has the depth it
        encloses at, so both ends of a group share one."""
        out, stack = [], []
        for t in self.toks[a:b]:
            if stack and t.text == stack[-1]:
                stack.pop()
                out.append(len(stack))
            elif t.text in _OPEN:
                out.append(len(stack))
                stack.append(_OPEN[t.text])
            else:
                out.append(len(stack))
        return out

    def _heads(self, i: int, j: int, depth: list[int], a: int) -> list[str]:
        """The first name of each comma-separated part of tokens [i, j)."""
        toks, heads, want = self.toks, [], True
        for k in range(i, j):
            if depth[k - a] != 0:
                continue
            if toks[k].text == ",":
                want = True
            elif want and toks[k].kind == "ident":
                heads.append(toks[k].text)
                want = False
        return heads

    def _body(self, decl: Decl, i: int, sig_end: int, b: int) -> None:
        """What the declaration names, where, and the locals its body brings in."""
        toks = self.toks
        introduced: set[str] = set()
        for k in range(i, b):
            t = toks[k]
            if t.text in _INTRODUCERS:
                for u in toks[k + 1:b]:
                    if u.line != t.line:
                        break
                    if u.kind == "ident" and "." not in u.text:
                        introduced.add(u.text)
                    elif u.text not in _NAME_GLUE:
                        break
            if t.kind != "ident":
                continue
            if t.text in ("sorry", "admit"):
                decl.sorry += 1
            elif not (k > i and toks[k - 1].text == "." and toks[k - 1].pos + 1 == t.pos):
                (decl.refs_statement if k < sig_end else decl.refs_body).add(t.text)
        decl.locals |= introduced

    def _fields(self, i: int, b: int, depth: list[int], a: int, parent: Decl) -> list[Decl]:
        toks = self.toks
        end = next((k for k in range(i, b) if toks[k].first and toks[k].text == "deriving"), b)
        if i >= end:
            return []
        col = toks[i].col
        starts, past = [], i
        for k in range(i, end):
            # A doc comment and attributes above a field begin it.
            if k >= past and depth[k - a] == 0 and (k == i or (toks[k].first and toks[k].col == col)):
                starts.append(k)
                past = self._prefix(k)[0] + 1
        fields: list[Decl] = []
        for n, k in enumerate(starts):
            stop = starts[n + 1] if n + 1 < len(starts) else end
            j, doc, _, _ = self._prefix(k)
            names: list[Tok] = []
            if j < stop and toks[j].text in ("(", "{", "["):
                close = self._group_end(j, stop)
                inner = toks[j + 1:close - 1]
                cut = next((x for x, t in enumerate(inner) if t.text == ":"), None)
                names = [t for t in (inner[:cut] if cut is not None else [])
                         if t.kind == "ident" and "." not in t.text]
                colon = j + 1 + cut if cut is not None else None
                type_end = close - 1
            else:
                while j < stop and toks[j].kind == "ident" and "." not in toks[j].text:
                    names.append(toks[j])
                    j += 1
                if j < stop and toks[j].text == "::":
                    continue  # `mk ::` names the constructor
                colon = next((x for x in range(j, stop) if depth[x - a] == 0
                              and toks[x].text in (":", ":=")), None)
                if colon is not None and toks[colon].text == ":=":
                    colon = None if not names else colon
                type_end = stop
            if colon is None:
                continue
            type_str = ""
            if toks[colon].text == ":":
                default = next((x for x in range(colon + 1, type_end)
                                if depth[x - a] == 0 and toks[x].text == ":="), type_end)
                type_str = self._text(colon + 1, default, 120)
            for t in names:
                fields.append(Decl("field", "", t.text, f"{parent.qualified}.{t.text}",
                                   parent.namespace, t.line, line_end=toks[stop - 1].line,
                                   label=t.text, doc=doc, type_str=type_str))
        return fields

    def _constructors(self, i: int, b: int, depth: list[int], a: int, parent: Decl) -> list[Decl]:
        toks, found = self.toks, []
        last_name = -1
        for k in range(i, b):
            t = toks[k]
            if t.first and t.text == "deriving":
                break
            if t.text != "|" or depth[k - a] != 0:
                continue
            # `| a | b` on one line, or a bar that begins a line or the list.
            if not (t.first or k == i or k - 1 == i or k - 1 == last_name):
                continue
            j, doc, _, _ = self._prefix(k + 1)
            if j >= b or toks[j].kind != "ident" or "." in toks[j].text:
                continue
            last_name = j
            nxt = toks[j + 1] if j + 1 < b else None
            bare = nxt is None or nxt.text == "|" or (nxt.first and nxt.text == "deriving") or (
                nxt.kind == "doc")
            stop = next((x for x in range(j + 1, b) if depth[x - a] == 0 and (
                toks[x].text == "|" and toks[x].first or toks[x].first and toks[x].text == "deriving")), b)
            found.append(Decl("constructor", "", toks[j].text, f"{parent.qualified}.{toks[j].text}",
                              parent.namespace, toks[j].line, label=toks[j].text, doc=doc,
                              type_str="" if bare else self._text(j + 1, stop, 120)))
        return found


def read_file(src: str) -> FileRead:
    """The declarations and imports of one Lean file."""
    return _Reader(src).read()


# ── The parser ────────────────────────────────────────────────────────────────

# Every `kind` this parser emits; `constructs.yaml` is held to it both ways.
KINDS = ("theorem", "def", "abbrev", "opaque", "axiom", "structure", "class", "inductive",
         "instance", "example", "macro", "field", "constructor")

# The modules a Lean toolchain ships; anything else comes from a package.
_CORE_MODULES = {"Init", "Lean", "Std"}

_AMBIGUOUS = object()


class LeanLanguageParser:
    """LanguageParser implementation for `.lean` files, stdlib only."""

    language: ClassVar[str] = "lean"
    extensions: ClassVar[list[str]] = [".lean"]
    kinds: ClassVar[tuple[str, ...]] = KINDS

    # Whole tree at once: imports and the names a proof cites cross files.
    batch_whole_tree: ClassVar[bool] = True

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        graph = nx.DiGraph()
        if depth < 2:
            return graph
        reads = {(f.url or f.name): read_file(f.raw) for f in files if f.raw}

        names: dict[str, list[tuple[str, str]]] = {}  # full name -> [(node id, file)]
        emitted: list[tuple[Decl, str, str]] = []
        for file, read in reads.items():
            for decl in read.decls:
                node_id = self._emit(graph, decl, file, level=2)
                emitted.append((decl, node_id, file))
                if decl.qualified:
                    names.setdefault(decl.qualified, []).append((node_id, file))
                for child in decl.children:
                    child_id = node_id
                    if depth >= 3:
                        child_id = self._emit(graph, child, file, level=3)
                        graph.add_edge(node_id, child_id, **make_edge("contains"))
                    if decl.qualified:
                        names.setdefault(child.qualified, []).append((child_id, file))

        for decl, node_id, file in emitted:
            self._relate(graph, decl, node_id, file, names)

        graph.graph["file_relations"] = self._imports(graph, reads)
        graph.graph["file_meta"] = {
            file: {"imports": [name for name, _ in read.imports],
                   "sorry": sum(d.sorry for d in read.decls)}
            for file, read in reads.items()
        }
        construct_service.annotate(graph)
        return graph

    # -- emitting nodes ---------------------------------------------------------

    @staticmethod
    def _emit(graph: nx.DiGraph, decl: Decl, file: str, level: int) -> str:
        base = node_id = f"lean::{file}::{decl.kind}::{decl.qualified or decl.label}::{decl.line}"
        seen = 1
        while node_id in graph:
            seen += 1
            node_id = f"{base}#{seen}"
        meta: dict = {"line_end": decl.line_end or decl.line}
        if level == 2:
            meta.update(qualifiers=decl.qualifiers, attributes=decl.attributes,
                        namespace=".".join(decl.namespace))
        for key, value in (("qualified", decl.qualified), ("keyword", decl.keyword),
                           ("doc", decl.doc), ("statement", decl.statement),
                           ("proof", decl.proof), ("sorry", decl.sorry),
                           ("extends", decl.extends), ("class", decl.class_name),
                           ("type_str", decl.type_str)):
            if value:
                meta[key] = value
        if decl.kind in ("structure", "class") and not decl.enumeration:
            meta["field_count"] = sum(c.kind == "field" for c in decl.children)
        if decl.kind == "inductive":
            meta["variant_count"] = len(decl.children)
            meta["enumeration"] = decl.enumeration
        graph.add_node(node_id, **make_node(
            node_id, depth=level, language="lean", kind=decl.kind, label=decl.label,
            file=file, line=decl.line, meta=meta))
        return node_id

    # -- relations between declarations -----------------------------------------

    def _relate(self, graph: nx.DiGraph, decl: Decl, node_id: str, file: str,
                names: dict[str, list[tuple[str, str]]]) -> None:
        def find(ref: str) -> tuple[str, str] | None:
            return _resolve(ref, decl, file, names)

        for kind, refs in (("inherits", decl.extends),
                           ("implements", [decl.class_name] if decl.class_name else [])):
            for ref in refs:
                found = find(ref)
                if found and found[0] != node_id:
                    graph.add_edge(node_id, found[0], **make_edge(kind), resolution=found[1])

        own = {node_id} | set(graph.successors(node_id))
        used: dict[str, list[str]] = {}
        for part, refs in (("statement", decl.refs_statement), ("body", decl.refs_body)):
            for ref in sorted(refs):
                if _parts(ref)[:1] and _parts(ref)[0] in decl.locals:
                    continue
                found = find(ref)
                if found and found[0] not in own:
                    seen = used.setdefault(found[0], [part, found[1]])
                    if seen[0] != part:
                        seen[0] = "both"
        for target, (part, resolution) in used.items():
            graph.add_edge(node_id, target, **make_edge("uses"), part=part, resolution=resolution)

    # -- imports ----------------------------------------------------------------

    @staticmethod
    def _imports(graph: nx.DiGraph, reads: dict[str, FileRead]) -> list[tuple[str, str, dict]]:
        paths = {key.replace("\\", "/"): key for key in reads}
        # A directory or file a batch holds is a local module's root, so an
        # import under it that names no file here is a missing file, not an
        # external package.
        local_roots = {part for path in paths for part in posixpath.splitext(path)[0].split("/")}
        relations: dict[tuple[str, str], dict] = {}
        for file, read in reads.items():
            for module, _ in read.imports:
                path = "/".join(_parts(module)) + ".lean"
                hits = [key for p, key in paths.items() if p == path or p.endswith("/" + path)]
                if len(hits) == 1:
                    if hits[0] != file:
                        relations.setdefault((file, hits[0]),
                                             {"kind": "depends_on", "resolution": "module-path"})
                    continue
                root = _parts(module)[0] if _parts(module) else ""
                if hits or not root or root in local_roots:
                    continue
                dest = f"external::lean::{root}"
                if dest not in graph:
                    graph.add_node(dest, **make_node(
                        dest, depth=1, language="external", kind="external_module",
                        label=root, meta={"core": root in _CORE_MODULES}))
                relations.setdefault((file, dest), {"kind": "depends_on", "resolution": "external"})
        return [(src, dst, attrs) for (src, dst), attrs in relations.items()]


def _pick(full: str, file: str, names: dict[str, list[tuple[str, str]]]):
    """The node named *full*: None when nothing is, `_AMBIGUOUS` when more
    than one is and the file does not settle it."""
    found = names.get(full)
    if not found:
        return None
    if len(found) == 1:
        return found[0][0]
    here = [node for node, f in found if f == file]
    return here[0] if len(here) == 1 else _AMBIGUOUS


def _resolve(ref: str, decl: Decl, file: str,
             names: dict[str, list[tuple[str, str]]]) -> tuple[str, str] | None:
    """The node *ref* names inside *decl*, and how that was decided."""
    parts = _parts(ref)
    rooted = parts[:1] == ("_root_",)
    if rooted:
        parts = parts[1:]
    namespace = () if rooted else decl.namespace
    for k in range(len(parts), 0, -1):
        prefix = ".".join(parts[:k])
        for d in range(len(namespace), -1, -1):
            hit = _pick(".".join(namespace[:d] + (prefix,)), file, names)
            if hit is _AMBIGUOUS:
                return None
            if hit:
                return hit, "namespace" if d else "exact"
        if rooted:
            continue
        opened = {_pick(f"{o}.{prefix}", file, names) for o in decl.opens} - {None}
        if len(opened) == 1 and _AMBIGUOUS not in opened:
            return opened.pop(), "open"
        if opened:
            return None
    return None


ParserRegistry.register(LeanLanguageParser())
