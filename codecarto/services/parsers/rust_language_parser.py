"""
Rust Language Parser
====================
Reads Rust source at the **item level** -- what a tokenizer and a brace matcher
can know without a compiler -- and emits the unified node schema.

**WHERE THIS STOPS, AND WHY THERE.** Rust's items (`fn`, `struct`, `enum`,
`union`, `trait`, `impl`, `mod`, `type`, `const`, `static`, `use`, `extern`
blocks, `macro_rules!`) are delimited by keywords and balanced brackets, so a
tokenizer reads them exactly. What it cannot read is anything that needs name
resolution, type inference or macro expansion: which `Read` a `use` brings in
when two are in scope, what a method call's receiver is, what `cfg_if!` or a
derive expands to. Those belong to the engine that owns them -- `rustc`, through
`rust-analyzer` -- and this module does not imitate it. Each relation below
says how it was resolved, so nothing drawn from a heuristic reads as compiled.

Relations, and how each is found
--------------------------------
contains     item -> its fields, variants, methods, associated items, and the
             items of an inline `mod` block. Exact.
declares     `mod foo;` -> the file it names (`foo.rs` or `foo/mod.rs`, or a
             `#[path]`). Exact for files present in the batch.
depends_on   file -> file, from `use` paths walked through the module tree the
             `mod` declarations build; file -> external crate otherwise. A
             workspace crate is recognised by its directory name, which is
             right when the directory and the package agree and is said to be
             a guess in the edge's `resolution`.
implements   `impl Trait for T` -> `Trait`, when exactly one local trait has
             that name.
extends      `impl [Trait for] T` -> `T`, when exactly one local type has that
             name.
inherits     `trait A: B` -> `B` (supertrait), unique local name.
aliases      `type A = B` -> `B`, unique local name.
type_of      field -> the local type its type mentions, unique local name.
calls        fn -> fn. `f(..)` by unique free-function name; `Self::f(..)`,
             `T::f(..)` and `self.f(..)` through the impl's self type. Every
             other method call is counted as unresolved rather than guessed:
             `.len()` on a `Vec` is not a call to a local `len`.

Facts carried for the firmware and FFI boundary
-----------------------------------------------
`meta['attributes']` keeps each outer attribute as written (`repr(C)`,
`link_section = ".boot"`, `cortex_m_rt::entry`, `no_mangle`), and
`meta['qualifiers']` the keyword tokens an item was declared with (`pub`,
`unsafe`, `async`, `const`, `extern`, `mut`) -- the same key the C adapter uses,
so `lexicon_bridge` and the construct vocabulary read both languages alike.
Inner attributes of a file (`#![no_std]`, `#![no_main]`) are file facts and
reach the file node's `meta` through the pipeline's `file_meta` hook.

Node ID format
--------------
``rust::{file}::{kind}::{qualified name}::{line}`` -- ``file`` is the File's
``url`` or ``name``, so two crates' ``src/lib.rs`` never share an id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar, Iterable

import networkx as nx

from codecarto.models.source_data import File
from codecarto.services import construct_service
from codecarto.services.construct_service import attribute_name
from codecarto.services.parsers.language_parser import (
    ParserRegistry,
    make_edge,
    make_node,
)

# ── Tokens ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Tok:
    kind: str  # 'ident' | 'lifetime' | 'literal' | 'punct' | 'doc'
    text: str
    line: int


_TOKEN = re.compile(
    r"""
     (?P<ws>\s+)
    |(?P<doc>///(?!/)[^\n]*)
    |(?P<comment>//[^\n]*)
    |(?P<block>/\*)
    |(?P<rawstr>(?:br|cr|r)(?P<hashes>\#*)")
    |(?P<rawident>r\#[^\W\d]\w*)
    |(?P<str>[bc]?"(?:[^"\\]|\\.)*")
    |(?P<char>b?'(?:[^'\\\n]|\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F_]{1,8}\}|.))')
    |(?P<lifetime>'[^\W\d]\w*)
    |(?P<ident>[^\W\d]\w*)
    |(?P<number>0[xob][\w]+|\d[\d_]*(?:\.(?![.\w])[\d_]*)?(?:[eE][+-]?[\d_]+)?\w*)
    |(?P<punct>>>=|<<=|\.\.\.|\.\.=|::|->|=>|==|!=|<=|>=|&&|\|\||\+=|-=|\*=|/=|%=|\^=|&=|\|=|<<|>>|\.\.|[^\s\w])
    """,
    re.VERBOSE | re.DOTALL,
)


def tokenize(src: str) -> list[Tok]:
    """Rust source -> tokens. Comments are dropped, outer doc lines kept.

    Total on any input: a quote that never closes becomes one punct token and
    reading carries on after it; an unterminated block comment or raw string
    runs to the end of the text.
    """
    toks: list[Tok] = []
    pos, n, line = 0, len(src), 1
    while pos < n:
        m = _TOKEN.match(src, pos)
        if m is None:  # unterminated string literal, or a lone quote
            toks.append(Tok("punct", src[pos], line))
            line += src[pos] == "\n"
            pos += 1
            continue
        kind = m.lastgroup
        text = m.group()
        if kind == "block":
            depth, j = 1, m.end()
            while j < n and depth:
                if src.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif src.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            text = src[pos:j]
            if text.startswith("/**") and not text.startswith("/***") and len(text) > 4:
                toks.append(Tok("doc", text[3:-2].strip().splitlines()[0] if text[3:-2].strip() else "", line))
            line += text.count("\n")
            pos = j
            continue
        if kind == "rawstr":
            close = '"' + m.group("hashes")
            j = src.find(close, m.end())
            j = n if j < 0 else j + len(close)
            toks.append(Tok("literal", src[pos:j], line))
            line += src.count("\n", pos, j)
            pos = j
            continue
        if kind == "doc":
            toks.append(Tok("doc", text[3:].strip(), line))
        elif kind in ("str", "char", "number"):
            toks.append(Tok("literal", text, line))
        elif kind == "rawident":
            toks.append(Tok("ident", text[2:], line))
        elif kind in ("ident", "lifetime", "punct"):
            toks.append(Tok(kind, text, line))
        line += text.count("\n")
        pos = m.end()
    return toks


# ── Items ─────────────────────────────────────────────────────────────────────

# Every `kind` this parser can emit. `constructs.yaml` maps each one, and a
# test holds the two to each other in both directions.
KINDS = (
    "function", "method", "struct", "enum", "union", "trait", "impl", "module",
    "type", "const", "static", "use", "extern_crate", "extern_block", "macro",
    "macro_invocation", "field", "variant", "assoc_type", "assoc_const",
)

_QUALIFIERS = {"pub", "default", "const", "async", "unsafe", "extern", "safe", "auto"}
_KEYWORDS = {
    "as", "async", "await", "break", "const", "continue", "crate", "dyn", "else",
    "enum", "extern", "false", "fn", "for", "if", "impl", "in", "let", "loop",
    "match", "mod", "move", "mut", "pub", "ref", "return", "self", "Self",
    "static", "struct", "super", "trait", "true", "type", "unsafe", "use",
    "where", "while", "yield",
}
_STD_CRATES = {"std", "core", "alloc", "proc_macro", "test"}
# Volatile access has no keyword in Rust; these calls are how it is spelled.
_VOLATILE = {"read_volatile", "write_volatile", "volatile_load", "volatile_store",
             "volatile_copy_memory", "volatile_set_memory"}


@dataclass
class Item:
    kind: str
    name: str
    line: int
    line_end: int = 0
    visibility: str = ""
    qualifiers: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    abi: str = ""
    doc: str = ""
    children: list["Item"] = field(default_factory=list)
    label: str = ""
    type_str: str = ""
    type_refs: list[str] = field(default_factory=list)
    trait: str = ""
    self_type: str = ""
    supertraits: list[str] = field(default_factory=list)
    use_paths: list[list[str]] = field(default_factory=list)
    mod_inline: bool = False
    mod_path_attr: str = ""
    receiver: str = ""
    param_count: int = 0
    calls: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    macros: list[str] = field(default_factory=list)
    unsafe_blocks: int = 0
    volatile_accesses: int = 0
    payload: bool = False


class _Reader:
    """Recursive descent over one file's tokens, at the item level only."""

    def __init__(self, toks: list[Tok]) -> None:
        self.t = toks
        self.n = len(toks)
        self.close = self._match_brackets()

    def _match_brackets(self) -> dict[int, int]:
        pairs = {"(": ")", "[": "]", "{": "}"}
        close: dict[int, int] = {}
        stack: list[int] = []
        for i, tok in enumerate(self.t):
            if tok.kind != "punct":
                continue
            if tok.text in pairs:
                stack.append(i)
            elif tok.text in (")", "]", "}"):
                # Pop to the nearest opener of the same kind; anything above it
                # was never closed and is closed here, so a stray bracket in
                # broken code costs one item rather than the rest of the file.
                for depth in range(len(stack) - 1, -1, -1):
                    if pairs[self.t[stack[depth]].text] == tok.text:
                        for opener in stack[depth:]:
                            close[opener] = i
                        del stack[depth:]
                        break
        for opener in stack:
            close[opener] = self.n - 1 if self.n else 0
        return close

    # -- small helpers ---------------------------------------------------------

    def text(self, i: int) -> str:
        return self.t[i].text if 0 <= i < self.n else ""

    def kind(self, i: int) -> str:
        return self.t[i].kind if 0 <= i < self.n else ""

    def group_end(self, i: int) -> int:
        """Index of the closer of the bracket at *i*."""
        return self.close.get(i, i)

    def skip_generics(self, i: int) -> int:
        """*i* at `<`: index just past the matching `>`."""
        depth = 0
        while i < self.n:
            t = self.t[i].text
            if t in ("(", "[", "{"):
                i = self.group_end(i) + 1
                continue
            if t == "<":
                depth += 1
            elif t == "<<":
                depth += 2
            elif t in (">", ">="):
                depth -= 1
            elif t in (">>", ">>="):
                depth -= 2
            elif t in (";",) and depth > 0:
                return i
            i += 1
            if depth <= 0:
                return i
        return i

    def until(self, i: int, end: int, stops: set[str], angles: bool = False) -> int:
        """First index in [i, end) whose token is in *stops* at bracket depth 0,
        skipping bracket groups. *end* if none.

        `angles` also holds the stop until every `<` has closed. Only for type
        positions: in an expression `<` is a comparison and never closes, and
        counting it there would carry the search to the end of the file."""
        angle = 0
        while i < end:
            t = self.t[i].text
            if self.t[i].kind == "punct":
                if t in ("(", "[", "{") and not (t in stops and angle == 0):
                    i = self.group_end(i) + 1
                    continue
                if not angles:
                    pass
                elif t == "<":
                    angle += 1
                elif t == "<<":
                    angle += 2
                elif t == ">" and angle:
                    angle -= 1
                elif t == ">>" and angle:
                    angle = max(0, angle - 2)
            if t in stops and angle == 0:
                return i
            i += 1
        return end

    def joined(self, i: int, j: int, limit: int = 96) -> str:
        """Tokens [i, j) as compact source text, cut at *limit* characters."""
        out: list[str] = []
        prev = ""
        for tok in self.t[i:j]:
            if tok.kind == "doc":
                continue
            t = tok.text
            tight = t in (",", ";", ")", "]", ">", "::", ".", "?") or prev in (
                "(", "[", "<", "::", ".", "&", "#", "!") or (t in ("(", "[", "<", "!") and prev and (prev[-1].isalnum() or prev[-1] in "_>"))
            if out and not tight:
                out.append(" ")
            out.append(t)
            prev = t
        text = "".join(out)
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def idents(self, i: int, j: int) -> list[str]:
        return [tok.text for tok in self.t[i:j] if tok.kind == "ident" and tok.text not in _KEYWORDS]

    def type_head(self, i: int, j: int) -> str:
        """The named type a type expression is about: `&'a mut Vec<T>` -> `Vec`,
        `crate::hw::Uart<Tx>` -> `Uart`, `[u8; 4]` -> `[u8; 4]`."""
        while i < j and (self.text(i) in ("&", "&&", "*", "mut", "dyn", "impl", "const", "unsafe", "extern", "?")
                         or self.kind(i) in ("lifetime", "literal")):
            i += 1
        if i < j and self.text(i) in ("(", "["):
            return self.joined(i, self.group_end(i) + 1, 40)
        last = ""
        while i < j and (self.kind(i) == "ident" or self.text(i) == "::"):
            if self.kind(i) == "ident":
                last = self.text(i)
            i += 1
        return last

    # -- the item loop ----------------------------------------------------------

    def items(self, i: int, end: int) -> tuple[list[Item], list[str]]:
        """Items in [i, end), and the inner attributes found among them."""
        found: list[Item] = []
        inner: list[str] = []
        attrs: list[str] = []
        docs: list[str] = []
        while i < end:
            tok = self.t[i]
            if tok.kind == "doc":
                docs.append(tok.text)
                i += 1
                continue
            if tok.text == "#" and self.text(i + 1) == "!" and self.text(i + 2) == "[":
                j = self.group_end(i + 2)
                inner.append(self.joined(i + 3, j, 200))
                i = j + 1
                continue
            if tok.text == "#" and self.text(i + 1) == "[":
                j = self.group_end(i + 1)
                attrs.append(self.joined(i + 2, j, 200))
                i = j + 1
                continue
            item, i = self.item(i, end)
            if item is not None:
                item.attributes = attrs
                item.doc = next((d for d in docs if d), "")
                found.append(item)
            attrs, docs = [], []
        return found, inner

    def item(self, i: int, end: int) -> tuple[Item | None, int]:
        """One item starting at *i*; returns it (or None) and the index after."""
        start = i
        visibility = ""
        qualifiers: list[str] = []
        abi = ""
        if self.text(i) == "pub":
            visibility = "pub"
            qualifiers.append("pub")
            i += 1
            if self.text(i) == "(":
                j = self.group_end(i)
                visibility = "pub(" + self.joined(i + 1, j) + ")"
                i = j + 1
        while i < end and self.text(i) in _QUALIFIERS - {"pub"}:
            word = self.text(i)
            nxt = self.text(i + 1)
            if word == "const" and nxt not in ("fn", "unsafe", "async", "extern"):
                break  # a const item, not a const fn
            if word == "unsafe" and nxt == "{":
                break
            if word == "extern" and nxt == "crate":
                break
            if word in ("default", "auto", "safe") and self.kind(i + 1) != "ident":
                break
            qualifiers.append(word)
            i += 1
            if word == "extern":
                abi = "C"
                if self.kind(i) == "literal" and self.text(i).startswith('"'):
                    abi = self.text(i).strip('"')
                    i += 1
        kw = self.text(i)
        line = self.t[i].line if i < self.n else self.t[start].line

        def done(item: Item, j: int) -> tuple[Item, int]:
            item.visibility = visibility
            item.qualifiers = qualifiers
            item.abi = item.abi or abi
            item.line_end = self.t[min(j, self.n - 1)].line if self.n else line
            return item, j + 1

        if kw == "fn" and self.kind(i + 1) == "ident":
            return done(*self.fn(i, end, line))
        if kw in ("struct", "union") and self.kind(i + 1) == "ident" and (
                kw == "struct" or self.text(i + 2) in ("<", "{", "where")):
            return done(*self.struct(i, end, line, kw))
        if kw == "enum" and self.kind(i + 1) == "ident":
            return done(*self.enum(i, end, line))
        if kw == "trait" and self.kind(i + 1) == "ident":
            return done(*self.trait(i, end, line))
        if kw == "impl":
            return done(*self.impl(i, end, line))
        if kw == "mod" and self.kind(i + 1) == "ident":
            name = self.text(i + 1)
            j = i + 2
            if self.text(j) == "{":
                close = self.group_end(j)
                children, inner = self.items(j + 1, close)
                return done(Item("module", name, line, children=children, mod_inline=True,
                                 attributes=inner), close)
            return done(Item("module", name, line), self.until(j, end, {";"}))
        if kw == "type" and self.kind(i + 1) == "ident":
            name = self.text(i + 1)
            stop = self.until(i + 2, end, {"=", ";"})
            j = self.until(stop, end, {";"})
            item = Item("type", name, line)
            if self.text(stop) == "=":
                item.type_str = self.joined(stop + 1, j)
                item.type_refs = self.idents(stop + 1, j)
            return done(item, j)
        if kw in ("const", "static") and (self.kind(i + 1) == "ident" or self.text(i + 1) == "_"):
            j0 = i + 1
            if kw == "static" and self.text(j0) == "mut" and self.kind(j0 + 1) == "ident":
                qualifiers.append("mut")
                j0 += 1
            name = self.text(j0)
            qualifiers.append(kw)
            colon = self.until(j0 + 1, end, {":", ";"})
            j = self.until(colon, end, {";"})
            eq = self.until(colon, j, {"="}, angles=True)
            item = Item(kw, name, line)
            if self.text(colon) == ":":
                item.type_str = self.joined(colon + 1, eq)
                item.type_refs = self.idents(colon + 1, eq)
            return done(item, j)
        if kw == "use":
            j = self.until(i + 1, end, {";"})
            item = Item("use", self.joined(i + 1, j, 80), line)
            item.use_paths = self.use_tree(i + 1, j, [])
            return done(item, j)
        if kw == "extern" and self.text(i + 1) == "crate" and self.kind(i + 2) == "ident":
            j = self.until(i + 3, end, {";"})
            item = Item("extern_crate", self.text(i + 2), line)
            item.use_paths = [[self.text(i + 2)]]
            return done(item, j)
        if "extern" in qualifiers and kw == "{":
            close = self.group_end(i)
            children, _ = self.items(i + 1, close)
            for child in children:
                if child.kind == "function":
                    child.qualifiers = ["extern"] + child.qualifiers
                    child.abi = abi
            return done(Item("extern_block", f'extern "{abi}"', line, children=children, abi=abi), close)
        if kw == "macro_rules" and self.text(i + 1) == "!" and self.kind(i + 2) == "ident":
            j = i + 3
            close = self.group_end(j) if self.text(j) in ("(", "[", "{") else j
            if self.text(j) != "{" and self.text(close + 1) == ";":
                close += 1
            return done(Item("macro", self.text(i + 2), line), close)
        # An item-level macro invocation: `path::to::name! { .. }` / `( .. );`
        if self.kind(i) == "ident" and not qualifiers and not visibility:
            j = i
            while self.kind(j) == "ident" and self.text(j + 1) == "::":
                j += 2
            if self.kind(j) == "ident" and self.text(j + 1) == "!":
                k = j + 2
                if self.kind(k) == "ident":  # `macro_name! ident { .. }`
                    k += 1
                if self.text(k) in ("(", "[", "{"):
                    close = self.group_end(k)
                    if self.text(k) != "{" and self.text(close + 1) == ";":
                        close += 1
                    path = self.joined(i, j + 1)
                    return done(Item("macro_invocation", self.text(j), line, label=f"{path}!"), close)
        # Not an item this reader knows: skip to the end of the statement or
        # the next balanced block, so one unknown form costs only itself.
        j = start
        while j < end:
            t = self.text(j)
            if t == ";":
                break
            if t == "{":
                j = self.group_end(j)
                break
            if t in ("(", "["):
                j = self.group_end(j)
            j += 1
        return None, max(j + 1, start + 1)

    # -- one parser per item shape ------------------------------------------------

    def fn(self, i: int, end: int, line: int) -> tuple[Item, int]:
        item = Item("function", self.text(i + 1), line)
        j = i + 2
        if self.text(j) == "<":
            j = self.skip_generics(j)
        if self.text(j) == "(":
            pclose = self.group_end(j)
            params = self.split_commas(j + 1, pclose)
            if params:
                first = params[0]
                words = [self.text(k) for k in range(first[0], first[1])]
                if "self" in words and ":" not in words[: words.index("self")]:
                    item.receiver = "".join(w for w in words if w not in ("mut",) or words[0] == "mut") \
                        if len(words) <= 4 else "self"
                    item.receiver = " ".join(words).replace("& ", "&").replace(" self", " self")
                    params = params[1:]
            item.param_count = len(params)
            j = pclose + 1
        body = self.until(j, end, {"{", ";"})
        if self.text(body) == "{":
            close = self.group_end(body)
            self.read_body(item, body + 1, close)
            return item, close
        return item, body

    def split_commas(self, i: int, j: int) -> list[tuple[int, int]]:
        """Top-level comma-separated spans in [i, j), angle-aware."""
        spans: list[tuple[int, int]] = []
        start = i
        while i < j:
            k = self.until(i, j, {","}, angles=True)
            if k > start:
                spans.append((start, k))
            i = start = k + 1
        return spans

    def read_body(self, item: Item, i: int, j: int) -> None:
        """Calls, macro invocations and unsafe blocks inside a function body."""
        calls: list[tuple[str, tuple[str, ...]]] = []
        macros: list[str] = []
        k = i
        while k < j:
            tok = self.t[k]
            if tok.kind != "ident":
                k += 1
                continue
            if tok.text == "unsafe" and self.text(k + 1) == "{":
                item.unsafe_blocks += 1
            nxt = self.text(k + 1)
            if nxt == "!" and self.text(k + 2) in ("(", "[", "{") and self.text(k - 1) != ".":
                macros.append(tok.text)
                k += 2
                continue
            if tok.text in _KEYWORDS and tok.text not in ("self", "Self"):
                k += 1
                continue
            # Walk a path `a::b::<T>::c` to its last segment.
            segs = [tok.text]
            m = k + 1
            while self.text(m) == "::":
                if self.text(m + 1) == "<":
                    m = self.skip_generics(m + 1)
                    continue
                if self.kind(m + 1) != "ident":
                    break
                segs.append(self.text(m + 1))
                m += 2
            if self.text(m) == "::" and self.text(m + 1) == "<":  # turbofish at the end
                m = self.skip_generics(m + 1)
            if self.text(m) == "!" and self.text(m + 1) in ("(", "[", "{") and len(segs) > 1:
                macros.append(segs[-1])  # `core::arch::asm!(..)`
                k = m + 1
                continue
            if self.text(m) == "(" and segs[-1] in _VOLATILE:
                item.volatile_accesses += 1
            if self.text(m) == "(" and segs[-1] not in _KEYWORDS and not (
                    len(segs) == 1 and segs[0][:1].isupper()):
                prev = self.text(k - 1)
                if prev == ".":
                    receiver = self.text(k - 2)
                    calls.append(("self-method" if receiver == "self" and self.text(k - 3) != "." else "method",
                                  (segs[-1],)))
                elif prev not in ("fn", "struct", "enum", "->"):
                    calls.append(("path", tuple(segs)))
            k = m if m > k else k + 1
        item.calls = calls
        item.macros = sorted(set(macros))

    def struct(self, i: int, end: int, line: int, kw: str) -> tuple[Item, int]:
        item = Item("struct" if kw == "struct" else "union", self.text(i + 1), line)
        j = i + 2
        if self.text(j) == "<":
            j = self.skip_generics(j)
        stops = {"{", ";"} if self.text(j) == "where" else {"{", "(", ";"}
        stop = self.until(j, end, stops)
        if self.text(stop) == "{":
            close = self.group_end(stop)
            item.children = self.fields(stop + 1, close)
            return item, close
        if self.text(stop) == "(":
            close = self.group_end(stop)
            for n, (a, b) in enumerate(self.split_commas(stop + 1, close)):
                a = self.skip_attrs(a, b)
                if self.text(a) == "pub":
                    a = self.group_end(a + 1) + 1 if self.text(a + 1) == "(" else a + 1
                child = Item("field", str(n), self.t[a].line if a < self.n else line)
                child.type_str = self.joined(a, b)
                child.type_refs = self.idents(a, b)
                item.children.append(child)
            return item, self.until(close + 1, end, {";"})
        return item, stop

    def skip_attrs(self, a: int, b: int) -> int:
        while a < b and (self.kind(a) == "doc" or (self.text(a) == "#" and self.text(a + 1) == "[")):
            a = a + 1 if self.kind(a) == "doc" else self.group_end(a + 1) + 1
        return a

    def fields(self, i: int, j: int) -> list[Item]:
        out: list[Item] = []
        for a, b in self.split_commas(i, j):
            attrs: list[str] = []
            while a < b and (self.kind(a) == "doc" or (self.text(a) == "#" and self.text(a + 1) == "[")):
                if self.kind(a) == "doc":
                    a += 1
                else:
                    close = self.group_end(a + 1)
                    attrs.append(self.joined(a + 2, close, 200))
                    a = close + 1
            qualifiers = []
            if self.text(a) == "pub":
                qualifiers.append("pub")
                a = self.group_end(a + 1) + 1 if self.text(a + 1) == "(" else a + 1
            if self.kind(a) != "ident" or self.text(a + 1) != ":":
                continue
            child = Item("field", self.text(a), self.t[a].line, attributes=attrs, qualifiers=qualifiers)
            child.type_str = self.joined(a + 2, b)
            child.type_refs = self.idents(a + 2, b)
            out.append(child)
        return out

    def enum(self, i: int, end: int, line: int) -> tuple[Item, int]:
        item = Item("enum", self.text(i + 1), line)
        brace = self.until(i + 2, end, {"{", ";"})
        if self.text(brace) != "{":
            return item, brace
        close = self.group_end(brace)
        for a, b in self.split_commas(brace + 1, close):
            a = self.skip_attrs(a, b)
            if self.kind(a) != "ident":
                continue
            variant = Item("variant", self.text(a), self.t[a].line)
            if self.text(a + 1) == "{":
                variant.children = self.fields(a + 2, self.group_end(a + 1))
                variant.payload = True
            elif self.text(a + 1) == "(":
                inner = self.group_end(a + 1)
                variant.type_str = self.joined(a + 2, inner)
                variant.type_refs = self.idents(a + 2, inner)
                variant.payload = True
            eq = self.until(a + 1, b, {"="})
            if eq < b:
                variant.type_str = "= " + self.joined(eq + 1, b, 40)
            item.children.append(variant)
        return item, close

    def trait(self, i: int, end: int, line: int) -> tuple[Item, int]:
        item = Item("trait", self.text(i + 1), line)
        j = i + 2
        if self.text(j) == "<":
            j = self.skip_generics(j)
        brace = self.until(j, end, {"{", ";"})
        if self.text(j) == ":":
            where = self.until(j + 1, brace, {"where"})
            for a, b in self.plus_split(j + 1, where):
                head = self.type_head(a, b)
                if head and head[0] != "[":
                    item.supertraits.append(head)
        if self.text(brace) != "{":
            return item, brace
        close = self.group_end(brace)
        children, _ = self.items(brace + 1, close)
        item.children = [self.associated(c) for c in children]
        return item, close

    def plus_split(self, i: int, j: int) -> list[tuple[int, int]]:
        spans, start = [], i
        while i < j:
            k = self.until(i, j, {"+"}, angles=True)
            if k > start:
                spans.append((start, k))
            i = start = k + 1
        return spans

    @staticmethod
    def associated(child: Item) -> Item:
        if child.kind == "function":
            child.kind = "method"
        elif child.kind == "type":
            child.kind = "assoc_type"
        elif child.kind == "const":
            child.kind = "assoc_const"
        return child

    def impl(self, i: int, end: int, line: int) -> tuple[Item, int]:
        j = i + 1
        if self.text(j) == "<":
            j = self.skip_generics(j)
        brace = self.until(j, end, {"{", ";"})
        header_end = self.until(j, brace, {"where"}, angles=True)
        # The `for` that separates trait from type is the first one at depth 0
        # that is not a higher-ranked `for<'a>`.
        k, split = j, -1
        while k < header_end:
            k2 = self.until(k, header_end, {"for"}, angles=True)
            if k2 >= header_end:
                break
            if self.text(k2 + 1) != "<":
                split = k2
                break
            k = k2 + 1
        negative = self.text(j) == "!"
        item = Item("impl", "", line)
        if split >= 0:
            item.trait = self.type_head(j + negative, split)
            item.self_type = self.type_head(split + 1, header_end)
            item.label = f"impl {'!' if negative else ''}{item.trait} for {item.self_type}"
        else:
            item.self_type = self.type_head(j, header_end)
            item.label = f"impl {item.self_type}"
        item.name = item.label[5:]
        if self.text(brace) != "{":
            return item, brace
        close = self.group_end(brace)
        children, _ = self.items(brace + 1, close)
        item.children = [self.associated(c) for c in children]
        return item, close

    def use_tree(self, i: int, j: int, prefix: list[str]) -> list[list[str]]:
        """`a::{b, c::d as e, self}` -> [[a, b], [a, c, d], [a]]."""
        paths: list[list[str]] = []
        segs = list(prefix)
        k = i
        while k < j:
            t = self.text(k)
            if t == "{":
                close = self.group_end(k)
                for a, b in self.split_commas(k + 1, close):
                    paths.extend(self.use_tree(a, b, segs))
                return paths
            if t == "*":
                paths.append(segs + ["*"])
                return paths
            if t == "as":
                break
            if self.kind(k) == "ident":
                if t == "self" and segs and k > i:
                    paths.append(list(segs))
                    return paths
                segs.append(t)
            k += 1
        if segs:
            paths.append(segs)
        return paths


def read_items(src: str) -> tuple[list[Item], list[str]]:
    """Every item in a file's source, and the file's inner attributes."""
    toks = tokenize(src)
    reader = _Reader(toks)
    return reader.items(0, len(toks))


# ── Module tree ───────────────────────────────────────────────────────────────


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _dirname(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def is_crate_root(path: str) -> bool:
    """A file a target starts from: `lib.rs`, `main.rs`, `build.rs`, or a
    single-file target under `src/bin`, `examples`, `tests` or `benches`."""
    parts = _norm(path).split("/")
    if parts[-1] in ("lib.rs", "main.rs", "build.rs"):
        return True
    return len(parts) >= 2 and parts[-2] in ("bin", "examples", "tests", "benches")


def _owns_directory(path: str) -> bool:
    """Whether `mod foo;` in this file looks for `foo.rs` beside it (crate
    roots and `mod.rs`) rather than in a directory named after the file."""
    return is_crate_root(path) or _basename(path) == "mod.rs"


def crate_name_for(root: str) -> str:
    """A crate root's name by its package directory: `crates/hal-core/src/lib.rs`
    -> `hal_core`. Right whenever the directory and the package agree, which is
    the convention and not a rule; edges resolved through it say so."""
    parts = _norm(root).split("/")
    if len(parts) >= 3 and parts[-2] == "src":
        return parts[-3].replace("-", "_")
    return ""


@dataclass
class _Module:
    path: tuple[str, ...]  # ('crate', 'net', 'tcp')
    file: str
    children: dict[str, "_Module"] = field(default_factory=dict)
    parent: "_Module | None" = None


# ── Parser ────────────────────────────────────────────────────────────────────


class RustLanguageParser:
    """LanguageParser implementation for `.rs` files, stdlib only."""

    language: ClassVar[str] = "rust"
    extensions: ClassVar[list[str]] = [".rs"]

    # Whole tree at once: `mod` declarations, `use` paths and calls cross files.
    batch_whole_tree: ClassVar[bool] = True

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        graph = nx.DiGraph()
        if depth < 2:
            return graph

        keyed: dict[str, File] = {}
        for f in files:
            if f.raw:
                keyed[_norm(f.url or f.name)] = f
        parsed: dict[str, tuple[list[Item], list[str]]] = {
            key: read_items(f.raw) for key, f in keyed.items()
        }
        original_key = {key: (f.url or f.name) for key, f in keyed.items()}

        relations: list[tuple[str, str, dict]] = []
        file_meta: dict[str, dict] = {}
        for key, (_, inner) in parsed.items():
            if inner:
                # `#![cfg_attr(not(test), no_std)]` is no_std where it matters
                # and is counted; the attribute text says the condition.
                file_meta[original_key[key]] = {
                    "inner_attributes": inner,
                    "no_std": any("no_std" in a for a in inner),
                    "no_main": any("no_main" in a for a in inner),
                }

        index = _Index()
        for key, (items, _) in parsed.items():
            self._emit(graph, items, original_key[key], parent=None, prefix="",
                       level=2, depth=depth, index=index)

        modules, declares = self._module_tree(parsed)
        for item, target in declares:
            node_id = index.node_of.get(id(item))
            if node_id:
                relations.append((node_id, original_key[target], {"kind": "declares"}))
        for src, dst, attrs in self._dependencies(parsed, modules, original_key):
            if dst.startswith("external::") and dst not in graph:
                graph.add_node(dst, **make_node(
                    dst, depth=1, language="external", kind="external_crate",
                    label=attrs["crate"], meta={"std": attrs["std"]}))
            relations.append((src, dst, attrs))
        self._resolve(graph, index)

        graph.graph["file_relations"] = relations
        graph.graph["file_meta"] = file_meta

        construct_service.annotate(graph)
        return graph

    # -- emitting nodes ---------------------------------------------------------

    def _emit(self, graph: nx.DiGraph, items: Iterable[Item], file: str, parent: str | None,
              prefix: str, level: int, depth: int, index: "_Index",
              owner: Item | None = None) -> None:
        for item in items:
            if level > depth:
                return
            qualified = f"{prefix}{item.name}" if item.name else f"{prefix}{item.kind}"
            node_id = f"rust::{file}::{item.kind}::{qualified}::{item.line}"
            meta: dict = {
                "qualifiers": item.qualifiers,
                "visibility": item.visibility,
                "attributes": item.attributes,
                "line_end": item.line_end or item.line,
            }
            for key, value in (("abi", item.abi), ("doc", item.doc), ("type_str", item.type_str),
                               ("trait", item.trait), ("self_type", item.self_type),
                               ("receiver", item.receiver), ("macros", item.macros),
                               ("unsafe_blocks", item.unsafe_blocks),
                               ("supertraits", item.supertraits)):
                if value:
                    meta[key] = value
            if item.kind in ("function", "method"):
                meta["param_count"] = item.param_count
            if item.kind in ("struct", "union"):
                meta["field_count"] = len(item.children)
            if item.kind == "enum":
                meta["variant_count"] = len(item.children)
                meta["c_like"] = bool(item.children) and not any(v.payload for v in item.children)
            if item.volatile_accesses:
                meta["volatile_accesses"] = item.volatile_accesses
            if item.kind == "static" and "mut" in item.qualifiers:
                meta["shared_mutable"] = True
            if item.kind == "module":
                meta["inline"] = item.mod_inline
            graph.add_node(node_id, **make_node(
                node_id, depth=min(level, 3), language="rust", kind=item.kind,
                label=item.label or (f"{item.name}!" if item.kind == "macro" else item.name),
                file=file, line=item.line, meta=meta))
            if parent is not None:
                graph.add_edge(parent, node_id, **make_edge("contains"))
            index.add(item, node_id, file, owner)
            if item.children:
                child_prefix = f"{qualified}::"
                self._emit(graph, item.children, file, node_id, child_prefix, level + 1,
                           depth, index, owner=item)

    # -- module tree and use resolution -----------------------------------------

    def _module_tree(self, parsed: dict[str, tuple[list[Item], list[str]]]
                     ) -> tuple[dict[str, _Module], list[tuple[Item, str]]]:
        """Each file's module, walked from every crate root, and every
        `mod foo;` item paired with the file it named, when that file is in
        the batch."""
        modules: dict[str, _Module] = {}
        declares: list[tuple[Item, str]] = []

        def visit(key: str, module: _Module, items: list[Item], dir_for_children: str,
                  seen: set[str]) -> None:
            for item in items:
                if item.kind != "module":
                    continue
                child = module.children.get(item.name) or _Module(module.path + (item.name,), key, parent=module)
                module.children[item.name] = child
                sub_dir = f"{dir_for_children}/{item.name}" if dir_for_children else item.name
                if item.mod_inline:
                    visit(key, child, item.children, sub_dir, seen)
                    continue
                path_attr = next((a for a in item.attributes if attribute_name(a) == "path"), "")
                candidates = []
                if path_attr:
                    m = re.search(r'"([^"]+)"', path_attr)
                    if m:
                        candidates.append(f"{_dirname(key)}/{m.group(1)}" if _dirname(key) else m.group(1))
                candidates += [f"{sub_dir}.rs", f"{sub_dir}/mod.rs"]
                target = next((c for c in candidates if c in parsed and c not in seen), None)
                if target is None:
                    continue
                declares.append((item, target))
                child.file = target
                modules[target] = child
                target_dir = _dirname(target) if _owns_directory(target) else target[:-3]
                visit(target, child, parsed[target][0], target_dir, seen | {target})

        for key in sorted(parsed):
            if is_crate_root(key) and key not in modules:
                root = _Module(("crate",), key)
                modules[key] = root
                visit(key, root, parsed[key][0], _dirname(key), {key})
        return modules, declares

    def _dependencies(self, parsed: dict[str, tuple[list[Item], list[str]]],
                      modules: dict[str, _Module], original_key: dict[str, str]
                      ) -> list[tuple[str, str, dict]]:
        crates: dict[str, _Module] = {}
        for key, module in modules.items():
            name = crate_name_for(key) if module.path == ("crate",) else ""
            if name and _basename(key) == "lib.rs":
                crates[name] = module

        edges: dict[tuple[str, str], dict] = {}
        for key, (items, _) in parsed.items():
            here = modules.get(key)
            for item in _walk(items):
                for path in item.use_paths:
                    target, resolution = _resolve_use(path, here, crates)
                    if target is None:
                        first = path[0].lstrip(":") if path else ""
                        # A capitalised head is a type or a variant in scope
                        # (`use Color::*`), never a crate by convention.
                        if not first or first in ("crate", "self", "super") or first[:1].isupper() or (
                                here and first in here.children):
                            continue
                        dest = f"external::crate::{first}"
                        attrs = {"kind": "depends_on", "resolution": "external",
                                 "crate": first, "std": first in _STD_CRATES}
                    else:
                        if target.file == key:
                            continue
                        dest = original_key[target.file]
                        attrs = {"kind": "depends_on", "resolution": resolution}
                    edges.setdefault((original_key[key], dest), attrs)
        return [(src, dst, attrs) for (src, dst), attrs in edges.items()]

    # -- cross-item relations ----------------------------------------------------

    def _resolve(self, graph: nx.DiGraph, index: "_Index") -> None:
        for node_id, item in index.impls:
            if item.trait:
                target = index.unique("trait", item.trait)
                if target:
                    graph.add_edge(node_id, target, **make_edge("implements"), resolution="unique-name")
            if item.self_type:
                target = index.unique("type", item.self_type)
                if target:
                    graph.add_edge(node_id, target, **make_edge("extends"), resolution="unique-name")
        for node_id, item in index.traits:
            for name in item.supertraits:
                target = index.unique("trait", name)
                if target and target != node_id:
                    graph.add_edge(node_id, target, **make_edge("inherits"), resolution="unique-name")
        for node_id, item in index.typed:
            kind = "aliases" if item.kind == "type" else "type_of"
            for name in sorted(set(item.type_refs)):
                target = index.unique("type", name) or (index.unique("trait", name) if kind == "type_of" else None)
                if target and target != node_id:
                    graph.add_edge(node_id, target, **make_edge(kind), resolution="unique-name")
        for node_id, item, owner in index.callers:
            unresolved = 0
            counts: dict[str, int] = {}
            for form, segs in item.calls:
                target = None
                if form == "path":
                    if len(segs) >= 2 and (segs[-2] == "Self" or segs[-2][:1].isupper()):
                        self_type = owner.self_type if (segs[-2] == "Self" and owner is not None) else segs[-2]
                        target = index.associated(self_type, segs[-1])
                    else:
                        target = index.unique("fn", segs[-1])
                elif form == "self-method" and owner is not None:
                    target = index.associated(owner.self_type or owner.name, segs[-1])
                if target and target != node_id:
                    counts[target] = counts.get(target, 0) + 1
                else:
                    unresolved += 1
            for target, count in counts.items():
                graph.add_edge(node_id, target, **make_edge("calls", float(count)),
                               resolution="unique-name")
            if item.calls:
                graph.nodes[node_id]["meta"]["calls_unresolved"] = unresolved


def _walk(items: Iterable[Item]) -> Iterable[Item]:
    for item in items:
        yield item
        yield from _walk(item.children)


def _resolve_use(path: list[str], here: _Module | None, crates: dict[str, _Module]
                 ) -> tuple[_Module | None, str]:
    """The deepest module a `use` path walks to, and how it was found."""
    if not path:
        return None, ""
    first = path[0]
    rest = path[1:]
    resolution = "module-tree"
    if first == "crate" and here is not None:
        module = here
        while module.parent is not None:
            module = module.parent
    elif first in ("self",) and here is not None:
        module = here
    elif first == "super" and here is not None:
        module = here.parent or here
        while rest and rest[0] == "super":
            module = module.parent or module
            rest = rest[1:]
    elif here is not None and first in here.children:
        module, rest = here.children[first], rest
    elif first.lstrip(":") in crates:
        module = crates[first.lstrip(":")]
        resolution = "crate-by-directory"
    else:
        return None, ""
    for seg in rest:
        child = module.children.get(seg)
        if child is None:
            break
        module = child
    return module, resolution


class _Index:
    """Names to node ids, kept only to resolve a relation when exactly one
    local thing has the name -- an ambiguous name resolves to nothing."""

    _TYPE_KINDS = {"struct", "enum", "union", "type", "trait"}

    def __init__(self) -> None:
        self.by: dict[tuple[str, str], list[str]] = {}
        self.assoc: dict[tuple[str, str], list[str]] = {}
        self.impls: list[tuple[str, Item]] = []
        self.traits: list[tuple[str, Item]] = []
        self.typed: list[tuple[str, Item]] = []
        self.callers: list[tuple[str, Item, Item | None]] = []
        self.node_of: dict[int, str] = {}

    def add(self, item: Item, node_id: str, file: str, owner: Item | None) -> None:
        self.node_of[id(item)] = node_id
        if item.kind == "function":
            self.by.setdefault(("fn", item.name), []).append(node_id)
        if item.kind in self._TYPE_KINDS - {"trait"}:
            self.by.setdefault(("type", item.name), []).append(node_id)
        if item.kind == "trait":
            self.by.setdefault(("trait", item.name), []).append(node_id)
            self.traits.append((node_id, item))
        if item.kind == "impl":
            self.impls.append((node_id, item))
        if item.kind == "method" and owner is not None:
            self.assoc.setdefault((owner.self_type or owner.name, item.name), []).append(node_id)
        if item.kind in ("field", "type", "variant") and item.type_refs:
            self.typed.append((node_id, item))
        if item.kind in ("function", "method") and item.calls:
            self.callers.append((node_id, item, owner if owner is not None and owner.kind in ("impl", "trait") else None))

    def unique(self, kind: str, name: str) -> str | None:
        found = self.by.get((kind, name), [])
        return found[0] if len(found) == 1 else None

    def associated(self, self_type: str, name: str) -> str | None:
        found = self.assoc.get((self_type, name), [])
        return found[0] if len(found) == 1 else None


# ── Register on import ────────────────────────────────────────────────────────
ParserRegistry.register(RustLanguageParser())
