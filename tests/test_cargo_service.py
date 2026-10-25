"""Reading a Cargo workspace: both engines, the recorded documents, the graph.

Every test reads a *copy* of `tests/fixtures/cargo/workspace` with its file
times set on purpose. Whether a recorded document is stale is decided by
modification times, and a checkout sets those in whatever order it writes the
files -- so a test that read the fixture in place would pass or fail by the
order git happened to use.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from click.testing import CliRunner

from codecarto.cli import cli
from codecarto.main import app
from codecarto.services import cargo_service
from codecarto.services.local_repo_service import get_local_repo
from codecarto.services.unified_parser_service import UnifiedParserService

FIXTURE = Path(__file__).parent / "fixtures" / "cargo" / "workspace"
HOUR = 3600


def copy_workspace(tmp_path: Path, documents: str = "current") -> Path:
    """The fixture, its sources an hour old, its documents `current` (newer
    than every source), `stale` (older) or `absent`."""
    root = tmp_path / "ws"
    shutil.copytree(FIXTURE, root)
    then = time.time() - HOUR
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, (then, then))
    docs = root / cargo_service.DOCUMENTS
    if documents == "absent":
        shutil.rmtree(docs)
    else:
        stamp = time.time() if documents == "current" else then - HOUR
        for path in docs.iterdir():
            os.utime(path, (stamp, stamp))
    return root


def edit_metadata(root: Path, data: dict | None = None) -> dict:
    """The copy's metadata.json, or, given *data*, that written back as current."""
    path = root / cargo_service.DOCUMENTS / cargo_service.METADATA_DOCUMENT
    if data is None:
        return json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(data), encoding="utf-8")
    now = time.time()
    os.utime(path, (now, now))
    return data


def package(reading, name):
    found = reading.package(name)
    assert found is not None, name
    return found


def deps(pkg) -> dict[str, tuple]:
    return {d.name: (d.kind, d.optional, d.platform, d.version) for d in pkg.dependencies}


# ── The manifests, read without cargo ─────────────────────────────────────────


class TestManifests:
    @pytest.fixture
    def reading(self, tmp_path):
        return cargo_service.read(copy_workspace(tmp_path, "absent"))

    def test_engine_and_members(self, reading):
        assert reading.ok and reading.engine == "manifests"
        assert {p.name for p in reading.packages} == {"hal", "blinky", "host-tool"}
        assert all(p.member and p.workspace == "Cargo.toml" for p in reading.packages)

    def test_workspace_inheritance_and_lockfile_versions(self, reading):
        hal = package(reading, "hal")
        assert (hal.version, hal.edition) == ("0.1.0", "2021")
        assert deps(hal)["heapless"] == ("normal", False, "", "0.8.0")  # `workspace = true`

    def test_declared_not_resolved(self, reading):
        """Without cargo, an optional dependency nobody enabled is still drawn,
        as optional -- the caveat says features are as declared."""
        assert deps(package(reading, "hal"))["defmt"][:2] == ("normal", True)
        assert "declared rather than resolved" in cargo_service.caveat(reading)

    def test_dependency_kinds_platforms_and_paths(self, reading):
        host = package(reading, "host-tool")
        assert deps(host)["cc"][0] == "build"
        assert deps(host)["proptest"][0] == "dev"
        assert deps(host)["libc"][2] == "cfg(unix)"
        hal_dep = next(d for d in host.dependencies if d.name == "hal")
        assert (hal_dep.source, hal_dep.path) == ("path", "crates/hal")

    def test_targets_are_discovered_by_convention(self, reading):
        kinds = {(t.kinds[0], t.name) for t in package(reading, "blinky").targets}
        assert kinds == {("bin", "blinky"), ("custom-build", "build-script-build")}
        assert [t.kinds for t in package(reading, "hal").targets] == [["lib"]]

    def test_firmware_facts(self, reading):
        assert package(reading, "blinky").no_std == "yes"
        assert package(reading, "host-tool").no_std == ""
        assert package(reading, "blinky").memory_maps == ["crates/blinky/memory.x"]
        assert package(reading, "host-tool").links == "crc"
        firmware = reading.firmware
        assert firmware["build_targets"] == ["thumbv7em-none-eabihf"]
        assert firmware["runners"]["thumbv7em-none-eabihf"].startswith("probe-rs run")
        assert firmware["linker_scripts"] == ["link.x"]

    @pytest.mark.parametrize("config", [
        '[build]\ntarget = "thumbv7em-none-eabihf"\nrustflags = "-C link-arg=-Tlink.x"\n',
        '[target.thumbv7em-none-eabihf]\nrustflags = "-C link-arg=-Tlink.x"\n',
    ], ids=["build", "target"])
    def test_rustflags_given_as_one_string_are_read(self, tmp_path, config):
        """cargo takes `rustflags` as a list or as one space-separated string."""
        root = copy_workspace(tmp_path, "absent")
        write(root / ".cargo" / "config.toml", config)
        assert cargo_service.read(root).firmware["linker_scripts"] == ["link.x"]

    def test_a_target_path_outside_its_package_is_not_read(self, tmp_path):
        """A manifest may name any path as a target's source -- `/dev/zero`,
        another checkout's file -- and this runs in a route."""
        root = tmp_path / "ws"
        crate(root, "probe", "probe", '[lib]\npath = "../outside/lib.rs"\n')
        write(root / "outside" / "lib.rs", "#![no_std]\n")
        assert package(cargo_service.read(root), "probe").no_std == ""

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="a FIFO needs os.mkfifo")
    def test_a_target_path_that_is_not_a_regular_file_is_not_read(self, tmp_path):
        """A FIFO named as the lib's path would block the route on open."""
        import threading

        root = tmp_path / "fifo"
        crate(root, ".", "fifo", '[lib]\npath = "src/pipe.rs"\n')
        pipe = root / "src" / "pipe.rs"
        os.mkfifo(pipe)
        reader = threading.Thread(target=cargo_service.read, args=(root,), daemon=True)
        reader.start()
        reader.join(10)
        blocked = reader.is_alive()
        if blocked:  # let the blocked open return, so the thread can end
            os.close(os.open(pipe, os.O_WRONLY | os.O_NONBLOCK))
        assert not blocked, "reading the lib's path blocked on a FIFO"

    def test_absent_documents_are_sentences(self, reading):
        assert [d.present for d in reading.documents] == [False, False]
        assert all(cargo_service.RECORD_COMMAND in d.problem for d in reading.documents)
        assert "not the same as a clean build" in cargo_service.caveat(reading)


