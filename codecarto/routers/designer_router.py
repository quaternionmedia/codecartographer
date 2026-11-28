"""What the harness declares about each shape of collaboration, for the Designer panel.

- `/designer/data` -- every shape the harness's plane declares, set beside the
  harness's account of whether it could run now, with the options under the
  shape they vary, what the harness has, and which harness answered.
- `/designer/gjgf` -- the same as `GraphData`, the graph format every other
  plot here produces: a node per shape and per need, an edge from a shape to
  each need it states.

Each answers in `generate_return`'s envelope with status 200. A harness that
is not answering is a `results` carrying `unreachable`; one that answers and
has no plane, or states a schema this window does not read, carries
`unreadable`; each with a `problem`, a `remedy` and a `where`, as every estate
route reports an absent seam.

Both routes read. Neither sends anything to the harness.

Each is a plain `def`, so the reads of the harness and the layout run in the
threadpool and hold up no other request.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from codecarto.models.plot_data import PlotOptions
from codecarto.services import designer_service, estate_service
from codecarto.util.utilities import generate_return

DesignerRouter = APIRouter()


@DesignerRouter.get("/data")
def designer_data() -> dict[str, Any]:
    """Every shape, what it needs, and whether the harness says it could run."""
    return generate_return(results=designer_service.read())


@DesignerRouter.get("/gjgf")
def designer_gjgf(
    layout: str = Query(designer_service.LAYOUT),
    palette_id: str = Query("0"),
) -> dict[str, Any]:
    """The shapes against the needs they state, in this project's envelope.

    A layout nobody registered is `unreadable` with the registered ones
    named, as on every estate route.
    """
    document = designer_service.read()
    if "shapes" not in document:
        return generate_return(results=document)
    options = PlotOptions(layout=layout, palette_id=palette_id, type="d3")
    made = designer_service.picture(document)
    try:
        graph = designer_service.as_gjgf(document, made, options)
    except ValueError as error:
        return generate_return(results=estate_service.unknown_layout(
            error, f"/designer/gjgf?layout={layout}"))
    return generate_return(results={
        "graph": graph,
        "metadata": designer_service.metadata(document, made, options),
    })
