"""Where a showgraph's nodes go: each group a ring around its own node, packed.

The compound layout (`models/custom_layouts/compound_layout.py`) is a code
layout. It gives a directory an orbit wide enough for a file's symbols and
spaces directories by a spring layout scaled to the largest, so nine families
of five to nine members each came out about 4,900 units wide. Framed in the
canvas that is a scale of about 0.15, a nine-pixel name drawn a pixel and a
half high, and a showgraph is first of all a map of names.

`pack` re-places a showgraph laid out by the compound layout, in its gJGF:

- **A group is a ring.** A node that `contains` others sits at the centre of
  a ring of what it holds, spaced so the names have room; a subgroup is one
  item on its parent's ring, as wide as its own ring.
- **The top level is packed in rows** wider than they are tall, as the canvas
  is, so the fit draws the estate at a scale its names can be read at.
- **A node no outline holds stays outside every outline.** A member two
  families claim goes between them, at the mean of what it is joined to, and
  is pushed out of any outline it lands in, so the picture still asserts no
  single home.
- **A project's view is a ring around the project.**
- **In the whole corpus, a project's code is one evenly full disc round it**
  (`_patches`), each directory's code a patch of the disc. Laid out as a code
  map lays out a parse -- a disc of discs, each padded for an outline the
  corpus does not draw -- the corpus came out about 28,000 units wide, and
  framed whole each file was drawn under a fifth of a pixel.

Each ring member is given `label_at`, the side its name goes on -- outward
from its ring -- and a node whose outline already names it is given `none`.

Only positions and `label_at` change. Which nodes there are, what they say and
which edges join them is the graph's, and is not touched here.

`code_map` lays a parse out for the Map layout, and for the Showcase a
showgraph's code view opens in (`showcase`): each directory a disc of its
files, its subdirectories packed around the disc, and the whole turned to the
canvas's shape. A file is given
room for itself, not for its name: a code map has hundreds of names, and the
canvas draws each one only once zooming in leaves it room, so the map is drawn
small enough to frame.
"""

from __future__ import annotations

import math
from typing import Any, NamedTuple

import networkx as nx

from codecarto.services import circle_pack

# How much larger a map draws its nodes than a code graph does: the canvas's
# `MAP_NODE_SCALE` in `streaming_renderer.ts`, which a test holds equal.
MAP_NODE_SCALE = 2.5


def _drawn_r(depth: Any) -> float:
    """A node's drawn radius on a map at the canvas's default node size, 4:
    `web/src/features/graph/services/depth_scale.ts`'s multiplier for its
    depth, times `MAP_NODE_SCALE`."""
    multiplier = {0: 3.0, 1: 1.8, 3: 0.6}.get(depth, 1.0) if isinstance(depth, int) else 1.0
    return 4.0 * multiplier * MAP_NODE_SCALE


NODE_R = {depth: _drawn_r(depth) for depth in (0, 1, 2)}
LEAF_R = _drawn_r(2)
# An outline's padding beyond what it encloses, by depth, as
# `compound_layout.ts`'s `computeGroupBounds` draws it.
PAD = {0: 40.0, 1: 20.0}

SPACING = 72.0      # arc between two neighbours on a ring: room for a name
RING_MIN = 60.0     # the smallest ring, so a group of two is still a ring
HUB_CLEAR = 28.0    # between a group's node and the nearest thing on its ring
GAP = 140.0         # between two top-level outlines: room for outward names
GROUP_GAP = 110.0   # the same between two outlines on one ring
FREE_CLEAR = 56.0   # how far outside an outline a node it does not hold sits
FREE_APART = 72.0   # between two nodes no outline holds
ASPECT = 2.2        # the packed rows' width over their height
# A code map's spacing. A directory's outline is drawn around it and its files
# by the canvas, `compound_layout.ts`'s padding beyond each node's reach, which
# is half as much again as its drawn radius; `CODE_PAD` keeps two outlines apart.
FILE_GAP = 6.0          # between two files in a directory's disc: a name is not given room
CODE_REACH = 0.5 * 4.0 * 1.8 * MAP_NODE_SCALE  # a file's reach past its radius
CODE_PAD = 40.0 + CODE_REACH  # the canvas's outline padding, and that reach
CODE_GROUP_GAP = 16.0   # between two directories' outlines
CANVAS_ASPECT = 1400 / 900  # the canvas an exported picture is drawn in, width over height