# ── cargo's own documents ─────────────────────────────────────────────────────


class TestRecordedDocuments:
    def test_current_metadata_is_cargos_resolution(self, tmp_path):
        reading = cargo_service.read(copy_workspace(tmp_path, "current"))
        assert reading.engine == "cargo metadata"
        hal = package(reading, "hal")
        assert "defmt" not in deps(hal)  # optional and not enabled: not resolved
        assert hal.resolved_features == ["default", "stm32f4"]
        externals = {p.name for p in reading.packages if not p.member}
        assert {"heapless", "cc", "clap", "libc", "proptest", "cortex-m-rt", "panic-halt"} == externals

    def test_stale_metadata_is_not_used_and_says_why(self, tmp_path):
        """Mutation: return the document even when `doc.stale` -- this fails."""
        reading = cargo_service.read(copy_workspace(tmp_path, "stale"))
        assert reading.engine == "manifests"
        metadata_doc = reading.documents[0]
        assert metadata_doc.present and metadata_doc.stale and not metadata_doc.used
        assert "manifests were read instead" in metadata_doc.problem

    def test_a_package_declared_twice_keeps_each_declarations_settings(self, tmp_path):
        """host-tool declares proptest as an optional dependency and as a
        dev-dependency: each edge carries its own declaration's settings."""
        root = copy_workspace(tmp_path, "current")
        data = edit_metadata(root)
        host = next(p for p in data["packages"] if p["name"] == "host-tool")
        dev = next(d for d in host["dependencies"] if d["name"] == "proptest")
        host["dependencies"].insert(0, {**dev, "kind": None, "req": "^1.4", "optional": True})
        node = next(n for n in data["resolve"]["nodes"] if n["id"] == host["id"])
        next(d for d in node["deps"] if d["name"] == "proptest")["dep_kinds"] = [
            {"kind": None, "target": None}, {"kind": "dev", "target": None}]
        edit_metadata(root, data)
        found = {(d.kind, d.optional, d.req) for d in package(cargo_service.read(root), "host-tool").dependencies
                 if d.name == "proptest"}
        assert found == {("normal", True, "^1.4"), ("dev", False, "^1")}

    def test_transitive_draws_cargos_resolution_when_it_answered(self, tmp_path):
        """With metadata.json in use the lockfile is not read, so `transitive`
        draws the resolution's dependencies of dependencies instead."""
        root = copy_workspace(tmp_path, "current")
        data = edit_metadata(root)
        hash32 = "registry+https://github.com/rust-lang/crates.io-index#hash32@0.3.1"
        heapless = next(p for p in data["packages"] if p["name"] == "heapless")
        data["packages"].append({**heapless, "name": "hash32", "version": "0.3.1", "id": hash32})
        data["resolve"]["nodes"].append({"id": hash32, "deps": [], "dependencies": [], "features": []})
        next(n for n in data["resolve"]["nodes"] if n["id"] == heapless["id"])["deps"] = [
            {"name": "hash32", "pkg": hash32, "dep_kinds": [{"kind": None, "target": None}]}]
        edit_metadata(root, data)
        reading = cargo_service.read(root)
        assert reading.engine == "cargo metadata"
        edge = cargo_service.as_graph(reading, transitive=True).get_edge_data("crate::heapless", "crate::hash32")
        assert edge is not None and edge[0]["label"] == "resolved"

    def test_metadata_older_than_the_lockfile_is_not_used(self, tmp_path):
        """`cargo update -p heapless` rewrites only Cargo.lock, which is a
        manifest: the resolution recorded before it is stale."""
        root = copy_workspace(tmp_path, "current")
        lock = root / "Cargo.lock"
        lock.write_text(lock.read_text(encoding="utf-8").replace(
            'name = "heapless"\nversion = "0.8.0"', 'name = "heapless"\nversion = "0.8.1"'), encoding="utf-8")
        later = time.time() + 60
        os.utime(lock, (later, later))
        reading = cargo_service.read(root)
        assert reading.engine == "manifests"
        assert reading.documents[0].stale and not reading.documents[0].used
        assert deps(package(reading, "hal"))["heapless"][3] == "0.8.1"

    def test_metadata_older_than_the_cargo_config_is_not_used(self, tmp_path):
        root = copy_workspace(tmp_path, "current")
        later = time.time() + 60
        os.utime(root / ".cargo" / "config.toml", (later, later))
        reading = cargo_service.read(root)
        assert reading.engine == "manifests" and reading.documents[0].stale

    def test_a_file_with_the_wrong_shape_is_not_cargos(self, tmp_path):
        root = copy_workspace(tmp_path, "current")
        path = root / cargo_service.DOCUMENTS / cargo_service.METADATA_DOCUMENT
        path.write_text(json.dumps({"packages": []}), encoding="utf-8")
        reading = cargo_service.read(root)
        assert reading.engine == "manifests"
        assert "version: 1" in reading.documents[0].problem

    def test_diagnostics_build_scripts_and_outcome(self, tmp_path):
        reading = cargo_service.read(copy_workspace(tmp_path, "current"))
        assert [(d.level, d.package, d.line) for d in reading.diagnostics] == [
            ("warning", "hal", 11), ("warning", "blinky", 28), ("error", "host-tool", 10)]
        assert reading.scripts[0]["linked_libs"] == ["static=crc"]
        assert reading.build_success is False
        check = reading.documents[1]
        assert check.used and not check.stale

    def test_rustcs_summary_of_its_run_is_not_a_diagnostic(self, tmp_path):
        """The fixture carries the span-less lines rustc ends each crate with --
        `1 warning emitted`, `aborting due to 1 previous error`, the failure
        note -- and one error is one error."""
        reading = cargo_service.read(copy_workspace(tmp_path, "current"))
        assert cargo_service.metadata(reading)["diagnostics"] == {"warning": 2, "error": 1}
        graph = cargo_service.as_graph(reading)
        assert graph.nodes["crate::host-tool"]["label"] == "host-tool 0.1.0 · 1 error"
        assert graph.nodes["crate::hal"]["label"] == "hal 0.1.0 · 1 warning"

    def test_a_check_that_never_finished_is_not_a_clean_build(self, tmp_path):
        """A check.jsonl with no build-finished message is cargo stopping
        before the check did -- no diagnostics in it is not a clean build."""
        root = copy_workspace(tmp_path, "current")
        check = root / cargo_service.DOCUMENTS / cargo_service.CHECK_DOCUMENT
        check.write_text("", encoding="utf-8")
        reading = cargo_service.read(root)
        assert reading.diagnostics == [] and reading.build_success is None
        assert "build-finished" in reading.documents[1].problem
        assert "not a clean one" in cargo_service.caveat(reading)

    def test_a_check_older_than_a_source_says_so(self, tmp_path):
        reading = cargo_service.read(copy_workspace(tmp_path, "stale"))
        check = reading.documents[1]
        assert check.used and check.stale
        assert "a source has changed since" in cargo_service.caveat(reading)

    @pytest.mark.parametrize("package_id,name", [
        ("hal 0.1.0 (path+file:///ws/crates/hal)", "hal"),
        ("path+file:///ws/crates/hal#0.1.0", "hal"),
        ("path+file:///ws/crates/host#host-tool@0.1.0", "host-tool"),
        ("registry+https://github.com/rust-lang/crates.io-index#heapless@0.8.0", "heapless"),
    ])
    def test_package_ids_in_both_spellings(self, package_id, name):
        assert cargo_service.package_name(package_id) == name


