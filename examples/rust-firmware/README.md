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
cargo's home to `/cargo-home` -- so nothing names the machine it was recorded on.

The window reads these files and never runs cargo. Each is read with its age:
a file older than the source it describes is said to be, and a resolution older
than a manifest is not used. To record them afresh, with a Rust toolchain and
the `thumbv7em-none-eabihf` target installed:

```sh
uv run codecarto cargo record examples/rust-firmware --map blinky
```
