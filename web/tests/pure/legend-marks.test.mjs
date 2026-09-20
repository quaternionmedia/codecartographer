/**
 * The legend describes the graph that was drawn.
 *
 * **WHAT THIS IS FOR, AND WHAT A DOM TEST WOULD MISS.** Asserting that a key
 * renders six rows is easy and proves nothing: the key this replaces rendered
 * six rows unconditionally, naming node kinds whether or not the graph held
 * any. The question worth testing is whether every row corresponds to something
 * on screen and every thing on screen is covered by a row — which is these
 * functions, and nothing to do with markup.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  DEFAULT_EDGE_COLOR,
  DEFAULT_EDGE_KIND,
  DEFAULT_NODE_COLOR,
  DEFAULT_NODE_KIND,
  edgeMarks,
  marksCover,
  nodeMarks,
  readable,
} from '../../dist-pure/features/graph/extensions/legend_marks.js';
import {
  KNOWN_SHAPES,
  nodePath,
} from '../../dist-pure/features/graph/services/node_shapes.js';

// --- what the key covers -------------------------------------------------------

test('every node is accounted for by exactly one mark', () => {
  const nodes = [
    { kind: 'function', shape: 'hexagon', color: '#a' },
    { kind: 'function', shape: 'hexagon', color: '#a' },
    { kind: 'class', shape: 'square', color: '#b' },
    {},
  ];

  const marks = nodeMarks(nodes);

  // Mutation: drop the `else seen.set(...)` branch and this fails — the
  // unkinded node stops being counted and the key silently describes 3 of 4.
  assert.equal(marksCover(marks), nodes.length);
});

test('a node with no kind is counted under a default rather than dropped', () => {
  const marks = nodeMarks([{}]);
  assert.equal(marks.length, 1);
  assert.equal(marks[0].kind, DEFAULT_NODE_KIND);
  assert.equal(marks[0].color, DEFAULT_NODE_COLOR);
  assert.equal(marks[0].shape, undefined);
});

test('one kind drawn two ways is two rows', () => {
  /** A reader matches a swatch against what is on screen, not against an average. */
  const marks = nodeMarks([
    { kind: 'file', shape: 'square', color: '#aaa' },
    { kind: 'file', shape: 'diamond', color: '#aaa' },
  ]);

  // Mutation: key on `kind` alone and this collapses to one row.
  assert.equal(marks.length, 2);
  assert.deepEqual(marks.map((m) => m.shape).sort(), ['diamond', 'square']);
});

test('marks come back most common first', () => {
  const marks = nodeMarks([
    { kind: 'rare', shape: 'square', color: '#a' },
    { kind: 'common', shape: 'square', color: '#b' },
    { kind: 'common', shape: 'square', color: '#b' },
    { kind: 'common', shape: 'square', color: '#b' },
  ]);
  assert.equal(marks[0].kind, 'common');
  assert.equal(marks[0].count, 3);
});

// --- edges ---------------------------------------------------------------------

test('edge kind is read before edge label', () => {
  /** A label is per-edge and would give one row per edge. `kind` is the class. */
  const marks = edgeMarks([
    { kind: 'CALLS', label: 'alpha->beta', color: '#f90' },
    { kind: 'CALLS', label: 'beta->gamma', color: '#f90' },
  ]);

  // Mutation: read `label` first and this becomes two rows.
  assert.equal(marks.length, 1);
  assert.equal(marks[0].kind, 'CALLS');
  assert.equal(marks[0].count, 2);
});

test('an edge with neither kind nor label still counts', () => {
  const marks = edgeMarks([{}, {}]);
  assert.equal(marks.length, 1);
  assert.equal(marks[0].kind, DEFAULT_EDGE_KIND);
  assert.equal(marks[0].color, DEFAULT_EDGE_COLOR);
  assert.equal(marksCover(marks), 2);
});

test('an empty graph produces no rows rather than a default one', () => {
  assert.deepEqual(nodeMarks([]), []);
  assert.deepEqual(edgeMarks([]), []);
});

// --- display -------------------------------------------------------------------

test('schema words are made readable without becoming a different word', () => {
  assert.equal(readable('async_function'), 'Async function');
  assert.equal(readable('file'), 'File');
  assert.equal(readable(''), '');
});

// --- the swatch and the canvas cannot disagree ---------------------------------

test('every known shape draws a distinct path', () => {
  /**
   * The key's whole job is that a swatch matches a node. An unknown shape falls
   * through to a circle, which is indistinguishable from a node that asked for
   * one — so a shape silently dropped from the switch would produce a key that
   * confidently draws the wrong mark.
   *
   * Mutation: delete the `diamond` case and this fails, because diamond and
   * circle become the same path.
   */
  const drawn = KNOWN_SHAPES.map((shape) => nodePath(shape, 8));
  assert.equal(new Set(drawn).size, new Set(KNOWN_SHAPES).size - 1,
    'only circle should share the default path');
});

test('a shape nobody registered falls back to the circle', () => {
  assert.equal(nodePath('trapezoid', 8), nodePath('circle', 8));
});
