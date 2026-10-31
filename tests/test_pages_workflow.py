"""What `.github/workflows/pages.yml` publishes, from where, and with what it may write.

**IT PUBLISHES THE PAGE'S OWN FOLDER.** The page without a server is built on
its own (`npm run build:view`, Vite's mode `view`) into a folder of its own,
and the window's build, `web/dist`, would publish a dock that asks routes no
static host answers. The folder the workflow uploads is read here from
`web/vite.config.js`, and the build step from `web/package.json`, rather than
from a list in this file.

**ONLY MAIN PUBLISHES, AND ONLY ONE JOB MAY.** A pull request is never
deployed: it builds and serves the page in the browser suite instead. The
workflow reads the repository and nothing more, and the deploy job alone
holds Pages's write and its identity token.

Seen red before trusted: with the upload pointed at `web/dist`, or the
page's build writing no `index.html`, the folder test failed; with a
`pull_request` trigger added, the trigger test; with `pages: write` given to
the build job, or to the whole workflow, the permissions test; with the
workflow's own path left out of the filter, the path test.

WHAT THIS CANNOT SEE. Whether Pages is enabled with GitHub Actions as its
source, which is a setting of the repository, and whether the deployed page
draws: the browser suite opens the same folder from a static server.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
WEB = ROOT / "web"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _triggers() -> dict:
    doc = _workflow()
    # YAML 1.1, which PyYAML reads, takes the bare key `on` for True.
    return doc.get("on", doc.get(True))


def _the_pages_folder() -> str:
    """The folder the page's build writes, as `web/vite.config.js` names it for mode `view`."""
    config = (WEB / "vite.config.js").read_text(encoding="utf-8")
    found = re.search(r"outDir:\s*page\s*\?\s*'\.\./([^']+)'", config)
    assert found, "web/vite.config.js names no outDir for the page's build"
    return f"web/{found.group(1)}"


def test_it_publishes_the_folder_the_pages_own_build_writes():
    steps = _workflow()["jobs"]["build"]["steps"]
    runs = [step["run"] for step in steps if "run" in step]
    assert "npm run build:view" in runs, f"the build job runs {runs}, not the page's build"
    script = json.loads((WEB / "package.json").read_text(encoding="utf-8"))["scripts"]["build:view"]
    folder = _the_pages_folder()
    assert "--mode view" in script, f"build:view does not build the page's mode: {script}"
    # A folder's address opens the page: the build writes it as index.html too.
    assert f"{folder.removeprefix('web/')}/index.html" in script, f"build:view writes no index.html: {script}"
    uploads = [step for step in steps if str(step.get("uses", "")).startswith("actions/upload-pages-artifact@")]
    assert len(uploads) == 1, "the build job should upload one Pages artifact"
    assert uploads[0]["with"]["path"] == folder, (
        f"the workflow publishes {uploads[0]['with']['path']}; the page's build writes {folder}")


def test_only_main_is_published():
    triggers = _triggers()
    assert set(triggers) == {"push", "workflow_dispatch"}, f"pages.yml runs on {sorted(triggers)}"
    assert triggers["push"]["branches"] == ["main"]


def test_only_the_deploy_job_may_write_and_only_to_pages():
    workflow = _workflow()
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert "permissions" not in jobs["build"], "the build job should hold only the workflow's read"
    assert jobs["deploy"]["permissions"] == {"pages": "write", "id-token": "write"}
    assert jobs["deploy"]["environment"]["name"] == "github-pages"
    assert jobs["deploy"]["needs"] == "build"


def test_a_change_to_what_the_build_reads_publishes_it():
    paths = _triggers()["push"]["paths"]
    assert "web/**" in paths
    assert ".github/workflows/pages.yml" in paths
