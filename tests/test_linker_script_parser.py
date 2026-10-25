"""The linker-script reader: regions, sections, symbols and what places what."""

from __future__ import annotations

import pytest

from codecarto.models.source_data import File
from codecarto.services.parsers.language_parser import ParserRegistry
from codecarto.services.parsers.linker_script_parser import LinkerScriptParser, size_in_bytes

MEMORY_X = """
/* STM32F411CE:
   512K of flash, 128K of RAM */
MEMORY
{
  FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 512K
  RAM (rwx)  : ORIGIN = 0x20000000, LENGTH = 128K
  CCM        : ORIGIN = 0x10000000, LENGTH = 192K - LENGTH(RAM)
}
_stack_start = ORIGIN(RAM) + LENGTH(RAM);
"""

LINK_X = """
INCLUDE memory.x
ENTRY(Reset);
REGION_ALIAS("REGION_TEXT", FLASH);

SECTIONS
{
  .vector_table ORIGIN(FLASH) :
  {
    LONG(_stack_start);
    KEEP(*(.vector_table.reset_vector));
  } > FLASH

  .text : { *(.text .text.*); } > REGION_TEXT

  .data : ALIGN(4)
  {
    __sdata = .;
    *(.data .data.*);
    __edata = .;
  } > RAM AT > FLASH

  PROVIDE(__sidata = LOADADDR(.data));

  .bss (NOLOAD) : { __sbss = .; *(.bss .bss.*); __ebss = .; } > RAM
  /DISCARD/ : { *(.ARM.exidx .ARM.exidx.*); }
}
"""


@pytest.fixture(scope="module")
def graph():
    files = [File(name="memory.x", url="fw/memory.x", raw=MEMORY_X),
             File(name="link.x", url="fw/link.x", raw=LINK_X)]
    return LinkerScriptParser().parse_files(files, depth=3)


def by(graph, kind):
    return {d["label"]: (n, d) for n, d in graph.nodes(data=True) if d.get("kind") == kind}


def parse_one(text: str, depth: int = 3, name: str = "link.ld"):
    return LinkerScriptParser().parse_files([File(name=name, url=name, raw=text)], depth=depth)


def test_registered_for_linker_script_extensions():
    for ext in (".ld", ".lds", ".x"):
        assert isinstance(ParserRegistry.get(ext), LinkerScriptParser)


@pytest.mark.parametrize("text,expected", [
    ("512K", 524288), ("0x08000000", 0x08000000), ("128K", 131072), ("1M", 1 << 20),
    ("256K - 4K", 258048), ("2 * 64K", 131072), ("LENGTH(RAM) - 64K", None),
    ("_stack_size", None), ("64K / 2", None), ("__import__('os')", None),
])
def test_size_in_bytes_evaluates_arithmetic_and_nothing_else(text, expected):
    """Mutation: let `value` accept `ast.Div` -- the division row fails."""
    assert size_in_bytes(text) == expected


def test_regions_carry_their_sizes_and_attributes(graph):
    regions = by(graph, "region")
    flash = regions["FLASH"][1]["meta"]
    assert (flash["attributes"], flash["length_bytes"], flash["origin_value"]) == ("rx", 524288, 0x08000000)
    assert regions["RAM"][1]["meta"]["length_bytes"] == 131072


def test_a_length_that_names_another_region_keeps_its_whole_expression(graph):
    """` LENGTH(RAM)` inside an expression looks like the start of the next
    region -- whitespace, then a name -- until the `:` a region needs is
    required. Mutation: let the lookahead accept `(` in place of `:` -- the
    length is cut to `192K -` and this fails."""
    ccm = by(graph, "region")["CCM"][1]["meta"]
    assert ccm["length"] == "192K - LENGTH(RAM)"
    assert ccm["length_bytes"] is None and ccm["evaluated"] is False


def test_sections_are_placed_and_loaded(graph):
    sections = by(graph, "section")
    assert set(sections) == {".vector_table", ".text", ".data", ".bss", "/DISCARD/"}
    regions = {label: node_id for label, (node_id, _) in by(graph, "region").items()}
    placed = {(graph.nodes[u]["label"], graph.nodes[v]["label"])
              for u, v, d in graph.edges(data=True) if d["kind"] == "placed_in"}
    assert {(".vector_table", "FLASH"), (".text", "REGION_TEXT"), (".data", "RAM"), (".bss", "RAM")} <= placed
    loaded = {(graph.nodes[u]["label"], graph.nodes[v]["label"])
              for u, v, d in graph.edges(data=True) if d["kind"] == "loaded_from"}
    assert loaded == {(".data", "FLASH")}
    assert graph.has_edge(regions["REGION_TEXT"], regions["FLASH"])  # the alias