class Spacing(NamedTuple):
    """How far apart a code map's nodes are packed (`_disc`, `_rows`): between
    two leaves of one disc, between two discs packed round it, past a disc the
    canvas does not outline, past a directory's disc and a file's that it
    does, and between two things nothing holds."""
    leaf: float
    group: float
    reach: float
    pad: tuple[float, float] = (CODE_PAD, CODE_PAD)
    apart: float = GAP


MAP_SPACING = Spacing(FILE_GAP, CODE_GROUP_GAP, CODE_REACH)
# The Showcase's defaults (`showcase`): a dot's radius, and the gap between two.
SHOWCASE_DOT = 2.0
SHOWCASE_GAP = 0.5
# A Showcase's dot by its depth, in a member's: a directory's twice as wide, a
# file's half again. `DOT_SCALE` in `web/src/features/graph/services/showcase.ts`,
# which a test holds equal.
SHOWCASE_SCALE = {0: 2.0, 1: 1.5}
# How far an outline is drawn past what it encloses on a Showcase, in dots: a
# directory's this, and a file's half (`showcasePadding`, and the canvas's
# `computeGroupBounds`).
SHOWCASE_PAD = 4.0
# Which kind a Showcase packs first of two the same size (`_glyph`), so two
# symbols that hold alike are packed, and coloured, alike.
GLYPH_ORDER = {kind: rank for rank, kind in enumerate((
    "argument", "name", "constant", "string", "symbol", "call", "loop", "import",
    "variable", "field", "enum_constant", "function", "async_function", "method",
    "class", "struct", "union", "enum", "module"))}
# What a Showcase draws as a glyph of its own, with what it holds round it.
GLYPH_KINDS = frozenset({"function", "async_function", "method", "class", "struct", "union", "enum"})
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))


def _depth(node: dict[str, Any]) -> int | None:
    depth = node["metadata"].get("depth")
    return int(depth) if isinstance(depth, (int, float)) else None


def _is_code(node: dict[str, Any]) -> bool:
    """A node of a project's code, drawn inside the estate (`corpus_graph`)."""
    return bool(node["metadata"].get("code"))


def _children(gjgf: dict[str, Any]) -> dict[str, list[str]]:
    """What each node holds: `contains` edges one depth down, in edge order.
    A project's code is not one of the estate's groups, and is left out."""
    nodes = gjgf["nodes"]
    held: dict[str, list[str]] = {}
    for edge in gjgf["edges"]:
        if (edge.get("metadata") or {}).get("kind") != "contains":
            continue
        source, target = edge["source"], edge["target"]
        if source not in nodes or target not in nodes or _is_code(nodes[target]):
            continue
        above, below = _depth(nodes[source]), _depth(nodes[target])
        if above is None or below != above + 1:
            continue
        if target not in held.setdefault(source, []):
            held[source].append(target)
    return held


def _side(angle: float) -> str:
    """Outward from a ring, for a member at `angle` (0 is east, y grows down)."""
    x, y = math.cos(angle), math.sin(angle)
    if abs(x) >= 0.35:
        return "right" if x > 0 else "left"
    return "below" if y > 0 else "above"


class _Packer:
    def __init__(self, gjgf: dict[str, Any]) -> None:
        self.nodes = gjgf["nodes"]
        self.held = _children(gjgf)
        self.label_at: dict[str, str] = {}
        # A project's code, laid out as a disc round the project, which is then
        # one item on its family's ring, as wide as the disc.
        code: dict[str, list[str]] = {}
        for edge in gjgf["edges"]:
            source, target = edge["source"], edge["target"]
            if ((edge.get("metadata") or {}).get("kind") == "contains" and source in self.nodes
                    and target in self.nodes and _is_code(self.nodes[target])):
                code.setdefault(source, []).append(target)
        label = lambda n: str(self.nodes[n]["metadata"].get("label", n))  # noqa: E731
        for members in code.values():
            members.sort(key=label)
        self.discs = {hub: _patches(hub, code, lambda n: _drawn_r(_depth(self.nodes[n])), self.label_at)
                      for hub in code if not _is_code(self.nodes[hub])}

    def node_r(self, node_id: str) -> float:
        depth = _depth(self.nodes[node_id])
        return NODE_R.get(depth, LEAF_R) if depth is not None else LEAF_R

    def ring(self, hub_r: float, items: list[tuple[str, float]],
             ) -> tuple[list[tuple[str, float, float, float]], float]:
        """Each item's place on a ring around a hub of radius `hub_r`.

        Returns `(id, x, y, angle)` per item and the ring's radius. Each item
        takes an arc as wide as itself or `SPACING`, whichever is more, so a
        subgroup is given its whole width and a member its name's room.
        """
        # A subgroup's arc also holds the names its neighbours put outward.
        arcs = [SPACING if r <= NODE_R[0] else 2 * r + GROUP_GAP for _, r in items]
        return _ring(hub_r, items, arcs)

    def group(self, hub: str) -> tuple[dict[str, tuple[float, float]], float]:
        """A group laid out around its own node at the origin, and its outline's radius."""
        items: list[tuple[str, float]] = []
        inner: dict[str, tuple[dict[str, tuple[float, float]], float]] = {}
        for child in self.held.get(hub, []):
            if self.held.get(child):
                inner[child] = self.group(child)
                items.append((child, inner[child][1]))
            elif child in self.discs:
                inner[child] = self.discs[child]
                items.append((child, inner[child][1]))
            else:
                items.append((child, self.node_r(child)))
        local: dict[str, tuple[float, float]] = {hub: (0.0, 0.0)}
        placed, radius = self.ring(self.node_r(hub), items)
        for item, x, y, angle in placed:
            if item in inner:
                for node_id, (dx, dy) in inner[item][0].items():
                    local[node_id] = (x + dx, y + dy)
            else:
                local[item] = (x, y)
                self.label_at[item] = _side(angle)
        # The outline names the group, so its node's own label would say it twice.
        self.label_at[hub] = "none"
        widest = max((r for _, r in items), default=0.0)
        return local, radius + widest + PAD.get(_depth(self.nodes[hub]) or 0, PAD[0])


