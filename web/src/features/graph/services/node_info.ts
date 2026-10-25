/**
 * What the radial menu's View → Info says about a node, and where View →
 * Source and a double-click take the reader.
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

/** `src/main.rs:12`, `src/main.rs` with no line, or null for a node that came from no file. */
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

/**
 * Where View → Source and a double-click on a node take the reader: the file's
 * page on its forge, at the node's line when one is known and at the top of
 * the file when not; or, for a file with no page -- one read from disk or
 * uploaded -- the file and line to name beside the node.
 *
 * Null for a node from no file. That is the one rule for whether either route
 * is offered.
 */
export type SourceTarget =
  | { kind: 'forge'; href: string }
  | { kind: 'local'; text: string };

/** An edge as the renderer holds it: its kind flat, or under gJGF's `metadata`. */
export interface InfoEdge {
  source: unknown;
  target: unknown;
  kind?: unknown;
  metadata?: unknown;
}

/** The graph a node is drawn in, as far as finding its file needs it. */
export interface SourceGraph {
  nodes: ReadonlyMap<string, InfoNode>;
  edges: readonly InfoEdge[];
}

const RAW_GITHUB = /^https:\/\/raw\.githubusercontent\.com\/([^/]+\/[^/]+)\/([^/]+)\/(.+)$/;
const WEB_URL = /^https?:\/\//;

/** The kinds a node hangs from what holds it by; compound_layout.ts reads the same two. */
const CONTAINS = new Set(['contains', 'field_of']);

function endId(end: unknown): string | undefined {
  if (typeof end === 'string') return end;
  const id = (end as { id?: unknown } | null | undefined)?.id;
  return typeof id === 'string' ? id : undefined;
}

function isContainment(edge: InfoEdge): boolean {
  if (CONTAINS.has(edge.kind as string)) return true;
  return CONTAINS.has((edge.metadata as { kind?: unknown } | undefined)?.kind as string);
}

/**
 * The file node a node is drawn inside, up the graph's containment edges: the
 * node itself when it is one, and null when no file node holds it.
 */
export function containingFile(node: InfoNode, graph: SourceGraph): InfoNode | null {
  const parentOf = new Map<string, string>();
  for (const edge of graph.edges) {
    if (!isContainment(edge)) continue;
    const from = endId(edge.source);
    const to = endId(edge.target);
    if (from && to && !parentOf.has(to)) parentOf.set(to, from);
  }
  const seen = new Set<string>();
  let at: InfoNode | undefined = node;
  while (at && !seen.has(at.id)) {
    if (at.kind === 'file') return at;
    seen.add(at.id);
    const up = parentOf.get(at.id);
    at = up === undefined ? undefined : graph.nodes.get(up);
  }
  return null;
}

/**
 * A node that names its file by a URL is opened there. One that does not --
 * a C symbol names its file's stem, a Python symbol `module.py` -- is opened
 * where the file node it is drawn inside says the file is, at its own line;
 * with no file node above it, it is named by its own `file`.
 */
export function sourceTarget(node: InfoNode, graph?: SourceGraph): SourceTarget | null {
  if (typeof node.file !== 'string' || !node.file) return null;
  let file = node.file;
  if (!WEB_URL.test(file) && graph) {
    const held = containingFile(node, graph)?.file;
    if (typeof held === 'string' && held) file = held;
  }
  const line = typeof node.line === 'number' && node.line > 0 ? node.line : 0;
  const raw = file.match(RAW_GITHUB);
  if (raw) {
    const anchor = line ? `#L${line}` : '';
    return { kind: 'forge', href: `https://github.com/${raw[1]}/blob/${raw[2]}/${raw[3]}${anchor}` };
  }
  if (WEB_URL.test(file)) return { kind: 'forge', href: file };
  return { kind: 'local', text: `${String(node.label ?? node.id)}  ${file}${line ? `:${line}` : ''}` };
}
