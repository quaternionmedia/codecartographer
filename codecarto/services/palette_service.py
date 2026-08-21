"""Resolving a node's `base` into the style the palette says it has.

**THE PALETTE ALREADY DESCRIBED ALL OF THIS AND NOTHING READ IT.** `Palette`
carries `bases`, `labels`, `alphas`, `sizes`, `shapes` and `colors`, and before
this module the rendering path used none of them: `GraphSerializer` sized nodes
from an edge-count heuristic and coloured them only for dependency plots, from
two hard-coded names. `palette_id` reached the output as a line of metadata and
decided nothing. So a palette could be edited, saved and selected without
changing a single pixel.

**THE DOTTED BASE IS A HIERARCHY, AND THAT IS THE POINT OF IT.**
`control.cond.if` is a kind of `control.cond`, which is a kind of `control`.
A palette that names a colour for `control` and not for `control.cond.if` has
said what colour an `if` is. Resolution walks the dots leftwards and falls back
to `unknown` at the end, so a palette is allowed to be as coarse or as fine as
its author wants -- which is what a hierarchy is for, and it only works if
something walks it.

**MARKERS AND SHAPES ARE TWO VOCABULARIES.** The palette's `shapes` are
matplotlib markers (`o`, `s`, `^`) because that is what plotted these graphs
first. The canvas is gravis now, which names shapes (`circle`, `rectangle`,
`hexagon`). Both are real and neither is wrong; the translation belongs in one
place with a test, rather than in each renderer that needs it.
"""

from __future__ import annotations

from dataclasses import dataclass

from codecarto.models.plot_data import DefaultPalette, Palette

# matplotlib marker -> gravis shape. gravis knows only these three, so several
# markers land on the same shape; that is a limit of the canvas rather than a
# decision, and it is written down here so nobody re-derives it per renderer.
MARKER_TO_SHAPE: dict[str, str] = {
    "o": "circle",
    ".": "circle",
    "s": "rectangle",
    "p": "rectangle",
    "P": "rectangle",
    "D": "rectangle",
    "d": "rectangle",
    "^": "hexagon",
    "v": "hexagon",
    "<": "hexagon",
    ">": "hexagon",
    "*": "hexagon",
    "h": "hexagon",
    "H": "hexagon",
    # `x` is a cross in matplotlib and gravis has no cross. It is mapped to
    # `hexagon` deliberately rather than falling through to the default,
    # because falling through would put it with the circles -- and `x` was
    # chosen by a palette author precisely to stand apart from `o`. A test
    # checks every marker the default palette uses is named here, which is how
    # this one was found silently becoming a circle.
    "x": "hexagon",
    "X": "hexagon",
    "+": "hexagon",
}
DEFAULT_SHAPE = "circle"

# The base every unresolved base ends at. Named rather than inlined, because
# "unknown" is a real entry in every palette and not a synonym for missing.
UNKNOWN = "unknown"

# The palette sizes were chosen for matplotlib's area-based scatter sizes
# (400, 800, ...). gravis sizes are radii. Dividing keeps the *relations*
# between sizes, which is what a palette author chose, and drops the units,
# which they did not.
SIZE_DIVISOR = 20.0
MIN_SIZE = 6.0


@dataclass(frozen=True)
class Style:
    """What the palette says a node of some base looks like."""

    base: str
    """The base actually resolved to, which may be an ancestor of the one asked
    for. Carried so a caller can tell an exact hit from an inherited one --
    a palette author looking at a wrong colour needs to know which entry
    produced it."""

    color: str = "gray"
    shape: str = DEFAULT_SHAPE
    marker: str = "o"
    size: float = 20.0
    alpha: float = 1.0
    label: str = ""

    @property
    def inherited(self) -> bool:
        """Whether this came from an ancestor rather than an exact entry."""
        return self.base == UNKNOWN


def ancestry(base: str) -> list[str]:
    """A base and every base it is a kind of, most specific first.

    `control.cond.if` -> `control.cond.if`, `control.cond`, `control`, `unknown`
    """
    if not base:
        return [UNKNOWN]
    parts = base.split(".")
    found = [".".join(parts[:n]) for n in range(len(parts), 0, -1)]
    if UNKNOWN not in found:
        found.append(UNKNOWN)
    return found


def base_for(node_type: str, palette: Palette | None = None) -> str:
    """The base a node type maps to, via the palette's own `bases` table.

    A type the palette does not name resolves to `unknown` rather than raising:
    a graph containing one node of an unrecognised type should still draw.
    """
    chosen = palette or DefaultPalette
    return chosen.bases.get(node_type, UNKNOWN)


def style_for(base: str, palette: Palette | None = None) -> Style:
    """The style for a base, inheriting along the dotted hierarchy."""
    chosen = palette or DefaultPalette

    def first(table: dict, fallback):
        for candidate in ancestry(base):
            if candidate in table:
                return table[candidate], candidate
        return fallback, UNKNOWN

    color, resolved = first(chosen.colors, "gray")
    marker, _ = first(chosen.shapes, "o")
    size, _ = first(chosen.sizes, 400)
    alpha, _ = first(chosen.alphas, 1.0)
    label, _ = first(chosen.labels, "")

    return Style(
        base=resolved,
        color=str(color),
        shape=MARKER_TO_SHAPE.get(str(marker), DEFAULT_SHAPE),
        marker=str(marker),
        size=max(MIN_SIZE, float(size) / SIZE_DIVISOR),
        alpha=float(alpha),
        label=str(label),
    )


def style_for_type(node_type: str, palette: Palette | None = None) -> Style:
    """The style for a node's `type`, through the palette's `bases` table."""
    return style_for(base_for(node_type, palette), palette)


def apply_to(graph, palette: Palette | None = None, *,
             overwrite: bool = False) -> int:
    """Style every node in a graph from its `type` or `base`. Returns how many.

    **DOES NOT OVERWRITE BY DEFAULT.** A node that already carries a `color`
    was coloured by something that knew more than the palette does -- a
    dependency plot marking an external package, say -- and a styling pass that
    stamped over it would silently discard that. `overwrite=True` is for the
    caller who means it.
    """
    styled = 0
    for _, data in graph.nodes(data=True):
        base = data.get("base") or base_for(str(data.get("type", "")), palette)
        style = style_for(base, palette)
        for key, value in (("color", style.color), ("shape", style.shape),
                           ("size", style.size), ("opacity", style.alpha)):
            if overwrite or key not in data:
                data[key] = value
        styled += 1
    return styled