def _ring(hub_r: float, items: list[tuple[str, float]], arcs: list[float],
          ) -> tuple[list[tuple[str, float, float, float]], float]:
    """Items on a ring around a hub of radius `hub_r`, each given its arc."""
    if not items:
        return [], 0.0
    widest = max(r for _, r in items)
    radius = max(RING_MIN, sum(arcs) / (2 * math.pi), hub_r + widest + HUB_CLEAR)
    total = sum(arcs)
    # An arc is longer than the straight line across it, and two
    # neighbours meet along the line: widen the ring until each pair of
    # neighbours is as far apart as their arcs asked for.
    if len(items) > 1:
        for i in range(len(items)):
            j = (i + 1) % len(items)
            between = math.pi * (arcs[i] + arcs[j]) / total
            need = (arcs[i] + arcs[j]) / 2
            chord = 2 * math.sin(min(between, math.pi) / 2)
            if chord > 0:
                radius = max(radius, need / chord)
    placed, run = [], 0.0
    for (item, _), arc in zip(items, arcs):
        angle = -math.pi / 2 + 2 * math.pi * (run + arc / 2) / total
        run += arc
        placed.append((item, radius * math.cos(angle), radius * math.sin(angle), angle))
    return placed, radius


def _rows(circles: list[tuple[str, float]], gap: float = GAP) -> dict[str, tuple[float, float]]:
    """Circles in rows, largest first, `gap` apart, about `ASPECT` times wider
    than tall, centred."""
    if not circles:
        return {}
    ordered = sorted(circles, key=lambda c: -c[1])
    area = sum((2 * r + gap) ** 2 for _, r in ordered)
    width = max(max(2 * r for _, r in ordered), math.sqrt(area * ASPECT))
    rows: list[list[tuple[str, float]]] = [[]]
    used = 0.0
    for circle in ordered:
        span = 2 * circle[1] + (gap if rows[-1] else 0.0)
        if rows[-1] and used + span > width:
            rows.append([])
            used, span = 0.0, 2 * circle[1]
        rows[-1].append(circle)
        used += span
    centres: dict[str, tuple[float, float]] = {}
    y = 0.0
    for row in rows:
        height = max(2 * r for _, r in row)
        row_width = sum(2 * r for _, r in row) + gap * (len(row) - 1)
        x = -row_width / 2
        for name, r in row:
            centres[name] = (x + r, y + height / 2)
            x += 2 * r + gap
        y += height + gap
    shift = (y - gap) / 2
    return {name: (cx, cy - shift) for name, (cx, cy) in centres.items()}


