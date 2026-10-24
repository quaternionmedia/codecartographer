"""The triplet's graph leg: every family and project the corpus names.

**THIS SERVES A CODECARTO GRAPH, NOT A PICTURE OF ONE**, as every estate router
here does, so a showgraph draws on the same canvas with the same layouts,
outlines, palettes and radial menu as a code map.

**THE ROUTES, AND WHAT EACH ANSWERS.**

- `/show/subjects` -- what can be drawn: every family the corpus declares, every
  public repository a family or the roster names, and where the reading came
  from. The Show panel lists these.
- `/show/index/gjgf` -- every family at once, its nesting, each member once.
- `/show/family/{name}/gjgf` -- one family.
- `/show/project/{name}/gjgf` -- one repository's place in the estate: the
  `estate` view of its showgraph.
- `/show/project/{name}/views` -- which of a project's three views can be drawn
  here and how. `estate` is the graph above; `code` is the parse of its
  default branch on the host, through `/parse/stream-url`; `system` is the
  derived system monitor, through `/system/compose`. A view that cannot be
  drawn says why, rather than being left out.

**AN ABSENCE ANSWERS 200 WITH THE PROBLEM IN `results`**, the rule every estate
router follows: a corpus whose families document is missing or at a schema this
window does not read, a family the corpus does not declare, a repository no
family or roster entry names, and a private member, which is counted and never
drawn by name.

The routes are plain `def`, so FastAPI runs them off the event loop: measuring
a family's dependencies reads its members' clones, and a slow disk must hold up
nothing else (`tests/test_slow_seams_hold_up_nothing.py` is the rule).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from codecarto.models.plot_data import PlotOptions
from codecarto.services import clones, estate_service, show_service, system_composer
from codecarto.util.utilities import generate_return

ShowRouter = APIRouter()


def _options(layout: str, palette_id: str) -> PlotOptions:
    return PlotOptions(layout=layout, palette_id=palette_id, type="d3")


def _absent(problem: str, remedy: str, where: str) -> dict[str, Any]:
    return generate_return(results={"unreadable": True, "problem": problem,
                                    "remedy": remedy, "where": where})


def _unreadable(reading: show_service.Reading) -> dict[str, Any]:
    return _absent(
        reading.reason,
        ("point this window at a corpus checkout that carries it with "
         "CODECARTO_CORPUS, or move this project's governance pin forward "
         "(`propagate/<name>-<date>` in the corpus, merged into `project/<name>`)"),
        reading.source)


def _draw(reading, graph, layout: str, palette_id: str, where: str) -> dict[str, Any]:
    options = _options(layout, palette_id)
    try:
        drawn = show_service.as_gjgf(graph, options)
    except ValueError as error:
        return generate_return(results=estate_service.unknown_layout(error, where))
    return generate_return(results={
        "graph": drawn,
        "metadata": show_service.metadata(reading, graph, options),
    })


@ShowRouter.get("/subjects")
def show_subjects() -> dict[str, Any]:
    """Every family and public project that can be drawn, and where they came from."""
    reading = show_service.read()
    if not reading.ok:
        return _unreadable(reading)
    return generate_return(results={
        **show_service.subjects(reading),
        "provenance": show_service.provenance(reading),
        "notes": reading.notes,
    })


@ShowRouter.get("/index/gjgf")
def show_index(layout: str = Query("Kamada Kawai"),
               palette_id: str = Query("0")) -> dict[str, Any]:
    """Every family, its nesting, and each member drawn once."""
    reading = show_service.read()
    if not reading.ok:
        return _unreadable(reading)
    return _draw(reading, show_service.index_graph(reading), layout, palette_id,
                 f"/show/index/gjgf?layout={layout}")


@ShowRouter.get("/family/{name}/gjgf")
def show_family(name: str, layout: str = Query("Kamada Kawai"),
                palette_id: str = Query("0")) -> dict[str, Any]:
    """One family: its subfamilies, its members, and every seam touching them."""
    reading = show_service.read()
    if not reading.ok:
        return _unreadable(reading)
    if name not in reading.families:
        return _absent(f"the corpus declares no family named {name!r}",
                       "choose one of: " + ", ".join(reading.families),
                       reading.source)
    return _draw(reading, show_service.family_graph(reading, name), layout,
                 palette_id, f"/show/family/{name}/gjgf?layout={layout}")


def _project_problem(reading: show_service.Reading, name: str) -> dict[str, Any] | None:
    if show_service.PRIVATE.match(name):
        return _absent("a private member is counted and never drawn by name", "",
                       reading.source)
    if name not in show_service.projects(reading):
        return _absent(f"no family and no roster entry names {name!r}",
                       "a repository is placed in a family in ci/workspace.yaml",
                       reading.source)
    return None


@ShowRouter.get("/project/{name}/gjgf")
def show_project(name: str, layout: str = Query("Kamada Kawai"),
                 palette_id: str = Query("0")) -> dict[str, Any]:
    """One repository's place in the estate: the `estate` view of its showgraph."""
    reading = show_service.read()
    if not reading.ok:
        return _unreadable(reading)
    problem = _project_problem(reading, name)
    if problem:
        return problem
    return _draw(reading, show_service.project_graph(reading, name), layout,
                 palette_id, f"/show/project/{name}/gjgf?layout={layout}")


@ShowRouter.get("/project/{name}/views")
def show_project_views(name: str) -> dict[str, Any]:
    """Which of the project's three views this window can draw, and how."""
    reading = show_service.read()
    if not reading.ok:
        return _unreadable(reading)
    problem = _project_problem(reading, name)
    if problem:
        return problem

    code: dict[str, Any]
    if reading.org:
        code = {"available": True, "url": f"https://github.com/{reading.org}/{name}",
                "depth": 1}
    else:
        code = {"available": False,
                "problem": "the inventory names no organisation, so the host address is unknown",
                "remedy": "regenerate status/inventory.yaml with `uv run qm inventory --write`"}

    clone = clones.find(name)
    system: dict[str, Any]
    if clone is None:
        system = {"available": False,
                  "problem": f"no clone of {name} beside this checkout",
                  "remedy": "clone it beside this one, or set CODECARTO_REPO_ROOTS"}
    else:
        components = len(system_composer.discover(clone))
        system = {"available": components > 0, "components": components}
        if not components:
            system.update(problem=(f"{name} declares no system this window reads: no "
                                   f"Helm chart, ArgoCD Application, Terraform or "
                                   f"Dockerfile"),
                          remedy="")
    return generate_return(results={
        "name": name,
        "estate": {"available": True},
        "code": code,
        "system": system,
    })
