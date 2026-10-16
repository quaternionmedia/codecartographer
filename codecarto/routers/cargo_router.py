"""A Cargo workspace, on this project's canvas.

**THIS SERVES A CODECARTO GRAPH, NOT A PICTURE OF ONE**, the rule every estate
router follows: `/cargo/gjgf` returns the graph format every other plot here
produces, so a crate graph is drawn with the same canvas, layouts, legend and
radial menu as a code map.

**THE ROUTES, AND WHAT EACH ANSWERS.**

- `/cargo/gjgf?path=` -- crates, their targets, dependencies, native libraries
  and device targets, as `GraphData`. `features=true` adds each crate's
  features and what they enable; `transitive=true` adds the lockfile's
  dependencies of dependencies.
- `/cargo/data?path=` -- the reading itself, without a layout: packages,
  dependencies with their kind and condition, the recorded diagnostics,
  build-script facts and which documents were read, so this window's answer
  can be compared with `cargo metadata`'s rather than only drawn.

**THIS ROUTE RUNS NOTHING.** It reads manifests and the documents
`codecarto cargo record` (or a person's own build) wrote under
`target/codecarto/`. `cargo_service`'s docstring says why running cargo from a
route would be running a cloned repository's code.

**A PATH THAT IS NOT A CARGO PROJECT IS A SENTENCE**, answered 200 with
`unreadable` in the results, exactly as the estate routes answer a seam they
could not read: an empty graph would claim a workspace with no crates.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from codecarto.models.plot_data import PlotOptions
from codecarto.services import cargo_service, estate_service
from codecarto.util.utilities import generate_return

CargoRouter = APIRouter()


def _unreadable(problem: str, where: str) -> dict[str, Any]:
    return generate_return(results={
        "unreadable": True,
        "problem": problem,
        "remedy": ("name a directory holding a Cargo.toml -- a workspace root or a "
                   "single crate -- as `path`. To add cargo's own resolution and the "
                   f"last check's diagnostics, run `{cargo_service.RECORD_COMMAND} <path>` "
                   "there first."),
        "where": where,
    })


def _read(path: str):
    if not path.strip():
        return None, _unreadable("no path was given, so there is no workspace to read",
                                 "/cargo?path=")
    reading = cargo_service.read(path.strip())
    if not reading.ok:
        return None, _unreadable(reading.reason, path)
    return reading, None


@CargoRouter.get("/gjgf")
async def cargo_gjgf(
    path: str = Query("", description="A directory holding a Cargo.toml"),
    layout: str = Query("Kamada Kawai"),
    palette_id: str = Query("0"),
    features: bool = Query(False),
    transitive: bool = Query(False),
) -> dict[str, Any]:
    """The workspace as `GraphData`, in this project's envelope.

    Which engine answered -- cargo's recorded resolution or the manifests --
    is `metadata.engine`, and what that engine cannot see is `metadata.caveat`.
    """
    reading, problem = _read(path)
    if problem is not None:
        return problem
    options = PlotOptions(layout=layout, palette_id=palette_id, type="d3")
    try:
        graph = cargo_service.as_gjgf(reading, options, features=features, transitive=transitive)
    except ValueError as error:
        return generate_return(results=estate_service.unknown_layout(
            error, f"/cargo/gjgf?layout={layout}"))
    return generate_return(results={
        "graph": graph,
        "metadata": cargo_service.metadata(reading, options),
    })


@CargoRouter.get("/data")
async def cargo_data(
    path: str = Query("", description="A directory holding a Cargo.toml"),
) -> dict[str, Any]:
    """Everything the reading holds, without a layout."""
    reading, problem = _read(path)
    if problem is not None:
        return problem
    return generate_return(results=cargo_service.as_data(reading))
