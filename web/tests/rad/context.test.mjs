/**
 * Which ring opens, that every item is reachable from the keyboard, and that
 * every selection can be cleared without a pointer.
 *
 *   npm run test:rad
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { canvasKeyVerb, menuContextFor } from '../../dist-rad/host/menu_context.js';
import { allMenuVerbs, resolveGraphMenu } from '../../dist-rad/host/resolve.js';

const at = { x: 10, y: 20 };
const open = (pointer, underPointer, selected) => menuContextFor({ pointer, underPointer, selected, position: at });

/** Every fact true, so an item is disabled only by the selection it is opened with. */
const EVERY_FACT = {
  depth: 0, hasRenderedChildren: true, hasSource: true, hasGroup: true, hasConstruct: true,
  anyHidden: true, physicsAvailable: true, layoutAvailable: true,
};

/** The verbs a keyboard reader can commit with this selection: the ring a key opens, and the canvas's own keys. */
function keyboardVerbs(selected) {
  const verbs = new Set();
  const walk = (items) => {
    for (const item of items) {
      if (item.enabled === false) continue;
      if (item.action) verbs.add(item.action);
      if (item.children) walk(item.children);
    }
  };
  walk(resolveGraphMenu(open(false, null, selected), { ...EVERY_FACT, selectionCount: selected.length }).items);
  for (const key of ['Escape']) {
    const verb = canvasKeyVerb(key, selected);
    if (verb) verbs.add(verb);
  }
  return verbs;
}

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

test('a key opens the canvas ring with nothing selected, the node\'s ring with one, the selection ring with several', () => {
  /* Mutation: open the selection ring for one node, as a key did -- no key
     reaches a node's ring, and this fails. */
  assert.equal(open(false, null, []).type, 'canvas');
  assert.deepEqual(open(false, null, ['a']), { type: 'node', targetIds: ['a'], position: at });
  assert.deepEqual(open(false, null, ['a', 'b']), { type: 'selection', targetIds: ['a', 'b'], position: at });
});

test('every verb a ring offers is reachable from the keyboard', () => {
  /* Mutation: open the selection ring for one node -- Collapse, Pin and View's
     Source, Info, Compare and Focus have no keyboard route, and this fails
     naming them. */
  const reachable = new Set();
  for (const selected of [[], ['a'], ['a', 'b']]) {
    for (const verb of keyboardVerbs(selected)) reachable.add(verb);
  }
  assert.deepEqual(allMenuVerbs().filter((verb) => !reachable.has(verb)), []);
});

test('with any selection, the keyboard can clear it', () => {
  /* Mutation: let Escape commit nothing -- one selected node's ring has no
     Deselect, and this fails for one node. */
  for (const selected of [['a'], ['a', 'b']]) {
    assert.ok(keyboardVerbs(selected).has('clear-selection'),
      `with ${selected.length} selected, no key clears the selection`);
  }
});

test('Escape clears a selection, and with nothing selected is left to whatever else hears it', () => {
  assert.equal(canvasKeyVerb('Escape', ['a']), 'clear-selection');
  assert.equal(canvasKeyVerb('Escape', ['a', 'b']), 'clear-selection');
  assert.equal(canvasKeyVerb('Escape', []), null);
  assert.equal(canvasKeyVerb('x', ['a']), null);
});

test('with any selection, a press off the nodes offers Deselect, enabled', () => {
  for (const selected of [['a'], ['a', 'b']]) {
    const ring = resolveGraphMenu(open(true, null, selected), { selectionCount: selected.length }).items;
    const deselect = ring.find((i) => i.action === 'clear-selection');
    assert.ok(deselect, `the canvas ring (${selected.length} selected) has no Deselect`);
    assert.notEqual(deselect.enabled, false, 'the canvas ring offers Deselect disabled');
  }
});