# ── Absence and bounds ────────────────────────────────────────────────────────


def test_not_a_directory_and_no_manifest_are_reasons(tmp_path):
    assert "not a directory" in cargo_service.read(tmp_path / "nope").reason
    (tmp_path / "empty").mkdir()
    assert "no Cargo.toml" in cargo_service.read(tmp_path / "empty").reason


def test_a_bound_that_fires_is_reported(tmp_path, monkeypatch):
    """Mutation: drop the note in `_walk` -- this fails."""
    monkeypatch.setattr(cargo_service, "MAX_MANIFESTS", 2)
    reading = cargo_service.read(copy_workspace(tmp_path, "absent"))
    assert any("manifest bound (2)" in note for note in reading.notes)
    assert "manifest bound" in cargo_service.caveat(reading)


def test_a_manifest_that_does_not_parse_is_a_note(tmp_path):
    root = copy_workspace(tmp_path, "absent")
    (root / "crates" / "hal" / "Cargo.toml").write_text("[package\nname = ", encoding="utf-8")
    reading = cargo_service.read(root)
    assert reading.ok and reading.package("hal") is None
    assert any("crates/hal/Cargo.toml did not parse" in n for n in reading.notes)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def fuzzed_crate(tmp_path: Path) -> Path:
    """A crate with the `fuzz/` directory `cargo fuzz init` writes, whose
    manifest makes it a workspace of one with `members = ["."]`."""
    root = tmp_path / "app"
    write(root / "Cargo.toml", '[package]\nname = "app"\nversion = "0.1.0"\n')
    write(root / "src" / "lib.rs", "")
    write(root / "fuzz" / "Cargo.toml",
          '[package]\nname = "app-fuzz"\nversion = "0.0.0"\npublish = false\n\n'
          '[package.metadata]\ncargo-fuzz = true\n\n'
          '[dependencies]\napp = { path = ".." }\n\n'
          '# Prevent this from interfering with workspaces\n[workspace]\nmembers = ["."]\n')
    write(root / "fuzz" / "fuzz_targets" / "parse.rs", "")
    return root


