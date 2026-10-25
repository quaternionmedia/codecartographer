"""
Linker Script Parser
====================
Reads GNU ld linker scripts (`.ld`, `.lds`, and the `memory.x` convention the
embedded Rust runtimes use) as the memory map a device is built against.

**THE LAYER BELOW BOTH LANGUAGES.** A C firmware and a Rust one meet here: each
names output sections, and the script places those sections into the device's
memory regions. A `#[link_section = ".ram_func"]` in Rust and an
`__attribute__((section(".ram_func")))` in C are claims this file decides, so it
is read into the same graph -- and, through `constructs.yaml`, the same
`layout.section` and `layout.region` constructs -- as the code that makes them.

What is read
------------
region   each `MEMORY { NAME (attrs) : ORIGIN = .., LENGTH = .. }` entry, with
         its origin and length as written and, where the expression is
         arithmetic on numbers with an optional K/M suffix, in bytes.
         `REGION_ALIAS("A", B)` is a region `A` that `aliases` B.
section  each output section inside `SECTIONS { .. }`, `placed_in` its VMA
         region (`> RAM`) and `loaded_from` its LMA region (`AT> FLASH`).
symbol   `name = expr;` and `PROVIDE(name = expr);` at script or SECTIONS
         level; one inside a section is that section's child. A symbol whose
         expression names `ORIGIN(R)` or `LENGTH(R)` `refers_to` region R.
entry    `ENTRY(symbol)`.

`INCLUDE file` becomes an `includes` relation to that file when it is in the
same parse -- cortex-m-rt's `link.x` includes the crate's `memory.x` this way.

How a name is resolved
----------------------
Every relation says how in its `resolution`, and a name more than one thing
could be draws nothing. An `INCLUDE` names the file beside the includer
(`same-directory`), else the one file in the batch whose path ends with the
name (`unique-name`). A region is the one its own file declares
(`same-file`), else the one the files it includes declare (`include`), else
the one region of that name in the batch (`unique-name`) -- so two boards'
`memory.x`, each with its `RAM`, keep their edges apart.

`.x` is also the extension of Sun RPC and Alex sources, so a `.x` file is read
only when it holds a linker statement; `.ld` and `.lds` always are.

Node ID format
--------------
``linker::{file}::{kind}::{name}::{line}``, the line its definition is on; a
second definition of one kind and name on one line takes ``#2``, and so on.

WHAT THIS CANNOT DO. Evaluate the script. A region size that depends on a
symbol, or a section placed by an expression rather than `> REGION`, is drawn
with the text as written and no byte count, and `meta.evaluated` says which.
"""

from __future__ import annotations

import ast
import math
import posixpath
import re
from typing import Callable, ClassVar, Iterable

import networkx as nx

from codecarto.models.source_data import File
from codecarto.services import construct_service
from codecarto.services.parsers.language_parser import (
    ParserRegistry,
    make_edge,
    make_node,
)

_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

# NAME (attrs) : ORIGIN = expr , LENGTH = expr -- the origin ends at a comma
# outside parentheses, so `MAX(a, b)` is one origin; the length ends at a line
# end, a `;`, or where the next region begins (a name, optional attributes,
# then `:`), so `LENGTH = LENGTH(FLASH) - 4K` keeps its whole expression.
_REGION = re.compile(
    r"([A-Za-z_][\w.]*)\s*(?:\(\s*([!rwxaliRWXALI]*)\s*\))?\s*:\s*"
    r"(?:ORIGIN|org|o)\s*=\s*((?:[^,()]|\((?:[^()]|\([^()]*\))*\))+?)\s*,\s*(?:LENGTH|len|l)\s*=\s*([^\n;}]+?)"
    r"\s*(?=\n|;|$|\s[A-Za-z_][\w.]*\s*(?:\([^)]*\)\s*)?:)"
)

