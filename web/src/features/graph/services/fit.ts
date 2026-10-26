/**
 * Where the view goes to frame what is drawn.
 *
 * The canvas fits the graph when a stream ends, on the canvas ring's Fit, on
 * View ▸ Focus and on the Chrestomathy census's show. Each hands this the
 * extents that enclose what it wants framed, in graph coordinates: a node's
 * circle, the box of its label while labels are shown, and a group outline's
 * circle and its label's box (`framedExtents`). The answer is the zoom
 * transform that sets their bounding box in the middle of the viewport, as
 * large as fits inside a margin.
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

/** What a fit frames: a circle, or a box such as a label's. */
export type Extent = Circle | Box;

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

// The whole corpus, every project's code in its family, is framed at about a
// thirtieth: at a twentieth, the zoom limit was, it was framed cut off.
export const FIT_DEFAULTS: FitOptions = { margin: 24, minScale: 0.01, maxScale: 4 };

/** The box an extent covers; null when it has no finite place. */
function boxOf(extent: Extent): Box | null {
  if ('r' in extent) {
    const { x, y, r } = extent;
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    const reach = Number.isFinite(r) ? Math.max(0, r) : 0;
    return { minX: x - reach, minY: y - reach, maxX: x + reach, maxY: y + reach };
  }
  const { minX, minY, maxX, maxY } = extent;
  return [minX, minY, maxX, maxY].every(Number.isFinite) && minX <= maxX && minY <= maxY ? extent : null;
}

/** The box enclosing every extent; null when none has a finite place. */
export function boundsOf(extents: readonly Extent[]): Box | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const extent of extents) {
    const box = boxOf(extent);
    if (!box) continue;
    minX = Math.min(minX, box.minX);
    minY = Math.min(minY, box.minY);
    maxX = Math.max(maxX, box.maxX);
    maxY = Math.max(maxY, box.maxY);
  }
  return minX === Infinity ? null : { minX, minY, maxX, maxY };
}

/**
 * The transform that centres the extents' bounding box in a viewport of
 * `width` × `height`, scaled to fill it inside `margin` on the tighter axis and
 * held within the scale limits. Null when there is nothing to frame.
 */
export function fitTransform(
  extents: readonly Extent[],
  viewport: { readonly width: number; readonly height: number },
  options: FitOptions = FIT_DEFAULTS,
): ZoomTransform | null {
  const box = boundsOf(extents);
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

/** A node as a fit sees it, in graph coordinates. */
export interface FramedNode {
  readonly id: string;
  readonly x: number;
  readonly y: number;
  /** How far its shape reaches from its centre. */
  readonly reach: number;
  /**
   * The box its label is drawn in, while its label is shown; null while it
   * is not. A label is centred under its node at any width, so a long one at
   * the graph's edge reaches far past its node.
   */
  readonly label: Box | null;
}

/** A group outline as a fit sees it: its circle, drawn around the node `nodeId`. */
export interface FramedOutline extends Circle {
  readonly nodeId: string;
  /**
   * The box its label is drawn in, when it has one. A label too wide for a
   * small outline is set outside it (`outline_labels.ts`), past the circle.
   */
  readonly label?: Box | null;
}

/**
 * What a fit of `nodes` frames: each node's extent and its label's box while
 * it is shown, and the outline drawn around any of them with its label.
 *
 * A hidden node is left out, label and all, and so is an outline that holds
 * only hidden nodes: its own node and every node `holds` names inside it.
 * Hide draws a node at opacity 0 and keeps it, so the renderer still holds
 * it, and a frame that counted it would be centred off what is drawn.
 */
export function framedExtents(
  nodes: readonly FramedNode[],
  outlines: readonly FramedOutline[],
  holds: (nodeId: string) => readonly string[] = () => [],
  hidden: (nodeId: string) => boolean = () => false,
): Extent[] {
  const ids = new Set(nodes.map((n) => n.id));
  const extents: Extent[] = [];
  for (const n of nodes) {
    if (hidden(n.id)) continue;
    extents.push({ x: n.x, y: n.y, r: n.reach });
    if (n.label) extents.push(n.label);
  }
  for (const o of outlines) {
    if (!ids.has(o.nodeId)) continue;
    if (hidden(o.nodeId) && holds(o.nodeId).every(hidden)) continue;
    extents.push({ x: o.x, y: o.y, r: o.r });
    if (o.label) extents.push(o.label);
  }
  return extents;
}
