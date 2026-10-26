/**
 * Placing the group outlines' labels stays quick on a large graph.
 *
 * **THE DEFECT THIS PINS.** Each label tries up to 150 spots round its
 * outline, and each spot was checked against every label already placed and
 * every node. The renderer places the labels synchronously when a stream
 * ends, when Group Outlines is turned on, at the end of every drag and after
 * a Delete or Collapse, so on a large graph each of those held the page:
 * 2,000 outlines among 20,000 nodes took 4.3 s. `outline_labels.ts` now files
 * every node's box and every placed label's by the grid cells it covers, and
 * checks a spot only against the boxes filed in its own cells.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { placeOutlineLabels } from '../../dist-pure/features/graph/services/outline_labels.js';

/**
 * The most the large graph below may take, in milliseconds. Checking every
 * box took 4,300 here; the grid takes about 100. The budget leaves a slower
 * machine ten times the room.
 */
const BUDGET_MS = 1_000;

/**
 * `outlines` outlines and `nodes` nodes scattered over a square `span` wide,
 * the same on every run: the labels 30 to 150 wide, the outlines 30 to 430
 * in radius, the nodes 6 to 18.
 */
function scene(outlines, nodes, span) {
  let seed = 1;
  const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  return {
    nodes: Array.from({ length: nodes }, () => ({ x: rand() * span, y: rand() * span, r: 6 + rand() * 12 })),
    outlines: Array.from({ length: outlines }, () => ({
      cx: rand() * span, cy: rand() * span, r: 30 + rand() * 400, w: 30 + rand() * 120, h: 11,
    })),
  };
}

test('2,000 outlines among 20,000 nodes are labelled within the budget', () => {
  /* Mutation: check each spot against every box again, the whole graph one
     cell -- it takes seconds, and this fails. */
  const { outlines, nodes } = scene(2_000, 20_000, 8_000);
  placeOutlineLabels(outlines.slice(0, 50), nodes.slice(0, 500));
  const started = performance.now();
  const places = placeOutlineLabels(outlines, nodes);
  const took = performance.now() - started;
  assert.equal(places.length, outlines.length);
  assert.ok(took < BUDGET_MS, `placing the labels took ${Math.round(took)} ms, over ${BUDGET_MS}`);
});

test('the grid places every label where checking every box would', () => {
  /* Mutation: file each box only in the cell its centre is in -- a spot
     misses a box reaching into its cells from the next, a label is set over
     a node or another label, and this fails. */
  const { outlines, nodes } = scene(300, 3_000, 2_500);
  assert.deepEqual(placeOutlineLabels(outlines, nodes), placeOutlineLabels(outlines, nodes, Infinity));
});
