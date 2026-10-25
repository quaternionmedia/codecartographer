"""Reading a linker's map: sections, symbols, and each region's measured use.

`tests/fixtures/linkmaps/firmware-gnu.map` is in the shape GNU ld prints for a
small C firmware; the fixture workspace's `target/codecarto/blinky.map` is in
the shape rust-lld prints for its `blinky` binary. Both were written by hand in
those shapes. `blinky-rust-lld.map` and `sensor-c-gnu.map` were written by the
linkers themselves; their sections below say how.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import time
from pathlib import Path

import pytest

from codecarto.services import cargo_service
from codecarto.services import link_map_service as L
from codecarto.services.local_repo_service import get_local_repo
from codecarto.services.unified_parser_service import UnifiedParserService

FIXTURES = Path(__file__).parent / "fixtures"
GNU = FIXTURES / "linkmaps" / "firmware-gnu.map"
WORKSPACE = FIXTURES / "cargo" / "workspace"
LLD = WORKSPACE / "target" / "codecarto" / "blinky.map"
BLINKY_REGIONS = [L.Region("FLASH", 0x08000000, 512 * 1024), L.Region("RAM", 0x20000000, 128 * 1024)]


def by_name(items):
    return {item.name: item for item in items}


# ── GNU ld ────────────────────────────────────────────────────────────────────


class TestGnu:
    @pytest.fixture(scope="class")
    def link_map(self):
        return L.read(GNU)

    def test_format_and_memory_table(self, link_map):
        assert link_map.ok and link_map.format == "gnu-ld"
        assert [(r.name, r.origin, r.length) for r in link_map.regions] == [
            ("FLASH", 0x08000000, 0x80000), ("RAM", 0x20000000, 0x20000)]

    def test_sections_including_one_whose_name_wraps(self, link_map):
        sections = by_name(link_map.sections)
        assert set(sections) == {".isr_vector", ".text", ".ARM.attributes", ".data", ".bss"}
        assert sections[".ARM.attributes"].size == 0x2e
        assert (sections[".data"].vma, sections[".data"].lma) == (0x20000000, 0x08000428)

    def test_inputs_and_symbols_including_a_wrapped_input(self, link_map):
        text = by_name(by_name(link_map.sections)[".text"].inputs)
        assert text[".text.crc32_update_with_a_long_name"].file == "build/crc.o"
        sizes = {s.name: s.size for s in link_map.symbols()}
        # One symbol alone in its input section takes the section's size; two
        # share theirs by address.
        assert sizes["main"] == 0x2c
        assert (sizes["uart_poll"], sizes["uart_isr"]) == (0x176, 0x38)
        assert "_estack" not in sizes and "_sdata" not in sizes  # script assignments

    def test_usage_counts_run_time_and_load_images(self, link_map):
        uses = by_name(L.usage(link_map, link_map.regions))
        flash, ram = uses["FLASH"], uses["RAM"]
        assert (flash.runtime_bytes, flash.load_bytes) == (0x188 + 0x2a0, 0x10)
        assert (ram.runtime_bytes, ram.load_bytes) == (0x10 + 0x104, 0)
        # A section linked at address 0 that no region holds is not counted.
        assert ".ARM.attributes" not in flash.sections + ram.sections


GNU_HEAD = """\
Memory Configuration

Name             Origin             Length             Attributes
FLASH            0x08000000         0x00080000         xr

Linker script and memory map

