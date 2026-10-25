/**
 * The one place a node's `shape` becomes an SVG path.
 *
 * **A LEGEND THAT DRAWS ITS OWN SHAPES IS A LEGEND THAT CAN LIE.** The legend
 * this project shipped hard-coded six `<path d="...">` strings describing the
 * shapes it believed the canvas used. Nothing tied the two together, so a
 * change to either side produced a key that confidently named the wrong thing —
 * the failure a legend exists to prevent. Both sides call this instead.
 *
 * `s` is the half-extent: a shape drawn at `s` fits a box of `2s`, centred on
 * the origin, so a caller can place it with a translate and nothing else.
 */
export function nodePath(shape: string | undefined, s: number, sides?: number): string {
  switch (shape) {
    case 'ngon':
      return polygonPath(s, sides);
    case 'square':
      return `M ${-s} ${-s} L ${s} ${-s} L ${s} ${s} L ${-s} ${s} Z`;
    case 'rectangle': {
      // Wider than tall. It drew `square`'s path, so an impl, a foreign block
      // and a linker section were each a class's or a field's mark.
      const h = s * 0.55;
      return `M ${-s} ${-h} L ${s} ${-h} L ${s} ${h} L ${-s} ${h} Z`;
    }
    case 'triangle': {
      const h = s * 1.5;
      return `M 0 ${-h} L ${s} ${h} L ${-s} ${h} Z`;
    }
    case 'diamond':
      return `M 0 ${-s} L ${s} 0 L 0 ${s} L ${-s} 0 Z`;
    case 'hexagon': {
      const a = s * 0.866;
      const b = s * 0.5;
      return `M 0 ${-s} L ${a} ${-b} L ${a} ${b} L 0 ${s} L ${-a} ${b} L ${-a} ${-b} Z`;
    }
    default:
      return `M ${s} 0 A ${s} ${s} 0 1 1 ${-s} 0 A ${s} ${s} 0 1 1 ${s} 0 Z`;
  }
}

/** `meta.sides`, for the `ngon` shape the C and Rust parsers draw records with. */
export function nodeSides(node: { meta?: unknown }): number | undefined {
  const meta = node.meta as { sides?: unknown } | undefined;
  return typeof meta?.sides === 'number' ? meta.sides : undefined;
}

/** The path the canvas draws a node with, at half-extent `s`. */
export function canvasPath(node: { shape?: unknown; meta?: unknown }, s: number): string {
  return nodePath(typeof node.shape === 'string' ? node.shape : undefined, s, nodeSides(node));
}

/**
 * Every shape name `nodePath` draws distinctly -- no two the same outline at
 * any size, and an `ngon` of any side count none of the others.
 *
 * Exported so a test can assert the set is covered rather than trusting the
 * switch to be complete — an unknown shape falls through to a circle, which is
 * indistinguishable from a node that asked for one. The server's tests read
 * this list from this file to hold every construct's look to it.
 */
export const KNOWN_SHAPES = [
  'square',
  'rectangle',
  'triangle',
  'diamond',
  'hexagon',
  'ngon',
  'circle',
] as const;

/**
 * How many sides a record's polygon is drawn with: the count it was sent,
 * rounded, from three up, and a pentagon when it was sent none.
 *
 * **THE RANGE IS THE SERVER'S, STATED ONCE.** `construct_service.NGON_SIDES`
 * clamps every count a parser derives; this side restated it as 3..12 while
 * the parsers clamped 3..10, two numbers for one rule. The canvas now draws the
 * count it is sent, and three is not a range but where a polygon starts. With
 * no count it is a pentagon, deliberately not six: a hexagon is already a shape
 * of its own here.
 */
export function polygonSides(sides?: number): number {
  if (typeof sides !== 'number' || !Number.isFinite(sides)) return 5;
  return Math.max(3, Math.round(sides));
}

/**
 * A regular polygon of `sides` sides, turned a quarter of a side from upright.
 *
 * **THE C PARSER ASKED FOR THIS AND THE CANVAS DREW A CIRCLE.** Its structs and
 * unions carry `shape: 'ngon'` with `meta.sides` set from the field count -- the
 * c-visualizer's grammar, where a record's outline says how many parts it has --
 * and until this case existed every one of them fell through to the default.
 * The construct vocabulary gives Rust's records the same shape, so a C struct
 * and a Rust struct of seven fields are one mark.
 *
 * **WHY TURNED.** Upright -- a vertex at the top -- four sides is exactly
 * `diamond` and six exactly `hexagon`, so every four-field struct -- and every
 * C union and Rust unit struct, which the server gave four sides for want of a
 * count -- was a function's mark. Flat-topped, four sides is `square`. Upright
 * and flat-topped are a whole number of half sides apart, so a quarter turn is
 * neither at any count: the record leans, and no other shape does.
 */
export function polygonPath(s: number, sides?: number): string {
  const n = polygonSides(sides);
  const turn = Math.PI / (2 * n);
  const points: string[] = [];
  for (let i = 0; i < n; i++) {
    const angle = -Math.PI / 2 + turn + (2 * Math.PI * i) / n;
    points.push(`${(s * Math.cos(angle)).toFixed(2)} ${(s * Math.sin(angle)).toFixed(2)}`);
  }
  return `M ${points.join(' L ')} Z`;
}
