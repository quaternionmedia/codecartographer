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
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codecarto.services import cargo_service, examples_service

REPO = Path(__file__).resolve().parents[1]
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


def _recorder():
    """scripts/record_example.py, which is a script rather than a package."""
    spec = importlib.util.spec_from_file_location("record_example", REPO / "scripts" / "record_example.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_recording_on_windows_names_only_the_stand_ins():
    """Mutation: keep a Windows path's separators after its root, or drop the
    `/` a file URL puts before a drive letter -- `/ws\\target...` or
    `path+file:///C:/...` is left, and this fails."""
    rec = _recorder()
    ws = "C:\\Users\\you\\repos\\codecartographer\\examples\\rust-firmware"
    roots = rec.stand_ins(ws, environ={"CARGO_HOME": "C:\\Users\\you\\.cargo",
                                       "RUSTUP_HOME": "C:\\Users\\you\\.rustup"})
    registry = "index.crates.io-1949cf8c6b5b557f"
    metadata = json.dumps({
        "workspace_root": ws,
        "target_directory": ws + "\\target",
        "packages": [
            {"id": "path+file:///C:/Users/you/repos/codecartographer/examples/rust-firmware/crates/hal#0.1.0",
             "manifest_path": ws + "\\crates\\hal\\Cargo.toml"},
            {"manifest_path": f"C:\\Users\\you\\.cargo\\registry\\src\\{registry}\\heapless-0.8.0\\Cargo.toml"},
        ],
    })
    assert json.loads(rec.portable_document("metadata.json", metadata, roots)) == {
        "workspace_root": "/ws",
        "target_directory": "/ws/target",
        "packages": [
            {"id": "path+file:///ws/crates/hal#0.1.0", "manifest_path": "/ws/crates/hal/Cargo.toml"},
            {"manifest_path": f"/cargo-home/registry/src/{registry}/heapless-0.8.0/Cargo.toml"},
        ],
    }
    # A drive letter in either case; a span's own file, relative, as rustc wrote it.
    check = json.dumps({"reason": "compiler-message", "message": {
        "rendered": "  --> c:\\users\\you\\.rustup\\toolchains\\1.99\\lib\\rustlib\\src\\rust\\library\\core\\src\\lib.rs:3:1\n",
        "spans": [{"file_name": "crates\\hal\\src\\uart.rs"}]}}) + "\n"
    message = json.loads(rec.portable_document("check.jsonl", check, roots))["message"]
    assert message == {
        "rendered": "  --> /rustup-home/toolchains/1.99/lib/rustlib/src/rust/library/core/src/lib.rs:3:1\n",
        "spans": [{"file_name": "crates\\hal\\src\\uart.rs"}]}
    link_map = f" 8000004  8000004        4     4         {ws}\\target\\release\\deps\\blinky-9.o:(.vector_table)\n"
    assert rec.portable_document("blinky.map", link_map, roots) == (
        " 8000004  8000004        4     4         /ws/target/release/deps/blinky-9.o:(.vector_table)\n")


def test_a_recording_on_linux_names_only_the_stand_ins():
    """Mutation: let the first `/` of a root match more than one -- `file:///home/...`
    becomes `file:/ws/...`, and this fails."""
    rec = _recorder()
    ws = "/home/alice/src/codecartographer/examples/rust-firmware"
    roots = rec.stand_ins(ws, environ={}, home=Path("/home/alice"))
    quote = "registry/src/index.crates.io-1949cf8c6b5b557f/quote-1.0.47/src/lib.rs"
    check = json.dumps({
        "package_id": f"path+file://{ws}/crates/blinky#0.1.0",
        "filenames": [f"{ws}/target/debug/build/blinky-1/build-script-build"],
        "target": {"src_path": f"/home/alice/.cargo/{quote}"},
        "linked_paths": [f"native={ws}/target/thumbv7em-none-eabihf/debug/build/blinky-2/out"],
        "out_dir": f"{ws}-old/target",  # a sibling that shares the workspace's prefix is not it
    }) + "\n"
    assert json.loads(rec.portable_document("check.jsonl", check, roots)) == {
        "package_id": "path+file:///ws/crates/blinky#0.1.0",
        "filenames": ["/ws/target/debug/build/blinky-1/build-script-build"],
        "target": {"src_path": f"/cargo-home/{quote}"},
        "linked_paths": ["native=/ws/target/thumbv7em-none-eabihf/debug/build/blinky-2/out"],
        "out_dir": f"{ws}-old/target",
    }


def test_recording_fails_naming_what_it_could_not_rewrite(tmp_path, capsys):
    """Mutation: return 0 whatever is left -- a target directory outside the
    workspace is written into the records with no word, and this fails."""
    rec = _recorder()
    root = tmp_path / "rust-firmware"
    docs = root / "target" / "codecarto"
    docs.mkdir(parents=True)
    ws = str(root)
    (docs / "metadata.json").write_text(json.dumps({"workspace_root": ws, "target_directory": f"{ws}/target"}))
    assert rec.main([ws, "--rewrite-only"]) == 0
    assert (docs / "metadata.json").read_text() == '{"workspace_root": "/ws", "target_directory": "/ws/target"}'

    (docs / "metadata.json").write_text(json.dumps({"workspace_root": ws, "target_directory": "/var/tmp/cargo-target"}))
    assert rec.main([ws, "--rewrite-only"]) == 1
    assert "metadata.json: /var/tmp/cargo-target" in capsys.readouterr().err


def test_a_recording_that_stopped_is_rewritten_and_still_fails(tmp_path, monkeypatch, capsys):
    """`cargo record` exits 1 after writing metadata.json when a later step
    fails -- a map cargo found current and did not link, say. Mutation: let
    that exit stop the script -- the tracked metadata.json is left naming the
    machine, and this fails."""
    from codecarto import cli as codecarto_cli

    rec = _recorder()
    root = tmp_path / "rust-firmware"
    docs = root / "target" / "codecarto"

    def record(args, standalone_mode):
        assert args[:2] == ["cargo", "record"] and args[3:] == ["--map", "blinky"]
        docs.mkdir(parents=True)
        (docs / "metadata.json").write_text(json.dumps({"workspace_root": str(root)}))
        raise SystemExit(1)

    monkeypatch.setattr(codecarto_cli.cli, "main", record)
    root.mkdir()
    assert rec.main([str(root), "--map", "blinky"]) == 1
    assert json.loads((docs / "metadata.json").read_text()) == {"workspace_root": "/ws"}
    assert "not a whole recording" in capsys.readouterr().err


def test_writing_the_committed_records_again_changes_nothing():
    """The recorder writes the records in the form they are committed in, so
    recording again changes only what cargo said differently."""
    rec = _recorder()
    roots = rec.stand_ins("/ws", environ={"CARGO_HOME": "/cargo-home", "RUSTUP_HOME": "/rustup-home"})
    for doc in sorted((EXAMPLE / "target" / "codecarto").iterdir()):
        text = doc.read_text(encoding="utf-8")
        assert rec.portable_document(doc.name, text, roots) == text, doc.name


@pytest.mark.parametrize("path, ignored", [
    ("target/.rustc_info.json", True),
    ("target/CACHEDIR.TAG", True),
    ("target/thumbv7em-none-eabihf/release/deps/libhal-d84773414db7f54d.rlib", True),
    ("target/thumbv7em-none-eabihf/release/blinky", True),
    ("target/debug/deps/libquote-cfe6a9c528a5c624.rmeta", True),
    ("target/release/build/blinky-093437938b8a410e/output", True),
    ("target/codecarto/metadata.json", False),
    ("target/codecarto/check.jsonl", False),
    ("target/codecarto/blinky.map", False),
])
def test_a_build_of_the_example_leaves_only_its_records_to_commit(path, ignored):
    """Mutation: drop the `examples/*/target/*` rule from .gitignore -- cargo's
    build output beside the records shows as untracked, and the ignored cases
    fail; drop the `!` rule after it, and the records are ignored."""
    git = shutil.which("git")
    if git is None:
        pytest.skip("no git")
    result = subprocess.run([git, "check-ignore", "-q", "--no-index", f"examples/rust-firmware/{path}"],
                            cwd=REPO, capture_output=True)
    if result.returncode not in (0, 1):
        pytest.skip("not a git work tree")
    assert (result.returncode == 0) is ignored


def test_the_records_name_no_machine():
    """Every absolute path in them is under /ws, /cargo-home or /rustup-home.
    Mutation: put `/home/alice/.cargo/registry/...` into a copy of check.jsonl
    and point `EXAMPLE` at it -- this fails naming that path, where a scan for
    drive letters, `Users` and `AppData` passed it."""
    rec = _recorder()
    for doc in sorted((EXAMPLE / "target" / "codecarto").iterdir()):
        text = doc.read_text(encoding="utf-8")
        assert rec.machine_paths(text) == [], doc.name
        assert "Users" not in text and "AppData" not in text, doc.name


@pytest.mark.parametrize("text, found", [
    ('"src_path": "/home/alice/.cargo/registry/src/x/lib.rs"', ["/home/alice/.cargo/registry/src/x/lib.rs"]),
    ('"id": "path+file:///home/alice/rust-firmware/crates/hal#0.1.0"', ["/home/alice/rust-firmware/crates/hal"]),
    ('"linked_paths": ["native=/opt/arm/lib"], "PATH": "/ws/bin:/usr/bin"', ["/opt/arm/lib", "/usr/bin"]),
    ("  --> /tmp/build/src/lib.rs:3:1", ["/tmp/build/src/lib.rs"]),
    (" 8000004 4 4 /wsx/target/blinky.o:(.text)", ["/wsx/target/blinky.o"]),  # a stand-in's prefix is not one
    ('"workspace_root": "C:\\\\Users\\\\you\\\\rust-firmware"', ["C:\\\\Users\\\\you\\\\rust-firmware"]),
    ('"id": "path+file:///C:/Users/you/rust-firmware#0.1.0"', ["C:/Users/you/rust-firmware"]),
    ('"/ws", "/ws/target/debug", "path+file:///ws/crates/hal#0.1.0", "/cargo-home/registry",'
     ' "/rustup-home/toolchains", "/ws/target/x.o:(.text)"', []),
    ('"homepage": "https://github.com/rust-embedded/cortex-m-rt", "source": "registry+https://x/"', []),
    ('"features": ["quote?/proc-macro"], "description": "runtime / startup, and/or more"', []),
])
def test_what_names_a_machine(text, found):
    """Mutation: find only drive letters -- the POSIX homes, an /opt toolchain
    and a stand-in's look-alike pass, and their cases fail."""
    assert _recorder().machine_paths(text) == found


EXAMPLES_TS = REPO / "web" / "src" / "features" / "examples" / "examples.ts"
GITHUB_EXAMPLE = re.compile(
    r"\{ label: '(?P<label>[^']+)', url: 'https://github\.com/[\w.-]+/[\w.-]+', "
    r"sizeKb: (?P<kb>\d+),\s*title: '(?P<title>[^']+)' \}")
DRAWN = ("with content", "structure only", "shallow root")
UNITS = {"KB": 1, "MB": 1_000, "GB": 1_000_000}


def _drawn(kb: int) -> str:
    """How much the server draws of a repository GitHub says is *kb* KB."""
    from codecarto.services import github_service

    if kb >= github_service._STRUCTURE_FETCH_LIMIT_KB:
        return "shallow root"
    return "with content" if kb < github_service._CONTENT_FETCH_LIMIT_KB else "structure only"


def test_each_github_example_is_titled_with_what_the_server_draws_of_its_size():
    """Mutation: the titles this branch had -- curl and Redis "full content" at
    ~151 and ~219 MB, requests and Lua at ~14 and ~12 MB, git, SQLite and React
    "structure only" past 50,000 KB -- and this fails naming those seven."""
    source = EXAMPLES_TS.read_text(encoding="utf-8")
    examples = [m.groupdict() for m in GITHUB_EXAMPLE.finditer(source)]
    assert len(examples) == source.count("url: 'https://github.com/"), "an example this does not read"
    assert re.search(r"export const SIZES_MEASURED = '\d{4}-\d{2}-\d{2}';", source)
    wrong = []
    for example in examples:
        kb, title = int(example["kb"]), example["title"]
        drawn = _drawn(kb)
        said = [word for word in DRAWN if word in title]
        if said != [drawn] or not title.endswith(f", {drawn}"):
            wrong.append(f"{example['label']} ({kb} KB) is drawn {drawn}; its title says {said or title}")
        size = re.search(r"\(~(\d+(?:\.\d+)?) (KB|MB|GB)\)", title)
        if not size or not 0.9 <= float(size[1]) * UNITS[size[2]] / kb <= 1.1:
            wrong.append(f"{example['label']} is {kb} KB; its title says {size[0] if size else title}")
    assert wrong == []


def test_the_route():
    from codecarto.main import app

    resp = TestClient(app).get("/repo/examples")
    assert resp.status_code == 200
    assert [e["id"] for e in resp.json()["results"]["examples"]] == ["rust-firmware"]
