/**
 * rad core — geometry. Platform-free: no DOM, no app imports.
 *
 * One polar convention (contract §2): angle origin −90° (12 o'clock),
 * clockwise. Radii in density-independent units.
 *
 * Ported from quaternionmedia/rad @ d362abd. Semantics are fixed by
 * conformance/vectors.json v0.4.0 — see core/README.md.
 */
import type { Geometry } from './types.js';

export const GEOM: Geometry = {
  startDeg: -90,
  clockwise: true,
  r0: 36,
  r1: 108,
  cancelScale: 1.35,
  longPressMs: 350,
  slop: 10,
};

/** Contract §1; the resolver enforces it rather than a reviewer noticing. */
export const MAX_ITEMS = 8;

/**
 * Ring fitting constants.
 *
 * `bandMin` is the band width at which a wedge at N=8 still clears a 44-unit
 * touch target. `topInset`/`bottomInset` reserve host chrome.
 */
export const RING = { bandMin: 56, margin: 8, topInset: 64, bottomInset: 40 };

/**
 * The outward cancel bound. Beyond it there is no target: a press, a release
 * or a highlight at r > r_cancel is a cancel in BOTH commit styles.
 *
 * Without it the committing region is unbounded in one style and bounded in
 * the other, so the same point commits or cancels depending on how the menu
 * was opened.
 */
export function rCancel(g: Geometry = GEOM): number {
  return g.r1 * g.cancelScale;
}

/**
 * The committing band, identical in both commit styles (contract §2/§3).
 * Inward of r0 is the dead-zone cancel; outward of r_cancel is its mirror.
 */
export function inBand(r: number, g: Geometry = GEOM): boolean {
  return r > g.r0 && r <= rCancel(g);
}

/**
 * Fit the ring to a viewport.
 *
 * Shrinks r1 *toward* the band minimum (r0 + bandMin) when the viewport
 * cannot hold the natural radius. Shrinking toward a minimum is not
 * shrinking below one, and it is strictly better than overflowing.
 */
export function fitRing(vw: number, vh: number, g: Geometry = GEOM): { r0: number; r1: number } {
  const avail = Math.min(vw, vh) / 2 - RING.margin;
  return { r0: g.r0, r1: Math.max(g.r0 + RING.bandMin, Math.min(g.r1, avail)) };
}

/**
 * Keep the ring on screen by shifting the centre inward.
 *
 * When the viewport cannot hold the ring on an axis the clamp's bounds invert.
 * A naive clamp resolves that by taking one bound, which pushes the ring off
 * the opposite edge; centring keeps the overflow symmetric, so no wedge is
 * less reachable than another. The axes are decided independently — a
 * viewport may hold the ring horizontally and not vertically, and usually does.
 */
export function clampRingCentre(
  x: number,
  y: number,
  vw: number,
  vh: number,
  r1: number,
): { x: number; y: number } {
  const m = r1 + 24;
  const axis = (v: number, lo: number, hi: number, extent: number) =>
    lo > hi ? extent / 2 : Math.min(Math.max(v, lo), hi);
  return {
    x: axis(x, m, vw - m, vw),
    y: axis(y, Math.max(m, RING.topInset), vh - m - RING.bottomInset, vh),
  };
}

export function normDeg(d: number): number {
  return ((d % 360) + 360) % 360;
}

/** Pure, and shared with the conformance vectors. */
export function angleToIndex(thetaDeg: number, n: number, startDeg: number = GEOM.startDeg): number {
  const rel = normDeg(thetaDeg - startDeg);
  return Math.round(rel / (360 / n)) % n;
}

export function itemCenterDeg(i: number, n: number, startDeg: number = GEOM.startDeg): number {
  return startDeg + i * (360 / n);
}

/**
 * Wedge path. Pure trigonometry that a host writing its own renderer needs —
 * exported so nobody reimplements the large-arc flag.
 */
export function arcPath(
  cx: number,
  cy: number,
  r0: number,
  r1: number,
  a0: number,
  a1: number,
): string {
  const p = (r: number, a: number): [number, number] => [
    cx + r * Math.cos((a * Math.PI) / 180),
    cy + r * Math.sin((a * Math.PI) / 180),
  ];
  const [x0, y0] = p(r1, a0);
  const [x1, y1] = p(r1, a1);
  const [x2, y2] = p(r0, a1);
  const [x3, y3] = p(r0, a0);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M${x0},${y0} A${r1},${r1} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${r0},${r0} 0 ${large} 0 ${x3},${y3} Z`;
}

/**
 * Screen delta → ring-polar. The ~20 lines the integration standard §3 says
 * every host writes; shipped here so this host's copy is the reference one.
 */
export function toPolar(dx: number, dy: number): { r: number; thetaDeg: number } {
  return {
    r: Math.hypot(dx, dy),
    thetaDeg: (Math.atan2(dy, dx) * 180) / Math.PI,
  };
}
