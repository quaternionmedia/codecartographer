# rust-firmware — a recorded Cortex-M workspace

A two-crate `no_std` workspace for a Cortex-M4F (`thumbv7em-none-eabihf`): `hal`,
a small hardware abstraction layer (a GPIO pin behind an `OutputPin` trait, a
`#[repr(C)]` register block, a UART with a receive buffer and an event enum),
and `blinky`, a binary on `cortex-m-rt` whose `#[entry]` loop blinks a pin, with
a `SysTick` handler counting ticks into a `static mut` and a `#[no_mangle]`
function placed in `.ram_func`. `crates/blinky/memory.x` lays out an
STM32F411-shaped part: 512 KiB of flash, 128 KiB of RAM.

It is in the project selector's Rust examples as **blinky (recorded)**, because
it is the one example that shows everything codecarto reads of a Rust firmware
without a Rust toolchain on the machine: the code map, the linker script's
regions, the Cargo panel's crates and targets, rustc's one warning on the line
it names, and the memory each region and function uses.

## What `target/codecarto/` is

What `codecarto cargo record --map blinky` wrote, run with real cargo (rustc
1.99) and rust-lld: `metadata.json` (`cargo metadata`), `check.jsonl` (`cargo
check --message-format=json`) and `blinky.map` (the linker's map of a release
link). Only the absolute paths in them are rewritten -- the workspace to `/ws`,
cargo's home to `/cargo-home`, rustup's to `/rustup-home`, each with `/` for a
separator -- so nothing names the machine it was recorded on; the JSON is
written back by Python's `json`.

The window reads these files and never runs cargo. Each is read with its age:
a file older than the source it describes is said to be, and a resolution older
than a manifest is not used. An age cannot say whether these records are of
the sources beside them, though: a fresh clone writes `target/` after `crates/`
whatever either holds. So `tests/test_examples.py` reads them against the
sources -- each line rustc quoted is that line of the file it names, each
member depends on what its `Cargo.toml` says, each item the map places is one
the sources define -- and an edit to `crates/` that changes any of those fails
it until the example is recorded again.

## Recording it afresh

With a Rust toolchain and the target installed (`rustup target add
thumbv7em-none-eabihf`), from the repository root:

```sh
uv run python scripts/record_example.py examples/rust-firmware --map blinky
uv run pytest tests/test_examples.py -q
```

The first is `uv run codecarto cargo record examples/rust-firmware --map
blinky`, which runs the example's build (`cargo check` compiles and executes
build scripts and proc macros), and then the rewrite of the paths above. It
exits 1 naming any absolute path it could not rewrite -- a `CARGO_TARGET_DIR`
outside the workspace, say -- because those records name the machine and are
not to be committed. The second holds the new records to the sources and to
`/ws`, `/cargo-home` and `/rustup-home`. Cargo's build output under `target/`
is ignored; only `target/codecarto/` is committed.

When a step of `record` fails -- a release build cargo finds current is not
linked again, so no map is written -- what it did write is still rewritten,
and the script exits non-zero: those records are not a whole recording.
`cargo clean --profile release` in the example lets the map be linked.