"""


@pytest.mark.parametrize("statement, size", [("BYTE 0x1", 1), ("SHORT 0x1234", 2),
                                             ("LONG 0x12345678", 4), ("QUAD 0x1", 8)])
@pytest.mark.parametrize("fill", [False, True])
def test_a_data_statement_is_bytes_not_a_symbol(statement, size, fill):
    """`LONG 0x12345678` in a script prints as `<address> <size> LONG <value>`,
    which reads like a symbol with a long name. Mutation: let it through --
    a symbol named `0x4 LONG 0x12345678` appears with a negative size, and
    after a fill the symbol before it grows past its section, and this fails."""
    at = 0x08000020 + (4 if fill else 0)
    text = (GNU_HEAD
            + f".text           0x08000000       {0x24 + (4 if fill else 0) + size:#x}\n"
            " .text.foo      0x08000000       0x20 build/a.o\n"
            "                0x08000000                foo\n"
            + (" *fill*         0x08000020        0x4 \n" if fill else "")
            + f"                {at:#010x}       {size:#x} {statement}\n"
            f" .text.bar      {at + size:#010x}        0xc build/a.o\n"
            f"                {at + size:#010x}                bar\n")
    assert [(s.name, s.size) for s in L.parse(text, "a.map").symbols()] == [("foo", 0x20), ("bar", 0xc)]


@pytest.mark.parametrize("text", [
    "  Linker script and memory map\n.text 0x0 0x0\n",
    "Linker script and memory map\nLOAD /src/Memory Configuration/x.o\n",
    "LOAD /src/Linker script and memory map/x.o\nMemory Configuration\n",
])
def test_a_header_that_is_not_at_the_start_of_a_line_is_a_reason_not_an_exception(text):
    """GNU ld starts each part of its map at column 0; the same words elsewhere
    (in a path, indented) are not a header. Mutation: look the header up with a
    bare `next()` -- StopIteration escapes and this fails."""
    found = L.parse(text, "odd.map")
    assert found.ok == text.startswith("Linker script")
    if not found.ok:
        assert "Linker script and memory map" in found.reason


def test_an_odd_map_aborts_neither_the_code_map_nor_the_cargo_reading(tmp_path):
    root = copy_workspace(tmp_path, stale=False)
    (root / "target" / "codecarto" / "odd.map").write_text("  Linker script and memory map\n")
    graph = parse_rust(root)
    assert node(graph, "region", "FLASH")["meta"]["measured"]["map"] == "blinky.map"
    doc = next(d for d in cargo_service.read(root).documents if d.name == "odd.map")
    assert not doc.used and "Linker script and memory map" in doc.problem


# ── LLD ───────────────────────────────────────────────────────────────────────


class TestLld:
    @pytest.fixture(scope="class")
    def link_map(self):
        return L.read(LLD)

    def test_sections_by_depth_not_by_column(self, link_map):
        """Out, In and Symbol are eight columns apart. Mutation: take the depth
        from where the text's group starts rather than its indent -- every row
        reads as a section and this fails."""
        assert link_map.ok and link_map.format == "lld"
        sections = by_name(link_map.sections)
        assert list(sections) == [".vector_table", ".text", ".rodata", ".data", ".bss", ".uninit", ".ram_func"]
        assert len(sections[".text"].inputs) == 7

    def test_a_script_assignment_is_neither_section_nor_symbol(self, link_map):
        names = {s.name for s in link_map.sections} | {s.name for s in link_map.symbols()}
        assert not any("_stack_start" in n for n in names)

    def test_usage_against_the_regions_memory_x_declares(self, link_map):
        """`.ram_func` runs from RAM and is loaded from flash; `.bss` has no
        load image. Mutation: count `.bss` as loaded -- this fails."""
        uses = by_name(L.usage(link_map, BLINKY_REGIONS))
        assert (uses["FLASH"].runtime_bytes, uses["FLASH"].load_bytes) == (0x400 + 0xb50 + 0x1e0, 0xe)
        assert (uses["RAM"].runtime_bytes, uses["RAM"].load_bytes) == (0x4 + 0xe, 0)
        assert round(uses["FLASH"].fill, 4) == round((0x1130 + 0xe) / (512 * 1024), 4)


# ── A region that starts at address 0 ─────────────────────────────────────────
# nRF52, SAMD, LPC and Kinetis parts put flash at 0, and both linkers print the
# sections kept only in the ELF file -- debug information, symbol tables,
# `.comment`, build attributes -- at address 0 too.

NRF_REGIONS = [L.Region("FLASH", 0x0, 1024 * 1024), L.Region("RAM", 0x20000000, 256 * 1024)]
NRF_LLD = """\
     VMA      LMA     Size Align Out     In      Symbol
       0        0      400     4 .vector_table
       0        0      400     4         a.o:(.vector_table.interrupts)
     400      400       30     4 .text
     400      400       30     2         a.o:(.text.main)
     400      400       30     1                 main
20000000 20000000        8     4 .bss
20000000 20000000        8     4         a.o:(.bss.TICKS)
       1        1       40     1 .defmt
       1        1       40     1         a.o:(.defmt.{"package":"blinky"})
       0        0    c0000     1 .debug_info
       0        0    c0000     1         a.o:(.debug_info)
       0        0    20000     1 .debug_str
       0        0    20000     1         <internal>:(.debug_str)
       0        0       99     1 .comment
       0        0       99     1         <internal>:(.comment)
       0        0       3c     1 .ARM.attributes
       0        0       3c     1         a.o:(.ARM.attributes)
       0        0      340     4 .symtab
       0        0      340     4         <internal>:(.symtab)
       0        0       d6     1 .shstrtab
       0        0       d6     1         <internal>:(.shstrtab)
       0        0      237     1 .strtab
       0        0      237     1         <internal>:(.strtab)
"""
NRF_GNU = """\
Memory Configuration

Name             Origin             Length             Attributes
FLASH            0x00000000         0x00100000         xr
RAM              0x20000000         0x00040000         xrw
*default*        0x00000000         0xffffffff

Linker script and memory map

.isr_vector     0x00000000      0x200
 .isr_vector    0x00000000      0x200 build/startup.o
                0x00000000                g_pfnVectors

.text           0x00000200       0x40
 .text.main     0x00000200       0x40 build/main.o
                0x00000200                main

.ARM.attributes
                0x00000000       0x34
 .ARM.attributes
                0x00000000       0x34 build/main.o
OUTPUT(build/firmware.elf elf32-littlearm)

.debug_info     0x00000000      0x867
 .debug_info    0x00000000      0x867 build/main.o

.comment        0x00000000       0x46
 .comment       0x00000000       0x46 build/main.o

.debug_frame    0x00000000      0x128
 .debug_frame   0x00000000      0x128 build/main.o
