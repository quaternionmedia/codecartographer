"""What `codecarto show export` decides before a browser draws anything.

The pictures come from the window (`web/tests/export/`); this module says which
subjects there are, what each document records about where its claims came
from, and refuses what must never be committed. Its checks:

- **The subjects are every family and public project, and the index.** A
  private member is counted on its family's graph and never drawn by name, so
  it is never a subject, and a name the window's address grammar refuses is
  refused here too.
- **A subject's claims digest covers its own rows only.** An edit elsewhere in
  the roster leaves every other subject's documents current; an edit to a
  project's own family, or to its roster entry, does not.
- **Nothing machine-scoped is written.** The backend names the corpus it read
  by where it sits on this disk (`~/repos/qm/qm/families.json`); a document
  carrying that, or any home or drive path, is refused.
- **An export is whole.** Every subject has its document, and every file a
  document names is there.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codecarto.services import show_export
from codecarto.services.show_export import Subject
from codecarto.services.show_service import Family, Reading


def _reading() -> Reading:
    reading = Reading(source="families.json", schema=2, commit="abc1234")
    reading.families = {
        "performing": Family(name="performing", drives="a show", subfamilies=["instruments"],
                             members=["stomp"]),
        "instruments": Family(name="instruments", drives="sound", within="performing",
                              members=["carlos", "private-3"]),
        "infrastructure": Family(name="infrastructure", drives="the estate", members=["qm", "moat"]),
    }
    reading.roster = {"carlos": {"role": "member", "phase": "alpha"}, "qm": {"role": "corpus"}}
    return reading


def test_a_subject_is_the_index_a_family_or_a_project_by_a_name_the_address_takes() -> None:
    assert show_export.parse_subject("index") == Subject("index")
    assert show_export.parse_subject("family:performing") == Subject("family", "performing")
    assert show_export.parse_subject("project:carlos") == Subject("project", "carlos")
    for bad in ("project:", "project:../qm", "repo:carlos", "project:private-3", "family:a/b"):
        with pytest.raises(ValueError):
            show_export.parse_subject(bad)


def test_all_is_every_public_project_then_every_family_then_the_index() -> None:
    chosen = show_export.subjects(_reading(), "all")
    # A family's code view is drawn from its projects' code maps this export
    # writes, so every project is drawn before any family. Mutation: draw the
    # families first -- each family's code view reads code maps not yet
    # written, and this fails.
    kinds = [s.kind for s in chosen]
    assert kinds.index("family") > max(i for i, kind in enumerate(kinds) if kind == "project")
    assert chosen[-1] == Subject("index")
    assert [s.name for s in chosen if s.kind == "family"] == ["infrastructure", "instruments", "performing"]
    assert [s.name for s in chosen if s.kind == "project"] == ["carlos", "moat", "qm", "stomp"]
    # Mutation: let `show_service.projects` list private members -- this fails.
    assert all(not s.name.startswith("private-") for s in chosen)


def test_with_an_inventory_a_project_is_one_the_host_lists() -> None:
    """The site has a page for each public repository the host lists, and a
    project's showgraph sits on that page; a name a family claims and the host
    does not list (planned, or not public) has no page to sit on."""
    reading = _reading()
    reading.inventory = {"carlos": {}, "moat": {}, "qm": {}}
    # Mutation: take every name a family claims -- stomp is drawn for no page,
    # and this fails.
    assert [s.name for s in show_export.subjects(reading, "all") if s.kind == "project"] == ["carlos", "moat", "qm"]


def test_a_project_has_three_views_a_family_two_and_the_index_one() -> None:
    assert Subject("project", "carlos").views == ("estate", "code", "system")
    # A family's code view is the family with its projects' code in it.
    # Mutation: give a family its estate alone -- no family's code is drawn,
    # and this fails.
    assert Subject("family", "performing").views == ("estate", "code")
    # The whole corpus is drawn a family at a time. Mutation: draw the index's
    # code and full views again -- a picture of every project's code at once,
    # and this fails.
    assert Subject("index").views == ("estate",)
    assert Subject("project", "carlos").folder == "project/carlos"
    assert Subject("index").folder == "index"


def test_a_projects_digest_moves_with_its_own_rows_and_no_one_elses() -> None:
    reading = _reading()
    carlos = Subject("project", "carlos")
    before = show_export.claims_digest(reading, carlos)
    # Another family's row changes: carlos's claims are as they were.
    reading.families["infrastructure"].drives = "everything"
    assert show_export.claims_digest(reading, carlos) == before
    # Its own family's row changes, and then its roster entry: each moves it.
    # Mutation: digest the project's name alone -- this fails.
    reading.families["instruments"].drives = "noise"
    after_family = show_export.claims_digest(reading, carlos)
    assert after_family != before
    reading.roster["carlos"]["phase"] = "beta"
    assert show_export.claims_digest(reading, carlos) != after_family


def test_a_familys_digest_covers_its_nesting_and_the_indexs_covers_every_family() -> None:
    reading = _reading()
    family = Subject("family", "instruments")
    index = Subject("index")
    before = (show_export.claims_digest(reading, family), show_export.claims_digest(reading, index))
    reading.families["performing"].subfamilies = []
    reading.families["instruments"].within = None
    assert show_export.claims_digest(reading, family) != before[0]
    assert show_export.claims_digest(reading, index) != before[1]


@pytest.mark.parametrize("where", [
    "~/repos/qm/qm/families.json",
    "C:\\Users\\someone\\repos\\qm",
    "c:/users/someone/repos",
    "/home/someone/qm",
    "/Users/someone/qm",
    # The window's own words for this machine, which a document read on every
    # machine cannot say.
    "3 member(s) had no clone beside this one, or one git could not read",
    "no clone of carlos beside this checkout",
    "the clone of alfred on this disk is at 4073abf",
])
def test_a_document_naming_a_place_on_a_disk_is_refused(where: str) -> None:
    document = {"provenance": {"claims": {"repo": "quaternionmedia/qm"}},
                "views": {"estate": {"metadata": {"source": where}}}}
    # Mutation: let `scrub` pass everything -- each of these fails.
    with pytest.raises(ValueError, match="views.estate.metadata.source"):
        show_export.scrub(document)


def test_a_document_naming_repositories_and_files_passes() -> None:
    show_export.scrub({
        "provenance": {"claims": {"repo": "quaternionmedia/qm", "commit": "abc1234"}},
        "views": {"estate": {"metadata": {"source": "families.json"}},
                  "code": {"metadata": {"url": "https://github.com/quaternionmedia/carlos"}}},
        "files": {"estate": "estate.svg"},
    })


@pytest.mark.parametrize("url", [
    "https://github.com/quaternionmedia/qm.git",
    "https://github.com/quaternionmedia/qm",
    "git@github.com:quaternionmedia/qm.git",
    "https://github.com/quaternionmedia/qm/",
])
def test_the_corpus_is_named_by_its_host_repository(url: str) -> None:
    # Mutation: return the URL as given -- the https forms keep their host and
    # this fails.
    assert show_export.repo_of(url) == "quaternionmedia/qm"


def test_a_remote_that_is_no_host_repository_is_refused() -> None:
    with pytest.raises(ValueError):
        show_export.repo_of("C:/Users/someone/repos/qm")


def test_an_export_missing_a_document_or_a_file_it_names_says_which(tmp_path: Path) -> None:
    chosen = [Subject("index"), Subject("project", "carlos")]
    (tmp_path / "index").mkdir()
    (tmp_path / "index" / "show.json").write_text(json.dumps({"files": {"estate": "estate.svg"}}))
    (tmp_path / "index" / "estate.svg").write_text("<svg/>")
    assert show_export.missing(tmp_path, chosen) == ["project/carlos/show.json"]

    (tmp_path / "project" / "carlos").mkdir(parents=True)
    (tmp_path / "project" / "carlos" / "show.json").write_text(
        json.dumps({"files": {"estate": "estate.svg", "code": "code.svg"}}))
    (tmp_path / "project" / "carlos" / "estate.svg").write_text("<svg/>")
    # Mutation: check the documents and not the files they name -- this fails.
    assert show_export.missing(tmp_path, chosen) == ["project/carlos/code.svg"]