def _push_out(free: dict[str, tuple[float, float]],
              outlines: list[tuple[float, float, float]],
              reach: dict[str, float] | None = None) -> None:
    """Move each free node out of every outline, and apart from the others,
    each as wide as `reach` gives it: a member carrying its code is its disc."""
    reach = reach or {}
    names = sorted(free)
    for _ in range(12):
        moved = False
        for i, name in enumerate(names):
            x, y = free[name]
            for cx, cy, r in outlines:
                dx, dy = x - cx, y - cy
                gap = math.hypot(dx, dy)
                need = r + FREE_CLEAR + reach.get(name, 0.0)
                if gap < need:
                    if gap < 1e-6:
                        dx, dy, gap = math.cos(i), math.sin(i), 1.0
                    x, y = cx + dx / gap * need, cy + dy / gap * need
                    moved = True
            for other in names[:i]:
                ox, oy = free[other]
                dx, dy = x - ox, y - oy
                gap = math.hypot(dx, dy)
                apart = FREE_APART + reach.get(name, 0.0) + reach.get(other, 0.0)
                if gap < apart:
                    if gap < 1e-6:
                        dx, dy, gap = 1.0, 0.0, 1.0
                    x, y = ox + dx / gap * apart, oy + dy / gap * apart
                    moved = True
            free[name] = (x, y)
        if not moved:
            break


def pack(gjgf: dict[str, Any], subject: str) -> dict[str, Any]:
    """Re-place the nodes of a showgraph's gJGF, in place, and return it."""
    nodes = gjgf.get("nodes") or {}
    if not nodes:
        return gjgf
    packer = _Packer(gjgf)
    contained = {child for held in packer.held.values() for child in held}
    tops = [n for n, node in nodes.items()
            if _depth(node) == 0 and n not in contained and packer.held.get(n)]
    laid = {top: packer.group(top) for top in tops}
    placed: dict[str, tuple[float, float]] = {}

    hub = f"repo::{subject.split(':', 1)[1]}" if subject.startswith("project:") else None
    if hub in nodes:
        rest = [n for n in nodes if n != hub and n not in contained and n not in laid]
        items = [(top, laid[top][1]) for top in tops] + [(n, LEAF_R) for n in rest]
        ring, _ = packer.ring(packer.node_r(hub), items)
        placed[hub] = (0.0, 0.0)
        for item, x, y, angle in ring:
            if item in laid:
                for node_id, (dx, dy) in laid[item][0].items():
                    placed[node_id] = (x + dx, y + dy)
            else:
                placed[item] = (x, y)
                packer.label_at[item] = _side(angle)
        packer.label_at[hub] = "below"
    else:
        centres = _rows([(top, laid[top][1]) for top in tops])
        for top, (cx, cy) in centres.items():
            for node_id, (dx, dy) in laid[top][0].items():
                placed[node_id] = (cx + dx, cy + dy)
        in_discs = {n for disc in packer.discs.values() for n in disc[0]}
        free_ids = [n for n in nodes if n not in placed and (n not in in_discs or n in packer.discs)]
        joined: dict[str, list[str]] = {n: [] for n in free_ids}
        for edge in gjgf["edges"]:
            for here, there in ((edge["source"], edge["target"]), (edge["target"], edge["source"])):
                if here in joined and there in placed:
                    joined[here].append(there)
        bottom = max((y for _, y in placed.values()), default=0.0) + FREE_CLEAR * 2
        free: dict[str, tuple[float, float]] = {}
        unjoined = 0
        for name in free_ids:
            if joined[name]:
                xs = [placed[n][0] for n in joined[name]]
                ys = [placed[n][1] for n in joined[name]]
                free[name] = (sum(xs) / len(xs), sum(ys) / len(ys))
            else:
                free[name] = (unjoined * FREE_APART, bottom)
                unjoined += 1
        outlines = [(centres[t][0], centres[t][1], laid[t][1]) for t in centres]
        _push_out(free, outlines, {n: packer.discs[n][1] for n in free if n in packer.discs})
        for name, (x, y) in free.items():
            for node_id, (dx, dy) in packer.discs.get(name, ({name: (0.0, 0.0)}, 0.0))[0].items():
                placed[node_id] = (x + dx, y + dy)
        for name in free:
            packer.label_at.setdefault(name, "below")

    for node_id, node in nodes.items():
        x, y = placed.get(node_id, (node["metadata"].get("x", 0.0), node["metadata"].get("y", 0.0)))
        node["metadata"]["x"] = float(x)
        node["metadata"]["y"] = float(y)
        if node_id in packer.label_at:
            node["metadata"]["label_at"] = packer.label_at[node_id]
    return gjgf


_CONTAINS = frozenset({"contains", "field_of"})
# The disc `code_map` gathers what nothing holds into, on a Showcase: a key no
# node id is.
_LOOSE = "\0loose"


