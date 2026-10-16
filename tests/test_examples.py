"""The examples bundled with this checkout, and that they still read.

`examples/rust-firmware` carries what real cargo and rust-lld recorded for it,
with only absolute paths rewritten. It is offered as the example that shows
everything without a toolchain, so what it shows is asserted here, read as the
window reads it: a record lost or replaced would leave the example drawing
without the thing it is offered for, and nothing would error.

A checkout's file times are whatever the checkout made them, so the test that
reads the records copies the example and gives its documents a fresh time, as
a recording would; what it guards is what the records show, not the clock.
"""

from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path

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
