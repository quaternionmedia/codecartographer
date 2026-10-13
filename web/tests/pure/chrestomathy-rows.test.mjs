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
