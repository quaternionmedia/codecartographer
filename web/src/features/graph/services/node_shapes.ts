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
    case 'rectangle':
      return `M ${-s} ${-s} L ${s} ${-s} L ${s} ${s} L ${-s} ${s} Z`;
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

/**
 * Every shape name `nodePath` draws distinctly.
 *
 * Exported so a test can assert the set is covered rather than trusting the
 * switch to be complete — an unknown shape falls through to a circle, which is
 * indistinguishable from a node that asked for one.
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
 * A regular polygon of `sides` sides, a vertex at the top.
 *
 * **THE C PARSER ASKED FOR THIS AND THE CANVAS DREW A CIRCLE.** Its structs and
 * unions carry `shape: 'ngon'` with `meta.sides` set from the field count -- the
 * c-visualizer's grammar, where a record's outline says how many parts it has --
 * and until this case existed every one of them fell through to the default.
 * The construct vocabulary gives Rust's records the same shape, so a C struct
 * and a Rust struct of seven fields are now one mark.
 *
 * Clamped to 3..12, as the parser contract says. With no count it is a
 * pentagon, deliberately not six: a hexagon is already a shape of its own here.
 */
export function polygonPath(s: number, sides?: number): string {
  const n = Math.min(12, Math.max(3, Math.round(sides ?? 5)));
  const points: string[] = [];
  for (let i = 0; i < n; i++) {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / n;
    points.push(`${(s * Math.cos(angle)).toFixed(2)} ${(s * Math.sin(angle)).toFixed(2)}`);
  }
  return `M ${points.join(' L ')} Z`;
}
