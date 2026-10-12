/**
 * The Chrestomathy panel's table says what each language spells, on which
 * layer, and that a language with no spelling has none.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  chrestomathyRows,
  layerLabels,
} from '../../dist-pure/features/cartography/chrestomathy_rows.js';

const product = [
  {
    language: 'c', display_name: 'C', has_lexicon: true, kinds: ['struct'], carried_by: [], note: '',
    tokens: [{ token: 'struct', contexts: [{ layer_ordinal: 2, layer_name: 'Aggregate & user-defined types', group: 'aggregate' }] }],
  },
  {
    language: 'rust', display_name: 'Rust', has_lexicon: true, kinds: ['struct'], carried_by: [],
    note: 'Layout is the compiler’s choice unless #[repr(C)] fixes it.',
    tokens: [{ token: 'struct', contexts: [{ layer_ordinal: 2, layer_name: 'Aggregate & user-defined types', group: 'aggregate' }] }],
  },
  {
    language: 'assembly', display_name: 'Assembly', has_lexicon: false, kinds: [], carried_by: [],
    note: 'Offsets from a base address; nothing names the record.', tokens: [],
  },
];

test('a language with no spelling is a row that says so, never a missing row', () => {
  /* Mutation: filter silent rows out of `chrestomathyRows` -- this fails. */
  const rows = chrestomathyRows(product);
  assert.deepEqual(rows.map((r) => r.language), ['c', 'rust', 'assembly']);
  const asm = rows[2];
  assert.equal(asm.silent, true);
  assert.equal(asm.spelling, '—');
  assert.match(asm.note, /nothing names the record/);
});

test('a spelled row carries its tokens, layers and parser kinds', () => {
  const rust = chrestomathyRows(product)[1];
  assert.equal(rust.silent, false);
  assert.equal(rust.spelling, 'struct');
  assert.deepEqual(rust.layers, ['L2 Aggregate & user-defined types · aggregate']);
  assert.equal(rust.parsedAs, 'struct (parsed)');
});

test('a facet carried by an attribute is not silent', () => {
  const [row] = chrestomathyRows([{
    language: 'rust', display_name: 'Rust', has_lexicon: true, tokens: [], kinds: [],
    carried_by: ['#[interrupt]', '#[exception]'], note: '',
  }]);
  assert.equal(row.silent, false);
  assert.equal(row.parsedAs, '#[interrupt], #[exception]');
});

test('layers are distinct and machine-facing first', () => {
  const labels = layerLabels([
    { layer_ordinal: 5, layer_name: 'Compile-time', group: 'evaluation' },
    { layer_ordinal: 0, layer_name: 'Memory', group: 'storage' },
    { layer_ordinal: 5, layer_name: 'Compile-time', group: 'evaluation' },
  ]);
  assert.deepEqual(labels, ['L0 Memory · storage', 'L5 Compile-time · evaluation']);
});