def _pack_around(core: float, circles: list[tuple[str, float]], gap: float,
                 ) -> dict[str, tuple[float, float]]:
    """Circles packed around a disc of radius `core` at the origin, largest
    first, each as near the centre as it can sit `gap` clear of the rest.

    Each one is tried tangent to every circle already placed and to every
    pair of them, and goes where it is nearest the centre and overlaps
    nothing. A pair's tangent place is the nearer of the two points `r + gap`
    beyond both.
    """
    placed: list[tuple[float, float, float]] = [(0.0, 0.0, core)]
    out: dict[str, tuple[float, float]] = {}

    def clear(x: float, y: float, r: float) -> bool:
        return all(math.hypot(x - px, y - py) >= pr + r + gap - 1e-6 for px, py, pr in placed)

    for name, r in sorted(circles, key=lambda c: -c[1]):
        best: tuple[float, float] | None = None
        best_d = math.inf
        candidates: list[tuple[float, float]] = []
        for px, py, pr in placed:
            reach = pr + r + gap
            for k in range(12):
                a = 2 * math.pi * k / 12
                candidates.append((px + reach * math.cos(a), py + reach * math.sin(a)))
        for i, (ax, ay, ar) in enumerate(placed):
            for bx, by, br in placed[i + 1:]:
                ra, rb = ar + r + gap, br + r + gap
                d = math.hypot(bx - ax, by - ay)
                if d < 1e-9 or d > ra + rb or d < abs(ra - rb):
                    continue
                along = (ra * ra - rb * rb + d * d) / (2 * d)
                h = math.sqrt(max(ra * ra - along * along, 0.0))
                mx, my = ax + along * (bx - ax) / d, ay + along * (by - ay) / d
                candidates.append((mx + h * (by - ay) / d, my - h * (bx - ax) / d))
                candidates.append((mx - h * (by - ay) / d, my + h * (bx - ax) / d))
        for x, y in candidates:
            here = math.hypot(x, y)
            if here < best_d and clear(x, y, r):
                best, best_d = (x, y), here
        if best is None:  # Nothing tangent was clear: beyond everything placed.
            far = max(math.hypot(px, py) + pr for px, py, pr in placed)
            best = (far + r + gap, 0.0)
        placed.append((best[0], best[1], r))
        out[name] = best
    return out


def _sunflower(hub_r: float, items: list[tuple[str, float]], gap: float,
               ) -> tuple[list[tuple[str, float, float, float]], float]:
    """Items filling a disc around a hub, each `gap` clear of its neighbours:
    the k-th at a radius growing with the square root of k, a golden angle on
    from the one before, so the disc is evenly full. Returns each item's place
    and angle, and the radius of the farthest centre."""
    if not items:
        return [], 0.0
    r = max(radius for _, radius in items)
    # Neighbours in a sunflower sit about 1.6 times its step apart.
    step = (2 * r + gap) / 1.6
    first = ((hub_r + r + gap) / step) ** 2
    placed = []
    for k, (item, _) in enumerate(items):
        radius, angle = step * math.sqrt(k + first), k * GOLDEN_ANGLE
        placed.append((item, radius * math.cos(angle), radius * math.sin(angle), angle))
    return placed, step * math.sqrt(len(items) - 1 + first)


def _hilbert(n: int, x: int, y: int) -> int:
    """How far along a Hilbert curve filling an `n` by `n` grid, `n` a power
    of two, the cell `(x, y)` is: cells near along the curve are near in the grid."""
    d, s = 0, n // 2
    while s:
        rx, ry = int((x & s) > 0), int((y & s) > 0)
        d += s * s * ((3 * rx) ^ ry)
        if not ry:
            if rx:
                x, y = n - 1 - x, n - 1 - y
            x, y = y, x
        s //= 2
    return d


def _patches(hub: str, held: dict[str, list[str]], radius_of, label_at: dict[str, str],
             ) -> tuple[dict[str, tuple[float, float]], float]:
    """`hub`'s code as one evenly full disc round it, each directory's code a
    patch of the disc; and the disc's radius with the canvas's outline padding.

    The places are a sunflower's (`_sunflower`), spaced as a code map spaces a
    directory's files, taken in the order a Hilbert curve passes them and given
    to the code depth first, each directory before what it holds: a run along
    the curve is a compact patch, so what a directory holds lies together. The
    corpus outlines none of it, so nothing in it is padded for an outline. Sets
    each one's `label_at` outward from `hub`, and `hub`'s `none`.
    """
    order: list[str] = []
    seen = {hub}

    def walk(node: str) -> None:
        for child in held.get(node, []):
            if child not in seen:
                seen.add(child)
                order.append(child)
                walk(child)

    walk(hub)
    local: dict[str, tuple[float, float]] = {hub: (0.0, 0.0)}
    label_at[hub] = "none"
    if not order:
        return local, radius_of(hub) + CODE_PAD
    items = [(node, radius_of(node)) for node in order]
    spots, radius = _sunflower(radius_of(hub), items, FILE_GAP)
    side, cells = max(radius, 1.0), 1 << 16

    def along(spot: tuple[str, float, float, float]) -> int:
        _, x, y, _ = spot
        return _hilbert(cells, int((x + side) / (2 * side) * (cells - 1)),
                        int((y + side) / (2 * side) * (cells - 1)))

    for node, (_, x, y, _) in zip(order, sorted(spots, key=along)):
        local[node] = (x, y)
        label_at[node] = _side(math.atan2(y, x))
    return local, radius + max(r for _, r in items) + CODE_PAD


