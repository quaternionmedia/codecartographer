/**
 * Where each group outline's label goes.
 *
 * A label sits inside its outline, against the rim: at the top when that is
 * free, else at the first place round the rim where it covers no label
 * already placed and no node -- further in, then just outside the rim,
 * within the outlines' extent first and then anywhere round it. Inside, the
 * label's corners stay inside the rim, so a label too wide for its outline
 * is set outside it, never across it; the fit frames each label where it is
 * set (`fit.ts`'s `framedExtents`). Outlines that enclose much the same
 * nodes are nearly concentric -- a layout that does not gather a directory's
 * files together (Spring, Circular) gives every directory a circle round
 * most of the graph -- and labels all set at the top would be written over
 * one another and over the nodes.
 *
 * Pure: the renderer measures each label and draws it where this says.
 */

export interface OutlineLabel {
  /** The outline's centre and radius, in graph coordinates. */
  readonly cx: number;
  readonly cy: number;
  readonly r: number;
  /** The label's measured width and height. */
  readonly w: number;
  readonly h: number;
}

/** A label's centre. */
export interface LabelPlace {
  readonly x: number;
  readonly y: number;
}

/** A node's drawn extent, which no label should cover. */
export interface Obstacle {
  readonly x: number;
  readonly y: number;
  readonly r: number;
}

/** Space kept between a label and the rim, and round a label. */
const INSET = 6;
const GAP = 2;

/** Round the rim from the top, alternating sides, every 15°. */
const ANGLES = [0, ...Array.from({ length: 11 }, (_, i) => [(i + 1) * 15, -(i + 1) * 15]).flat(), 180]
  .map((d) => ((d - 90) * Math.PI) / 180);

interface Box { l: number; t: number; r: number; b: number }

function boxAt(p: LabelPlace, w: number, h: number): Box {
  return { l: p.x - w / 2, t: p.y - h / 2, r: p.x + w / 2, b: p.y + h / 2 };
}

function overlaps(a: Box, b: Box): boolean {
  return a.l < b.r + GAP && b.l < a.r + GAP && a.t < b.b + GAP && b.t < a.b + GAP;
}

/** Whether a label's box fits inside its outline at all, its corners inside the rim. */
function fitsInside(o: OutlineLabel): boolean {
  return Math.hypot(o.w / 2, o.h / 2) <= o.r - GAP;
}

/**
 * The label's centre at `angle`: its box inside the rim, its edge facing the
 * rim `INSET` in and its corners clear of the rim, `depth` label-heights
 * further in; null when the box is too big for the outline. At a negative
 * depth, its box just outside the rim.
 */
function placeAt(o: OutlineLabel, angle: number, depth: number): LabelPlace | null {
  const ux = Math.cos(angle);
  const uy = Math.sin(angle);
  const reach = Math.abs(ux) * (o.w / 2) + Math.abs(uy) * (o.h / 2);
  if (depth < 0) {
    const d = o.r + INSET + reach;
    return { x: o.cx + d * ux, y: o.cy + d * uy };
  }
  if (!fitsInside(o)) return null;
  // The furthest out each corner can go along (ux, uy) and stay within
  // r - GAP of the centre; the box goes as far as its nearest-bound corner.
  const room = o.r - GAP;
  let d = o.r - INSET - reach;
  for (const [kx, ky] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
    const along = ux * kx * (o.w / 2) + uy * ky * (o.h / 2);
    d = Math.min(d, -along + Math.sqrt(along * along - (o.w * o.w + o.h * o.h) / 4 + room * room));
  }
  d = Math.max(0, d - depth * o.h * 1.5);
  return { x: o.cx + d * ux, y: o.cy + d * uy };
}

/**
 * Inside the rim and further in, then outside it within the outlines'
 * extent (-1), then outside it anywhere (-2).
 */
const DEPTHS = [0, 1, 2, 3, -1, -2];

/**
 * Each label's centre, in the order given. The largest outlines are placed
 * first, so a directory's label keeps the top and what it holds moves round.
 * A label takes the first place clear of the other labels and of every node;
 * with none, the place clear of the labels that covers fewest nodes; with
 * none of those either, the top, inside the rim when it fits there and
 * outside it when not. Inside the rim is tried before outside it.
 */
export function placeOutlineLabels(
  outlines: readonly OutlineLabel[],
  nodes: readonly Obstacle[] = [],
): LabelPlace[] {
  const nodeBoxes = nodes.map((n) => ({ l: n.x - n.r, t: n.y - n.r, r: n.x + n.r, b: n.y + n.r }));
  const extent: Box = {
    l: Math.min(...outlines.map((o) => o.cx - o.r)),
    t: Math.min(...outlines.map((o) => o.cy - o.r)),
    r: Math.max(...outlines.map((o) => o.cx + o.r)),
    b: Math.max(...outlines.map((o) => o.cy + o.r)),
  };
  const within = (b: Box) => b.l >= extent.l && b.t >= extent.t && b.r <= extent.r && b.b <= extent.b;
  const order = outlines.map((_, i) => i).sort((a, b) => outlines[b].r - outlines[a].r || a - b);
  const placed: Box[] = [];
  const places: LabelPlace[] = new Array(outlines.length);
  for (const i of order) {
    const o = outlines[i];
    let chosen: LabelPlace | null = null;
    let fewest = Infinity;
    for (const depth of DEPTHS) {
      for (const angle of ANGLES) {
        const p = placeAt(o, angle, depth);
        if (!p) break;
        const box = boxAt(p, o.w, o.h);
        if (depth === -1 && !within(box)) continue;
        if (depth === -2 && within(box)) continue;
        if (placed.some((other) => overlaps(box, other))) continue;
        const covered = nodeBoxes.filter((n) => overlaps(box, n)).length;
        if (covered < fewest) {
          fewest = covered;
          chosen = p;
        }
        if (covered === 0) break;
      }
      if (fewest === 0) break;
    }
    places[i] = chosen ?? placeAt(o, ANGLES[0], fitsInside(o) ? 0 : -1)!;
    placed.push(boxAt(places[i], o.w, o.h));
  }
  return places;
}
