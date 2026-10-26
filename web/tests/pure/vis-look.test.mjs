/**
 * The vis-network renderer draws the D3 canvas's marks, in its colours.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { visLook } from '../../dist-pure/features/graph/services/vis_look.js';
import { canvasPath, nodePath } from '../../dist-pure/features/graph/services/node_shapes.js';

test('a record and a rectangle are drawn with the canvas path, not as a dot', () => {
  /**
   * vis-network has neither shape, and both fell through to `dot`. Mutation:
   * take `ngon` out of the drawn set -- this fails with `dot`.
   */
  const record = { shape: 'ngon', meta: { sides: 7 } };
  const look = visLook(record, 'auto');
  assert.equal(look.shape, 'custom');
  assert.equal(nodePath(look.path.shape, 8, look.path.sides), canvasPath(record, 8));

  const impl = { shape: 'rectangle' };
  assert.equal(visLook(impl, 'auto').shape, 'custom');
  assert.equal(nodePath(visLook(impl, 'auto').path.shape, 8), canvasPath(impl, 8));
});

test('the shapes vis-network has stay its own', () => {
  assert.equal(visLook({ shape: 'circle' }, 'auto').shape, 'dot');
  assert.equal(visLook({ shape: 'diamond' }, 'auto').shape, 'diamond');
  assert.equal(visLook({ shape: 'hexagon' }, 'auto').shape, 'hexagon');
  assert.equal(visLook({}, 'auto').shape, 'dot');
  assert.equal(visLook({ shape: 'trapezoid' }, 'auto').shape, 'dot');
});

test('"Color By: Abstraction Layer" paints the layer colour here too', () => {
  /**
   * The renderer read `node.color` whatever was chosen. Mutation: ignore
   * `colorBy` -- this fails with the node's own colour.
   */
  const node = { color: '#ff9d3d', layer_color: '#ef4444' };
  assert.equal(visLook(node, 'layer').color, '#ef4444');
  assert.equal(visLook(node, 'auto').color, '#ff9d3d');
  assert.equal(visLook({ color: '#ff9d3d', layer_ordinal: 0 }, 'layer').color, '#ff9d3d',
    'placed on a layer and sent no colour: its own');
  assert.equal(visLook({}, 'layer').color, undefined, "vis-network's default stays its default");
});

test('"Color By: Construct" paints the construct colour here too', () => {
  /**
   * The vis-network canvas had its own colour rule, which knew the layer and
   * not the construct, so it ignored Construct while the D3 canvas and its key
   * followed it. Mutation: give `visLook` its own rule again (layer only) --
   * this fails with the crate's own colour.
   */
  const crate = { color: '#2563eb', construct_color: '#6d28d9' };
  assert.equal(visLook(crate, 'construct').color, '#6d28d9');
  assert.equal(visLook(crate, 'auto').color, '#2563eb');
  assert.equal(visLook({}, 'construct').color, undefined, "vis-network's default stays its default");
});