def _turned(places: dict[str, tuple[float, float]], aspect: float) -> dict[str, tuple[float, float]]:
    """The places turned to whichever angle, in steps of 5 degrees, frames
    them largest in a box `aspect` times wider than tall."""
    best, best_scale = places, 0.0
    for step in range(36):
        a = math.radians(step * 5)
        cos, sin = math.cos(a), math.sin(a)
        turned = {n: (x * cos - y * sin, x * sin + y * cos) for n, (x, y) in places.items()}
        xs = [x for x, _ in turned.values()]
        ys = [y for _, y in turned.values()]
        w, h = max(xs) - min(xs) or 1.0, max(ys) - min(ys) or 1.0
        scale = min(aspect / w, 1.0 / h)
        if scale > best_scale + 1e-12:
            best, best_scale = turned, scale
    return best


def _disc(hub: str, held: dict[str, list[str]], radius_of, label_at: dict[str, str],
          seen: frozenset[str] = frozenset(),
          outlined=lambda node: 0,
          spacing: Spacing = MAP_SPACING,
          whole=lambda node: None) -> tuple[dict[str, tuple[float, float]], float]:
    """`hub` laid out at the centre of a disc of what it holds that holds
    nothing, what it holds that holds others packed around the disc, each laid
    out the same way; and the radius of the circle round it all, with the
    canvas's outline padding where `outlined` says the canvas draws one round
    `hub` -- a directory's (0) or a file's (1) -- and a node's reach alone
    where it says None. Places are relative to that circle's centre. Sets each
    member's `label_at` outward from its hub, and the hub's `none`.

    A hub `whole` lays out -- a Showcase's file, by `_glyph` -- is laid out
    as it says instead."""
    laid = whole(hub)
    if laid is not None:
        return laid
    seen = seen | {hub}
    leaves = [c for c in held.get(hub, []) if not held.get(c) or c in seen]
    inner = {c: _disc(c, held, radius_of, label_at, seen, outlined, spacing, whole)
             for c in held.get(hub, []) if c not in leaves}
    local: dict[str, tuple[float, float]] = {hub: (0.0, 0.0)}
    core = radius_of(hub)
    if leaves:
        items = [(leaf, radius_of(leaf)) for leaf in leaves]
        placed, radius = _sunflower(radius_of(hub), items, spacing.leaf)
        for item, x, y, angle in placed:
            local[item] = (x, y)
            label_at[item] = _side(angle)
        core = radius + max(r for _, r in items)
    places = _pack_around(core, [(c, inner[c][1]) for c in inner], spacing.group)
    for child, (x, y) in places.items():
        for node_id, (dx, dy) in inner[child][0].items():
            local[node_id] = (x + dx, y + dy)
    label_at[hub] = "none"
    # The canvas draws a group's outline around what it holds, wherever its
    # own node sits, so the group is measured and placed by that circle: one
    # centred on the node grew twice as wide at each level a directory held a
    # single large one beside its files.
    discs = [(0.0, 0.0, core)] + [(x, y, inner[c][1]) for c, (x, y) in places.items()]
    cx = (min(x - r for x, _, r in discs) + max(x + r for x, _, r in discs)) / 2
    cy = (min(y - r for _, y, r in discs) + max(y + r for _, y, r in discs)) / 2
    reach = max(math.hypot(x - cx, y - cy) + r for x, y, r in discs)
    outline = outlined(hub)
    pad = spacing.reach if outline is None else spacing.pad[min(outline, 1)]
    return {node_id: (x - cx, y - cy) for node_id, (x, y) in local.items()}, reach + pad


