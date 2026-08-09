/**
 * The router, and the property the legacy menu failed on.
 *
 * rad's interaction contract names four defects in codecartographer's old
 * radial menu. One was "stubbed edge actions" — items that opened, animated,
 * committed, and did nothing. From the menu there is no way to tell that
 * apart from a working verb.
 *
 * The test below makes it impossible to reintroduce: every verb any ring can
 * commit must reach a named operation. A new menu item with no handler fails
 * here rather than in someone's hands.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { allMenuVerbs } from '../../dist-rad/host/resolve.js';
import { createIntentRouter } from '../../dist-rad/host/graph_intents.js';
import { viewActions, EMPTY_VIEW_STATE, anyHidden, colourTokenOf } from '../../dist-rad/host/view_state.js';

/** Records every call instead of doing anything. */
function spyOps() {
  const calls = [];
  const rec = (name) => (...args) => { calls.push([name, ...args]); };
  return {
    calls,
    hide: rec('hide'),
    showHidden: rec('showHidden'),
    togglePin: rec('togglePin'),
    colour: rec('colour'),
    remove: rec('remove'),
    expand: (...a) => { calls.push(['expand', ...a]); return Promise.resolve(); },
    collapse: rec('collapse'),
    fit: rec('fit'),
    relayout: rec('relayout'),
    spread: rec('spread'),
    cluster: rec('cluster'),
    togglePhysics: rec('togglePhysics'),
    selectNeighbors: rec('selectNeighbors'),
    clearSelection: rec('clearSelection'),
    focusGroup: rec('focusGroup'),
    viewSource: rec('viewSource'),
    showInfo: rec('showInfo'),
  };
}

const ctx = { type: 'node', targetIds: ['n1'], position: { x: 0, y: 0 } };

test('every verb the menu can commit reaches a named operation — no stubs', () => {
  const verbs = allMenuVerbs();
  assert.ok(verbs.length >= 15, `expected a real vocabulary, got ${verbs.length}`);

  const unhandled = [];
  for (const action of verbs) {
    const ops = spyOps();
    const route = createIntentRouter({ ops });
    try {
      route({ action, context: ctx, itemId: 'x' });
    } catch (e) {
      unhandled.push(`${action}: ${e.message.split('.')[0]}`);
      continue;
    }
    if (ops.calls.length === 0) unhandled.push(`${action}: routed to nothing`);
  }
  assert.deepEqual(unhandled, []);
});

test('an unknown verb throws rather than being silently dropped', () => {
  const route = createIntentRouter({ ops: spyOps() });
  assert.throws(
    () => route({ action: 'teleport', context: ctx, itemId: 'x' }),
    /no handler for verb 'teleport'/,
  );
});

test('colour verbs carry the token through, not a literal', () => {
  const ops = spyOps();
  createIntentRouter({ ops })({ action: 'color:signal', context: ctx, itemId: 'x' });
  assert.deepEqual(ops.calls, [['colour', ['n1'], 'signal']]);
  assert.equal(colourTokenOf('color:royal'), 'royal');
  assert.equal(colourTokenOf('hide'), null);
});

test('an async verb that rejects is surfaced, not swallowed', async () => {
  const errors = [];
  const ops = { ...spyOps(), expand: () => Promise.reject(new Error('parser 500')) };
  createIntentRouter({ ops, onError: (v, e) => errors.push([v, e.message]) })(
    { action: 'expand', context: ctx, itemId: 'x' },
  );
  await new Promise((r) => setTimeout(r, 0));
  assert.deepEqual(errors, [['expand', 'parser 500']]);
});

// ── view state ────────────────────────────────────────────────────────────

test('view state survives a round trip and stays sparse', () => {
  let s = viewActions.hide(EMPTY_VIEW_STATE, ['a', 'b']);
  assert.deepEqual(s, { a: { hidden: true }, b: { hidden: true } });
  assert.equal(anyHidden(s), true);

  s = viewActions.showAll(s);
  assert.deepEqual(s, {}, 'unhiding everything must leave no empty records behind');
  assert.equal(anyHidden(s), false);
});

test('pin toggles the whole selection to one state, not per node', () => {
  let s = viewActions.togglePin(EMPTY_VIEW_STATE, ['a']);
  assert.equal(s.a.pinned, true);
  // 'b' is unpinned, so a mixed selection pins rather than unpinning 'a'.
  s = viewActions.togglePin(s, ['a', 'b']);
  assert.equal(s.a.pinned, true);
  assert.equal(s.b.pinned, true);
  // Now uniform, so it unpins.
  s = viewActions.togglePin(s, ['a', 'b']);
  assert.deepEqual(s, {});
});

test('colour and hide compose without clobbering each other', () => {
  let s = viewActions.colour(EMPTY_VIEW_STATE, ['a'], 'gold');
  s = viewActions.hide(s, ['a']);
  assert.deepEqual(s.a, { colorToken: 'gold', hidden: true });
  s = viewActions.showAll(s);
  assert.deepEqual(s.a, { colorToken: 'gold' }, 'unhiding must not discard colour');
});

test('the state is serializable — it has to survive a cache replay', () => {
  let s = viewActions.colour(EMPTY_VIEW_STATE, ['a', 'b'], 'sky');
  s = viewActions.togglePin(s, ['b']);
  assert.deepEqual(JSON.parse(JSON.stringify(s)), s);
});
