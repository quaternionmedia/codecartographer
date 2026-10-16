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
 * the file when not; or, for a file read from disk, which a browser page
 * cannot open, the file and line to name beside the node.
 *
 * Null for a node from no file. That is the one rule for whether either route
 * is offered.
 */
export type SourceTarget =
  | { kind: 'forge'; href: string }
  | { kind: 'local'; text: string };

const RAW_GITHUB = /^https:\/\/raw\.githubusercontent\.com\/([^/]+\/[^/]+)\/([^/]+)\/(.+)$/;

export function sourceTarget(node: InfoNode): SourceTarget | null {
  const where = sourceLine(node);
  if (where === null) return null;
  const file = node.file as string;
  const line = typeof node.line === 'number' && node.line > 0 ? node.line : 0;
  const raw = file.match(RAW_GITHUB);
  if (raw) {
    const anchor = line ? `#L${line}` : '';
    return { kind: 'forge', href: `https://github.com/${raw[1]}/blob/${raw[2]}/${raw[3]}${anchor}` };
  }
  if (/^https?:\/\//.test(file)) return { kind: 'forge', href: file };
  return { kind: 'local', text: `${String(node.label ?? node.id)}  ${where}` };
}

/**
 * A local badge's text in at most `maxChars`: whole when it fits, else the
 * node's name, `…`, and the end of the path from a separator on, so the file
 * and line stay. An ellipsis at the end, which CSS gives, would cut the line.
 * With no room for the name, the end of the text alone.
 */
export function fitBadgeText(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;
  if (maxChars < 1) return '';
  const split = text.indexOf('  ');
  const name = split > 0 ? text.slice(0, split + 2) : '';
  const room = maxChars - name.length - 1;
  if (room < 1) return `…${text.slice(text.length - (maxChars - 1))}`;
  let tail = text.slice(text.length - room);
  const separator = tail.search(/[\\/]/);
  if (separator > 0) tail = tail.slice(separator);
  return `${name}…${tail}`;
}
