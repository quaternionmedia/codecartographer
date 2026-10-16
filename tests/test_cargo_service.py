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

    def test_features_and_what_they_enable(self, graph):
        assert graph.has_edge("feature::hal::default", "feature::hal::stm32f4")
        assert graph.nodes["feature::hal::stm32f4"]["meta"]["enabled"] is True
        assert graph.nodes["feature::hal::defmt"]["meta"]["enabled"] is False

    def test_metadata_carries_provenance(self, tmp_path):
        reading = cargo_service.read(copy_workspace(tmp_path, "current"))
        meta = cargo_service.metadata(reading)
        assert meta["kind"] == "cargo" and meta["engine"] == "cargo metadata"
        assert meta["generated_at"] and meta["caveat"]
        assert [d["name"] for d in meta["documents"]] == ["metadata.json", "check.jsonl", "blinky.map"]


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


def test_record_without_cargo_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path)])
    assert result.exit_code == 1
    assert "cargo is not on PATH" in result.output


def test_record_writes_what_cargo_printed(tmp_path, monkeypatch):
    """The commands and flags are asserted, since they are the contract: the
    window reads these two files and nothing else."""
    ran = []

    class Done:
        def __init__(self, stdout, returncode=0):
            self.stdout, self.returncode, self.stderr = stdout, returncode, ""

    def fake_run(command, **kwargs):
        ran.append(command[1:])
        if command[1] == "metadata":
            return Done('{"version": 1, "packages": []}')
        return Done('{"reason": "build-finished", "success": false}\n', returncode=101)

    monkeypatch.setattr("shutil.which", lambda name: "cargo")
    monkeypatch.setattr("subprocess.run", fake_run)
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert ran == [["metadata", "--format-version", "1", "--offline"],
                   ["check", "--workspace", "--message-format=json", "--offline"]]
    docs = tmp_path / cargo_service.DOCUMENTS
    assert json.loads((docs / "metadata.json").read_text())["version"] == 1
    assert "build-finished" in (docs / "check.jsonl").read_text()
    assert "cargo exited 101" in result.output  # a failing check still recorded


def test_record_reports_a_timeout_and_keeps_what_arrived(tmp_path, monkeypatch):
    import subprocess

    def slow(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 1, output='{"version": 1')

    monkeypatch.setattr("shutil.which", lambda name: "cargo")
    monkeypatch.setattr("subprocess.run", slow)
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path), "--timeout", "1"])
    assert result.exit_code == 1
    assert "did not finish in 1s" in result.output
    assert (tmp_path / cargo_service.DOCUMENTS / "metadata.json").read_text() == '{"version": 1'


# ── A recorded link map ───────────────────────────────────────────────────────


def test_a_recorded_map_measures_its_binary(tmp_path):
    reading = cargo_service.read(copy_workspace(tmp_path, "current"))
    doc = next(d for d in reading.documents if d.name == "blinky.map")
    assert doc.used and not doc.stale
    memory = reading.memory["blinky"]
    assert memory["package"] == "blinky" and memory["format"] == "lld"
    flash = next(r for r in memory["regions"] if r["name"] == "FLASH")
    assert flash["used_bytes"] == 0x1130 + 0xe
    label = cargo_service.as_graph(reading).nodes["target::blinky::bin::blinky"]["label"]
    assert label.endswith("FLASH 0.8%, RAM 0.0%")
    assert "blinky's memory use is its linker map" in cargo_service.caveat(reading)


def test_a_map_with_nothing_to_measure_against_says_so(tmp_path):
    root = copy_workspace(tmp_path, "current")
    (root / "crates" / "blinky" / "memory.x").unlink()
    reading = cargo_service.read(root)
    doc = next(d for d in reading.documents if d.name == "blinky.map")
    assert not doc.used and "no memory regions" in doc.problem
    assert "blinky" not in reading.memory


def test_record_links_a_binary_for_its_map(tmp_path, monkeypatch):
    """The map is the linker's own output: the command asks for it, and a
    build that wrote none is a failure, not a document."""
    ran = []

    class Done:
        stdout, stderr, returncode = "", "", 0

    def fake_run(command, **kwargs):
        ran.append(command[1:])
        if command[1] == "rustc":
            target = command[-1].split("-Map=", 1)[1]
            Path(target).write_text("     VMA      LMA     Size Align Out     In      Symbol\n")
        return Done()

    monkeypatch.setattr("shutil.which", lambda name: "cargo")
    monkeypatch.setattr("subprocess.run", fake_run)
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path), "--map", "blinky"])
    assert result.exit_code == 0, result.output
    expected = (tmp_path / cargo_service.DOCUMENTS / "blinky.map").resolve().as_posix()
    assert ran[-1] == ["rustc", "--profile", "release", "--bin", "blinky", "--offline", "--",
                       "-C", f"link-arg=-Map={expected}"]
    assert (tmp_path / cargo_service.DOCUMENTS / "blinky.map").is_file()

    (tmp_path / cargo_service.DOCUMENTS / "blinky.map").unlink()
    monkeypatch.setattr("subprocess.run", lambda command, **kwargs: Done())
    result = CliRunner().invoke(cli, ["cargo", "record", str(tmp_path), "--map", "blinky"])
    assert result.exit_code == 1
    assert "the linker wrote no blinky.map" in result.output
