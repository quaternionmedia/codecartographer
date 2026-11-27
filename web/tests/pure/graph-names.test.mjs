/**
 * Which graphs are drawn with their names, and the key and the staleness the
 * Interactions panel reads from a drawn graph.
 *
 *   npm run test:pure
 *
 * Each test names the mutation it was seen to fail under.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { namedGraph } from '../../dist-pure/features/graph/services/graph_names.js';
import { READING_ORDER, edgeKey, staleShown } from '../../dist-pure/features/estate/interactions.js';

test('a graph is drawn with its names when it is a showgraph or says its names are what it is for', () => {
  // Mutations: answer for a showgraph alone -- the interactions graph is drawn
  // unnamed; answer true for any metadata -- a code map is drawn with thousands.
  assert.equal(namedGraph({ kind: 'show' }), true);
  assert.equal(namedGraph({ kind: 'show', names: false }), true);
  assert.equal(namedGraph({ kind: 'interactions', names: true }), true);
  assert.equal(namedGraph({ kind: 'interactions' }), false);
  assert.equal(namedGraph({ kind: 'topology', names: 'yes' }), false);
  assert.equal(namedGraph({}), false);
  assert.equal(namedGraph(null), false);
  assert.equal(namedGraph(undefined), false);
});

const edge = (kind, color, style = 'solid') => ({ label: kind, metadata: { kind, color, style } });

test('the key has one line per colour drawn, with the kinds drawn in it, in the order they appear', () => {
  // Mutations: start a line for every edge -- `instructed` is listed twice;
  // key the lines by kind -- the grey kinds are six lines, not one.
  const key = edgeKey([
    edge('instructed', '#6db2ff'), edge('way in', '#6b7480'), edge('instructed', '#6db2ff', 'dashed'),
    edge('asked', '#e0c069'), edge('for', '#6b7480'), edge('way in', '#6b7480'), edge('answered', '#5ac8b0'),
  ]);
  assert.deepEqual(key.lines, [
    { color: '#6db2ff', kinds: ['instructed'] },
    { color: '#6b7480', kinds: ['way in', 'for'] },
    { color: '#e0c069', kinds: ['asked'] },
    { color: '#5ac8b0', kinds: ['answered'] },
  ]);
  assert.equal(key.dashed, true);
});

test('the key says dashed only when an edge is, and leaves out an edge that states no colour or no kind', () => {
  // Mutations: answer `dashed: true` whatever the edges -- a graph with no
  // unnamed row has a dash in its key; give an edge that names no kind a line
  // -- the key has a colour that says nothing.
  const key = edgeKey([
    edge('asked', '#e0c069'), { label: 'contains', metadata: { style: 'solid' } },
    { label: 'answered', metadata: { color: '#5ac8b0' } }, { label: 'loose' }, { metadata: { color: '#fff' } },
  ]);
  assert.deepEqual(key.lines, [
    { color: '#e0c069', kinds: ['asked'] },
    // No `kind` in the metadata: the edge's label names it.
    { color: '#5ac8b0', kinds: ['answered'] },
  ]);
  assert.equal(key.dashed, false);
  assert.deepEqual(edgeKey([]), { lines: [], dashed: false });
});

test('a graph drawn from fewer or more rows than the harness holds now says so, and one level with it says nothing', () => {
  // Mutations: answer '' whatever the counts -- a stale graph says nothing;
  // compare with `>` -- rows the harness no longer holds go unsaid.
  assert.equal(staleShown(8, 8), '');
  assert.equal(staleShown(8, 9),
    'The harness held 8 rows when this graph was drawn and holds 9 now. Draw again to read them.');
  assert.match(staleShown(9, 8), /held 9 rows .* holds 8 now/);
  assert.equal(staleShown(undefined, 9), '');
  assert.equal(staleShown(8, null), '');
  assert.equal(staleShown('8', 9), '');
});

test('the panel asks for the layout by the name the server reads as reading order', () => {
  // Mutation: spell it `Reading Order Layout` -- the server looks for
  // `reading_order_layout_layout` and refuses it. Held against the Python
  // registry by `tests/test_reading_order.py`, which lays out this spelling.
  assert.equal(READING_ORDER, 'Reading_Order');
});
