/**
 * Which ring opens, and that every selection can be cleared from one.
 *
 *   npm run test:rad
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { menuContextFor } from '../../dist-rad/host/menu_context.js';
import { resolveGraphMenu } from '../../dist-rad/host/resolve.js';

const at = { x: 10, y: 20 };
const open = (pointer, underPointer, selected) => menuContextFor({ pointer, underPointer, selected, position: at });

test('a press off the nodes opens the canvas ring, whatever is selected', () => {
  /* Mutation: let a selection win off the nodes too -- the canvas ring cannot
     be opened while anything is selected, and this fails. */
  assert.deepEqual(open(true, null, []), { type: 'canvas', targetIds: [], position: at });
  assert.equal(open(true, null, ['a']).type, 'canvas');
  assert.equal(open(true, null, ['a', 'b']).type, 'canvas');
});

test('a press on a node opens its ring, or the selection ring when several are selected', () => {
  assert.deepEqual(open(true, 'c', []), { type: 'node', targetIds: ['c'], position: at });
  assert.deepEqual(open(true, 'c', ['a']), { type: 'node', targetIds: ['c'], position: at });
  assert.deepEqual(open(true, 'c', ['a', 'b']), { type: 'selection', targetIds: ['a', 'b'], position: at });
});

test('a key opens the selection ring when anything is selected, one node included', () => {
  assert.equal(open(false, null, []).type, 'canvas');
  assert.deepEqual(open(false, null, ['a']), { type: 'selection', targetIds: ['a'], position: at });
  assert.equal(open(false, null, ['a', 'b']).type, 'selection');
});

test('with any selection, every way a ring opens off the nodes offers Deselect, enabled', () => {
  for (const selected of [['a'], ['a', 'b']]) {
    for (const pointer of [true, false]) {
      const context = open(pointer, null, selected);
      const ring = resolveGraphMenu(context, { selectionCount: selected.length }).items;
      const deselect = ring.find((i) => i.action === 'clear-selection');
      assert.ok(deselect, `${context.type} ring (${pointer ? 'pointer' : 'key'}, ${selected.length} selected) has no Deselect`);
      assert.notEqual(deselect.enabled, false, `${context.type} ring offers Deselect disabled`);
    }
  }
});