def test_a_workspace_that_lists_itself_is_read(tmp_path):
    """`Path.glob(".")` raises, and cargo-fuzz writes `members = ["."]`."""
    reading = cargo_service.read(fuzzed_crate(tmp_path))
    fuzz = package(reading, "app-fuzz")
    assert fuzz.member and fuzz.workspace == "fuzz/Cargo.toml"
    assert reading.package("app") is not None


def test_an_absolute_member_path_is_a_member(tmp_path):
    root = tmp_path / "ws"
    write(root / "Cargo.toml", f'[workspace]\nmembers = ["{(root / "a").as_posix()}"]\n')
    write(root / "a" / "Cargo.toml", '[package]\nname = "a"\nversion = "0.1.0"\n')
    assert package(cargo_service.read(root), "a").workspace == "Cargo.toml"


# ── Membership, as cargo decides it ───────────────────────────────────────────


def crate(root: Path, where: str, name: str, extra: str = "") -> None:
    write(root / where / "Cargo.toml", f'[package]\nname = "{name}"\nversion = "0.1.0"\n{extra}')
    write(root / where / "src" / "lib.rs", "")


def test_exclude_is_a_path_prefix(tmp_path):
    """cargo excludes everything under an `exclude` entry, unless a `members`
    entry names it explicitly."""
    root = tmp_path / "ws"
    write(root / "Cargo.toml", '[workspace]\nmembers = ["crates/*", "crates/legacy/*", "crates/legacy/kept"]\n'
                               'exclude = ["crates/legacy"]\n')
    for name in ("a", "legacy/old", "legacy/kept"):
        crate(root, f"crates/{name}", name.rsplit("/", 1)[-1])
    reading = cargo_service.read(root)
    assert reading.workspaces[0]["members"] == ["crates/a", "crates/legacy/kept"]
    assert package(reading, "old").workspace == ""