"""


def test_sections_kept_only_in_the_file_do_not_fill_a_region_at_zero():
    """Mutation: decide a section's region by its address alone -- 896 KiB of
    debug information reads as flash and this fails."""
    uses = by_name(L.usage(L.parse(NRF_LLD, "blinky.map"), NRF_REGIONS))
    assert uses["FLASH"].runtime_bytes == 0x400 + 0x30
    assert uses["FLASH"].sections == [".vector_table", ".text"]
    assert uses["RAM"].runtime_bytes == 8


def test_an_info_section_on_addresses_already_placed_is_not_placed():
    """`.defmt` is an `(INFO)` section at address 1: no name says so, but it
    lies on the vector table, and two sections the link placed cannot share an
    address. Mutation: drop the overlap rule -- `.defmt` counts and this fails."""
    uses = by_name(L.usage(L.parse(NRF_LLD, "blinky.map"), NRF_REGIONS))
    assert ".defmt" not in uses["FLASH"].sections


def test_a_gnu_map_at_zero_counts_what_it_placed():
    link_map = L.parse(NRF_GNU, "firmware.map")
    uses = by_name(L.usage(link_map, link_map.regions))
    assert (uses["FLASH"].runtime_bytes, uses["FLASH"].sections) == (0x240, [".isr_vector", ".text"])


def test_a_region_at_zero_the_link_put_nothing_in_holds_no_debug_data():
    """An STM32 aliases its flash at 0; a script may declare that alias. Nothing
    placed lies there, so only the name says `.ARM.attributes` is not placed.
    Mutation: drop the name rule -- the alias reads 46 B used and this fails."""
    link_map = L.read(GNU)
    uses = by_name(L.usage(link_map, [*link_map.regions, L.Region("ALIAS", 0x0, 0x80000)]))
    assert (uses["ALIAS"].used_bytes, uses["ALIAS"].sections) == (0, [])


# ── Names ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw,clean", [
    ("_ZN6blinky5delay17h5e1d2c3b4a596877E", "blinky::delay"),
    ("blinky::delay::h5e1d2c3b4a596877", "blinky::delay"),
    ("_$LT$hal..gpio..pin..Pin$u20$as$u20$hal..gpio..OutputPin$GT$::set_high::h0a1b2c3d4e5f6071",
     "<hal::gpio::pin::Pin as hal::gpio::OutputPin>::set_high"),
    ("_ZN83_$LT$hal..gpio..pin..Pin$u20$as$u20$hal..gpio..OutputPin$GT$8set_high17h0a1b2c3d4e5f6071E",
     "_ZN83_$LT$hal..gpio..pin..Pin$u20$as$u20$hal..gpio..OutputPin$GT$8set_high17h0a1b2c3d4e5f6071E"),
    ("fast_path", "fast_path"),
])
def test_demangle(raw, clean):
    """A length prefix that does not match is left as it was rather than
    guessed at (the fourth row says 83 where the part is 60)."""
    assert L.demangle(raw) == clean


def test_mangled_impl_round_trips():
    part = "_$LT$hal..gpio..pin..Pin$u20$as$u20$hal..gpio..OutputPin$GT$"
    mangled = f"_ZN{len(part)}{part}8set_high17h0a1b2c3d4e5f6071E"
    assert L.demangle(mangled) == "<hal::gpio::pin::Pin as hal::gpio::OutputPin>::set_high"


@pytest.mark.parametrize("symbol,key", [
    ("<hal::gpio::pin::Pin as hal::gpio::OutputPin>::set_high", ("Pin", "set_high")),
    ("hal::gpio::pin::<impl hal::gpio::OutputPin for hal::gpio::pin::Pin>::set_low", ("Pin", "set_low")),
    ("hal::gpio::pin::Pin::new", ("Pin", "new")),
    ("blinky::delay", (None, "delay")),
    ("SysTick", (None, "SysTick")),
    # v0 names, as LLD demangles them: a generic instance is its item, and a
    # closure its enclosing function.
    ("blinky::delay::<u32>", (None, "delay")),
    ("<hal::gpio::pin::Pin<hal::Output>>::set_high", ("Pin", "set_high")),
    ("<hal::uart::Uart>::write::<u8>", ("Uart", "write")),
    ("blinky::main::{closure#0}", (None, "main")),
    ("blinky::run::<u8>::{closure#0}::{closure#1}", (None, "run")),
    ("<hal::uart::Uart>::poll::{closure#0}", ("Uart", "poll")),
    ("blinky::main::{{closure}}", (None, "main")),  # the legacy spelling
])
def test_symbol_key(symbol, key):
    assert L.symbol_key(symbol) == key


def test_an_unknown_file_is_a_reason():
    found = L.parse("this is not a map\n", "notes.map")
    assert not found.ok and "neither LLD's column header" in found.reason


# ── On the code map ───────────────────────────────────────────────────────────


def copy_workspace(tmp_path: Path, stale: bool) -> Path:
    root = tmp_path / "ws"
    shutil.copytree(WORKSPACE, root)
    then = time.time() - 3600
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, (then, then))
    stamp = then - 60 if stale else time.time()
    os.utime(root / "target" / "codecarto" / "blinky.map", (stamp, stamp))
    return root


@pytest.fixture
def measured(tmp_path):
    root = copy_workspace(tmp_path, stale=False)
    directory = get_local_repo(str(root), extensions=[".rs", ".x"])
    return UnifiedParserService.build_graph(directory, depth=3, extensions=[".rs", ".x"])


def node(graph, kind, label, where=""):
    found = [d for _, d in graph.nodes(data=True)
             if d.get("kind") == kind and d.get("label") == label and where in str(d.get("file", "")).replace("\\", "/")]
    assert len(found) == 1, (kind, label, len(found))
    return found[0]


def test_regions_carry_their_measured_use(measured):
    flash = node(measured, "region", "FLASH")
    use = flash["meta"]["measured"]
    assert (use["runtime_bytes"], use["load_bytes"], use["length_bytes"]) == (0x1130, 0xe, 512 * 1024)
    assert use["map"] == "blinky.map" and use["stale"] is False
    assert "of 512.0 KiB used" in flash["hover"]
    assert flash["label"] == "FLASH"  # the label stays the name the script gave it


def test_code_items_carry_their_bytes_within_their_crate(measured):
    """`main` names four functions in this workspace -- two binaries and two
    build scripts; the map's binary decides which. Mutation: drop the crate
    from the join -- `main` is ambiguous and this fails."""
    assert node(measured, "function", "main", "/blinky/src/")["meta"]["bytes"] == 0x2e
    assert "bytes" not in node(measured, "function", "main", "/blinky/build.rs")["meta"]
    assert "bytes" not in node(measured, "function", "main", "/host-tool/src/")["meta"]
    assert node(measured, "function", "delay")["meta"]["bytes"] == 0x1c
    assert node(measured, "function", "fast_path")["meta"]["bytes"] == 0xe
    assert node(measured, "static", "TICKS")["meta"]["bytes"] == 4


def test_a_method_is_matched_through_its_impls_type(measured):
    """`set_high` is declared on the trait and defined in the impl for `Pin`;
    the symbol names the impl, so only the impl's method gets the bytes."""
    methods = [d for _, d in measured.nodes(data=True) if d.get("label") == "set_high"]
    assert sorted(d["meta"].get("bytes", 0) for d in methods) == [0, 0x26]


