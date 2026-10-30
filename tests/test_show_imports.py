"""What the corpus's projects import, set side by side (`show_imports`).

- **An import lands in another project only where that project holds a
  package of its name, and no other project does.** A module one file holds
  is no package; a name two projects hold is no link to either.
- **What a project holds is its own**: its top-level folders and modules, and
  a module in a folder that is no package. A module inside a package is the
  package's, and an import of its name is still someone else's.
- **A module no project holds is shared when two or more of the projects a
  page draws import it.**
- **A tree is read at a commit, once**, and what was installed or built is
  not read.
"""

from __future__ import annotations

import json
import os
import subprocess
import warnings
from pathlib import Path

from click.testing import CliRunner

from codecarto.cli import cli
from codecarto.services import show_imports


def _commit(repo: Path, files: dict[str, str], when: str = "2026-03-15T12:00:00Z") -> str:
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when,
           "GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@example.invalid",
           "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@example.invalid"}
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit", "-qm", "c"],
                   check=True, env=env)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True,
                          text=True).stdout.strip()


# Each project's tree, as the corpus's projects had them:
# - otto holds the package `otto`, and `cli.py`, one file, at its root;
# - showrunner holds `showrunner` under src/, and `common`, as otto does too;
# - theatremix holds its own `src/theatremix/showrunner.py`, which imports
#   showrunner's, and a folder of scripts, `ci/`, that imports `helper` from
#   beside itself;
# - wolf is a script package, named in its package.json;
# - alfred imports otto, wolf, both `common`s, a `cli` it does not hold, and
#   what it installed under node_modules.
TREES = {
    "otto": {
        "otto/__init__.py": "import fastapi\nimport pydantic\n",
        "otto/core.py": "from fastapi import FastAPI  # the app, and nothing else\nimport os\n",
        "cli.py": "import click\n",
        "common/__init__.py": "",
    },
    "showrunner": {
        "src/showrunner/__init__.py": "import pydantic\n",
        "common/__init__.py": "",
    },
    "theatremix": {
        "src/theatremix/__init__.py": "",
        "src/theatremix/showrunner.py": "import showrunner\nimport fastapi\n",
        "ci/helper.py": "",
        "ci/run.py": "import helper\n",
    },
    "wolf": {
        "package.json": json.dumps({"name": "wolf"}),
        "index.js": "import m from 'mithril'\n",
    },
    "alfred": {
        "app.py": "import otto.core\nimport fastapi\nimport os.path\nimport cli\nimport common\n",
        "web/main.js": ("import m from 'mithril'\nimport stream from 'mithril/stream'\n"
                        "import { test } from '@playwright/test'\nimport fs from 'node:fs'\n"
                        "import path from 'path'\nimport x from './x.js'\nconst w = require('wolf')\n"
                        "const parts = Array.from(', ')\n"),
        "node_modules/lodash/index.js": "import y from 'left-pad'\n",
    },
}


def _clones(tmp_path: Path, trees: dict[str, dict[str, str]] = TREES) -> tuple[Path, dict[str, str]]:
    where = tmp_path / "clones"
    commits = {}
    for name, files in trees.items():
        repo = where / name
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        commits[name] = _commit(repo, files)
    return where, commits


def _read_all(tmp_path: Path) -> dict[str, dict]:
    where, commits = _clones(tmp_path)
    return {name: show_imports.read_tree(where / name, commit) for name, commit in commits.items()}


# --- what a tree holds and imports -------------------------------------------

def test_a_module_one_file_holds_is_the_project_s_own_and_no_package(tmp_path: Path) -> None:
    # Mutation: hold a root module as a package -- alfred's `import cli`
    # lands in otto, as qm's landed in joe's cli.py, and this fails.
    trees = _read_all(tmp_path)
    assert trees["otto"]["packages"]["python"] == ["common", "otto"]
    found = show_imports.across(trees)
    assert ("alfred", "otto", "cli") not in {(l["source"], l["target"], l["module"]) for l in found["links"]}


def test_a_module_inside_a_package_is_the_package_s(tmp_path: Path) -> None:
    # theatremix's own src/theatremix/showrunner.py imports showrunner's
    # package. Mutation: take every module's name anywhere as the project's
    # own -- the import is theatremix's, the link is lost, and this fails.
    trees = _read_all(tmp_path)
    assert trees["theatremix"]["imports"]["python"] == {"fastapi": 1, "showrunner": 1}
    links = {(l["source"], l["target"], l["module"]) for l in show_imports.across(trees)["links"]}
    assert ("theatremix", "showrunner", "showrunner") in links


