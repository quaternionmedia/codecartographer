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
export function nodePath(shape: string | undefined, s: number): string {
  switch (shape) {
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
  'circle',
] as const;
