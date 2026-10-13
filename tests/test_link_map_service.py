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
import shutil
import time
from pathlib import Path

import pytest

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


def test_a_map_older_than_the_source_says_so(tmp_path):
    root = copy_workspace(tmp_path, stale=True)
    graph = UnifiedParserService.build_graph(get_local_repo(str(root), extensions=[".rs", ".x"]), 3, [".rs", ".x"])
    flash = node(graph, "region", "FLASH")
    assert flash["meta"]["measured"]["stale"] is True
    assert "(older than the source)" in flash["hover"]


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
                                       reason="libclang not installed — install with: uv sync --extra c-parsing")


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


@pytest.mark.parametrize("section, named", [
    (".bss.rx_buffer", "rx_buffer"), (".text.startup.main", "main"), (".text.unlikely.fault", "fault"),
    (".rodata.str1.1", None), (".text.unlikely", None), (".text", None)])
def test_which_input_sections_name_a_static(section, named):
    """A merged-string section and GCC's own subsections name no object.
    Mutation: let the name run on past a dot -- `str1.1` is read as one."""
    text = ("Memory Configuration\n\nName             Origin             Length             Attributes\n"
            "FLASH            0x08000000         0x00080000         xr\n\n"
            "Linker script and memory map\n\n"
            ".text           0x08000000       0x10\n"
            f" {section}\n"
            "                0x08000000       0x10 build/a.o\n")
    link_map = L.parse(text, "a.map")
    assert [s.name for s in link_map.symbols()] == ([named] if named else [])
