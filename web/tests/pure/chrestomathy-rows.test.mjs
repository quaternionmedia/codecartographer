/**
 * The Chrestomathy panel's table says what each language spells, on which
 * layer, and keeps a row the server sends with no spelling as a row that says
 * so.
 *
 * **THE ROWS ARE THE SERVER'S.** They come from
 * `fixtures/chrestomathy-readings.json`, which `tests/test_construct_service.py`
 * holds equal to what `construct_service.reading` sends. A hand-made reading
 * carried an assembly row for a record -- a row the server never sends -- and
 * so asserted a table nobody could see.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import {
  chrestomathyRows,
  layerLabels,
} from '../../dist-pure/features/cartography/chrestomathy_rows.js';

const SENT = JSON.parse(readFileSync(new URL('./fixtures/chrestomathy-readings.json', import.meta.url), 'utf-8'));
const product = SENT['type.product'];
const volatile = SENT['memory.volatile'];

test('every row the server sends is a row, in its order', () => {
  /* Mutation: filter silent rows out of `chrestomathyRows` -- the volatile case fails. */
  for (const sent of [product, volatile]) {
    assert.deepEqual(chrestomathyRows(sent).map((r) => r.language), sent.map((r) => r.language));
  }
});

test('a row the server sends with no spelling stays, and says so', () => {
  /** Rust has no keyword for a volatile access; its row is the note. */
  const rust = chrestomathyRows(volatile).find((r) => r.language === 'rust');
  assert.equal(rust.silent, true);
  assert.equal(rust.spelling, '—');
  assert.match(rust.note, /read_volatile/);
});

test('a spelled row carries its tokens, layers and parser kinds', () => {
  const rust = chrestomathyRows(product).find((r) => r.language === 'rust');
  assert.equal(rust.silent, false);
  assert.equal(rust.spelling, 'struct');
  assert.deepEqual(rust.layers, ['L2 Aggregate & user-defined types · aggregate']);
  assert.equal(rust.parsedAs, 'struct (parsed)');
});

test('a facet carried by a qualifier is not silent', () => {
  const c = chrestomathyRows(volatile).find((r) => r.language === 'c');
  assert.equal(c.silent, false);
  assert.equal(c.parsedAs, 'qualifier volatile');
});

test('layers are distinct and machine-facing first', () => {
  const labels = layerLabels([
    { layer_ordinal: 5, layer_name: 'Compile-time', group: 'evaluation' },
    { layer_ordinal: 0, layer_name: 'Memory', group: 'storage' },
    { layer_ordinal: 5, layer_name: 'Compile-time', group: 'evaluation' },
  ]);
  assert.deepEqual(labels, ['L0 Memory · storage', 'L5 Compile-time · evaluation']);
});

// --- the census: any graph read as its constructs ----------------------------

const census = {
  constructs: [
    { id: 'callable.function', name: 'Function', facet: false, count: 15, ids: ['r1', 'c1'],
      languages: [{ language: 'rust', display_name: 'Rust', count: 12 }, { language: 'c', display_name: 'C', count: 3 }] },
    { id: 'type.sum', name: 'Sum type', facet: false, count: 2, ids: ['r9'],
      languages: [{ language: 'rust', display_name: 'Rust', count: 2 }] },
  ],
  facets: [
    { id: 'memory.unsafe', name: 'Unsafe', facet: true, count: 1, ids: ['r1'],
      languages: [{ language: 'rust', display_name: 'Rust', count: 1 }] },
  ],
  unplaced: [{ language: 'rust', display_name: 'Rust', kind: 'doc_comment', count: 4 }],
  outside: [{ language: 'javascript', count: 30 }],
  unlabelled: 7,
};

test('a construct written in two languages on one canvas is marked: the comparison is right there', async () => {
  const { censusLines } = await import('../../dist-pure/features/cartography/chrestomathy_rows.js');
  const lines = censusLines(census);
  assert.deepEqual(lines.map((l) => [l.id, l.spread, l.shared, l.facet]), [
    ['callable.function', 'Rust 12 · C 3', true, false],
    ['type.sum', 'Rust 2', false, false],
    ['memory.unsafe', 'Rust 1', false, true],
  ]);
  assert.deepEqual(lines[0].ids, ['r1', 'c1']);
});

test('what the census could not place is said, every kind of it', async () => {
  /* Mutation: drop the unplaced sentences -- a graph would read as wholly
     covered by the vocabulary, and this fails. */
  const { censusGaps } = await import('../../dist-pure/features/cartography/chrestomathy_rows.js');
  assert.deepEqual(censusGaps(census), [
    '4 Rust doc_comment node(s): a kind the vocabulary does not place',
    '30 javascript node(s): a language the vocabulary does not list',
    '7 node(s) with no language: folders, files, or a graph that is not code',
  ]);
  assert.deepEqual(censusGaps({ ...census, unplaced: [], outside: [], unlabelled: 0 }), []);
});
