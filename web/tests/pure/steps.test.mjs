/**
 * The four steps from opening source to reading its graph, and what entering
 * each leaves in view.
 *
 * The dock is a model of Golden Layout's stacks -- each shows one window, and
 * a maximised one hides every other -- so what a step leaves in view is
 * asserted without a browser. steps.spec.ts sees it in one.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import {
  FIRST_STEP, STEPS, enterStep, nextStep, previousStep, stepNamed, stepNumber, stepOfPanel,
} from '../../dist-pure/layout/steps.js';

/** Every window `panel_registry.ts` registers, read as the docs test reads it. */
const REGISTERED = [...readFileSync('src/layout/panel_registry.ts', 'utf8').matchAll(/^\s+id: '([a-z-]+)',/gm)]
  .map((match) => match[1]);

/**
 * Stacks of windows, as Golden Layout keeps them: each shows its active
 * window, and while one is maximised it is the only stack shown. Showing a
 * window does not restore a maximised stack -- that is the step's to do.
 * Opening a closed window is `LayoutContext`'s, and steps.spec.ts sees it.
 */
function dock(...stacks) {
  const state = { stacks: stacks.map((ids) => ({ ids: [...ids], active: ids[0] })), maximised: null, focused: null };
  const stackOf = (id) => state.stacks.find((s) => s.ids.includes(id));
  return {
    state,
    show(id, focus) {
      stackOf(id).active = id;
      if (focus) state.focused = id;
    },
    maximise(id) { state.maximised = stackOf(id); },
    restore() { state.maximised = null; },
    /** The windows a reader can see. */
    inView() {
      const shown = state.maximised ? [state.maximised] : state.stacks;
      return shown.map((s) => s.active).sort();
    },
  };
}

/** The default layout: the canvas, then Files beside Open, Graph Settings and Estate. */
const defaultDock = () => dock(['graph'], ['file-tree'], ['open', 'graph-settings-panel', 'estate-panel']);

test('four steps, numbered from 1: Open, Browse, Tune, Read', () => {
  /** Mutation: call step 2 "Files" -- this fails, and so does the docs test that reads `docs/ui.md`'s table. */
  assert.deepEqual(STEPS.map((s) => `${stepNumber(s.id)} ${s.label}`), ['1 Open', '2 Browse', '3 Tune', '4 Read']);
  assert.equal(FIRST_STEP, 'open');
});

test('each step says what comes next, and the last says nothing', () => {
  /** Mutation: let nextStep wrap from Read to Open -- this fails. */
  assert.deepEqual(STEPS.map((s) => nextStep(s.id)?.id ?? null), ['browse', 'tune', 'read', null]);
  assert.deepEqual(STEPS.map((s) => previousStep(s.id)?.id ?? null), [null, 'open', 'browse', 'tune']);
});

test('a step that is not one is the first', () => {
  /** Mutation: let stepNamed fall back to the last step -- this fails. */
  assert.equal(stepNamed('render').id, 'open');
  assert.equal(stepNamed(undefined).id, 'open');
});

test('every registered window belongs to exactly one step', () => {
  /**
   * Choosing a window's tab says which step the reader is on, so a window no
   * step owns would leave the rail where it was. Mutation: drop 'cargo-panel'
   * from Open's `owns` -- this fails naming it.
   */
  assert.ok(REGISTERED.length > 0, 'no window ids found in panel_registry.ts; the pattern is stale');
  const owners = (id) => STEPS.filter((s) => s.owns.includes(id)).map((s) => s.id);
  const wrong = REGISTERED.filter((id) => owners(id).length !== 1).map((id) => `${id}: ${owners(id).join(', ') || 'none'}`);
  assert.deepEqual(wrong, []);
  const unregistered = STEPS.flatMap((s) => [...s.owns, ...s.forward]).filter((id) => !REGISTERED.includes(id));
  assert.deepEqual(unregistered, [], 'a step names a window panel_registry.ts does not register');
});

test('the tab chosen names its step', () => {
  /** Mutation: let stepOfPanel answer step 1 for a window no step owns -- the rail would move on a stale tab, and this fails. */
  assert.equal(stepOfPanel('estate-panel'), 'open');
  assert.equal(stepOfPanel('file-tree'), 'browse');
  assert.equal(stepOfPanel('graph-settings-panel'), 'tune');
  assert.equal(stepOfPanel('graph'), 'read');
  assert.equal(stepOfPanel('upload-panel'), null);
});

test('each step brings its own window forward first, and the canvas with it', () => {
  /** Mutation: drop 'graph' from Browse's `forward` -- this fails. */
  for (const step of STEPS) {
    assert.ok(step.owns.includes(step.forward[0]), `${step.id} is about a window it does not own`);
    assert.ok(step.forward.includes('graph'), `${step.id} leaves the canvas where it was`);
  }
});

test('in the default layout, each step leaves its window in view and hides what it does not need', () => {
  /** Mutation: set Read's `alone` to false -- Read leaves Files and Open in view, and this fails. */
  const expected = {
    open: ['file-tree', 'graph', 'open'],
    browse: ['file-tree', 'graph', 'open'],
    tune: ['file-tree', 'graph', 'graph-settings-panel'],
    read: ['graph'],
  };
  for (const step of STEPS) {
    const d = defaultDock();
    enterStep(step.id, d);
    assert.deepEqual(d.inView(), expected[step.id], `step ${step.id}`);
    assert.equal(d.state.focused, step.forward[0], `step ${step.id} focuses another window`);
  }
});

test('leaving Read restores the windows the canvas hid', () => {
  /** Mutation: drop `dock.restore()` from enterStep -- Tune stays behind the canvas, and this fails. */
  const d = defaultDock();
  enterStep('read', d);
  enterStep('tune', d);
  assert.deepEqual(d.inView(), ['file-tree', 'graph', 'graph-settings-panel']);
});

test('a stack the reader maximised gives way to the step', () => {
  const d = defaultDock();
  d.maximise('file-tree');
  enterStep('open', d);
  assert.deepEqual(d.inView(), ['file-tree', 'graph', 'open']);
});

test("where a step's windows share a stack, the one it is about is in front", () => {
  /** Mutation: show `forward` in its own order rather than in reverse -- the canvas is in front, and this fails. */
  const d = dock(['open', 'graph'], ['file-tree']);
  enterStep('open', d);
  assert.deepEqual(d.inView(), ['file-tree', 'open']);
});

