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

WHAT THIS CANNOT DO. Evaluate the script. A region size that depends on a
symbol, or a section placed by an expression rather than `> REGION`, is drawn
with the text as written and no byte count, and `meta.evaluated` says which.
"""

from __future__ import annotations

import ast
import math
import re
from pathlib import PurePosixPath
from typing import Callable, ClassVar

import networkx as nx

from codecarto.models.source_data import File
from codecarto.services import construct_service
from codecarto.services.parsers.language_parser import (
    ParserRegistry,
    make_edge,
    make_node,
)

_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

# NAME (attrs) : ORIGIN = expr , LENGTH = expr -- the length ends at a line
# end, a `;`, or where the next region begins (a name, optional attributes,
# then `:`), so `LENGTH = LENGTH(FLASH) - 4K` keeps its whole expression.
_REGION = re.compile(
    r"([A-Za-z_][\w.]*)\s*(?:\(\s*([!rwxaliRWXALI]*)\s*\))?\s*:\s*"
    r"(?:ORIGIN|org|o)\s*=\s*([^,]+?)\s*,\s*(?:LENGTH|len|l)\s*=\s*([^\n;}]+?)"
    r"\s*(?=\n|;|$|\s[A-Za-z_][\w.]*\s*(?:\([^)]*\)\s*)?:)"
)

# `name = expr;` or `PROVIDE(name = expr);`. The closing paren is consumed only
# when PROVIDE opened one, so `x = ORIGIN(RAM);` keeps its own.
_ASSIGN = re.compile(
    r"(?:(PROVIDE(?:_HIDDEN)?)\s*\(\s*)?([A-Za-z_.$][\w.$]*)\s*=\s*([^;]+?)\s*(?(1)\))\s*;"
)
_REGION_REF = re.compile(r"\b(?:ORIGIN|LENGTH)\s*\(\s*([A-Za-z_][\w.]*)\s*\)")
_SECTION_HEAD = re.compile(r"\s*([.A-Za-z_/][\w.\-/$]*)\s*([^:{;=]*?)\s*:\s*([^{;]*?)\{")


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


def _blocks(text: str, keyword: str) -> list[str]:
    """The bodies of every `KEYWORD { .. }` block, braces balanced."""
    bodies = []
    for match in re.finditer(rf"\b{keyword}\s*\{{", text):
        depth, i = 1, match.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        bodies.append(text[match.end(): i - 1])
    return bodies


def _sections(body: str) -> tuple[list[tuple[str, str, str]], str]:
    """(name, inner, placement) for each output section in a SECTIONS body,
    and the body with every section removed -- the statements between them."""
    found: list[tuple[str, str, str]] = []
    between: list[str] = []
    i = 0
    while i < len(body):
        match = _SECTION_HEAD.match(body, i)
        if match is None:
            stop = min((k for k in (body.find(";", i), body.find("{", i)) if k >= 0), default=-1)
            if stop < 0:
                between.append(body[i:])
                break
            if body[stop] == "{":  # a brace that opens nothing we recognise
                depth, k = 1, stop + 1
                while k < len(body) and depth:
                    depth += {"{": 1, "}": -1}.get(body[k], 0)
                    k += 1
                between.append(body[i:stop])
                i = k
                continue
            between.append(body[i: stop + 1])
            i = stop + 1
            continue
        depth, j = 1, match.end()
        while j < len(body) and depth:
            depth += {"{": 1, "}": -1}.get(body[j], 0)
            j += 1
        inner = body[match.end(): j - 1]
        # The placement follows the closing brace, on its line or on lines that
        # begin with `>` or `AT` -- nothing else continues a section statement.
        stop = re.search(r"\n\s*(?!>|AT\b)\S", body[j:])
        placement = body[j: j + stop.start()] if stop else body[j:]
        found.append((match.group(1), inner, placement))
        i = j + len(placement)
    return found, "".join(between)


class LinkerScriptParser:
    language: ClassVar[str] = "linker"
    extensions: ClassVar[list[str]] = [".ld", ".lds", ".x"]
    batch_whole_tree: ClassVar[bool] = True  # INCLUDE crosses files

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        graph = nx.DiGraph()
        if depth < 2:
            return graph
        # Comments become blank lines, so line numbers still match the source.
        texts = {f.url or f.name: _COMMENT.sub(lambda m: "\n" * m.group().count("\n"), f.raw)
                 for f in files if f.raw}
        by_name = {PurePosixPath(key.replace("\\", "/")).name: key for key in texts}

        # Regions first, across every file: `link.x` places sections in the
        # FLASH and RAM that `memory.x` declares and it INCLUDEs, so a region
        # is known to the whole batch, as it is to the linker.
        regions: dict[str, str] = {}
        for file, text in texts.items():
            self._regions(graph, file, text, regions)
        for file, text in texts.items():
            self._aliases(graph, file, text, regions)
        relations: list[tuple[str, str, dict]] = []
        for file, text in texts.items():
            relations += self._rest(graph, file, text, depth, regions, by_name)
        graph.graph["file_relations"] = relations
        construct_service.annotate(graph)
        return graph

    @staticmethod
    def _node(graph: nx.DiGraph, file: str, text: str, kind: str, name: str,
              level: int = 2, **meta) -> str:
        node_id = f"linker::{file}::{kind}::{name}"
        at = re.search(rf"(?<![\w.]){re.escape(name)}(?![\w.])", text)
        graph.add_node(node_id, **make_node(
            node_id, depth=level, language="linker", kind=kind, label=name,
            file=file, line=text.count("\n", 0, at.start()) + 1 if at else 0, meta=meta))
        return node_id

    def _regions(self, graph: nx.DiGraph, file: str, text: str, regions: dict[str, str]) -> None:
        for body in _blocks(text, "MEMORY"):
            for m in _REGION.finditer(body):
                name, attrs, origin, length = m.group(1), m.group(2) or "", m.group(3), m.group(4)
                length_bytes = size_in_bytes(length)
                origin_value = size_in_bytes(origin)
                rid = self._node(graph, file, text, "region", name, attributes=attrs,
                                 origin=origin.strip(), length=length.strip(),
                                 length_bytes=length_bytes, origin_value=origin_value,
                                 evaluated=length_bytes is not None and origin_value is not None)
                if length_bytes:
                    # Bigger memory, bigger node, log-scaled so a 1 MiB flash
                    # does not push a 4 KiB RAM out of sight.
                    graph.nodes[rid]["size"] = 10 + 2 * math.log2(max(length_bytes, 1024) / 1024)
                regions[name] = rid

    def _aliases(self, graph: nx.DiGraph, file: str, text: str, regions: dict[str, str]) -> None:
        for m in re.finditer(r'REGION_ALIAS\s*\(\s*"?([\w.]+)"?\s*,\s*([\w.]+)\s*\)', text):
            alias = self._node(graph, file, text, "region", m.group(1), alias_of=m.group(2))
            regions[m.group(1)] = alias
            if m.group(2) in regions and regions[m.group(2)] != alias:
                graph.add_edge(alias, regions[m.group(2)], **make_edge("aliases"))

    def _rest(self, graph: nx.DiGraph, file: str, text: str, depth: int,
              regions: dict[str, str], by_name: dict[str, str]) -> list[tuple[str, str, dict]]:
        def node(kind: str, name: str, level: int = 2, **meta) -> str:
            return self._node(graph, file, text, kind, name, level, **meta)

        for m in re.finditer(r"\bENTRY\s*\(\s*([\w.$]+)\s*\)", text):
            node("entry", m.group(1))

        relations: list[tuple[str, str, dict]] = []
        for m in re.finditer(r"\bINCLUDE\s+([\w./\-]+)", text):
            target = by_name.get(PurePosixPath(m.group(1)).name)
            if target and target != file:
                relations.append((file, target, {"kind": "includes"}))

        outside = text
        for keyword in ("SECTIONS", "MEMORY"):
            for body in _blocks(text, keyword):
                outside = outside.replace(body, "")
        for m in _ASSIGN.finditer(outside):
            self._symbol(graph, node, regions, m, parent=None, level=2)

        for body in _blocks(text, "SECTIONS"):
            found, between = _sections(body)
            for name, inner, placement in found:
                lma = re.search(r"AT\s*>\s*([\w.]+)", placement)
                vma = re.search(r">\s*([\w.]+)", re.sub(r"AT\s*>\s*[\w.]+", "", placement))
                sid = node("section", name, vma_region=vma.group(1) if vma else "",
                           lma_region=lma.group(1) if lma else "",
                           inputs=sorted(set(re.findall(r"\(\s*([.\w*]+)", inner)))[:12])
                if vma and vma.group(1) in regions:
                    graph.add_edge(sid, regions[vma.group(1)], **make_edge("placed_in"))
                if lma and lma.group(1) in regions:
                    graph.add_edge(sid, regions[lma.group(1)], **make_edge("loaded_from"))
                if depth >= 3:
                    for m in _ASSIGN.finditer(inner):
                        self._symbol(graph, node, regions, m, parent=sid, level=3)
            for m in _ASSIGN.finditer(between):
                self._symbol(graph, node, regions, m, parent=None, level=2)
        return relations

    @staticmethod
    def _symbol(graph: nx.DiGraph, node: Callable[..., str], regions: dict[str, str],
                m: re.Match, parent: str | None, level: int) -> None:
        name, expr = m.group(2), m.group(3)
        if name == ".":
            return  # the location counter is not a symbol
        sid = node("symbol", name, level=level, expression=expr.strip(),
                   provided=bool(m.group(1)))
        if parent:
            graph.add_edge(parent, sid, **make_edge("contains"))
        for ref in sorted(set(_REGION_REF.findall(expr))):
            if ref in regions:
                graph.add_edge(sid, regions[ref], **make_edge("refers_to"))


ParserRegistry.register(LinkerScriptParser())
