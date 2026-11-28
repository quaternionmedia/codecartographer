/**
 * What `/harness/interactions` returns, and how a panel words it.
 *
 * Each interaction is a row the harness recorded: an instruction, a question,
 * an answer or a tool run. The server states the act, the way in and the name
 * each row carries; these functions turn a stated value into the words or the
 * shade a panel shows, and derive nothing the document states.
 *
 * Pure: no DOM, no request and no import, so
 * `web/tests/pure/interactions.test.mjs` asserts every branch under node.
 *
 * What it cannot do: say whether a name is a person's or a program's. The
 * harness's rows carry the name alone, and it is shown as given.
 */

/** One row of `interactions.rows`. */
export interface Interaction {
  at: string | null;
  act: string;
  /** An instruction's source. Null on every other row. */
  way: string | null;
  /** The name the row carries, or null when it names nobody. */
  who: string | null;
  /** The field `who` was read from, or null when the row names nobody. */
  who_from: string | null;
  what: unknown;
  ref: unknown;
  project: string | null;
  session: unknown;
  chat: unknown;
  turn: unknown;
}

/** One row of `who.rows`: a name, an act and a way in, counted. */
export interface WhoRow {
  who: string | null;
  who_from: string | null;
  act: string;
  way: string | null;
  count: number;
  last: string | null;
}

/** One lane of `over_time.lanes`: an act and a way in, counted into spans. */
export interface Lane {
  act: string;
  way: string | null;
  count: number;
  cells: number[];
}

/** `instance`: which harness answered, as its health answer states it. */
export interface Instance {
  identified: boolean;
  where: string;
  pid: unknown;
  port: unknown;
  database_fingerprint: unknown;
  started_at: unknown;
  session: unknown;
  version: unknown;
  problem: string;
  remedy: string;
}

export interface InteractionsDocument {
  instance: Instance;
  interactions: { rows: Interaction[]; shown: number; more: number; more_is_floor: boolean };
  who: { rows: WhoRow[]; shown: number; more: number };
  over_time: { from: string | null; to: string | null; cells: number; lanes: Lane[]; undated: number };
  answers: { read: number; unread: number; limit: number };
  unread_lists: Array<{ what: string; problem: string; remedy: string; where: string }>;
  caveat: string;
}

/** What a panel says in place of a name when a row carries none. */
export const NOBODY = 'nobody named';

/** The name a row carries, or the words for a row that names nobody. */
export function whoShown(who: string | null | undefined): string {
  return who ? who : NOBODY;
}

/** An act with its way in, when the row names one: `instructed · voice`. */
export function actShown(act: string, way: string | null | undefined): string {
  return way ? `${act} · ${way}` : act;
}

/**
 * The shade of one span of a lane, 0 to 4.
 *
 * 0 is a span with nothing in it. Any count above zero is at least 1, so a
 * single interaction beside a busy span is still drawn.
 */
export function cellLevel(count: number, most: number): number {
  if (!(count > 0) || !(most > 0)) return 0;
  return Math.min(4, Math.max(1, Math.ceil((4 * count) / most)));
}

/** The largest count in any span of any lane: one scale for every lane. */
export function mostInACell(lanes: readonly Lane[]): number {
  let most = 0;
  for (const lane of lanes) for (const count of lane.cells) if (count > most) most = count;
  return most;
}

/**
 * Which harness answered, as one line, each field as the harness stated it.
 * `when` words the start time as the panel words every other time.
 */
export function instanceShown(instance: Instance, when: (value: unknown) => string): string {
  const stated = (value: unknown): string =>
    value === null || value === undefined || value === '' ? 'not stated' : String(value);
  return [
    `pid ${stated(instance.pid)}`,
    `port ${stated(instance.port)}`,
    `database ${stated(instance.database_fingerprint)}`,
    `started ${instance.started_at ? when(instance.started_at) : 'not stated'}`,
    `session ${stated(instance.session)}`,
    `version ${stated(instance.version)}`,
  ].join(' · ');
}