def test_a_path_dependency_inside_the_workspace_is_a_member(tmp_path):
    """A root `[workspace]` with no `members`: its package's path dependencies
    inside the workspace's directory are members, and theirs in turn."""
    root = tmp_path / "ws"
    crate(root, ".", "app", '[workspace]\n[dependencies]\ncore-lib = { path = "crates/core-lib" }\n')
    crate(root, "crates/core-lib", "core-lib", '[dependencies]\nleaf = { path = "../leaf" }\n')
    crate(root, "crates/leaf", "leaf")
    reading = cargo_service.read(root)
    for name in ("core-lib", "leaf"):
        found = package(reading, name)
        assert found.member and found.workspace == "Cargo.toml", name
        assert [t.kinds for t in found.targets] == [["lib"]]


def test_a_package_no_workspace_claims_is_its_own(tmp_path):
    """The crate beside `fuzz/` is no member of the fuzz workspace -- its path
    dependency points outside that directory -- and is a workspace of its own,
    as cargo treats it: a crate, not an external."""
    reading = cargo_service.read(fuzzed_crate(tmp_path))
    app = package(reading, "app")
    assert app.member and app.workspace == ""
    assert cargo_service.as_graph(reading).nodes["crate::app"]["kind"] == "crate"


def test_a_member_under_a_skipped_directory_is_read(tmp_path):
    """The walk skips `build/` and `dist/`; a member a workspace names there is
    read anyway."""
    root = tmp_path / "ws"
    write(root / "Cargo.toml", '[workspace]\nmembers = ["app", "build/codegen"]\n')
    crate(root, "app", "app")
    crate(root, "build/codegen", "codegen")
    reading = cargo_service.read(root)
    assert package(reading, "codegen").workspace == "Cargo.toml"
    assert reading.workspaces[0]["members"] == ["app", "build/codegen"]


@pytest.mark.parametrize("manifest,named", [
    ('[package]\nname = "hal"\nversion = "0.1.0"\n[dependencies]\nfoo = true\n', "foo"),
    ('[package]\nname = "hal"\nversion = "0.1.0"\n[features]\ndefault = 1\n', "default"),
], ids=["dependency-is-a-boolean", "feature-is-an-integer"])
def test_a_manifest_of_a_shape_cargo_refuses_is_a_note(tmp_path, manifest, named):
    """Valid TOML, but not a manifest: the package is not drawn, the reading
    goes on, and a note says which manifest and what in it."""
    root = copy_workspace(tmp_path, "absent")
    write(root / "crates" / "hal" / "Cargo.toml", manifest)
    reading = cargo_service.read(root)
    assert reading.ok and reading.package("hal") is None
    assert {p.name for p in reading.packages if p.member} == {"blinky", "host-tool"}
    note = next(n for n in reading.notes if n.startswith("crates/hal/Cargo.toml"))
    assert named in note


def test_a_config_of_a_shape_cargo_refuses_is_a_note(tmp_path):
    root = copy_workspace(tmp_path, "absent")
    write(root / ".cargo" / "config.toml", 'build = "thumbv7em-none-eabihf"\n')
    reading = cargo_service.read(root)
    assert reading.ok and reading.firmware["build_targets"] == []
    assert any(n.startswith(".cargo/config.toml has a shape") for n in reading.notes)


# ── The graph ─────────────────────────────────────────────────────────────────


