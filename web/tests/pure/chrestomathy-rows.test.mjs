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
