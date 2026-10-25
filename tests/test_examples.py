"""The examples bundled with this checkout, and that they still read.

`examples/rust-firmware` carries what real cargo and rust-lld recorded for it,
with only absolute paths rewritten. It is offered as the example that shows
everything without a toolchain, so what it shows is asserted here, read as the
window reads it: a record lost or replaced would leave the example drawing
without the thing it is offered for, and nothing would error.

A checkout's file times are whatever the checkout made them, so the test that
reads the records copies the example and gives its documents a fresh time, as
a recording would; what it guards is what the records show, not the clock.
That the records are of the sources committed beside them is not something a
clock can say at all -- a fresh clone writes `target/` after `crates/`, so an
edit to a source committed without recording again would read as current in
every clone -- so it is asserted from their content: each line rustc quoted
is that line of the file it names, and each item the linker placed is one the
sources define.
"""

from __future__ import annotations

import collections
import json
import os
import re
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codecarto.services import cargo_service, examples_service

EXAMPLE = examples_service.ROOT / "rust-firmware"


def test_the_bundled_examples_are_offered_with_where_they_are_read_from():
    found = {e["id"]: e for e in examples_service.bundled()}
    blinky = found["rust-firmware"]
    assert Path(str(blinky["path"])).is_dir() and blinky["cargo"] is True
    assert blinky["language"] == "rust" and blinky["label"] and blinky["title"]


def test_only_what_is_named_is_offered_and_nothing_is_an_answer(tmp_path, monkeypatch):
    (tmp_path / "stray").mkdir()
    monkeypatch.setattr(examples_service, "ROOT", tmp_path)
    assert examples_service.bundled() == []  # a directory there is not an example by being there
    monkeypatch.setattr(examples_service, "ROOT", tmp_path / "absent")
    assert examples_service.bundled() == []  # an installed package has no examples/


def test_the_recorded_example_reads_as_one_workspace(tmp_path):
    """Mutation: remove any one of the three records -- the engine, the
    warning or the measured memory is gone, and this fails. (Rewriting the
    recorded paths does not: the reader matches packages by name.)"""
    root = tmp_path / "rust-firmware"
    shutil.copytree(EXAMPLE, root)
    then = time.time() - 3600
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, (then, then))
    for doc in (root / "target" / "codecarto").iterdir():
        os.utime(doc, None)

    reading = cargo_service.read(root)
    assert reading.engine == "cargo metadata"
    assert all(d.used and not d.stale for d in reading.documents)
    assert {p.name for p in reading.packages if p.member} == {"blinky", "hal"}
    assert [(d.level, d.package, d.file, d.line) for d in reading.diagnostics] == [
        ("warning", "hal", "crates/hal/src/uart.rs", 11)]
    regions = {r["name"]: r["used_bytes"] for r in reading.memory["blinky"]["regions"]}
    assert regions == {"FLASH": 0x4b0, "RAM": 4}


def _committed(root: Path, recorded: str) -> Path | None:
    """The file in *root* a recorded path names: relative to the workspace, as
    rustc names a span's file, or under `/ws`. None for one outside it -- a
    dependency's source under `/cargo-home` is not committed."""
    name = recorded.replace("\\", "/")
    if name == "/ws" or name.startswith("/ws/"):
        return root / name[len("/ws/"):]
    return None if name.startswith("/") else root / name


def _spans(message: dict):
    yield from message.get("spans") or []
    for child in message.get("children") or []:
        yield from _spans(child)


def _declared(manifest: dict) -> set[str]:
    """The packages a Cargo.toml depends on, in every dependency table."""
    tables = [manifest.get(k) or {} for k in ("dependencies", "dev-dependencies", "build-dependencies")]
    for platform in (manifest.get("target") or {}).values():
        tables += [platform.get(k) or {} for k in ("dependencies", "dev-dependencies", "build-dependencies")]
    return {spec.get("package", alias) if isinstance(spec, dict) else alias
            for table in tables for alias, spec in table.items()}


ITEM = r"\b(?:fn|static(?:\s+mut)?|const|struct|enum|union|trait|type|mod)\s+{}\b"


