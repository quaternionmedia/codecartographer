"""The Rust reader: tokens, items, the module tree, and the relations it draws.

Item-level source is written inline where one test needs one shape; the
cross-file behaviour reads `tests/fixtures/cargo/workspace`, a small firmware
workspace with a HAL crate, a `no_std` binary and a host tool that builds C.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codecarto.models.source_data import File
from codecarto.services.local_repo_service import get_local_repo
from codecarto.services.parsers.language_parser import ParserRegistry
from codecarto.services.parsers.rust_language_parser import (
    KINDS,
    RustLanguageParser,
    crate_name_for,
    is_crate_root,
    read_items,
    tokenize,
)
from codecarto.services.unified_parser_service import UnifiedParserService

WORKSPACE = Path(__file__).parent / "fixtures" / "cargo" / "workspace"


def items_by_kind(src: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}

    def walk(items):
        for item in items:
            found.setdefault(item.kind, []).append(item.label or item.name)
            walk(item.children)

    walk(read_items(src)[0])
    return found


def parse(src: str, name: str = "src/lib.rs", depth: int = 3):
    return RustLanguageParser().parse_files([File(name=Path(name).name, url=name, raw=src)], depth=depth)


def node(graph, kind: str, label: str) -> dict:
    found = [d for _, d in graph.nodes(data=True) if d.get("kind") == kind and d.get("label") == label]
    assert len(found) == 1, (kind, label, found)
    return found[0]


def edges(graph, kind: str) -> set[tuple[str, str]]:
    return {(graph.nodes[u]["label"], graph.nodes[v]["label"])
            for u, v, d in graph.edges(data=True) if d["kind"] == kind}


# ── Tokens ────────────────────────────────────────────────────────────────────


class TestTokenize:
    def test_raw_string_holding_a_brace_and_a_quote_is_one_literal(self):
        toks = tokenize('let s = r#"a "quoted" } brace"#; fn after() {}')
        assert [t.text for t in toks if t.kind == "ident"][-1] == "after"
        assert sum(1 for t in toks if t.kind == "literal") == 1

    def test_lifetime_and_char_are_told_apart(self):
        toks = tokenize("fn f<'a>(x: &'a u8) -> char { 'x' }")
        assert [t.text for t in toks if t.kind == "lifetime"] == ["'a", "'a"]
        assert "'x'" in [t.text for t in toks if t.kind == "literal"]

    def test_nested_block_comment_is_dropped_whole(self):
        toks = tokenize("/* outer /* inner */ still comment */ fn real() {}")
        assert [t.text for t in toks if t.kind == "ident"] == ["fn", "real"]

    def test_outer_doc_kept_inner_doc_and_plain_comments_dropped(self):
        toks = tokenize("//! crate doc\n// note\n/// The answer.\nfn f() {}")
        assert [(t.kind, t.text) for t in toks if t.kind == "doc"] == [("doc", "The answer.")]

    def test_lines_count_through_multiline_strings(self):
        toks = tokenize('const S: &str = "a\nb\nc";\nfn after() {}')
        assert next(t for t in toks if t.text == "after").line == 4

    def test_raw_identifier_is_its_name(self):
        assert [t.text for t in tokenize("fn r#match() {}") if t.kind == "ident"] == ["fn", "match"]

    def test_unterminated_input_does_not_raise(self):
        toks = tokenize('fn f() { "never closed')
        assert ("punct", '"') in [(t.kind, t.text) for t in toks]
        assert tokenize("/* open forever fn f() {}") == []


# ── Items ─────────────────────────────────────────────────────────────────────


class TestItems:
    def test_every_item_shape_is_read(self):
        kinds = items_by_kind('''
            use std::fmt;
            extern crate alloc;
            mod inline { pub fn deep() {} }
            mod declared;
            pub struct S { a: u8 }
            pub struct T(u8, String);
            pub union U { a: u32, b: f32 }
            pub enum E { A, B(u8) }
            pub trait Tr { type Item; const N: usize; fn m(&self); }
            impl Tr for S { type Item = u8; const N: usize = 1; fn m(&self) {} }
            pub type Alias = Vec<u8>;
            const C: u8 = 1;
            static mut G: u32 = 0;
            extern "C" { fn ffi(x: u32) -> u32; }
            macro_rules! m { () => {} }
            lazy_static::lazy_static! { static ref X: u8 = 1; }
        ''')
        assert set(kinds) == {"use", "extern_crate", "module", "function", "struct", "field",
                              "union", "enum", "variant", "trait", "assoc_type", "assoc_const",
                              "method", "impl", "type", "const", "static", "extern_block",
                              "macro", "macro_invocation"}
        assert set(kinds) <= set(KINDS)

    def test_a_comparison_in_a_constant_does_not_swallow_the_file(self):
        """`<` in an expression never closes. Counted as an angle bracket, it
        carried the search for `;` to the end of the file and every later item
        vanished. Mutation: make `until` track angles by default -- this fails."""
        kinds = items_by_kind("const LIMIT: bool = 3 < 4;\nfn after() {}\nstruct Later;")
        assert kinds["function"] == ["after"]
        assert kinds["struct"] == ["Later"]

    def test_generics_closing_with_shift_token(self):
        kinds = items_by_kind("pub struct W<T: Into<Vec<u8>>> { inner: T }\nfn after() {}")
        assert kinds["struct"] == ["W"] and kinds["function"] == ["after"]

    def test_impl_header_names_trait_and_type_past_generics_and_hrtb(self):
        items, _ = read_items("impl<'a, T> From<T> for Wrapper<'a, T> where T: for<'b> Fn(&'b u8) {}")
        assert (items[0].trait, items[0].self_type) == ("From", "Wrapper")
        assert items[0].label == "impl From for Wrapper"

    def test_union_is_a_keyword_only_before_a_name(self):
        assert "union" not in items_by_kind("fn union() {}\nstatic union: u8 = 0;")
        assert items_by_kind("union U { a: u8 }")["union"] == ["U"]

    def test_enum_payload_decides_sum_or_enumeration(self):
        graph = parse("pub enum Mode { In = 0, Out = 1 }\npub enum Event { Rx(u8), Frame { b: u8 } }")
        assert node(graph, "enum", "Mode")["construct"] == "type.enumeration"
        assert node(graph, "enum", "Event")["construct"] == "type.sum"

    def test_qualifiers_attributes_and_receiver(self):
        graph = parse('''
            #[no_mangle]
            #[link_section = ".ram_func"]
            pub unsafe extern "C" fn fast(x: u32) -> u32 { x }
            impl S { pub const fn new(&mut self, a: u8) -> Self { todo!() } }
        ''')
        fast = node(graph, "function", "fast")
        assert fast["meta"]["qualifiers"] == ["pub", "unsafe", "extern"]
        assert fast["meta"]["abi"] == "C"
        assert fast["meta"]["attributes"] == ["no_mangle", 'link_section = ".ram_func"']
        new = node(graph, "method", "new")
        assert new["meta"]["receiver"] == "&mut self"
        assert new["meta"]["param_count"] == 1

    def test_unknown_item_level_tokens_cost_only_themselves(self):
        kinds = items_by_kind("??? garbage { not rust } ;\nfn survivor() {}")
        assert kinds["function"] == ["survivor"]

    def test_depth_two_stops_at_items(self):
        graph = parse("pub struct S { a: u8 }\nimpl S { fn m(&self) {} }", depth=2)
        assert {d["kind"] for _, d in graph.nodes(data=True)} == {"struct", "impl"}

    def test_crate_roots(self):
        assert is_crate_root("crates/hal/src/lib.rs") and is_crate_root("src/bin/tool.rs")
        assert is_crate_root("build.rs") and not is_crate_root("src/gpio/pin.rs")
        assert crate_name_for("crates/hal-core/src/lib.rs") == "hal_core"


# ── Relations ─────────────────────────────────────────────────────────────────


class TestRelations:
    SRC = '''
        pub trait OutputPin { fn set_high(&mut self); }
        pub struct Pin { block: Block }
        pub struct Block { odr: u32 }
        impl OutputPin for Pin {
            fn set_high(&mut self) { self.write(1); helper(); Self::make(); Pin::make(); x.len(); }
        }
        impl Pin {
            fn write(&mut self, v: u32) { unsafe { core::ptr::write_volatile(&mut self.block.odr, v) } }
            fn make() -> Self { todo!() }
        }
        fn helper() { Some(1); Point(1, 2); }
        fn twin() {}
        mod a { pub fn twin() {} }
        fn calls_twin() { twin(); }
        type Alias = Block;
    '''

    def test_implements_extends_and_type_of(self):
        graph = parse(self.SRC)
        assert ("impl OutputPin for Pin", "OutputPin") in edges(graph, "implements")
        assert ("impl OutputPin for Pin", "Pin") in edges(graph, "extends")
        assert ("impl Pin", "Pin") in edges(graph, "extends")
        assert ("block", "Block") in edges(graph, "type_of")
        assert ("Alias", "Block") in edges(graph, "aliases")

    def test_calls_resolve_through_self_and_unique_names_only(self):
        graph = parse(self.SRC)
        calls = edges(graph, "calls")
        assert ("set_high", "write") in calls  # self.write(..)
        assert ("set_high", "make") in calls   # Self::make() and Pin::make()
        assert ("set_high", "helper") in calls
        # `twin` names two functions: ambiguous, so nothing is drawn.
        assert not any(src == "calls_twin" for src, _ in calls)
        (set_high,) = [d for _, d in graph.nodes(data=True)
                       if d.get("label") == "set_high" and "calls_unresolved" in d["meta"]]
        assert set_high["meta"]["calls_unresolved"] == 1  # x.len()
        # Constructors are not calls.
        assert "calls_unresolved" not in node(graph, "function", "helper")["meta"]

    def test_firmware_facets(self):
        graph = parse('''
            static mut TICKS: u32 = 0;
            #[cortex_m_rt::entry]
            fn main() -> ! { loop { unsafe { core::arch::asm!("nop") } } }
            #[interrupt]
            fn TIM2() {}
        ''')
        main = node(graph, "function", "main")
        assert set(main["meta"]["facets"]) == {"firmware.entry", "asm.inline", "memory.unsafe"}
        assert node(graph, "function", "TIM2")["meta"]["facets"] == ["firmware.interrupt"]
        assert node(graph, "static", "TICKS")["meta"]["facets"] == ["memory.shared-mutable"]

    def test_volatile_has_no_keyword_and_is_found_by_call(self):
        graph = parse(self.SRC)
        assert "memory.volatile" in node(graph, "method", "write")["meta"]["facets"]


# ── Across the workspace fixture ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def workspace_graph():
    directory = get_local_repo(str(WORKSPACE), extensions=[".rs", ".x"])
    return UnifiedParserService.build_graph(directory, depth=3, extensions=[".rs", ".x"])


def file_id(graph, suffix: str) -> str:
    found = [n for n, d in graph.nodes(data=True) if d.get("kind") == "file" and n.endswith(suffix)]
    assert len(found) == 1, (suffix, found)
    return found[0]


class TestWorkspace:
    def test_registered_for_rs(self):
        assert isinstance(ParserRegistry.get(".rs"), RustLanguageParser)

    def test_target_directory_is_not_walked(self, workspace_graph):
        assert not any("/target/" in n for n in workspace_graph)

    def test_each_crate_keeps_its_own_files(self, workspace_graph):
        """`src/main.rs` exists in two crates; they are two nodes."""
        mains = [n for n, d in workspace_graph.nodes(data=True)
                 if d.get("kind") == "file" and n.endswith("/src/main.rs")]
        assert len(mains) == 2

    def test_symbols_hang_from_their_own_file(self, workspace_graph):
        blinky = file_id(workspace_graph, "crates/blinky/src/main.rs")
        host = file_id(workspace_graph, "crates/host-tool/src/main.rs")
        blinky_fns = {workspace_graph.nodes[v]["label"] for v in workspace_graph.successors(blinky)
                      if workspace_graph.nodes[v].get("kind") == "function"}
        host_fns = {workspace_graph.nodes[v]["label"] for v in workspace_graph.successors(host)
                    if workspace_graph.nodes[v].get("kind") == "function"}
        assert blinky_fns == {"main", "delay", "SysTick", "fast_path"}
        assert host_fns == {"main"}

    def test_mod_declarations_reach_their_files(self, workspace_graph):
        declared = {workspace_graph.nodes[v]["label"]
                    for u, v, d in workspace_graph.edges(data=True) if d["kind"] == "declares"}
        assert {"mod.rs", "pin.rs", "registers.rs", "uart.rs", "cli.rs"} <= declared

    def test_use_paths_become_file_dependencies(self, workspace_graph):
        pin = file_id(workspace_graph, "crates/hal/src/gpio/pin.rs")
        targets = {workspace_graph.nodes[v]["label"]: d.get("resolution")
                   for _, v, d in workspace_graph.out_edges(pin, data=True) if d["kind"] == "depends_on"}
        assert targets == {"mod.rs": "module-tree", "registers.rs": "module-tree"}

    def test_a_sibling_crate_is_found_by_directory_and_says_so(self, workspace_graph):
        blinky = file_id(workspace_graph, "crates/blinky/src/main.rs")
        deps = {workspace_graph.nodes[v]["label"]: d.get("resolution")
                for _, v, d in workspace_graph.out_edges(blinky, data=True) if d["kind"] == "depends_on"}
        assert deps["mod.rs"] == "crate-by-directory"  # hal::gpio
        assert deps["cortex_m_rt"] == "external"

    def test_no_std_is_a_fact_on_the_file(self, workspace_graph):
        lib = workspace_graph.nodes[file_id(workspace_graph, "crates/hal/src/lib.rs")]
        assert lib["meta"]["no_std"] is True
        main = workspace_graph.nodes[file_id(workspace_graph, "crates/blinky/src/main.rs")]
        assert main["meta"]["no_main"] is True

    def test_memory_map_is_read_beside_the_code(self, workspace_graph):
        regions = {d["label"]: d["meta"]["length_bytes"] for _, d in workspace_graph.nodes(data=True)
                   if d.get("kind") == "region"}
        assert regions == {"FLASH": 512 * 1024, "RAM": 128 * 1024}
