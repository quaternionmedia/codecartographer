"""The examples bundled with a checkout of this repository, offered by the
project selector beside the ones it fetches from GitHub.

**AN EXAMPLE THAT NEEDS NOTHING.** A bundled example is a directory under
`examples/` that the window can read with no network and no toolchain: its
recorded documents are part of it, so it shows what a GitHub example cannot --
the Cargo panel, rustc's diagnostics, the memory a link measured.

**CHOSEN, NOT DISCOVERED.** Only what `BUNDLED` names is offered; a directory
under `examples/` that it does not name is not an example by being there. And
an installed package has no `examples/` at all, so it offers none -- an empty
list, which is the answer, not an error.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "examples"

# In the order the selector shows them.
BUNDLED: list[dict[str, str]] = [
    {
        "id": "rust-firmware",
        "label": "blinky (recorded)",
        "language": "rust",
        "title": ("A two-crate Cortex-M workspace with the records real cargo and rust-lld "
                  "wrote for it: the code map, the Cargo panel, rustc's warning and the "
                  "measured memory, with no network and no toolchain"),
    },
]


def bundled() -> list[dict[str, object]]:
    """Each bundled example present in this checkout, with the absolute path it
    is read from and whether it is a Cargo workspace."""
    found: list[dict[str, object]] = []
    for example in BUNDLED:
        path = ROOT / example["id"]
        if path.is_dir():
            found.append({**example, "path": str(path), "cargo": (path / "Cargo.toml").is_file()})
    return found