class TestGraph:
    @pytest.fixture
    def graph(self, tmp_path):
        return cargo_service.as_graph(cargo_service.read(copy_workspace(tmp_path, "current")), features=True)

    def edges(self, graph, kind):
        return {(u, v, d.get("label"), d.get("style", "solid"))
                for u, v, d in graph.edges(data=True) if d["kind"] == kind}

    def test_dependency_kind_is_label_and_colour_and_conditions_are_dashed(self, graph):
        deps = self.edges(graph, "depends_on")
        assert ("crate::host-tool", "crate::proptest", "dev", "dashed") in deps
        assert ("crate::host-tool", "crate::libc", "depends (cfg(unix))", "dashed") in deps
        assert ("crate::blinky", "crate::hal", "depends", "solid") in deps
        # A build-dependency belongs to the build script, not the crate.
        assert ("target::host-tool::custom-build::build-script-build", "crate::cc", "build", "solid") in deps

    def test_the_native_boundary_declared_and_measured(self, graph):
        links = {(u, v, label) for u, v, label, _ in self.edges(graph, "links")}
        script = "target::host-tool::custom-build::build-script-build"
        assert (script, "native::crc", "links (declared)") in links
        assert (script, "native::crc", "links static") in links

    def test_device_and_memory_map(self, graph):
        assert graph.has_edge("workspace::Cargo.toml", "device::thumbv7em-none-eabihf")
        assert graph.has_edge("crate::blinky", "memory::crates/blinky/memory.x")
        runner = graph.nodes["device::thumbv7em-none-eabihf"]["meta"]["runner"]
        assert runner.startswith("probe-rs")

    def test_diagnostics_label_the_target_they_belong_to(self, graph):
        target = graph.nodes["target::host-tool::bin::host-tool"]
        assert target["label"] == "bin host-tool · 1 error"
        assert target["meta"]["diagnostics"] == {"error": 1}

    def test_a_diagnostic_belongs_to_the_target_of_its_kind(self, tmp_path):
        """A package's lib and bin share its name; a warning about the lib is
        not the bin's."""
        root = tmp_path / "tool"
        crate(root, ".", "tool")
        write(root / "src" / "main.rs", "fn main() {}\n")
        message = {"reason": "compiler-message", "package_id": "path+file:///x/tool#0.1.0",
                   "target": {"kind": ["lib"], "name": "tool"},
                   "message": {"message": "unused import", "level": "warning",
                               "spans": [{"file_name": "src/lib.rs", "line_start": 1, "is_primary": True}]}}
        write(root / cargo_service.DOCUMENTS / cargo_service.CHECK_DOCUMENT, json.dumps(message) + "\n")
        graph = cargo_service.as_graph(cargo_service.read(root))
        assert graph.nodes["target::tool::lib::tool"]["label"] == "lib tool · 1 warning"
        assert graph.nodes["target::tool::bin::tool"]["label"] == "bin tool"

    def test_features_and_what_they_enable(self, graph):
        assert graph.has_edge("feature::hal::default", "feature::hal::stm32f4")
        assert graph.nodes["feature::hal::stm32f4"]["meta"]["enabled"] is True
        assert graph.nodes["feature::hal::defmt"]["meta"]["enabled"] is False

    def test_metadata_carries_provenance(self, tmp_path):
        reading = cargo_service.read(copy_workspace(tmp_path, "current"))
        meta = cargo_service.metadata(reading)
        assert meta["kind"] == "cargo" and meta["engine"] == "cargo metadata"
        assert meta["generated_at"] and meta["caveat"]
        assert [d["name"] for d in meta["documents"]] == ["metadata.json", "check.jsonl"]


# ── The dev loop on the code map ──────────────────────────────────────────────


def test_recorded_diagnostics_land_on_the_items_they_name(tmp_path):
    root = copy_workspace(tmp_path, "current")
    directory = get_local_repo(str(root), extensions=[".rs"])
    graph = UnifiedParserService.build_graph(directory, depth=3, extensions=[".rs"])
    flagged = {d["label"]: d["meta"]["diagnostics"] for _, d in graph.nodes(data=True)
               if (d.get("meta") or {}).get("diagnostics")}
    # The innermost item holding the line: the field, not its struct.
    assert flagged == {"errors": {"warning": 1}, "SysTick": {"warning": 1}, "verbose": {"error": 1}}
    verbose = next(d for _, d in graph.nodes(data=True) if d.get("label") == "verbose")
    assert verbose["has_parse_warning"] is True
    assert verbose["meta"]["diagnostics_recorded_at"]


def test_a_check_older_than_a_source_is_stale_on_the_code_map_too(tmp_path):
    """Edit uart.rs after the check, so line 11 is now `struct Uart`: the overlay
    says stale, as a full read of the directory does; the diagnostic in the
    edited file is not put on whatever item now sits at its line; and the
    others say they are stale rather than marking an error as current."""
    root = copy_workspace(tmp_path, "current")
    uart = root / "crates" / "hal" / "src" / "uart.rs"
    uart.write_text("// two lines\n// added\n" + uart.read_text(encoding="utf-8"), encoding="utf-8")
    later = time.time() + 60
    os.utime(uart, (later, later))
    assert cargo_service.read(root).documents[1].stale
    assert cargo_service.recorded_diagnostics(root).documents[0].stale

    graph = UnifiedParserService.build_graph(get_local_repo(str(root), extensions=[".rs"]), 3, [".rs"])
    flagged = {d["label"]: d["meta"] for _, d in graph.nodes(data=True)
               if (d.get("meta") or {}).get("diagnostics")}
    assert set(flagged) == {"SysTick", "verbose"}
    assert all(meta["diagnostics_stale"] for meta in flagged.values())
    verbose = next(d for _, d in graph.nodes(data=True) if d.get("label") == "verbose")
    assert not verbose.get("has_parse_warning")


