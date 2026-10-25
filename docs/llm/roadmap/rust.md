# Rust and the firmware languages

How codecarto reads Rust -- its source, its Cargo workspace, its dev loop and
its build -- and the languages below it that firmware is made of, and how all of
them are set beside C and Python so the chrestomathy can compare them. What is
shipped is described as it is; what is next is named with the engine it would
buy, because a capability here first asks which engine should own it.

## The shape

Four readings, one vocabulary, one canvas.

| Reading | Reads | Module | Route or flow |
|---|---|---|---|
| Rust source | `.rs` files, item by item | `services/parsers/rust_language_parser.py` | the unified parse (`/parse/*`), like every language |
| Linker scripts | `.ld`, `.lds`, `memory.x` | `services/parsers/linker_script_parser.py` | the unified parse |
| A Cargo workspace | `Cargo.toml`, `Cargo.lock`, `.cargo/config.toml`, and what cargo recorded | `services/cargo_service.py` | `/cargo/gjgf`, `/cargo/data`, the Cargo panel |
| One construct across languages | `data/constructs.yaml` and the lexicons | `services/construct_service.py` | `/lexicon/chrestomathy/...`, the Chrestomathy panel |

The vocabulary that joins them is `codecarto/data/constructs.yaml`. A parser
keeps its own `kind` (what the language calls a thing); every node of a language
the vocabulary lists also gets `construct` (what it *is*) and, where its
qualifiers, attributes or body say so, `meta.facets`. That is the
standardisation: a C `struct` and a Rust `struct` are `type.product` and are
drawn alike; a Rust `enum` whose variants carry data is `type.sum` while C's
`enum` is `type.enumeration`; an `#[interrupt]` handler, a `#[link_section]`
static and a linker script's output section all name `layout.section` or
`firmware.interrupt`, so a reader can follow one idea from the source to the
memory map.

## The dev loop

```text
edit  ->  uv run codecarto cargo record <workspace> [--map <bin>]  ->  the window reads it
             runs cargo metadata and cargo check, and with           crate graph, diagnostics and
             --map links <bin> asking the linker for its map         memory use on the targets and
             writes target/codecarto/*.json[l] and <bin>.map         on the items they name
```

`codecarto cargo record` is the **only** place this project runs cargo. Running
cargo runs the workspace's build scripts and proc macros and its configured
`rustc`, so it is a person's act on a workspace they would build -- never a
route's, which anyone who can reach the port could trigger on any path. The
window reads what was recorded and says how old it is:

- `metadata.json` newer than every manifest is cargo's own resolution, used as
  it stands. Older, it is **not used** -- the manifests are read instead and the
  reading says why. A resolution delivered stale looks checked.
- `check.jsonl` puts rustc's diagnostics on the crate graph's targets and, in a
  local parse of the same repository, on the innermost Rust item whose lines
  hold each one, with `diagnostics_recorded_at` beside the counts. A source
  changed after the check is reported as `stale`; nothing re-checks.
- `<bin>.map` -- the linker's map of a release link -- measures what the
  linker script only declares: each region's use against its length, at run
  time and as load images, each section's size, and the bytes each function and
  static occupies. See *The memory map, measured* below.
- No document is a sentence: "no diagnostics drawn, which is not the same as a
  clean build".

## The memory map, measured

`services/link_map_service.py` reads the map a linker writes when asked
(`-Map=<file>`), in the two shapes firmware is linked with: GNU ld's
(`arm-none-eabi-gcc -Wl,-Map=...`, which also prints the memory table) and
LLD's (`rust-lld`, the default for Rust's embedded targets, which does not).
`codecarto cargo record --map <bin>` links `<bin>` with `--profile release` --
the build that is flashed -- and keeps its map; a C build passing
`-Wl,-Map=target/codecarto/<name>.map` writes one the window reads the same way.

- **A region's use** is the sections the link placed in it at run time, plus
  the load images of sections run from elsewhere (`.data`, a `.ram_func`).
  `.bss`, `.uninit`, a stack or heap have no load image -- told by name, since
  LLD's map does not print a section's type, and pinned by a test whose map
  gives `.bss` a flash load address the way a linker does.