def test_a_module_in_a_folder_that_is_no_package_is_the_project_s_own(tmp_path: Path) -> None:
    # ci/run.py imports helper from beside it. Mutation: hold only the top
    # level as the project's own -- `helper` is read as an import, and this fails.
    trees = _read_all(tmp_path)
    assert "helper" not in trees["theatremix"]["imports"]["python"]


def test_the_standard_library_builtins_and_paths_are_no_import(tmp_path: Path) -> None:
    # Mutations: keep the standard library (`os`), keep `node:` or bare
    # builtins (`fs`, `path`), or read `Array.from(', ')` as an import -- each
    # adds a name here, and this fails.
    trees = _read_all(tmp_path)
    assert trees["alfred"]["imports"] == {
        "python": {"cli": 1, "common": 1, "fastapi": 1, "otto": 1},
        "javascript": {"@playwright/test": 1, "mithril": 1, "wolf": 1},
    }


def test_a_module_is_counted_once_for_each_file_that_imports_it(tmp_path: Path) -> None:
    # alfred's main.js imports mithril twice, once by a subpath. Mutation:
    # count statements, not files -- mithril is 2, and this fails.
    trees = _read_all(tmp_path)
    assert trees["alfred"]["imports"]["javascript"]["mithril"] == 1
    assert trees["otto"]["imports"]["python"]["fastapi"] == 2


def test_what_was_installed_or_generated_is_not_read(tmp_path: Path, monkeypatch) -> None:
    # Mutations: read node_modules -- left-pad is an import -- or read a file
    # over LARGEST -- otto's core.py, set over it here, still imports fastapi
    # twice -- and this fails.
    monkeypatch.setattr(show_imports, "LARGEST", 40)
    trees = _read_all(tmp_path)
    assert "left-pad" not in trees["alfred"]["imports"]["javascript"]
    assert trees["otto"]["imports"]["python"]["fastapi"] == 1


def test_another_project_s_bad_escape_does_not_lose_its_imports(tmp_path: Path) -> None:
    # Python warns of `"\w"` in a string as it parses it, and a reader that
    # turns warnings into errors -- `-W error`, as a strict run does -- has
    # the parse fail and the file's imports read as none. Mutation: parse
    # without silencing it, and this fails.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert show_imports.python_imports('pattern = "\\w"\nimport fastapi\n') == ["fastapi"]


def test_a_script_import_names_its_package() -> None:
    assert show_imports.package_of("mithril/stream") == "mithril"
    assert show_imports.package_of("@playwright/test/reporter") == "@playwright/test"
    for none in ("./x.js", "../y", "/abs", "node:fs", "fs", ", ", "https://example.invalid/m.js"):
        assert show_imports.package_of(none) is None, none


# --- set side by side --------------------------------------------------------

def test_an_import_lands_in_the_one_project_holding_its_package(tmp_path: Path) -> None:
    found = show_imports.across(_read_all(tmp_path))
    assert [(l["source"], l["target"], l["language"], l["module"]) for l in found["links"]] == [
        ("alfred", "otto", "python", "otto"),
        ("alfred", "wolf", "javascript", "wolf"),
        ("theatremix", "showrunner", "python", "showrunner"),
    ]


def test_a_package_two_projects_hold_is_no_link_to_either(tmp_path: Path) -> None:
    # Mutation: land an import in the first of its holders -- alfred links to
    # otto by `common`, and this fails.
    found = show_imports.across(_read_all(tmp_path))
    assert "common" not in {l["module"] for l in found["links"]}
    assert found["ambiguous"] == [{"module": "common", "language": "python",
                                   "holders": ["otto", "showrunner"], "importers": ["alfred"]}]


def test_a_module_is_shared_when_two_or_more_import_it_and_counted_alone_otherwise(tmp_path: Path) -> None:
    # Mutation: share what one project imports -- alfred's `cli` and
    # @playwright/test, and otto's click, are drawn, and this fails.
    found = show_imports.across(_read_all(tmp_path))
    assert [(r["language"], r["module"], sorted(r["projects"])) for r in found["shared"]] == [
        ("python", "fastapi", ["alfred", "otto", "theatremix"]),
        ("javascript", "mithril", ["alfred", "wolf"]),
        ("python", "pydantic", ["otto", "showrunner"]),
    ]
    assert found["shared"][0]["projects"] == {"alfred": 1, "otto": 2, "theatremix": 1}
    assert found["alone"] == 3