# `name = expr;` or `PROVIDE(name = expr);`. The closing paren is consumed only
# when PROVIDE opened one, so `x = ORIGIN(RAM);` keeps its own. An `=` that
# another follows is a comparison (`ASSERT(a == b, ..)`), not an assignment.
_ASSIGN = re.compile(
    r"(?:(PROVIDE(?:_HIDDEN)?)\s*\(\s*)?([A-Za-z_.$][\w.$]*)\s*=(?!=)\s*([^;]+?)\s*(?(1)\))\s*;"
)
_REGION_REF = re.compile(r"\b(?:ORIGIN|LENGTH)\s*\(\s*([A-Za-z_][\w.]*)\s*\)")
_SECTION_HEAD = re.compile(r"\s*([.A-Za-z_/][\w.\-/$]*)\s*([^:{;=]*?)\s*:\s*([^{;]*?)\{")
_INCLUDE = re.compile(r"\bINCLUDE\s+([\w./\-]+)")
# `INCLUDE file` needs no `;`, so inside SECTIONS it is no section's name.
_INCLUDE_STATEMENT = re.compile(r"\s*INCLUDE\s+[\w./\-]+\s*;?")
# What follows a section's closing brace, and nothing else does: `> VMA`,
# `AT > LMA`, `:phdr`, `=fill`, and a trailing comma.
_PLACEMENT = re.compile(r"(?:\s*(?:AT\s*>\s*[\w.]+|>\s*[\w.]+|:\s*[\w.]+|=\s*[^\s;,}]+|,))*")
# A statement only a linker script makes: a `.x` file without one is someone
# else's (svd2rust's `device.x` is PROVIDEs alone, and is a linker script).
_LINKER_STATEMENT = re.compile(
    r"\b(?:MEMORY\s*\{|SECTIONS\s*\{|ENTRY\s*\(|INCLUDE\s+[\w./\-]|REGION_ALIAS\s*\(|PROVIDE(?:_HIDDEN)?\s*\()"
)


