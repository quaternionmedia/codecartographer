/**
 * How the vis-network ("Gravis") renderer draws a node: which of its shapes,
 * and in what colour.
 *
 * **THE SECOND CANVAS DRAWS THE FIRST ONE'S MARKS.** vis-network has no
 * polygon of N sides and no rectangle, so `ngon` and `rectangle` fell through
 * to a dot -- every record and every impl drawn as whatever had no shape at all
 * -- and it ignored "Color By". The shapes vis-network draws natively stay
 * native; the two it lacks are drawn as `custom`, from the same `nodePath` the
 * D3 canvas and its key use, so all three draw one mark. The colour is the D3
 * canvas's rule: a layer's colour in layer mode where the server sent one.
 *
 * Pure, so `node --test` holds it; `gravis_renderer.ts` only applies it.
 */

// `.js`, so the build `node --test` reads resolves it as the bundler does.
import { nodeSides, polygonSides } from './node_shapes.js';

const NATIVE: Record<string, string> = {
  circle: 'dot',
  square: 'square',
  triangle: 'triangle',
  diamond: 'diamond',
  hexagon: 'hexagon',
  star: 'star',
};

/** Shapes `node_shapes` draws that vis-network does not, drawn with `nodePath`. */
const DRAWN = new Set(['ngon', 'rectangle']);

export interface VisLook {
  /** A vis-network shape name, or `custom` for one drawn with `nodePath`. */
  shape: string;
  /** For `custom`: the `node_shapes` shape and, for a record, its side count. */
  path?: { shape: string; sides?: number };
  /** The fill, before opacity; undefined leaves vis-network's default. */
  color: string | undefined;
}

export interface VisNode {
  shape?: unknown;
  meta?: unknown;
  color?: unknown;
  layer_color?: unknown;
}

export function visLook(node: VisNode, colorBy: string | undefined): VisLook {
  const shape = typeof node.shape === 'string' ? node.shape.toLowerCase() : '';
  const layered = colorBy === 'layer' && typeof node.layer_color === 'string' && node.layer_color;
  const color = layered ? (node.layer_color as string)
    : typeof node.color === 'string' && node.color ? node.color : undefined;
  if (DRAWN.has(shape)) {
    const sides = shape === 'ngon' ? polygonSides(nodeSides(node)) : undefined;
    return { shape: 'custom', path: sides === undefined ? { shape } : { shape, sides }, color };
  }
  return { shape: NATIVE[shape] ?? 'dot', color };
}
