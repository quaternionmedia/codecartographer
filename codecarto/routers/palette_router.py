"""Palettes: the built-in one, and an honest answer about custom ones.

**THERE IS NO PALETTE STORE, AND THIS ROUTE NOW SAYS SO.** `/palette/custom`
used to answer 200 with `DefaultPalette` for every id, because the
`DatabaseContext` behind it was a placeholder that ignored its argument and
returned a constant. Two different ids produced byte-identical responses, and
both were indistinguishable from a successful lookup -- a caller had no way to
learn that custom palettes were never implemented. That is the failure mode a
stub should never have: not "it errors", but "it succeeds with the wrong thing".

The placeholder is gone. The route reports what it cannot do, in `results`,
following the same convention `topology_router` and `capability_router` use for
a dependency that is not there.
"""

from fastapi import APIRouter

from codecarto.util.exceptions import proc_exception
from codecarto.util.utilities import generate_return

PaletteRouter = APIRouter()


@PaletteRouter.get("/default")
async def get_default_palette():
    from codecarto.models.plot_data import DefaultPalette

    try:
        return generate_return(
            message="get_default_palette - Success", results=DefaultPalette.dict()
        )
    except Exception as e:
        return proc_exception(
            "get_palette",
            "Error getting default palette",
            {},
            e,
        )


@PaletteRouter.get("/custom")
async def get_custom_palette(palette_id: str):
    """A custom palette, if this deployment had anywhere to keep one.

    **STATUS 200, AND THE PROBLEM IN `results`.** The route itself works; it is
    the store behind it that does not exist, and an envelope status of 501 would
    say this service is unimplemented, which is false of the service. It also
    matters mechanically: `RequestHandler.handleResponse` treats any status but
    200 as a hard error and parses the message in a fixed shape, so a non-200
    envelope reaches the browser as a `TypeError` carrying no detail.

    `unavailable` is the marker to branch on. `requested` echoes the id so a
    caller can see the route read its argument -- which is the one thing the
    placeholder never demonstrated.
    """
    try:
        return generate_return(
            message="get_custom_palette - No palette store",
            results={
                "unavailable": True,
                "requested": palette_id,
                "problem": "this deployment has no store to keep custom palettes in",
                "remedy": "use GET /palette/default, or send a palette_id of '0'",
            },
        )
    except Exception as e:
        return proc_exception(
            "get_palette",
            "Error getting custom palette",
            {},
            e,
        )