NRF_OBJ = "/ws/target/thumbv7em-none-eabihf/release/deps/blinky-1.blinky.2-cgu.0.rcgu.o"
NRF_BLINKY_MAP = f"""\
     VMA      LMA     Size Align Out     In      Symbol
       0        0      400     4 .vector_table
       0        0      400     4         {NRF_OBJ}:(.vector_table.interrupts)
     400      400       30     4 .text
     400      400       20     2         {NRF_OBJ}:(.text.main)
     400      400       20     1                 main
     420      420       10     2         {NRF_OBJ}:(.text.delay)
     420      420       10     1                 blinky::delay
       0        0    c0000     1 .debug_info
       0        0    c0000     1         {NRF_OBJ}:(.debug_info)
"""


def nrf_package(tmp_path: Path, directory: str, package: str, main: str) -> Path:
    """A package with a build script, linked for a part whose flash is at 0."""
    root = tmp_path / "ws"
    pkg = root / directory
    (pkg / Path(main).parent).mkdir(parents=True)
    (root / "target" / "codecarto").mkdir(parents=True)
    (pkg / "Cargo.toml").write_text(f'[package]\nname = "{package}"\nversion = "0.1.0"\nedition = "2021"\n')
    (pkg / "build.rs").write_text('fn main() {\n    println!("cargo:rustc-link-search=.");\n}\n')
    (pkg / main).write_text("#![no_std]\n#![no_main]\n\nfn delay(n: u32) {\n    let _ = n;\n}\n\n"
                            "#[entry]\nfn main() -> ! {\n    loop { delay(1); }\n}\n")
    (pkg / "memory.x").write_text("MEMORY\n{\n  FLASH : ORIGIN = 0x00000000, LENGTH = 1024K\n"
                                  "  RAM : ORIGIN = 0x20000000, LENGTH = 256K\n}\n")
    then = time.time() - 3600
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, (then, then))
    (root / "target" / "codecarto" / "blinky.map").write_text(NRF_BLINKY_MAP)
    return root


def parse_rust(root: Path):
    return UnifiedParserService.build_graph(get_local_repo(str(root), extensions=[".rs", ".x"]),
                                            3, [".rs", ".x"])


def test_the_binary_is_found_by_its_package_not_its_directory(tmp_path):
    """Package `blinky` checked out in `fw/`: no directory is named after the
    crate the map's symbols name, so cargo's targets say which file the binary
    starts from. Mutation: name crates by directory alone -- the binary is
    crate `fw`, its `main` gets nothing and this fails."""
    root = nrf_package(tmp_path, "fw", "blinky", "src/main.rs")
    graph = parse_rust(root)
    assert "bytes" not in node(graph, "function", "main", "/fw/build.rs")["meta"]
    assert node(graph, "function", "main", "/fw/src/main.rs")["meta"]["bytes"] == 0x20
    assert node(graph, "function", "delay", "/fw/src/main.rs")["meta"]["bytes"] == 0x10
    # Flash at 0 holds the vector table and the code, not the 768 KiB of debug information.
    assert node(graph, "region", "FLASH")["hover"].startswith("FLASH — 1.0 KiB of 1024.0 KiB used (0.1%)")
    reading = cargo_service.read(root)
    label = cargo_service.as_graph(reading).nodes["target::blinky::bin::blinky"]["label"]
    assert label.endswith("FLASH 0.1%, RAM 0.0%")


