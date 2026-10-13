/**
 * What the radial menu's View → Source and View → Info say about a node.
 *
 * **EVERY USE SAYS IT.** Both verbs once spoke through a once-per-session
 * hint, so the second Info, and every Info after it, opened the menu,
 * committed, and showed nothing -- from the menu, indistinguishable from
 * working, which is the defect rad's integration record says a host must not
 * ship. What they say is decided here, where a test can read it; the host only
 * shows it.
 */

export interface InfoNode {
  id: string;
  label?: unknown;
  kind?: unknown;
  language?: unknown;
  file?: unknown;
  line?: unknown;
  construct_name?: unknown;
  meta?: unknown;
  [key: string]: unknown;
}

/** `src/main.rs:12`, or null for a node that came from no file. */
export function sourceLine(node: InfoNode): string | null {
  if (typeof node.file !== 'string' || !node.file) return null;
  const line = typeof node.line === 'number' && node.line > 0 ? `:${node.line}` : '';
  return `${node.file}${line}`;
}

/**
 * `delay · rust function · Function (memory.unsafe) · src/main.rs:12` -- name,
 * what its parser called it, what it is across languages and what else it is,
 * where.
 */
export function infoLine(node: InfoNode): string {
  const parts = [String(node.label ?? node.id)];
  const what = [node.language, node.kind].filter((x) => typeof x === 'string' && x).join(' ');
  if (what) parts.push(what);
  const facets = (node.meta as { facets?: unknown } | undefined)?.facets;
  const also = Array.isArray(facets) && facets.length ? ` (${facets.join(', ')})` : '';
  if (typeof node.construct_name === 'string') parts.push(node.construct_name + also);
  const source = sourceLine(node);
  if (source) parts.push(source);
  return parts.join(' · ');
}