def size_in_bytes(text: str) -> int | None:
    """`512K` -> 524288, `0x08000000` -> 134217728, `256K - 4K` -> 258048.

    None for anything that is not arithmetic on numbers: a symbol, a function
    such as `LENGTH(FLASH)`, a division. Evaluated by walking the expression's
    syntax tree, never by executing it."""
    def scaled(m: re.Match) -> str:
        return str(int(m.group(1), 0) * {"": 1, "K": 1024, "M": 1 << 20}[m.group(2).upper()])

    try:
        python = re.sub(r"(0[xX][0-9A-Fa-f]+|\d+)([kKmM]?)\b", scaled, text.strip())
        tree = ast.parse(python, mode="eval")
    except (SyntaxError, ValueError):
        return None

    def value(node: ast.AST) -> int:
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -value(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            left, right = value(node.left), value(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            return left * right
        raise ValueError(type(node).__name__)

    try:
        return value(tree.body)
    except ValueError:
        return None


def _blank(text: str, spans: Iterable[tuple[int, int]]) -> str:
    """*text* with every span's characters but its newlines made spaces, so an
    offset found in the result is the same offset in *text*."""
    out = list(text)
    for a, b in spans:
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "
    return "".join(out)


def _close(text: str, i: int, end: int) -> int:
    """*i* just past a `{`: the index just past the `}` that closes it."""
    depth = 1
    while i < end and depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return i


def _blocks(text: str, keyword: str) -> list[tuple[int, int]]:
    """Where the body of every `KEYWORD { .. }` block starts and ends."""
    return [(m.end(), _close(text, m.end(), len(text)) - 1)
            for m in re.finditer(rf"\b{keyword}\s*\{{", text)]


def _sections(text: str, start: int, end: int
              ) -> tuple[list[tuple[str, int, int, int, str]], list[tuple[int, int]]]:
    """(name, where the name is, inner start, inner end, placement) for each
    output section in the SECTIONS body `text[start:end]`, and the spans the
    sections and unrecognised blocks take -- what is left between them is the
    body's own statements."""
    found: list[tuple[str, int, int, int, str]] = []
    taken: list[tuple[int, int]] = []
    i = start
    while i < end:
        include = _INCLUDE_STATEMENT.match(text, i, end)
        if include:
            i = include.end()
            continue
        match = _SECTION_HEAD.match(text, i, end)
        if match is None:
            stop = min((k for k in (text.find(";", i, end), text.find("{", i, end)) if k >= 0), default=-1)
            if stop < 0:
                break
            if text[stop] == "{":  # a brace that opens nothing we recognise
                k = _close(text, stop + 1, end)
                taken.append((stop, k))
                i = k
                continue
            i = stop + 1
            continue
        j = _close(text, match.end(), end)
        # The placement is what may follow a closing brace, and ends at the
        # first thing that may not -- the next section's name, say.
        placement = _PLACEMENT.match(text, j, end)
        found.append((match.group(1), match.start(1), match.end(), j - 1, placement.group()))
        taken.append((match.start(), placement.end()))
        i = max(placement.end(), i + 1)
    return found, taken


def _includes(file: str, text: str, keys: dict[str, str]) -> list[tuple[str, str]]:
    """The file each `INCLUDE` names, and how it was found. *keys* maps each
    file's path, with `/` separators, to its key."""
    here = posixpath.dirname(file.replace("\\", "/"))
    found: list[tuple[str, str]] = []
    for m in _INCLUDE.finditer(text):
        written = posixpath.normpath(m.group(1))
        beside = posixpath.normpath(posixpath.join(here, written))
        if beside in keys and keys[beside] != file:
            found.append((keys[beside], "same-directory"))
            continue
        named = [key for path, key in keys.items()
                 if key != file and (path == written or path.endswith("/" + written))]
        if len(named) == 1:
            found.append((named[0], "unique-name"))
    return found


class LinkerScriptParser:
    language: ClassVar[str] = "linker"
    extensions: ClassVar[list[str]] = [".ld", ".lds", ".x"]
    batch_whole_tree: ClassVar[bool] = True  # INCLUDE crosses files

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        graph = nx.DiGraph()
        if depth < 2:
            return graph
        # Comments become blank lines, so line numbers still match the source.
        texts: dict[str, str] = {}
        for f in files:
            if not f.raw:
                continue
            key = f.url or f.name
            text = _COMMENT.sub(lambda m: "\n" * m.group().count("\n"), f.raw)
            if (f.name or key).lower().endswith(".x") and not _LINKER_STATEMENT.search(text):
                continue  # Sun RPC, Alex: not a linker script
            texts[key] = text
        keys = {key.replace("\\", "/"): key for key in texts}

        relations: list[tuple[str, str, dict]] = []
        includes: dict[str, list[tuple[str, str]]] = {}
        for file, text in texts.items():
            includes[file] = _includes(file, text, keys)
            relations += [(file, target, {"kind": "includes", "resolution": how})
                          for target, how in includes[file]]

        # Regions and aliases first, across every file: `link.x` places
        # sections in the FLASH and RAM that `memory.x` declares and it
        # INCLUDEs, so a region is known beyond its own file, as it is to the
        # linker -- but a file's own and its includes' come first.
        declared: dict[str, dict[str, list[str]]] = {}
        aliases: list[tuple[str, str, str]] = []
        for file, text in texts.items():
            declared[file] = self._regions(graph, file, text)
            for m in re.finditer(r'REGION_ALIAS\s*\(\s*"?([\w.]+)"?\s*,\s*([\w.]+)\s*\)', text):
                alias = self._node(graph, file, text, m.start(1), "region", m.group(1), alias_of=m.group(2))
                declared[file].setdefault(m.group(1), []).append(alias)
                aliases.append((file, alias, m.group(2)))
        region = _region_lookup(declared, includes)
        for file, alias, target in aliases:
            found = region(file, target)
            if found and found[0] != alias:
                graph.add_edge(alias, found[0], **make_edge("aliases"), resolution=found[1])

        for file, text in texts.items():
            self._rest(graph, file, text, depth, region)
        graph.graph["file_relations"] = relations
        construct_service.annotate(graph)
        return graph

    @staticmethod
    def _node(graph: nx.DiGraph, file: str, text: str, at: int, kind: str, name: str,
              level: int = 2, **meta) -> str:
        """A node for the definition of *name* at offset *at* of *text*."""
        line = text.count("\n", 0, at) + 1
        base = node_id = f"linker::{file}::{kind}::{name}::{line}"
        seen = 1
        while node_id in graph:  # `_a = 1; _a = 2;` on one line
            seen += 1
            node_id = f"{base}#{seen}"
        graph.add_node(node_id, **make_node(
            node_id, depth=level, language="linker", kind=kind, label=name,
            file=file, line=line, meta=meta))
        return node_id

    def _regions(self, graph: nx.DiGraph, file: str, text: str) -> dict[str, list[str]]:
        """The regions *file*'s MEMORY blocks declare, by name."""
        declared: dict[str, list[str]] = {}
        for start, end in _blocks(text, "MEMORY"):
            for m in _REGION.finditer(text, start, end):
                name, attrs, origin, length = m.group(1), m.group(2) or "", m.group(3), m.group(4)
                length_bytes = size_in_bytes(length)
                origin_value = size_in_bytes(origin)
                rid = self._node(graph, file, text, m.start(1), "region", name, attributes=attrs,
                                 origin=origin.strip(), length=length.strip(),
                                 length_bytes=length_bytes, origin_value=origin_value,
                                 evaluated=length_bytes is not None and origin_value is not None)
                if length_bytes:
                    # Bigger memory, bigger node, log-scaled so a 1 MiB flash
                    # does not push a 4 KiB RAM out of sight.
                    graph.nodes[rid]["size"] = 10 + 2 * math.log2(max(length_bytes, 1024) / 1024)
                declared.setdefault(name, []).append(rid)
        return declared

    def _rest(self, graph: nx.DiGraph, file: str, text: str, depth: int,
              region: Callable[[str, str], tuple[str, str] | None]) -> None:
        def node(at: int, kind: str, name: str, level: int = 2, **meta) -> str:
            return self._node(graph, file, text, at, kind, name, level, **meta)

        def place(sid: str, name: str, kind: str) -> None:
            found = region(file, name)
            if found:
                graph.add_edge(sid, found[0], **make_edge(kind), resolution=found[1])

        def symbol(m: re.Match, parent: str | None, level: int) -> None:
            name, expr = m.group(2), m.group(3)
            if name == ".":
                return  # the location counter is not a symbol
            sid = node(m.start(2), "symbol", name, level=level, expression=expr.strip(),
                       provided=bool(m.group(1)))
            if parent:
                graph.add_edge(parent, sid, **make_edge("contains"))
            for ref in sorted(set(_REGION_REF.findall(expr))):
                place(sid, ref, "refers_to")

        for m in re.finditer(r"\bENTRY\s*\(\s*([\w.$]+)\s*\)", text):
            node(m.start(1), "entry", m.group(1))

        bodies = _blocks(text, "SECTIONS")
        outside = _blank(text, bodies + _blocks(text, "MEMORY"))
        for m in _ASSIGN.finditer(outside):
            symbol(m, parent=None, level=2)

        for start, end in bodies:
            found, taken = _sections(text, start, end)
            for name, at, inner_start, inner_end, placement in found:
                lma = re.search(r"AT\s*>\s*([\w.]+)", placement)
                vma = re.search(r">\s*([\w.]+)", re.sub(r"AT\s*>\s*[\w.]+", "", placement))
                inner = text[inner_start:inner_end]
                sid = node(at, "section", name, vma_region=vma.group(1) if vma else "",
                           lma_region=lma.group(1) if lma else "",
                           inputs=sorted(set(re.findall(r"\(\s*([.\w*]+)", inner)))[:12])
                if vma:
                    place(sid, vma.group(1), "placed_in")
                if lma:
                    place(sid, lma.group(1), "loaded_from")
                if depth >= 3:
                    for m in _ASSIGN.finditer(text, inner_start, inner_end):
                        symbol(m, parent=sid, level=3)
            between = _blank(text, [(0, start), (end, len(text))] + taken)
            for m in _ASSIGN.finditer(between):
                symbol(m, parent=None, level=2)


def _region_lookup(declared: dict[str, dict[str, list[str]]],
                   includes: dict[str, list[tuple[str, str]]]
                   ) -> Callable[[str, str], tuple[str, str] | None]:
    """`region(file, name)`: the region node *name* means in *file*, and how
    that was decided -- or None, when no region or more than one could be it."""
    def reached(file: str) -> set[str]:
        seen: set[str] = set()
        todo = [file]
        while todo:
            for target, _ in includes.get(todo.pop(), []):
                if target not in seen and target != file:
                    seen.add(target)
                    todo.append(target)
        return seen

    def region(file: str, name: str) -> tuple[str, str] | None:
        own = declared.get(file, {}).get(name, [])
        if own:
            return (own[0], "same-file") if len(own) == 1 else None
        via = {rid for f in reached(file) for rid in declared.get(f, {}).get(name, [])}
        if via:
            return (via.pop(), "include") if len(via) == 1 else None
        anywhere = [rid for names in declared.values() for rid in names.get(name, [])]
        return (anywhere[0], "unique-name") if len(anywhere) == 1 else None

    return region


ParserRegistry.register(LinkerScriptParser())
