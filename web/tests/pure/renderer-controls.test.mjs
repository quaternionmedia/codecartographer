/**
 * Graph Settings offers a control only on a renderer that reads it.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { rendererControls } from '../../dist-pure/features/graph/services/renderer_controls.js';

test('physics is offered only where a simulation runs', () => {
  /* Mutation: offer physics on the D3 canvas again -- three controls that move
     nothing, and this fails. */
  assert.equal(rendererControls('gravis').physics, true);
  for (const renderer of ['d3', 'notebook', 'system']) {
    assert.equal(rendererControls(renderer).physics, false, `${renderer} has no simulation`);
  }
});

test('the layout algorithm is the D3 canvas\'s, and the visual controls skip Notebook and System Monitor', () => {
  assert.deepEqual(rendererControls('d3'), { layout: true, physics: false, visual: true });
  assert.deepEqual(rendererControls('notebook'), { layout: false, physics: false, visual: false });
  assert.deepEqual(rendererControls('system'), { layout: false, physics: false, visual: false });
});
