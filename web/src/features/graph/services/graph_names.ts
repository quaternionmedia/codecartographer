/**
 * Whether a graph is drawn as a map of names.
 *
 * A showgraph is, and so is any graph whose metadata says its names are what
 * it is for (`names: true`). Every other graph keeps its names off until the
 * reader turns them on in Graph Settings: a parsed repository has thousands.
 *
 * Pure: no DOM and no import, so `web/tests/pure/graph-names.test.mjs` asserts
 * it under node.
 */
export function namedGraph(metadata: { kind?: unknown; names?: unknown } | null | undefined): boolean {
  return metadata?.kind === 'show' || metadata?.names === true;
}
