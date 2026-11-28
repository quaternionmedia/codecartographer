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

- `GET /designer/designs` -- the designs and components the harness holds for
  one project, and whether this window saves a design for the request asking.
- `GET /designer/schema/{kind}` -- the harness's schema of one kind's
  configuration, which the composing form is built from.
- `GET /designer/composition/gjgf` -- every saved design joined to what its
  configuration references, with the design being composed when one is
  named, as `GraphData`.
- `POST /designer/designs` -- one design a person composed, relayed to the
  harness, which validates and saves it. A design that was not saved is a
  `results` carrying `refused`, with each message beside its field.

Every route but the last reads. The last sends one document and keeps none.

Each is a plain `def`, so the requests to the harness and the layout run in
the threadpool and hold up no other request.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from codecarto.models.plot_data import PlotOptions
from codecarto.services import (compose_service, designer_service, estate_service,
                                instruct_service)
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


class Design(BaseModel):
    """What a person composed: a name, a kind, and the configuration filled in."""

    name: str = ""
    topology_type: str = ""
    description: str | None = None
    project: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


def _standing(request: Request) -> str:
    """Why this request's design is not relayed, or "" when it is."""
    server = request.scope.get("server") or (None, None)
    client = request.client.host if request.client else None
    return instruct_service.standing(server[0], client, request.headers)


@DesignerRouter.get("/designs")
def designs(request: Request, project: str | None = Query(None)) -> dict[str, Any]:
    """The saved designs and components of one project, and whether one is saved here."""
    return generate_return(results=compose_service.read(project, _standing(request)))


@DesignerRouter.post("/designs")
def save_design(body: Design, request: Request) -> dict[str, Any]:
    """Relay one design to the harness, which validates and saves it.

    The harness's row is returned as it gave it, with its address and its
    verdict, and its refusal with each message beside the field it is about.
    """
    return generate_return(results=compose_service.save(
        body.model_dump(), _standing(request)))


@DesignerRouter.get("/schema/{kind}")
def design_schema(kind: str) -> dict[str, Any]:
    """The harness's schema of one kind's configuration."""
    return generate_return(results=compose_service.schema(kind))


def _listed(value: str) -> list[str]:
    return [name.strip() for name in value.split(",") if name.strip()]


@DesignerRouter.get("/composition/gjgf")
def composition_gjgf(
    project: str | None = Query(None),
    name: str = Query(""),
    kind: str = Query(""),
    components: str = Query(""),
    compose: str = Query(""),
    draft: bool = Query(False),
    layout: str = Query(compose_service.LAYOUT),
    palette_id: str = Query("0"),
) -> dict[str, Any]:
    """Saved designs joined to what each references, with the draft when asked.

    `draft` draws the design being composed from `name`, `kind` and the
    comma-separated `components` and `compose` it names so far. Nothing is
    sent to the harness but the two reads `GET /designer/designs` makes.
    """
    document = compose_service.read(project, "")
    if "designs" not in document:
        return generate_return(results=document)
    composing = ({"name": name, "topology_type": kind,
                  "config": {"components": _listed(components), "compose": _listed(compose)}}
                 if draft else None)
    made = compose_service.picture(document, composing)
    options = PlotOptions(layout=layout, palette_id=palette_id, type="d3")
    try:
        graph = compose_service.as_gjgf(made, options, str(document.get("where", "")))
    except ValueError as error:
        return generate_return(results=estate_service.unknown_layout(
            error, f"/designer/composition/gjgf?layout={layout}"))
    return generate_return(results={
        "graph": graph,
        "metadata": compose_service.metadata(document, made, options),
    })