def test_no_recorded_check_means_no_overlay(tmp_path):
    root = copy_workspace(tmp_path, "absent")
    graph = UnifiedParserService.build_graph(get_local_repo(str(root), extensions=[".rs"]), 3, [".rs"])
    assert not any((d.get("meta") or {}).get("diagnostics") for _, d in graph.nodes(data=True))


# ── The routes ────────────────────────────────────────────────────────────────


client = TestClient(app)


def test_route_draws_a_workspace(tmp_path):
    root = copy_workspace(tmp_path, "current")
    found = client.get("/cargo/gjgf", params={"path": str(root), "features": "true"}).json()
    assert found["status"] == 200
    assert found["results"]["metadata"]["engine"] == "cargo metadata"
    assert "crate::hal" in found["results"]["graph"]["nodes"]


@pytest.mark.parametrize("params,problem", [
    ({}, "no path was given"),
    ({"path": "definitely/not/here"}, "not a directory"),
])
def test_route_answers_absence_with_a_sentence(params, problem):
    found = client.get("/cargo/gjgf", params=params).json()
    assert found["status"] == 200 and found["results"]["unreadable"] is True
    assert problem in found["results"]["problem"]
    assert "cargo record" in found["results"]["remedy"]


def test_route_answers_an_unknown_layout_with_a_sentence(tmp_path):
    root = copy_workspace(tmp_path, "absent")
    found = client.get("/cargo/gjgf", params={"path": str(root), "layout": "nonsense"}).json()
    assert found["results"]["unreadable"] is True


def test_route_draws_a_crate_with_a_fuzz_directory(tmp_path):
    """`test_estate_routers_never_raise_to_the_browser` reads the router's
    source for `raise`; this drives the route with a manifest that made the
    reader raise beneath it."""
    found = TestClient(app, raise_server_exceptions=False).get(
        "/cargo/gjgf", params={"path": str(fuzzed_crate(tmp_path))})
    assert found.status_code == 200, found.text[:200]
    assert {"crate::app", "crate::app-fuzz"} <= set(found.json()["results"]["graph"]["nodes"])


def test_route_answers_a_reader_that_raised_with_a_sentence(tmp_path, monkeypatch):
    """Mutation: drop the guard in `cargo_router._read` -- this fails."""
    def broken(path):
        raise TypeError("'bool' object is not iterable")

    monkeypatch.setattr(cargo_service, "read", broken)
    found = TestClient(app, raise_server_exceptions=False).get("/cargo/data", params={"path": str(tmp_path)})
    assert found.status_code == 200, found.text[:200]
    results = found.json()["results"]
    assert results["unreadable"] is True and "not iterable" in results["problem"]


def test_data_route_is_comparable_with_cargo(tmp_path):
    found = client.get("/cargo/data", params={"path": str(copy_workspace(tmp_path, "absent"))}).json()
    results = found["results"]
    assert results["engine"] == "manifests"
    assert {p["name"] for p in results["packages"]} == {"hal", "blinky", "host-tool"}


# ── The CLI: the one place cargo is run ───────────────────────────────────────


def test_read_command_runs_nothing_and_prints_the_reading(tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("cargo read must not run a process")

    monkeypatch.setattr("subprocess.run", refuse)
    result = CliRunner().invoke(cli, ["cargo", "read", str(copy_workspace(tmp_path, "current"))])
    assert result.exit_code == 0, result.output
    assert "read from cargo metadata" in result.output
    assert "libc 0.2.153  (normal, cfg(unix))" in result.output


def test_read_command_reads_a_crate_with_a_fuzz_directory(tmp_path):
    result = CliRunner().invoke(cli, ["cargo", "read", str(fuzzed_crate(tmp_path))])
    assert result.exit_code == 0, repr(result.exception)
    assert "app-fuzz 0.0.0" in result.output


def test_record_without_cargo_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path)])
    assert result.exit_code == 1
    assert "cargo is not on PATH" in result.output