def code_map(graph: nx.DiGraph, radius_of=None, spacing: Spacing = MAP_SPACING,
             files=None) -> dict[str, tuple[float, float]]:
    """A parse laid out as a map, in the canvas's units, and each node's `label_at`.

    A node that `contains` others sits at the centre of a disc of what it
    holds that holds nothing, its files; what it holds that holds others, its
    subdirectories, are packed around that disc, each laid out the same way
    (`_disc`). What nothing holds is packed in rows, and the whole is turned to
    the canvas's shape. A file's name goes outward from its directory, and a
    node its outline names is given `none`. Sets `label_at` on the graph's
    nodes and returns each node's place.

    `radius_of` and `spacing` size and space it (the Map's by default). With
    `files` -- the Showcase's -- a file that holds anything is laid out by it,
    `files(file, held, label_at)` giving its places and radius, and what
    nothing holds and holds nothing is gathered into one disc beside the map
    rather than rowed.
    """
    held: dict[str, list[str]] = {}
    parent: dict[str, str] = {}
    for source, target, data in graph.edges(data=True):
        if data.get("kind") in _CONTAINS and target not in parent and source != target:
            parent[target] = source
            held.setdefault(source, []).append(target)
    for members in held.values():
        members.sort(key=lambda n: str(graph.nodes[n].get("label", n)))

    label_at: dict[str, str] = {}
    radius_of = radius_of or (lambda n: _drawn_r(graph.nodes[n].get("depth", 1)))  # noqa: E731
    tops = [n for n in graph.nodes if n not in parent]
    # The canvas outlines a directory, and a file round its symbols
    # (`compound_layout.ts`); a symbol holding members it does not, and a
    # disc padded for one round each class left a file's map mostly empty.
    outlined = lambda n: graph.nodes[n].get("depth", 1) if graph.nodes[n].get("depth", 1) in (0, 1) else None  # noqa: E731

    def whole(hub: str):
        if files is None or graph.nodes[hub].get("depth") != 1:
            return None
        return files(hub, held, label_at)

    laid = {top: _disc(top, held, radius_of, label_at, outlined=outlined, spacing=spacing, whole=whole)
            for top in tops if held.get(top)}
    loose = [top for top in tops if top not in laid] if files is not None else []
    gathered = set(loose) if len(loose) > 1 else set()
    loose = [top for top in loose if top in gathered]
    circles = [(top, laid[top][1]) if top in laid else (top, radius_of(top))
               for top in tops if top not in gathered]
    if loose:
        # Round an empty centre a dot wide, as a disc is round its hub: from
        # none, the first few crowd closer than the gap.
        widest = max(radius_of(top) for top in loose)
        flower, radius = _sunflower(widest, [(top, radius_of(top)) for top in loose], spacing.leaf)
        laid[_LOOSE] = ({top: (x, y) for top, x, y, _ in flower},
                        radius + max(radius_of(top) for top in loose) + spacing.reach)
        circles.append((_LOOSE, laid[_LOOSE][1]))
        for top, _, _, angle in flower:
            label_at[top] = _side(angle)
    placed: dict[str, tuple[float, float]] = {}
    for top, (cx, cy) in _rows(circles, spacing.apart).items():
        if top in laid:
            for node_id, (dx, dy) in laid[top][0].items():
                placed[node_id] = (cx + dx, cy + dy)
        else:
            placed[top] = (cx, cy)
            label_at.setdefault(top, "below")
    for node_id, side in label_at.items():
        graph.nodes[node_id]["label_at"] = side
    # Turning moves where each name should go, so the sides are set from the
    # turned places: outward from the node that holds it.
    placed = _turned(placed, CANVAS_ASPECT)
    for child, holder in parent.items():
        if label_at.get(child, "none") != "none" and child in placed and holder in placed:
            (x, y), (hx, hy) = placed[child], placed[holder]
            graph.nodes[child]["label_at"] = _side(math.atan2(y - hy, x - hx))
    return placed


def chars_scale(chars: Any) -> float:
    """A dot's radius, in a member's, for the `chars` characters of source it
    stands for: half a member's up to ten, one more for each ten times as
    many, and at most four. A node the parser measured no source for is a
    member's."""
    if not isinstance(chars, (int, float)) or chars <= 0:
        return 1.0
    return min(max(0.5 + math.log10(chars / 10), 0.5), 4.0)


