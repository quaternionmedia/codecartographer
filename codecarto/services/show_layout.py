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

Each ring member is given `label_at`, the side its name goes on -- outward
from its ring -- and a node whose outline already names it is given `none`.

Only positions and `label_at` change. Which nodes there are, what they say and
which edges join them is the graph's, and is not touched here.
"""

from __future__ import annotations

import math
from typing import Any

# A node's drawn radius at the canvas's default node size, by depth, as
# `web/src/features/graph/services/depth_scale.ts` draws it.
NODE_R = {0: 12.0, 1: 7.2, 2: 4.0}
LEAF_R = 4.0
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


def _depth(node: dict[str, Any]) -> int | None:
    depth = node["metadata"].get("depth")
    return int(depth) if isinstance(depth, (int, float)) else None


def _children(gjgf: dict[str, Any]) -> dict[str, list[str]]:
    """What each node holds: `contains` edges one depth down, in edge order."""
    nodes = gjgf["nodes"]
    held: dict[str, list[str]] = {}
    for edge in gjgf["edges"]:
        if (edge.get("metadata") or {}).get("kind") != "contains":
            continue
        source, target = edge["source"], edge["target"]
        if source not in nodes or target not in nodes:
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
        if not items:
            return [], 0.0
        # A subgroup's arc also holds the names its neighbours put outward.
        arcs = [SPACING if r <= NODE_R[0] else 2 * r + GROUP_GAP for _, r in items]
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

    def group(self, hub: str) -> tuple[dict[str, tuple[float, float]], float]:
        """A group laid out around its own node at the origin, and its outline's radius."""
        items: list[tuple[str, float]] = []
        inner: dict[str, tuple[dict[str, tuple[float, float]], float]] = {}
        for child in self.held.get(hub, []):
            if self.held.get(child):
                inner[child] = self.group(child)
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


def _rows(circles: list[tuple[str, float]]) -> dict[str, tuple[float, float]]:
    """Circles in rows, largest first, about `ASPECT` times wider than tall, centred."""
    if not circles:
        return {}
    ordered = sorted(circles, key=lambda c: -c[1])
    area = sum((2 * r + GAP) ** 2 for _, r in ordered)
    width = max(max(2 * r for _, r in ordered), math.sqrt(area * ASPECT))
    rows: list[list[tuple[str, float]]] = [[]]
    used = 0.0
    for circle in ordered:
        span = 2 * circle[1] + (GAP if rows[-1] else 0.0)
        if rows[-1] and used + span > width:
            rows.append([])
            used, span = 0.0, 2 * circle[1]
        rows[-1].append(circle)
        used += span
    centres: dict[str, tuple[float, float]] = {}
    y = 0.0
    for row in rows:
        height = max(2 * r for _, r in row)
        row_width = sum(2 * r for _, r in row) + GAP * (len(row) - 1)
        x = -row_width / 2
        for name, r in row:
            centres[name] = (x + r, y + height / 2)
            x += 2 * r + GAP
        y += height + GAP
    shift = (y - GAP) / 2
    return {name: (cx, cy - shift) for name, (cx, cy) in centres.items()}


def _push_out(free: dict[str, tuple[float, float]],
              outlines: list[tuple[float, float, float]]) -> None:
    """Move each free node out of every outline, and apart from the others."""
    names = sorted(free)
    for _ in range(12):
        moved = False
        for i, name in enumerate(names):
            x, y = free[name]
            for cx, cy, r in outlines:
                dx, dy = x - cx, y - cy
                gap = math.hypot(dx, dy)
                need = r + FREE_CLEAR
                if gap < need:
                    if gap < 1e-6:
                        dx, dy, gap = math.cos(i), math.sin(i), 1.0
                    x, y = cx + dx / gap * need, cy + dy / gap * need
                    moved = True
            for other in names[:i]:
                ox, oy = free[other]
                dx, dy = x - ox, y - oy
                gap = math.hypot(dx, dy)
                if gap < FREE_APART:
                    if gap < 1e-6:
                        dx, dy, gap = 1.0, 0.0, 1.0
                    x, y = ox + dx / gap * FREE_APART, oy + dy / gap * FREE_APART
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
        free_ids = [n for n in nodes if n not in placed]
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
        _push_out(free, outlines)
        placed.update(free)
        for name in free:
            packer.label_at.setdefault(name, "below")

    for node_id, node in nodes.items():
        x, y = placed.get(node_id, (node["metadata"].get("x", 0.0), node["metadata"].get("y", 0.0)))
        node["metadata"]["x"] = float(x)
        node["metadata"]["y"] = float(y)
        if node_id in packer.label_at:
            node["metadata"]["label_at"] = packer.label_at[node_id]
    return gjgf