def test_a_page_s_projects_share_among_themselves_and_import_from_anyone(tmp_path: Path) -> None:
    # A page drawing alfred and wolf: mithril is shared between them,
    # fastapi is not (otto and theatremix are not drawn), and alfred's import
    # of otto still lands. Mutations: share across every tree read -- fastapi
    # is drawn -- or ask only the page's projects who holds a package -- the
    # link to otto is lost -- and this fails.
    found = show_imports.across(_read_all(tmp_path), among=["alfred", "wolf"])
    assert [r["module"] for r in found["shared"]] == ["mithril"]
    assert {(l["source"], l["target"]) for l in found["links"]} == {("alfred", "otto"), ("alfred", "wolf")}


def test_a_clone_is_read_once_per_commit_and_a_failure_is_not_kept(tmp_path: Path, monkeypatch) -> None:
    # Mutations: keep a failed read -- the second call is None too -- or keep
    # nothing -- the third call reads git again -- and this fails.
    where, _ = _clones(tmp_path, {"otto": TREES["otto"]})
    real, calls = subprocess.run, []

    def counted(args, *rest, **kwargs):
        if "ls-tree" in args:
            calls.append(args)
            if len(calls) == 1:
                return subprocess.CompletedProcess(args, 128, b"", b"fatal: a test")
        return real(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "run", counted)
    assert show_imports.read(where / "otto") is None
    assert show_imports.read(where / "otto")["packages"]["python"] == ["common", "otto"]
    show_imports.read(where / "otto")
    assert len(calls) == 2


# --- the corpus, measured ------------------------------------------------------

def _corpus(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    """otto from January, importing fastapi; alfred from March, importing
    fastapi and otto; a commit of alfred's in April past the drawn one adds
    an import of pydantic. stomp's document names a commit its clone lacks,
    ira's names none, and dossier has no clone."""
    clones, show = tmp_path / "clones", tmp_path / "show"
    for name in ("otto", "alfred", "stomp"):
        (clones / name).mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(clones / name)], check=True)
    otto = _commit(clones / "otto", {"otto/__init__.py": "import fastapi\n"}, "2026-01-15T12:00:00Z")
    alfred = _commit(clones / "alfred", {"app.py": "import fastapi\nimport otto\n"}, "2026-03-15T12:00:00Z")
    _commit(clones / "alfred", {"later.py": "import pydantic\n"}, "2026-04-15T12:00:00Z")
    _commit(clones / "stomp", {"s.py": "import fastapi\n"}, "2026-02-15T12:00:00Z")
    for name, commit in (("otto", otto), ("alfred", alfred), ("stomp", "0" * 40), ("ira", None),
                         ("dossier", "1" * 40)):
        folder = show / "project" / name
        folder.mkdir(parents=True)
        source = {"source": {"commit": commit}} if commit else {}
        folder.joinpath("show.json").write_text(json.dumps({"provenance": source}), encoding="utf-8")
    return clones, show, {"otto": otto, "alfred": alfred}


def test_the_corpus_is_read_at_its_drawn_commits_and_month_by_month(tmp_path: Path) -> None:
    # Mutations: read a clone at its tip -- pydantic is imported by alfred --
    # or start a project before its first commit -- February holds alfred --
    # and this fails.
    clones, show, commits = _corpus(tmp_path)
    report = show_imports.survey(clones, show, back=3)
    assert report["through"] == "2026-03"
    assert report["left_out"] == {"dossier": "no clone", "ira": "its document names no source commit",
                                  "stomp": "its clone lacks 0000000"}
    assert report["projects"]["alfred"] == {"commit": commits["alfred"],
                                            "packages": {"python": [], "javascript": []}, "imports": 2}
    assert [(l["source"], l["target"]) for l in report["links"]] == [("alfred", "otto")]
    assert [(r["module"], r["projects"]) for r in report["shared"]] == [("fastapi", {"alfred": 1, "otto": 1})]
    # A join is a line the imports view draws: a link, or a project to a
    # module it shares.
    assert [(r["month"], r["projects"], r["shared"], r["links"], r["joins"]) for r in report["months"]] == [
        ("2026-01", 1, 0, 0, 0), ("2026-02", 1, 0, 0, 0), ("2026-03", 2, 1, 1, 3)]


def test_show_imports_prints_the_links_and_writes_the_report(tmp_path: Path) -> None:
    clones, show, _ = _corpus(tmp_path)
    out = tmp_path / "imports.json"
    result = CliRunner().invoke(cli, ["show", "imports", str(clones), str(show), "--months", "3",
                                      "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "alfred -> otto  python:otto  1 file(s)" in result.output
    assert "left out: dossier (no clone)" in result.output
    assert json.loads(out.read_text(encoding="utf-8"))["links"][0]["module"] == "otto"