def test_symbols_entry_and_include(graph):
    symbols = by(graph, "symbol")
    assert symbols["_stack_start"][1]["meta"]["expression"] == "ORIGIN(RAM) + LENGTH(RAM)"
    assert symbols["__sidata"][1]["meta"]["provided"] is True
    assert symbols["__sidata"][1]["meta"]["expression"] == "LOADADDR(.data)"
    assert {"__sdata", "__edata", "__sbss", "__ebss"} <= set(symbols)
    assert set(by(graph, "entry")) == {"Reset"}
    assert graph.graph["file_relations"] == [
        ("fw/link.x", "fw/memory.x", {"kind": "includes", "resolution": "same-directory"})]


def test_every_relation_says_how_it_was_resolved(graph):
    """The record's rule: an edge that is not nesting carries a `resolution`."""
    unlabelled = {d["kind"] for _, _, d in graph.edges(data=True)
                  if d["kind"] != "contains" and "resolution" not in d}
    assert unlabelled == set()
    assert all("resolution" in attrs for _, _, attrs in graph.graph["file_relations"])


def test_nodes_carry_the_construct_vocabulary(graph):
    assert by(graph, "region")["FLASH"][1]["construct"] == "layout.region"
    assert by(graph, "section")[".text"][1]["construct"] == "layout.section"
    assert by(graph, "entry")["Reset"][1]["construct"] == "firmware.entry"


def test_line_numbers_survive_comment_removal(graph):
    """The fixture's comment spans two lines, so a comment deleted outright
    moves FLASH up one. Mutation: substitute comments with nothing."""
    assert by(graph, "region")["FLASH"][1]["line"] == 6


STM32CUBE = """ENTRY(Reset_Handler)

_estack = ORIGIN(RAM) + LENGTH(RAM);

MEMORY
{
RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 128K
}

SECTIONS
{
  /DISCARD/ : { libc.a ( * ) }
  .text : { *(.text) } > RAM
  /DISCARD/ : { *(.ARM.exidx*) }
}
"""


def test_a_node_is_where_it_is_defined_and_each_definition_is_one():
    """An id was kind and name, and a line the name's first appearance: the
    two `/DISCARD/` sections were one node, and `RAM` sat on line 3, where
    `_estack` reads it, not on line 7, where MEMORY declares it. Mutation:
    take the line from the first appearance again."""
    graph = parse_one(STM32CUBE)
    lines = sorted((d["kind"], d["label"], d["line"]) for _, d in graph.nodes(data=True))
    assert lines == [("entry", "Reset_Handler", 1),
                     ("region", "RAM", 7),
                     ("section", ".text", 13),
                     ("section", "/DISCARD/", 12),
                     ("section", "/DISCARD/", 14),
                     ("symbol", "_estack", 3)]


CORTEX_M_RT_ASSERT = """
SECTIONS
{
  .vector_table ORIGIN(FLASH) :
  {
    __vector_table = .;
    LONG(_stack_start);
    KEEP(*(.vector_table.reset_vector));
    __reset_vector = .;
  } > FLASH
}
ASSERT(__reset_vector == ADDR(.vector_table) + 0x8, "BUG(cortex-m-rt): .reset_vector is not right after .vector_table");
"""


def test_a_comparison_is_not_an_assignment():
    """`==` begins with `=`: cortex-m-rt's ASSERT read as a script-level
    `__reset_vector = = ADDR(..)`, which at depth 3 the real one inside the
    section overwrote, sharing its id. Mutation: let the `=` be followed by
    another -- the ASSERT's symbol comes back."""
    def reset_vectors(depth):
        return [(d["meta"]["expression"], d["line"]) for _, d in parse_one(CORTEX_M_RT_ASSERT, depth).nodes(data=True)
                if d["label"] == "__reset_vector"]
    assert reset_vectors(2) == []
    assert reset_vectors(3) == [(".", 9)]


def test_a_placement_belongs_to_the_section_it_follows():
    """A section's placement was the rest of its line, so a second section on
    it was dropped and the first took its `> RAM`; and an `INCLUDE` with no
    `;` before a section was read as a section named `INCLUDE`."""
    graph = parse_one("MEMORY { RAM : ORIGIN = 0, LENGTH = 1K }\n"
                      "SECTIONS {\n"
                      "  .a : { *(.a) } .b : { *(.b) } > RAM\n"
                      "  INCLUDE more.ld\n"
                      "  .c : { *(.c) } > RAM AT > RAM :text =0xFF,\n"
                      "  .d : { *(.d) }\n"
                      "}\n")
    sections = {label: (d["meta"]["vma_region"], d["meta"]["lma_region"])
                for label, (_, d) in by(graph, "section").items()}
    assert sections == {".a": ("", ""), ".b": ("RAM", ""), ".c": ("RAM", "RAM"), ".d": ("", "")}


def test_an_origin_with_a_comma_inside_parentheses_is_read():
    """`[^,]+?` could not hold the comma of `MAX(a, b)`, and the region was
    dropped without a word."""
    ram = by(parse_one("MEMORY\n{\n  RAM : ORIGIN = MAX(0x100, 0x200), LENGTH = 4K\n}\n"), "region")["RAM"][1]
    assert (ram["meta"]["origin"], ram["meta"]["origin_value"], ram["meta"]["length_bytes"],
            ram["meta"]["evaluated"], ram["line"]) == ("MAX(0x100, 0x200)", None, 4096, False, 3)