def test_a_binary_this_parse_did_not_read_lends_its_bytes_to_nothing(tmp_path):
    """`src/bin/blinky.rs` in package `firmware`: the local reader skips `bin`
    directories, so the binary's items are not on the map, and the build
    script's `main` must not stand in for them. Mutation: fall back to an item
    outside any `src` folder when the binary's crate has none -- `build.rs`'s
    `main` takes 32 B and this fails."""
    graph = parse_rust(nrf_package(tmp_path, ".", "firmware", "src/bin/blinky.rs"))
    assert "bytes" not in node(graph, "function", "main", "/build.rs")["meta"]


F401 = "/* STM32F401CC */\nMEMORY\n{\n  FLASH : ORIGIN = 0x08000000, LENGTH = 256K\n  RAM : ORIGIN = 0x20000000, LENGTH = 64K\n}\n"


def test_each_script_is_measured_against_what_it_declares(tmp_path):
    """Two board variants beside one binary both declare FLASH. Mutation: key
    the measured use by region name -- the last script's figures land on both
    and this fails."""
    root = copy_workspace(tmp_path, stale=False)
    (root / "crates" / "blinky" / "memory-f401.x").write_text(F401)
    os.utime(root / "crates" / "blinky" / "memory-f401.x", (time.time() - 3600,) * 2)
    graph = parse_rust(root)
    f411 = node(graph, "region", "FLASH", "/blinky/memory.x")
    f401 = node(graph, "region", "FLASH", "/blinky/memory-f401.x")
    assert (f411["meta"]["measured"]["length_bytes"], f401["meta"]["measured"]["length_bytes"]) == (
        512 * 1024, 256 * 1024)
    assert "of 512.0 KiB used" in f411["hover"] and "of 256.0 KiB used" in f401["hover"]


def test_a_script_that_disagrees_with_the_maps_memory_table_is_not_the_one_linked(tmp_path):
    """GNU ld prints the regions it linked with; a script declaring a FLASH of
    another length was not that link's. Mutation: stamp the table's figures on
    every region of the name -- the F401 script claims 512 KiB and this fails."""
    root = copy_workspace(tmp_path, stale=False)
    (root / "crates" / "blinky" / "memory-f401.x").write_text(F401)
    os.utime(root / "crates" / "blinky" / "memory-f401.x", (time.time() - 3600,) * 2)
    shutil.copy(GNU, root / "target" / "codecarto" / "blinky.map")
    graph = parse_rust(root)
    assert node(graph, "region", "FLASH", "/blinky/memory.x")["meta"]["measured"]["length_bytes"] == 0x80000
    assert "measured" not in node(graph, "region", "FLASH", "/blinky/memory-f401.x")["meta"]


def test_a_map_older_than_the_source_is_not_used_and_says_so(tmp_path):
    """A recorded document is used only while it is current (the window reads
    what cargo wrote, section 3 and 5). Mutation: stamp the stale figures,
    marked stale -- the region and `main` carry them and this fails."""
    root = copy_workspace(tmp_path, stale=True)
    graph = parse_rust(root)
    flash = node(graph, "region", "FLASH")
    measured = flash["meta"]["measured"]
    assert (measured["map"], measured["stale"], measured["used"]) == ("blinky.map", True, False)
    assert "used_bytes" not in measured
    assert "not measured" in flash["hover"] and "before a source changed" in flash["hover"]
    assert "bytes" not in node(graph, "function", "main", "/blinky/src/")["meta"]
    assert "bytes" not in node(graph, "static", "TICKS")["meta"]


# ── A map rust-lld wrote ──────────────────────────────────────────────────────
# `blinky-rust-lld.map` is the map rust-lld 1.99 wrote for this workspace's
# `blinky`, linked with `--profile release` (LTO, opt-level "s") by
# `codecarto cargo record --map blinky`; only its object paths are rewritten.
# What it has that a map written from the documentation did not: rows LLD prints
# with no text, ARM mapping symbols, each symbol's own size, v0 names with the
# suffix LTO adds, and the trampoline cortex-m-rt puts in front of `#[entry]`.

REAL = FIXTURES / "linkmaps" / "blinky-rust-lld.map"


