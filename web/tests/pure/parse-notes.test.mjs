/**
 * What a parse said it could not read reaches the reader on every path that
 * draws one.
 *
 * The streams carry it as `note` events; a one-shot parse -- an uploaded file,
 * through `/parse/unified` -- carries it as `metadata.notes`, which nothing in
 * the front end read, so an uploaded `.c` without libclang drew as an empty
 * file and said nothing. `tests/test_a_parser_that_cannot_run.py` holds the
 * server to that shape; this holds the front end to reading it.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { parseNotes, notesTail } from '../../dist-pure/features/graph/services/parse_notes.js';

const NOTE = '1 c file(s) drawn without their contents: libclang is not installed, so C and C++ '
  + 'declarations cannot be read. Install it with: uv sync --extra c-parsing';

test("a one-shot parse's notes are read from its metadata", () => {
  const results = { graph: { nodes: {}, edges: [] }, metadata: { layout: 'Spring', notes: [NOTE] } };
  assert.deepEqual(parseNotes(results), [NOTE]);
});

test('a parse with nothing to say has no notes, and nothing else is taken for one', () => {
  assert.deepEqual(parseNotes({ graph: {}, metadata: { layout: 'Spring' } }), []);
  assert.deepEqual(parseNotes({ graph: {} }), []);
  assert.deepEqual(parseNotes(null), []);
  assert.deepEqual(parseNotes({ metadata: { notes: 'one sentence, not a list' } }), []);
  assert.deepEqual(parseNotes({ metadata: { notes: [NOTE, 7, ''] } }), [NOTE]);
});

test('the status line keeps them after their toasts are gone', () => {
  assert.equal(notesTail([]), '');
  assert.equal(notesTail(['a', 'b']), ' — a; b');
});
