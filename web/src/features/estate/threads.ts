/**
 * How the Threads panel words the harness's archive and one conversation.
 *
 * Pure: it takes the documents `/harness/threads` and `/harness/thread`
 * return and gives back what the panel shows, and imports nothing, so it is
 * asserted under node.
 */

/** One conversation as the archive lists it. */
export interface ThreadRow {
  source: unknown;
  id: unknown;
  title: unknown;
  turns: unknown;
  last_seen: unknown;
  diverged: unknown;
  address: unknown;
}

/** `/harness/threads`. */
export interface ThreadsDocument {
  where: string;
  threads: ThreadRow[];
  shown: number;
  more: number;
  sources: Record<string, number>;
  totals: Record<string, unknown>;
  generated_at: unknown;
  reading: Record<string, unknown>;
}

/** One turn as a panel lists it. */
export interface TurnRow {
  index: number;
  id: unknown;
  role: string;
  at: unknown;
  text: string;
  cut: boolean;
}

/** `/harness/thread`. */
export interface ThreadDocument {
  where: string;
  source: unknown;
  id: unknown;
  title: unknown;
  url: unknown;
  started_at: unknown;
  partial: unknown;
  turns: { count: number; roles: Record<string, number>; rows: TurnRow[]; shown: number; more: number };
  drawn: number;
  mark: string;
  caveat: string;
}

/** Which conversation: the two words the harness's route takes. */
export interface Chosen {
  source: string;
  id: string;
}

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

function asked(params: Record<string, string | undefined>): string {
  const parts = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  return parts.length ? `?${parts.join('&')}` : '';
}

/** The query that lists conversations of one source whose title holds a text. */
export function listQuery(source: string, titled: string): string {
  return asked({ source: source.trim(), titled: titled.trim() });
}

/** The query that names one conversation, with a layout when one is asked for. */
export function threadQuery(chosen: Chosen, layout?: string): string {
  return asked({ source: chosen.source, id: chosen.id, layout });
}

/** A row's conversation, or null when the archive's row does not name one. */
export function chosenOf(row: ThreadRow): Chosen | null {
  const source = text(row.source);
  const id = text(row.id);
  return source && id ? { source, id } : null;
}

/** A conversation's title, or that the archive gives it none. */
export function titleShown(title: unknown): string {
  return text(title).trim() || 'no title';
}

/** How many turns the archive counts for a row, or '' when it counts none. */
export function turnsShown(turns: unknown): string {
  if (typeof turns !== 'number') return '';
  return turns === 1 ? '1 turn' : `${turns} turns`;
}

/** What is said under a list cut short, or ''. */
export function moreShown(more: number): string {
  return more > 0 ? `${more} more the archive lists are not shown; narrow by source or title.` : '';
}

/** Each role with how many turns carry it, in the order the conversation first uses them. */
export function rolesShown(roles: Record<string, number>): string {
  return Object.entries(roles).map(([role, count]) => `${role} ${count}`).join(' · ');
}

/** How many of a conversation's turns are drawn. */
export function drawnShown(drawn: number, count: number): string {
  if (count === 0) return 'this conversation holds no turn';
  return drawn < count ? `the newest ${drawn} of ${count} turns are drawn` : `all ${count} turns are drawn`;
}

/** What the archive says of itself, each sentence as given. */
export function readingShown(reading: Record<string, unknown>): string[] {
  return Object.values(reading).map(text).filter((said) => said !== '');
}

/** Whether a graph's metadata names this conversation. */
export function drawnIs(metadata: { kind?: unknown; thread?: unknown } | null | undefined, chosen: Chosen | null): boolean {
  if (!metadata || metadata.kind !== 'thread' || !chosen) return false;
  const held = (metadata.thread ?? {}) as { source?: unknown; id?: unknown };
  return text(held.source) === chosen.source && text(held.id) === chosen.id;
}

/**
 * Whether the graph on the canvas is drawn again for a reading of the
 * conversation: following is ticked, the canvas holds this conversation's
 * graph, the reading's mark is another than the graph's, and no drawing is
 * out.
 */
export function followDue(follow: boolean, onCanvas: boolean, drawn: unknown, now: string, drawing: boolean): boolean {
  return follow && onCanvas && typeof drawn === 'string' && drawn !== now && !drawing;
}

/** What the hint says of a drawn conversation and the archive. */
export function followShown(follow: boolean, seconds: number): string {
  return follow
    ? `While this panel is open the conversation is read again every ${seconds} s, and drawn again when its turns change.`
    : 'The graph is the conversation as read for that drawing, and stays as drawn until it is drawn again.';
}