class TestRealLld:
    @pytest.fixture(scope="class")
    def link_map(self):
        return L.read(REAL)

    def test_sections_and_no_empty_rows(self, link_map):
        assert all(s.name for s in link_map.sections)
        alloc = [(s.name, s.vma, s.size) for s in link_map.sections if s.size and s.vma]
        assert alloc == [(".vector_table", 0x08000000, 0x400), (".text", 0x08000400, 0xb0),
                         (".bss", 0x20000000, 4)]

    def test_symbols_carry_the_size_lld_printed_and_mapping_symbols_are_skipped(self, link_map):
        """Mutation: size symbols by distance even when LLD printed a size --
        `Reset` comes out 63 (its Thumb address is odd) and this fails. Mutation:
        keep `$t` and `$d` -- they appear as symbols and this fails."""
        sizes = {L.demangle(s.name): s.size for s in link_map.symbols()}
        assert not any(name.startswith("$") for name in sizes)
        assert (sizes["Reset"], sizes["SysTick"], sizes["main"]) == (0x3e, 0x14, 8)
        assert sizes["blinky::__cortex_m_rt_main"] == 0x2a
        assert sizes["blinky::TICKS"] == 4  # `blinky::TICKS (.0)` as LLD printed it

    def test_usage(self, link_map):
        uses = by_name(L.usage(link_map, BLINKY_REGIONS))
        assert (uses["FLASH"].used_bytes, uses["RAM"].used_bytes) == (0x4b0, 4)

    def test_a_region_at_zero_holds_none_of_its_debug_information(self, link_map):
        """The same link with flash moved to 0, as an nRF52 lays it out: every
        flash address 0x08000000 lower, the columns kept. Mutation: decide a
        section's region by its address alone -- the 9,482 B of `.debug_*`,
        `.symtab`, `.strtab` and `.comment` count as flash and this fails."""
        assert by_name(L.usage(link_map, NRF_REGIONS))["FLASH"].used_bytes == 0  # nothing placed below 1 MiB
        moved = re.sub(r"(?m)^( *)8000([0-9a-f]{3})( +)8000([0-9a-f]{3}) ", r"\1    \2\3    \4 ", REAL.read_text())
        uses = by_name(L.usage(L.parse(moved, "nrf.map"), NRF_REGIONS))
        assert by_name(L.parse(moved, "nrf.map").sections)[".vector_table"].vma == 0
        assert (uses["FLASH"].used_bytes, uses["RAM"].used_bytes) == (0x4b0, 4)

    def test_on_the_code_map_the_entry_function_owns_its_trampoline(self, tmp_path):
        """cortex-m-rt renames `#[entry] fn main` to `__cortex_m_rt_main` and
        calls it from a `main` trampoline; both are `main`'s bytes. Mutation:
        drop the runtime prefix -- `main` gets only the trampoline's 8."""
        root = copy_workspace(tmp_path, stale=False)
        shutil.copy(REAL, root / "target" / "codecarto" / "blinky.map")
        graph = UnifiedParserService.build_graph(get_local_repo(str(root), extensions=[".rs", ".x"]),
                                                 3, [".rs", ".x"])
        assert node(graph, "function", "main", "/blinky/src/")["meta"]["bytes"] == 0x2a + 8
        assert node(graph, "function", "SysTick")["meta"]["bytes"] == 0x14
        assert node(graph, "static", "TICKS")["meta"]["bytes"] == 4
        # LTO inlined `delay` into its caller: no symbol, so no bytes of its own.
        assert "bytes" not in node(graph, "function", "delay")["meta"]
        assert node(graph, "region", "FLASH")["meta"]["measured"]["used_bytes"] == 0x4b0


V0_MAP = """\
     VMA      LMA     Size Align Out     In      Symbol
 8000000  8000000       60     4 .text
 8000000  8000000       20     2         blinky.o:(.text._RINvCs1_6blinky5delaymEB2_)
 8000000  8000000       20     1                 blinky::delay::<u32>
 8000020  8000020       10     2         blinky.o:(.text._RINvCs1_6blinky5delayhEB2_)
 8000020  8000020       10     1                 blinky::delay::<u8>
 8000030  8000030       10     2         blinky.o:(.text._RNCNvCs1_6blinky4main0B3_)
 8000030  8000030       10     1                 blinky::main::{closure#0}
 8000040  8000040        8     2         blinky.o:(.text.main)
 8000040  8000040        8     1                 main
 8000048  8000048       18     2         hal.o:(.text._RNCNvMs_NtCs2_3hal4uartNtB4_4Uart4poll0B6_)
 8000048  8000048       18     1                 <hal::uart::Uart>::poll::{closure#0}
"""


def test_generic_instances_and_closures_are_their_items_bytes(tmp_path):
    """Two instances of `delay`, a closure in `main` and one in `Uart::poll`.
    Mutation: take a symbol's last segment as its name -- `<u32>`, `<u8>` and
    `{closure#0}` name nothing, every one counts as outside, and this fails."""
    root = copy_workspace(tmp_path, stale=False)
    (root / "target" / "codecarto" / "blinky.map").write_text(V0_MAP)
    graph = parse_rust(root)
    assert node(graph, "function", "delay")["meta"]["bytes"] == 0x20 + 0x10
    assert node(graph, "function", "main", "/blinky/src/")["meta"]["bytes"] == 0x10 + 8
    assert node(graph, "method", "poll")["meta"]["bytes"] == 0x18
    assert node(graph, "function", "delay")["meta"]["measured"]["symbols"] == [
        "blinky::delay::<u32>", "blinky::delay::<u8>"]


