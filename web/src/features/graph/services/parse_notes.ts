/**
 * What a parse said it could not read, as the reader is told it.
 *
 * A parser that cannot run over files the graph still draws -- C without
 * libclang -- leaves those files empty, and an empty file reads as a file with
 * nothing in it. So the server says why beside the graph: a `note` event on
 * each stream, `metadata.notes` on a one-shot `/parse/unified` result. Every
 * path that draws one shows each note as a toast and keeps them in the status
 * line; an uploaded file is drawn through the one-shot route, and nothing read
 * its notes. What is read, and what the status line says, is decided here,
 * where `node --test` reads it.
 */

/** The notes of a `/parse/unified` result (`{graph, metadata}`), or none. */
export function parseNotes(results: unknown): string[] {
  const metadata = (results as { metadata?: { notes?: unknown } } | null)?.metadata;
  const notes = metadata?.notes;
  if (!Array.isArray(notes)) return [];
  return notes.filter((note): note is string => typeof note === 'string' && note.length > 0);
}

/** The status line's tail for *notes*, kept after their toasts are gone. */
export function notesTail(notes: readonly string[]): string {
  return notes.length ? ` — ${notes.join('; ')}` : '';
}
