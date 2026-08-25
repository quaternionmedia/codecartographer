/**
 * What a legend says, separated from how it is drawn.
 *
 * **THE LESSON THIS FILE IS BUILT ON.** rad's integration review found three
 * verbs that were one `fitView()` call wearing three labels, and the suite
 * stayed green because the spy sat at the operation boundary and never read an
 * operation body. Op bodies were application code that no test build compiled.
 * A legend has the same shape of risk: the DOM is easy to assert and says
 * nothing, while the interesting question — *does the key describe the graph
 * that was actually drawn* — lives in these two functions.
 *
 * So they are pure, DOM-free, and compiled by `tsconfig.pure.json` for
 * `node --test`. `legend_extension.ts` renders what they return and decides
 * nothing itself.
 */

/** A node kind, and the mark that stands for it. */
export interface NodeMark {
  kind: string;
  shape: string | undefined;
  color: string;
  count: number;
}

/** An edge kind, and the mark that stands for it. */
export interface EdgeMark {
  kind: string;
  color: string;
  count: number;
}

/** The fields a mark is derived from. Deliberately narrower than `GraphNode`. */
export interface MarkableNode {
  kind?: unknown;
  shape?: unknown;
  color?: unknown;
}

export interface MarkableEdge {
  kind?: unknown;
  label?: unknown;
  color?: unknown;
}

export const DEFAULT_NODE_KIND = 'node';
export const DEFAULT_NODE_COLOR = 'steelblue';
export const DEFAULT_EDGE_KIND = 'edge';
export const DEFAULT_EDGE_COLOR = '#555';

/** `async_function` -> `Async function`. Display only; never a key. */
export function readable(kind: string): string {
  const spaced = kind.replace(/[_-]+/g, ' ').trim();
  return spaced ? spaced[0].toUpperCase() + spaced.slice(1) : kind;
}

/**
 * The distinct node marks present, most common first.
 *
 * **KEYED ON KIND *AND* MARK.** One kind drawn two ways is two rows: a reader
 * matching a swatch against a node needs the row that matches what is on
 * screen, and collapsing them yields a key that is right on average and wrong
 * in front of them.
 *
 * **A NODE WITH NO KIND IS COUNTED, NOT DROPPED.** The counts have to add up to
 * the picture, or the key becomes a second, quieter claim about how much of the
 * graph the reader is seeing.
 */
export function nodeMarks(nodes: readonly MarkableNode[]): NodeMark[] {
  const seen = new Map<string, NodeMark>();
  for (const node of nodes) {
    const kind = typeof node.kind === 'string' && node.kind ? node.kind : DEFAULT_NODE_KIND;
    const shape = typeof node.shape === 'string' && node.shape ? node.shape : undefined;
    const color = typeof node.color === 'string' && node.color ? node.color : DEFAULT_NODE_COLOR;
    const key = `${kind}|${shape ?? ''}|${color}`;
    const found = seen.get(key);
    if (found) found.count += 1;
    else seen.set(key, { kind, shape, color, count: 1 });
  }
  return [...seen.values()].sort((a, b) => b.count - a.count);
}

/**
 * The distinct edge marks present, most common first.
 *
 * **`kind` IS READ BEFORE `label`.** A label is what one edge says about itself
 * and is often unique per edge, which would produce a key with one row per
 * edge — technically accurate and useless. `kind` is the field Q3 adds for
 * exactly this: a fact about the class of relation rather than the instance.
 */
export function edgeMarks(edges: readonly MarkableEdge[]): EdgeMark[] {
  const seen = new Map<string, EdgeMark>();
  for (const edge of edges) {
    const named =
      (typeof edge.kind === 'string' && edge.kind) ||
      (typeof edge.label === 'string' && edge.label) ||
      DEFAULT_EDGE_KIND;
    const color = typeof edge.color === 'string' && edge.color ? edge.color : DEFAULT_EDGE_COLOR;
    const key = `${named}|${color}`;
    const found = seen.get(key);
    if (found) found.count += 1;
    else seen.set(key, { kind: named, color, count: 1 });
  }
  return [...seen.values()].sort((a, b) => b.count - a.count);
}

/** Total nodes and edges the marks account for — the key's own arithmetic. */
export function marksCover(
  marks: readonly { count: number }[],
): number {
  return marks.reduce((total, mark) => total + mark.count, 0);
}