# ── A map GNU ld wrote ────────────────────────────────────────────────────────
# `sensor-c-gnu.map` is the map arm-none-eabi-ld 2.44 (Arm GNU Toolchain
# 14.3.Rel1) wrote linking `linkmaps/sensor-c/` for a Cortex-M4 with `-Os
# -ffunction-sections -fdata-sections -Wl,--gc-sections` and newlib-nano; only
# the toolchain's install path is rewritten and its line endings made LF. What it
# has that the map written by hand did not: a stack the script reserves, for
# which ld prints a load address and writes no image; statics, which ld does not
# list; the second size ld prints for a relaxed input; and names one file
# declares and another defines.

REAL_GNU = FIXTURES / "linkmaps" / "sensor-c-gnu.map"
SENSOR = FIXTURES / "linkmaps" / "sensor-c"
requires_libclang = pytest.mark.skipif(importlib.util.find_spec("clang") is None,
                                       reason="libclang not installed — install with: uv sync --locked --extra dev --extra c-parsing")


class TestRealGnu:
    @pytest.fixture(scope="class")
    def link_map(self):
        return L.read(REAL_GNU)

    def test_usage_is_what_arm_none_eabi_size_reports(self, link_map):
        """`arm-none-eabi-size` on the same link: text 696, data 12, bss 3348.
        Mutation: give a section an image whenever its load address differs --
        the reserved stack's 2052 bytes count against FLASH and this fails."""
        uses = by_name(L.usage(link_map, link_map.regions))
        assert (uses["FLASH"].runtime_bytes, uses["FLASH"].load_bytes) == (696, 12)
        assert uses["RAM"].used_bytes == 12 + 3348
        stack = by_name(link_map.sections)["._user_stack"]
        assert stack.lma != stack.vma and not stack.loads

    def test_size_still_agrees_when_flash_starts_at_zero(self, link_map):
        """The same link with flash moved to 0 -- its memory table, sections and
        load addresses 0x08000000 lower. Mutation: decide a section's region by
        its address alone -- `.ARM.attributes`, `.comment` and the 7,879 B of
        `.debug_*` count as flash and this fails."""
        assert by_name(L.usage(link_map, NRF_REGIONS))["FLASH"].used_bytes == 0  # nothing placed below 1 MiB
        moved = L.parse(re.sub(r"0x08([0-9a-f]{6})\b", r"0x00\1", REAL_GNU.read_text()), "nrf.map")
        assert by_name(moved.regions)["FLASH"].origin == 0
        uses = by_name(L.usage(moved, moved.regions))
        assert (uses["FLASH"].runtime_bytes, uses["FLASH"].load_bytes) == (696, 12)
        assert uses["RAM"].used_bytes == 12 + 3348

    def test_statics_are_named_by_the_section_gcc_gave_them(self, link_map):
        """Mutation: read no name from an input section's own -- `rx_buffer`,
        `table` and `ticks` are missing and this fails."""
        sizes = {s.name: s.size for s in link_map.symbols()}
        assert (sizes["rx_buffer"], sizes["table"], sizes["ticks"], sizes["banner"]) == (0x100, 0x400, 4, 0x11)
        assert sizes["main"] == 0x58  # in `.text.startup.main`, and listed by ld

    def test_a_size_before_relaxing_is_not_a_symbol(self, link_map):
        """Mutation: read `(size before relaxing)` as a name -- it appears twice,
        once 1 byte short of nothing, and this fails."""
        assert not any(s.name.startswith("(") for s in link_map.symbols())
        assert all(s.size and s.size > 0 for s in link_map.symbols())

    @requires_libclang
    def test_on_the_code_map_each_name_goes_to_the_file_that_defined_it(self, tmp_path):
        """`startup.c` declares `main`, `SysTick_Handler` and `USART2_IRQHandler`;
        `main.c` and `uart.c` define them. Mutation: do not narrow by the object
        the map names -- each answers from two files and gets no bytes."""
        root = tmp_path / "sensor-c"
        shutil.copytree(SENSOR, root)
        (root / "target" / "codecarto").mkdir(parents=True)
        shutil.copy(REAL_GNU, root / "target" / "codecarto" / "sensor-c.map")
        extensions = [".c", ".h", ".ld"]
        graph = UnifiedParserService.build_graph(get_local_repo(str(root), extensions=extensions),
                                                 3, extensions)
        assert node(graph, "function", "main", "main")["meta"]["bytes"] == 0x58
        assert "bytes" not in node(graph, "function", "main", "startup")["meta"]
        assert node(graph, "function", "USART2_IRQHandler", "uart")["meta"]["bytes"] == 0x2c
        assert node(graph, "variable", "rx_buffer")["meta"]["bytes"] == 0x100
        # -Os inlined `delay_ms` into `main`: no symbol, so no bytes of its own.
        assert "bytes" not in node(graph, "function", "delay_ms")["meta"]
        assert node(graph, "region", "FLASH")["meta"]["measured"]["used_bytes"] == 696 + 12