- **On the code map**, the linker script's regions and sections carry what was
  measured (`meta.measured`, and a tooltip that says it), and functions and
  statics carry `meta.bytes`: a symbol is demangled (Rust's legacy mangling,
  and the half-demangled form LLD prints) and joined within the crate it was
  compiled in, by name and, for a method, its impl's type -- only where one
  item answers. A file's crate is the target whose root reaches it through
  `mod` items, cargo's targets naming the roots, so a package need not sit in a
  directory named after it; an unmangled name is looked for in the map's own
  binary only. A symbol from outside the parse (`core`, a runtime) is counted,
  not drawn.
- **Only placed sections count.** Both linkers print debug information, symbol
  tables, `.comment` and build attributes at address 0, inside any region that
  starts there (nRF52, SAMD, LPC, Kinetis); they are told by name, or by lying
  on addresses a placed section already holds (an `(INFO)` section such as
  defmt's).
- **On the crate graph**, the binary's target says its fill per region, and the
  map is a document row with its age. Once a source changes after it the map
  is not used -- as a stale `metadata.json` is not -- and the row, the caveat
  and the code map's regions say why.

What it cannot see: inlined code has no symbol, so its bytes are its caller's;
and a map is only as current as the link that wrote it.

## What the Rust reader knows, and how

The reader is a tokenizer and a brace matcher -- stdlib only, the same tier as
the regex parsers it replaces for `.rs`, and deliberately no further. Items,
their nesting, visibility, qualifiers, attributes, `extern` blocks and ABIs,
receivers, field types and the calls in a body are what a tokenizer can know.
Name resolution, types and macro expansion are the compiler's, and each relation
it draws says how it was found (`resolution` on the edge): `module-tree` for a
`use` walked through the `mod` declarations, `crate-by-directory` for a sibling
crate recognised by its directory, `unique-name` for a call, impl or field type
resolved only because exactly one local item has the name. Its module
docstring lists every relation.

What it does not do, on purpose: expand macros (an item inside `cfg_if!` or
`bitflags!` is a `macro_invocation`, not its expansion), resolve a method call
on anything but `self`, or follow a `use` through a re-export it cannot see.

## Holding the joins

Each join drifts silently -- a renamed token, a new parser kind, a changed
colour -- and the picture still draws, so each is a test
(`tests/test_construct_service.py`): every token the vocabulary names is in that
language's lexicon; the Rust parser's `KINDS` and the vocabulary map each other
exactly; every C kind is mapped; C's reference design (`c_language_parser`'s
shapes and colours) agrees with the vocabulary's looks; every look is a shape
the canvas draws. Each guard was broken once and seen red.

## Next, in order

1. **Semantic resolution, bought rather than built.** `rust-analyzer scip` and
   `scip-clang` write one index format (SCIP) for Rust and for C/C++. Reading it
   would replace every `unique-name` edge with a resolved one, for both
   languages, through one seam -- the `ownership-is-the-deliverable` and
   `seams-on-standard-protocols` answer to "how does a code map know what a call
   is". How its protobuf wire format is decoded is a house-stack question, so
   it starts as an org record.
2. **Peripherals.** CMSIS-SVD files describe a device's registers; joined to the
   `#[repr(C)]` register blocks the reader already finds, a HAL's structs would
   point at the hardware they model.
3. **C firmware at parity.** `.ino` sketches through the C adapter (as C++),
   `compile_commands.json` (`c_parser_phase3_compile_commands.md`), and clang's
   machine-readable diagnostics, so a C workspace has the same overlay a Rust
   one has.
4. **The build itself.** `cargo build --timings` and the unit graph (unstable
   today) would draw what compiled, in what order, for how long. Read from a
   recorded document, as the check is.
5. **Running firmware.** probe-rs and defmt logs as a monitoring overlay on the
   same graph: which handler ran, from a recorded trace. The `monitoring` rung,
   reached the same way.
6. **More of the chrestomathy.** Lexicons for C++, assembly directives and the
   linker script; constructs for ownership, generics and closures; Python's
   facets.

`tree-sitter` is declared in the `multilang` extra and imported nowhere. An org
record decides whether it joins the house stack before any code imports it.

## Where to start reading

`rust_language_parser.py`'s docstring, then `constructs.yaml`'s header, then
`cargo_service.py`'s docstring -- each says what it cannot see. The fixture
`tests/fixtures/cargo/workspace` is a small firmware workspace (a HAL, a
`no_std` binary with `memory.x`, a host tool whose build script compiles C) with
recorded cargo documents, and every behaviour above has a test that reads it.
