# Rust and the firmware languages: next

**State:** open — delete when the six steps below have landed.

What is shipped -- the Rust reader, linker scripts and link maps, the Cargo
workspace and the dev loop that records it -- is in
[Architecture](../architecture.md#rust-cargo-and-the-firmware-languages) and
[Services](../services.md#link_map_service). Each step below is named with the
engine it would buy.

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
   `compile_commands.json` ([c_parser_phase3_compile_commands.md](c_parser_phase3_compile_commands.md)),
   and clang's machine-readable diagnostics, so a C workspace has the same
   overlay a Rust one has.
4. **The build itself.** `cargo build --timings` and the unit graph (unstable
   today) would draw what compiled, in what order, for how long. Read from a
   recorded document, as the check is.
5. **Running firmware.** probe-rs and defmt logs as a monitoring overlay on the
   same graph: which handler ran, from a recorded trace. The `monitoring` rung,
   reached the same way.
6. **More of the chrestomathy**: the lexicons and constructs in
   [lexicon.md](lexicon.md).

`tree-sitter` is declared in the `multilang` extra and imported nowhere. An org
record decides whether it joins the house stack before any code imports it.