def test_a_name_two_files_answer_goes_to_the_one_the_object_names():
    """The guard the libclang test above holds, on a graph built by hand as the
    C parser draws one -- `file` is the source's stem -- so it runs without
    libclang. `startup.c` declares `main` and `USART2_IRQHandler`; `main.c` and
    `uart.c` define them. Mutation: do not narrow by the object the map names
    -- each name answers from two files, gets no bytes, and this fails."""
    import networkx as nx

    graph = nx.DiGraph()
    for stem, kind, label in [("startup", "function", "main"), ("main", "function", "main"),
                              ("startup", "function", "USART2_IRQHandler"),
                              ("uart", "function", "USART2_IRQHandler"), ("uart", "variable", "rx_buffer")]:
        graph.add_node(f"c::{stem}::{label}", language="c", kind=kind, label=label, file=stem, meta={})
    joined = L.annotate(graph, L.read(REAL_GNU), owner="sensor-c", recorded_at="", stale=False)
    bytes_of = {n: d["meta"].get("bytes") for n, d in graph.nodes(data=True)}
    assert bytes_of == {"c::startup::main": None, "c::main::main": 0x58,
                        "c::startup::USART2_IRQHandler": None, "c::uart::USART2_IRQHandler": 0x2c,
                        "c::uart::rx_buffer": 0x100}
    assert joined["ambiguous"] == 0


def test_a_local_of_a_statics_name_takes_none_of_its_bytes():
    """A local that lives for one call (`meta.automatic`) has no storage a map
    could list, but the join took every C `variable` by its file and name: a
    local `rx_buffer` in `uart.c` was a second answer for the static's symbol,
    and the static got no bytes. Mutation: join an automatic local -- `ambiguous`
    is 1 and the static's bytes are missing."""
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_node("c::uart::rx_buffer", language="c", kind="variable", label="rx_buffer",
                   file="uart", meta={})
    graph.add_node("c::uart::uart_pending::rx_buffer", language="c", kind="variable", label="rx_buffer",
                   file="uart", meta={"automatic": True, "no_linkage": True})
    joined = L.annotate(graph, L.read(REAL_GNU), owner="sensor-c", recorded_at="", stale=False)
    assert graph.nodes["c::uart::rx_buffer"]["meta"].get("bytes") == 0x100
    assert "bytes" not in graph.nodes["c::uart::uart_pending::rx_buffer"]["meta"]
    assert joined["ambiguous"] == 0


@requires_libclang
def test_on_the_code_map_a_local_of_a_statics_name_takes_none_of_its_bytes(tmp_path):
    """The guard above, on the parser's own graph: the C parser marks a local
    `automatic`, and the static it shares a file and a name with keeps its 256
    bytes."""
    root = tmp_path / "sensor-c"
    shutil.copytree(SENSOR, root)
    with (root / "src" / "uart.c").open("a", newline="\n") as source:
        source.write("\nsize_t uart_pending(void)\n{\n    size_t rx_buffer = rx_head - rx_tail;\n"
                     "    return rx_buffer;\n}\n")
    (root / "target" / "codecarto").mkdir(parents=True)
    shutil.copy(REAL_GNU, root / "target" / "codecarto" / "sensor-c.map")  # newer than every source
    extensions = [".c", ".h", ".ld"]
    graph = UnifiedParserService.build_graph(get_local_repo(str(root), extensions=extensions), 3, extensions)
    local = graph.nodes["uart::uart_pending::rx_buffer"]
    assert local["meta"].get("automatic") and "bytes" not in local["meta"]
    assert graph.nodes["uart::rx_buffer"]["meta"]["bytes"] == 0x100


@pytest.mark.parametrize("section, named", [
    (".bss.rx_buffer", "rx_buffer"), (".text.startup.main", "main"), (".text.unlikely.fault", "fault"),
    # The clones GCC makes under -Os and -O2 -- constant-propagated, split,
    # with scalar-replaced arguments -- are the function they were cloned from.
    (".text.uart_rx.constprop.0", "uart_rx"), (".text.crc_step.part.0", "crc_step"),
    (".text.filter.isra.0", "filter"), (".text.parse.isra.0.constprop.0", "parse"),
    (".text.unlikely.fault.part.0", "fault"), (".text.tick.lto_priv.0", "tick"),
    (".rodata.str1.1", None), (".text.unlikely", None), (".text", None), (".text.foo.bar", None)])
def test_which_input_sections_name_a_static(section, named):
    """A merged-string section and GCC's own subsections name no object.
    Mutation: let the name run on past a dot -- `str1.1` is read as one.
    Mutation: allow no clone suffix -- `.text.uart_rx.constprop.0` names
    nothing, a cloned static gets no bytes, and this fails."""
    text = ("Memory Configuration\n\nName             Origin             Length             Attributes\n"
            "FLASH            0x08000000         0x00080000         xr\n\n"
            "Linker script and memory map\n\n"
            ".text           0x08000000       0x10\n"
            f" {section}\n"
            "                0x08000000       0x10 build/a.o\n")
    link_map = L.parse(text, "a.map")
    assert [s.name for s in link_map.symbols()] == ([named] if named else [])