class Done:
    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


def fake_cargo(monkeypatch, metadata: Done, check: Done) -> list[list[str]]:
    """cargo on PATH, answering each command with what it is given; returns
    the commands run, and where."""
    ran = []

    def fake_run(command, **kwargs):
        ran.append(command[1:] + [f"cwd={Path(kwargs['cwd']).name}"])
        return metadata if command[1] == "metadata" else check

    monkeypatch.setattr("shutil.which", lambda name: "cargo")
    monkeypatch.setattr("subprocess.run", fake_run)
    return ran


FINISHED = Done('{"reason": "build-finished", "success": false}\n', returncode=101)


def test_record_writes_what_cargo_printed(tmp_path, monkeypatch):
    """The commands and flags are asserted, since they are the contract: the
    window reads these two files and nothing else, and `--locked` keeps cargo
    from rewriting Cargo.lock, which is not under target/."""
    write(tmp_path / "Cargo.toml", '[package]\nname = "app"\nversion = "0.1.0"\n')
    ran = fake_cargo(monkeypatch, Done('{"version": 1, "packages": []}'), FINISHED)
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path)])
    assert result.exit_code == 0, result.output
    here = f"cwd={tmp_path.name}"
    assert ran == [["metadata", "--format-version", "1", "--locked", "--offline", here],
                   ["check", "--workspace", "--message-format=json", "--locked", "--offline", here]]
    docs = tmp_path / cargo_service.DOCUMENTS
    assert json.loads((docs / "metadata.json").read_text())["version"] == 1
    assert "build-finished" in (docs / "check.jsonl").read_text()
    assert "cargo exited 101" in result.output  # a failing check still recorded


def test_record_refuses_a_directory_without_a_manifest(tmp_path, monkeypatch):
    """PATH defaults to `.`: run anywhere else, record ran cargo and made
    target/codecarto/ there first."""
    ran = fake_cargo(monkeypatch, Done('{"version": 1, "packages": []}'), FINISHED)
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path)])
    assert result.exit_code == 1
    assert "no Cargo.toml" in result.output
    assert ran == [] and not (tmp_path / "target").exists()


def test_record_from_a_member_crate_writes_where_the_workspace_is_read(tmp_path, monkeypatch):
    """Run in a member's directory, cargo answers for the workspace above it;
    the documents go to that workspace's target/codecarto/, where reading the
    workspace looks for them."""
    root = tmp_path / "ws"
    write(root / "Cargo.toml", '[workspace]\nmembers = ["crates/*"]\n')
    crate(root, "crates/hal", "hal")
    metadata = Done(json.dumps({"version": 1, "packages": [], "workspace_root": str(root)}))
    fake_cargo(monkeypatch, metadata, FINISHED)
    result = CliRunner().invoke(cli, ["cargo", "record", str(root / "crates" / "hal")])
    assert result.exit_code == 0, result.output
    assert not (root / "crates" / "hal" / "target").exists()
    assert [d.present for d in cargo_service.read(root).documents] == [True, True]


def test_record_says_a_check_that_never_compiled_failed(tmp_path, monkeypatch):
    """`--offline` with a dependency not yet downloaded: cargo prints its
    error on stderr and no JSON at all."""
    write(tmp_path / "Cargo.toml", '[package]\nname = "app"\nversion = "0.1.0"\n')
    stopped = Done("", returncode=101, stderr="error: failed to download `heapless v0.8.0`\n\nCaused by:\n"
                                              "  attempting to make an HTTP request, but --offline was specified\n")
    fake_cargo(monkeypatch, Done('{"version": 1, "packages": []}'), stopped)
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path)])
    assert result.exit_code == 1, result.output
    assert "wrote target/codecarto/check.jsonl" not in result.output
    assert "failed to download `heapless v0.8.0`" in result.output


def test_record_reports_a_timeout_and_keeps_what_arrived(tmp_path, monkeypatch):
    import subprocess

    def slow(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 1, output='{"version": 1')

    write(tmp_path / "Cargo.toml", '[package]\nname = "app"\nversion = "0.1.0"\n')
    monkeypatch.setattr("shutil.which", lambda name: "cargo")
    monkeypatch.setattr("subprocess.run", slow)
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path), "--timeout", "1"])
    assert result.exit_code == 1
    assert "did not finish in 1s" in result.output
    assert (tmp_path / cargo_service.DOCUMENTS / "metadata.json").read_text() == '{"version": 1'