def _glyph(hub: str, held: dict[str, list[str]], radius_of, label_at: dict[str, str], gap: float,
           key) -> tuple[dict[str, tuple[float, float]], float]:
    """`hub` and what it holds packed tight round it (`circle_pack`), each that
    holds others packed the same way first: places relative to the circle
    round them all, and its radius. What it holds is packed in the order
    `key` gives, which depends on nothing but what each is, so two symbols
    that hold alike are drawn alike, wherever they are. Sets each member's
    `label_at` outward from `hub`."""
    children = held.get(hub, [])
    inner = {child: _glyph(child, held, radius_of, label_at, gap, key) for child in children}
    ordered = sorted(children, key=lambda child: key(child, inner[child][1]))
    centres, radius = circle_pack.pack([radius_of(hub)] + [inner[child][1] for child in ordered], gap)
    (hx, hy), local = centres[0], {hub: centres[0]}
    for child, (cx, cy) in zip(ordered, centres[1:]):
        for node, (dx, dy) in inner[child][0].items():
            local[node] = (cx + dx, cy + dy)
        label_at[child] = _side(math.atan2(cy - hy, cx - hx))
    return local, radius


def _below(hub: str, held: dict[str, list[str]]) -> list[str]:
    """What `hub` holds, and what that holds, depth first."""
    found: list[str] = []
    for child in held.get(hub, []):
        found.append(child)
        found.extend(_below(child, held))
    return found


def _by_symbol(hub: str, held: dict[str, list[str]], is_symbol) -> dict[str, list[str]]:
    """`held` below `hub` with only `hub` and its symbols holding: what a
    call, a loop or a name holds is held by the symbol over it. Each level a
    glyph nests is a circle round circles, and the gaps between them; nested
    at every level the walker holds by, a file was a quarter dots."""
    out: dict[str, list[str]] = {}

    def gather(at: str, into: str) -> None:
        for child in held.get(at, []):
            out.setdefault(into, []).append(child)
            gather(child, child if is_symbol(child) and held.get(child) else into)

    gather(hub, hub)
    return out


def showcase_radius(depth: Any, dot: float) -> float:
    """A node's radius on a Showcase: a dot, wider for a file or a directory
    (`SHOWCASE_SCALE`)."""
    return dot * SHOWCASE_SCALE.get(depth, 1.0) if isinstance(depth, int) else dot


def showcase(graph: nx.DiGraph, dot: float = SHOWCASE_DOT, gap: float = SHOWCASE_GAP,
             nest: bool = True, sized: bool = True) -> dict[str, tuple[float, float]]:
    """A parse laid out as a showcase: the Map's directories and files, every
    node a dot -- a file's and a directory's a little wider
    (`showcase_radius`), and, `sized`, a symbol's or a member's by the source
    it stands for (`chars_scale`) -- each `gap` from the next, packed tight.

    A file is a disc of its code, as large as what it holds. With `nest`, each
    function and class is a glyph: all it holds packed round it, largest
    first and then kind by kind (`_glyph`), so two functions that hold alike
    look alike wherever they are; and the file packs its glyphs and the rest
    of its code the same way. Without, the file packs all of its code round
    it in that order. A file's outline is
    `SHOWCASE_PAD` half-dots past its disc, a directory's twice that, and two
    discs packed round one directory are a dot and three gaps apart. What
    nothing holds -- a module imported from outside -- is one more disc beside
    the map. Sets each node's `dot_scale`, its radius in dots, which the
    canvas draws it at (`streaming_renderer.ts`), and `label_at` as
    `code_map` does.
    """
    dot = max(float(dot), 0.1)
    gap = max(float(gap), 0.0)

    def radius_of(node: str) -> float:
        data = graph.nodes[node]
        depth = data.get("depth", 1)
        if depth in SHOWCASE_SCALE or not sized:
            return showcase_radius(depth, dot)
        return dot * chars_scale((data.get("meta") or {}).get("chars"))

    def key(node: str, radius: float):
        # Largest first, as circles pack densest: ordered by kind first, a
        # file was a third dots, and nearer two fifths this way.
        data = graph.nodes[node]
        return -round(radius, 6), GLYPH_ORDER.get(data.get("kind"), len(GLYPH_ORDER)), str(data.get("label", node))

    pad = SHOWCASE_PAD * dot

    def is_symbol(node: str) -> bool:
        return graph.nodes[node].get("kind") in GLYPH_KINDS

    def files(hub: str, held: dict[str, list[str]], label_at: dict[str, str]):
        code = _by_symbol(hub, held, is_symbol) if nest else {hub: _below(hub, held)}
        local, radius = _glyph(hub, code, radius_of, label_at, gap, key)
        label_at[hub] = "none"
        return local, radius + pad / 2

    for node in graph.nodes:
        graph.nodes[node]["dot_scale"] = radius_of(node) / dot
    return code_map(graph, radius_of=radius_of,
                    spacing=Spacing(gap, dot + 3 * gap, dot * 0.5, (pad, pad / 2), 2 * dot + 2 * gap),
                    files=files)