def test_a_region_is_read_from_the_file_then_what_it_includes_then_once_in_the_batch():
    """Regions sat in one table for the batch, by name, the last file read
    winning: two boards that each declare `RAM` crossed their edges. A name
    is looked up in its own file, then in the files that file includes, then
    in the batch when exactly one file declares it -- and otherwise nothing,
    as for `.shared`, which either board's `RAM` could be."""
    board = "MEMORY {{ RAM : ORIGIN = {origin}, LENGTH = 64K }}\n_stack_start = ORIGIN(RAM) + LENGTH(RAM);\n"
    link = "INCLUDE memory.x\nREGION_ALIAS(\"REGION_DATA\", RAM);\nSECTIONS { .data : { } > REGION_DATA }\n"
    files = [File(name="memory.x", url="board-a/memory.x", raw=board.format(origin="0x20000000")),
             File(name="memory.x", url="board-b/memory.x", raw=board.format(origin="0x10000000")),
             File(name="link.x", url="board-a/link.x", raw=link),
             File(name="link.x", url="board-b/link.x", raw=link),
             File(name="flash.ld", url="common/flash.ld", raw="MEMORY { FLASH : ORIGIN = 0, LENGTH = 1M }\n"),
             File(name="common.ld", url="common/common.ld",
                  raw="SECTIONS { .shared : { } > RAM\n .text : { } > FLASH }\n")]
    graph = LinkerScriptParser().parse_files(files, depth=3)
    drawn = {(graph.nodes[u]["file"], graph.nodes[u]["label"], d["kind"], graph.nodes[v]["file"],
              graph.nodes[v]["label"], d.get("resolution"))
             for u, v, d in graph.edges(data=True) if d["kind"] != "contains"}
    assert drawn == {
        ("board-a/memory.x", "_stack_start", "refers_to", "board-a/memory.x", "RAM", "same-file"),
        ("board-b/memory.x", "_stack_start", "refers_to", "board-b/memory.x", "RAM", "same-file"),
        ("board-a/link.x", "REGION_DATA", "aliases", "board-a/memory.x", "RAM", "include"),
        ("board-b/link.x", "REGION_DATA", "aliases", "board-b/memory.x", "RAM", "include"),
        ("board-a/link.x", ".data", "placed_in", "board-a/link.x", "REGION_DATA", "same-file"),
        ("board-b/link.x", ".data", "placed_in", "board-b/link.x", "REGION_DATA", "same-file"),
        ("common/common.ld", ".text", "placed_in", "common/flash.ld", "FLASH", "unique-name"),
    }


def test_an_include_two_files_could_answer_draws_nothing():
    """`INCLUDE` was matched by base name, the last file of that name winning.
    The file beside the includer is the one meant; failing that, the one file
    in the batch whose path ends with the name; failing that, nothing."""
    memory = "MEMORY { RAM : ORIGIN = 0, LENGTH = 1K }\n"
    files = [File(name="memory.x", url="board-a/memory.x", raw=memory),
             File(name="memory.x", url="board-b/memory.x", raw=memory),
             File(name="link.x", url="board-a/link.x", raw="INCLUDE memory.x\n"),
             File(name="link.x", url="rt/link.x", raw="INCLUDE memory.x\n"),
             File(name="regions.ld", url="common/regions.ld", raw=memory),
             File(name="app.ld", url="app/app.ld", raw="INCLUDE common/regions.ld\n")]
    relations = LinkerScriptParser().parse_files(files, depth=3).graph["file_relations"]
    assert sorted(relations, key=lambda r: r[0]) == [
        ("app/app.ld", "common/regions.ld", {"kind": "includes", "resolution": "unique-name"}),
        ("board-a/link.x", "board-a/memory.x", {"kind": "includes", "resolution": "same-directory"}),
    ]


def test_a_dot_x_file_is_a_linker_script_only_when_it_says_so():
    """`.x` is also Sun RPC's extension and Alex's, and every such file was
    read as a linker script (`const MAXNAMLEN = 255;` a symbol). A `.x` is
    read when it holds a linker statement -- svd2rust's `device.x` is only
    PROVIDEs; `.ld` and `.lds` are always read."""
    files = [File(name="nfs_prot.x", url="rpc/nfs_prot.x",
                  raw="const MAXNAMLEN = 255;\nenum ftype { NFNON = 0, NFREG = 1 };\n"
                      "program NFS { version V3 { void NULLPROC(void) = 0; } = 3; } = 100003;\n"),
             File(name="device.x", url="pac/device.x", raw="PROVIDE(WWDG = DefaultHandler);\n"),
             File(name="extra.ld", url="ld/extra.ld", raw="_heap_size = 0x400;\n")]
    graph = LinkerScriptParser().parse_files(files, depth=3)
    assert {d["file"] for _, d in graph.nodes(data=True)} == {"pac/device.x", "ld/extra.ld"}