def _unlike_their_sources(root: Path) -> tuple[list[str], collections.Counter]:
    """Where the records under *root*'s `target/codecarto/` disagree with the
    sources beside them, and how many of each kind of fact were compared."""
    docs = root / "target" / "codecarto"
    problems: list[str] = []
    compared: collections.Counter = collections.Counter()

    def exists(recorded: str, where: str) -> None:
        path = _committed(root, recorded)
        if path is not None:
            compared["path"] += 1
            if not path.is_file():
                problems.append(f"{where} names {recorded}, which is not in the example")

    # check.jsonl: what rustc quoted is what the file it names says there.
    for line in (docs / cargo_service.CHECK_DOCUMENT).read_text(encoding="utf-8").splitlines():
        message = json.loads(line)
        if message.get("reason") == "compiler-artifact" and "file:///ws" in message.get("package_id", ""):
            exists(message["target"]["src_path"], "check.jsonl")
        for span in _spans(message.get("message") or {}):
            path = _committed(root, span["file_name"])
            if path is None:
                continue
            if not path.is_file():
                problems.append(f"check.jsonl quotes {span['file_name']}, which is not in the example")
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            for at, quoted in enumerate(span.get("text") or [], start=span["line_start"]):
                compared["quoted line"] += 1
                now = lines[at - 1] if at <= len(lines) else None
                if now != quoted["text"]:
                    problems.append(f"check.jsonl: {path.relative_to(root).as_posix()}:{at} reads "
                                    f"{now!r}; rustc quoted {quoted['text']!r}")

    # metadata.json: each member's manifest and targets are there, and it
    # depends on what its Cargo.toml says it does.
    metadata = json.loads((docs / cargo_service.METADATA_DOCUMENT).read_text(encoding="utf-8"))
    members = [p for p in metadata["packages"] if p["id"] in metadata["workspace_members"]]
    for package in members:
        exists(package["manifest_path"], "metadata.json")
        for target in package["targets"]:
            exists(target["src_path"], "metadata.json")
        manifest = _committed(root, package["manifest_path"])
        if manifest is not None and manifest.is_file():
            compared["dependencies"] += 1
            recorded = {d["name"] for d in package["dependencies"]}
            declared = _declared(cargo_service._toml().loads(manifest.read_text(encoding="utf-8")))
            if recorded != declared:
                problems.append(f"metadata.json: {package['name']} depends on {sorted(recorded)}; "
                                f"its Cargo.toml says {sorted(declared)}")

    # BIN.map: what the linker placed of a member crate is an item its sources
    # define, and each handler a binary's sources declare was placed.
    sources = {p["name"].replace("-", "_"): "\n".join(
        f.read_text(encoding="utf-8")
        for f in sorted((_committed(root, p["manifest_path"]).parent / "src").rglob("*.rs")))
        for p in members}
    for map_path in sorted(docs.glob("*.map")):
        text = map_path.read_text(encoding="utf-8")
        for crate, source in sources.items():
            for name in re.findall(rf"(?<![\w:]){crate}::(?:\w+::)*(\w+)", text):
                compared["placed item"] += 1
                item = name.removeprefix("__cortex_m_rt_")  # the entry macro's rename of `main`
                if not re.search(ITEM.format(re.escape(item)), source):
                    problems.append(f"{map_path.name} places {crate}::{name}; "
                                    f"no `{item}` is defined in {crate}'s sources")
        handlers = re.findall(r"#\[(entry|exception)\]\s*(?:pub\s+)?(?:unsafe\s+)?fn\s+(\w+)",
                              sources.get(map_path.stem, ""))
        for kind, name in handlers:
            compared["handler"] += 1
            symbol = f"{map_path.stem}::__cortex_m_rt_{name}" if kind == "entry" else name
            if not re.search(rf"\s{re.escape(symbol)}$", text, re.M):
                problems.append(f"{map_path.name} places no {symbol}, which the #[{kind}] "
                                f"fn {name} in {map_path.stem}'s sources is linked as")
    return problems, compared


def test_the_records_are_of_the_sources_beside_them():
    """Mutation, in a copy `EXAMPLE` is pointed at: edit the line rustc quoted
    (`    errors: u32,` at crates/hal/src/uart.rs:11), rename `TICKS` or
    `SysTick` in blinky's main.rs, or drop `defmt` from hal's Cargo.toml --
    each fails, while the re-timed reading above passes on the same copy. The
    next test keeps two of those edits failing."""
    if cargo_service._toml() is None:
        pytest.skip("no TOML reader (tomllib is 3.11+; tomli is not installed)")
    problems, compared = _unlike_their_sources(EXAMPLE)
    assert problems == []
    # Every kind of fact was found to compare, so an empty list is an answer.
    assert set(compared) == {"path", "quoted line", "dependencies", "placed item", "handler"}, compared


def test_an_edit_the_records_were_not_made_from_is_named(tmp_path):
    if cargo_service._toml() is None:
        pytest.skip("no TOML reader (tomllib is 3.11+; tomli is not installed)")
    root = tmp_path / "rust-firmware"
    shutil.copytree(EXAMPLE, root)
    uart = root / "crates" / "hal" / "src" / "uart.rs"
    uart.write_text(uart.read_text(encoding="utf-8").replace("errors: u32,", "errors: u16,"),
                    encoding="utf-8")
    main = root / "crates" / "blinky" / "src" / "main.rs"
    main.write_text(main.read_text(encoding="utf-8").replace("TICKS", "COUNT"), encoding="utf-8")
    problems, _ = _unlike_their_sources(root)
    assert [p.split(";")[0] for p in problems] == [
        "check.jsonl: crates/hal/src/uart.rs:11 reads '    errors: u16,'",
        "blinky.map places blinky::TICKS",
    ]


def test_the_records_name_no_machine():
    """Every absolute path is under /ws, /cargo-home or /rustup-home."""
    for doc in (EXAMPLE / "target" / "codecarto").iterdir():
        text = doc.read_text(encoding="utf-8")
        assert not re.search(r"(?<![a-z])[A-Za-z]:[\\/]", text), doc.name
        assert "Users" not in text and "AppData" not in text, doc.name


def test_the_route():
    from codecarto.main import app

    resp = TestClient(app).get("/repo/examples")
    assert resp.status_code == 200
    assert [e["id"] for e in resp.json()["results"]["examples"]] == ["rust-firmware"]
