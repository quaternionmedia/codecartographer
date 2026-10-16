/**
 * Where the view goes to frame what is drawn.
 *
 * The canvas fits the graph when a stream ends, on the canvas ring's Fit, on
 * View ▸ Focus and on the Chrestomathy census's show. Each hands this the
 * circles that enclose what it wants framed, in graph coordinates: a node's
 * extent, and a group outline's circle. The answer is the zoom transform that
 * sets their bounding box in the middle of the viewport, as large as fits
 * inside a margin.
 *
 * The box, not the nodes' average: a graph with more nodes on one side has its
 * average off the middle of what is drawn, and a frame centred there runs the
 * other side, and the group outlines around it, off the canvas.
 */

/** A circle in graph coordinates: a node's extent, or a group outline. */
export interface Circle {
  readonly x: number;
  readonly y: number;
  readonly r: number;
}

export interface Box {
  readonly minX: number;
  readonly minY: number;
  readonly maxX: number;
  readonly maxY: number;
}

/** d3's zoom transform: screen = graph × k + (x, y). */
export interface ZoomTransform {
  readonly x: number;
  readonly y: number;
  readonly k: number;
}

export interface FitOptions {
  /** Screen pixels left clear on every side. */
  readonly margin: number;
  /** The zoom's own lower limit. */
  readonly minScale: number;
  /**
   * The furthest a fit zooms in. One small node framed alone would otherwise
   * fill the canvas, and the reader loses where it is.
   */
  readonly maxScale: number;
}

export const FIT_DEFAULTS: FitOptions = { margin: 24, minScale: 0.05, maxScale: 4 };

/** The box enclosing every circle; null when none has a finite place. */
export function boundsOf(circles: readonly Circle[]): Box | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const { x, y, r } of circles) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    const reach = Number.isFinite(r) ? Math.max(0, r) : 0;
    minX = Math.min(minX, x - reach);
    minY = Math.min(minY, y - reach);
    maxX = Math.max(maxX, x + reach);
    maxY = Math.max(maxY, y + reach);
  }
  return minX === Infinity ? null : { minX, minY, maxX, maxY };
}

/**
 * The transform that centres the circles' bounding box in a viewport of
 * `width` × `height`, scaled to fill it inside `margin` on the tighter axis and
 * held within the scale limits. Null when there is nothing to frame.
 */
export function fitTransform(
  circles: readonly Circle[],
  viewport: { readonly width: number; readonly height: number },
  options: FitOptions = FIT_DEFAULTS,
): ZoomTransform | null {
  const box = boundsOf(circles);
  if (!box) return null;
  const roomX = Math.max(1, viewport.width - 2 * options.margin);
  const roomY = Math.max(1, viewport.height - 2 * options.margin);
  const spanX = box.maxX - box.minX;
  const spanY = box.maxY - box.minY;
  const fits = Math.min(spanX > 0 ? roomX / spanX : Infinity, spanY > 0 ? roomY / spanY : Infinity);
  const k = Math.min(options.maxScale, Math.max(options.minScale, Number.isFinite(fits) ? fits : options.maxScale));
  const cx = (box.minX + box.maxX) / 2;
  const cy = (box.minY + box.maxY) / 2;
  return { x: viewport.width / 2 - k * cx, y: viewport.height / 2 - k * cy, k };
}