/** What a panel says about answers the server did not read, or ''. */
export function answersShown(answers: { unread: number; limit: number }): string {
  if (!(answers.unread > 0)) return '';
  return `answered questions whose answer was not read: ${answers.unread}. `
    + `An answer is one read of the harness each, and at most ${answers.limit} are read.`;
}

/** What a panel says about interactions with no readable time, or ''. */
export function undatedShown(undated: number): string {
  return undated > 0 ? `interactions with no readable time, in no span: ${undated}.` : '';
}

/** What a panel says under the who table about the rows it does not show. */
export function moreNamesShown(more: number): string {
  return more > 0 ? `${more} more the harness's rows give and this panel does not show` : '';
}

/** The layout the interactions graph is drawn in when its panel draws it. */
export const READING_ORDER = 'Reading_Order';

/** The graph as rows alone, and with every source, project, chat and session a node. */
export const ROWS = 'rows';
export const ALL = 'all';

/** What the route is asked to draw: rows alone unless every node is wanted. */
export function detailAsked(everyNode: boolean): string {
  return everyNode ? ALL : ROWS;
}

/** As much of a drawn edge as the key reads: its kind, colour and line. */
export interface KeyedEdge {
  label?: unknown;
  metadata?: { kind?: unknown; color?: unknown; style?: unknown } | null;
}

/** One line of the key: a colour as drawn, and the kinds of edge drawn in it. */
export interface KeyLine {
  color: string;
  kinds: string[];
}

/**
 * The key to a drawn graph's edges, read from the edges themselves: each
 * colour with the kinds drawn in it, in the order they first appear, and
 * whether any edge is dashed. An edge that states no colour is left out.
 */
export function edgeKey(edges: readonly KeyedEdge[]): { lines: KeyLine[]; dashed: boolean } {
  const lines: KeyLine[] = [];
  let dashed = false;
  for (const edge of edges) {
    const held = edge.metadata ?? {};
    if (held.style === 'dashed') dashed = true;
    const kind = typeof held.kind === 'string' && held.kind ? held.kind
      : typeof edge.label === 'string' ? edge.label : '';
    if (typeof held.color !== 'string' || !held.color || !kind) continue;
    let line = lines.find((found) => found.color === held.color);
    if (!line) {
      line = { color: held.color, kinds: [] };
      lines.push(line);
    }
    if (!line.kinds.includes(kind)) line.kinds.push(kind);
  }
  return { lines, dashed };
}

/**
 * What a panel says when the harness holds a different number of rows than
 * the graph on the canvas was drawn from, or ''. Rows that changed without
 * the number changing are not seen.
 */
export function staleShown(drawn: unknown, now: unknown): string {
  if (typeof drawn !== 'number' || typeof now !== 'number' || drawn === now) return '';
  return `The harness held ${drawn} rows when this graph was drawn and holds ${now} now. Draw again to read them.`;
}

/**
 * One string for what a reading lists: how many rows the harness holds, each
 * listed row's act, reference and time, and how many answers were read. Two
 * readings share it only when they list the same rows.
 *
 * A row the reading holds back is in the count alone, so one that changed
 * there without the count changing is not seen.
 */
export function readingMark(reading: InteractionsDocument): string {
  const listed = reading.interactions.rows.map((row) => `${row.act} ${String(row.ref)} ${row.at ?? ''}`);
  return [reading.interactions.shown + reading.interactions.more, reading.answers.read, ...listed].join('\n');
}

/**
 * Whether the graph on the canvas is drawn again for a reading: following is
 * ticked, the canvas holds this seam's graph, this panel drew it, the reading
 * lists other rows than the one it was drawn beside, and no drawing is out.
 */
export function followDue(
  follow: boolean, kind: unknown, drawn: string | null, now: string, drawing: boolean,
): boolean {
  return follow && kind === 'interactions' && drawn !== null && drawn !== now && !drawing;
}

/** What the hint under the button says of a drawn graph and the harness. */
export function followShown(follow: boolean): string {
  return follow
    ? 'While this panel is open, the graph is drawn again when the rows the harness lists change.'
    : 'The graph is the harness as read for that drawing, and stays as drawn until it is drawn again.';
}
