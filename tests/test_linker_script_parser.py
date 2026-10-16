"""The linker-script reader: regions, sections, symbols and what places what."""

from __future__ import annotations

import pytest

from codecarto.models.source_data import File
from codecarto.services.parsers.language_parser import ParserRegistry
from codecarto.services.parsers.linker_script_parser import LinkerScriptParser, size_in_bytes

MEMORY_X = """
/* STM32F411CE */
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
    assert graph.graph["file_relations"] == [("fw/link.x", "fw/memory.x", {"kind": "includes"})]


def test_nodes_carry_the_construct_vocabulary(graph):
    assert by(graph, "region")["FLASH"][1]["construct"] == "layout.region"
    assert by(graph, "section")[".text"][1]["construct"] == "layout.section"
    assert by(graph, "entry")["Reset"][1]["construct"] == "firmware.entry"


def test_line_numbers_survive_comment_removal(graph):
    assert by(graph, "region")["FLASH"][1]["line"] == 5
