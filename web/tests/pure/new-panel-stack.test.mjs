/**
 * Where a window the "+" menu opens is added: beside the stack whose tab the
 * reader last clicked, else in the fullest stack, and never over the canvas
 * while another stack exists.
 *
 * The dock is plain objects shaped as Golden Layout's items are (`isStack`,
 * `contentItems`, `element`), so the choice is asserted without a browser.
 * add-window.spec.ts sees it in one: the demo graph left in view.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { stackForNewPanel, stackOfTabClicked } from '../../dist-pure/layout/new_panel_stack.js';

const component = (id) => ({ isStack: false, contentItems: [], id });
const stack = (name, ...ids) => ({ isStack: true, contentItems: ids.map(component), element: { name } });
const row = (...items) => ({ isStack: false, contentItems: items });

/** The default layout's shape: the canvas above, Files beside the dock's tabs below. */
function dock() {
  const canvas = stack('canvas', 'graph');
  const files = stack('files', 'file-tree');
  const tabs = stack('tabs', 'open', 'graph-settings-panel', 'estate-panel');
  return { canvas, files, tabs, root: { isStack: false, contentItems: [canvas, row(files, tabs)] } };
}

test('with no tab clicked, the fullest stack that is not the canvas', () => {
  const d = dock();
  assert.equal(stackForNewPanel(d.root, d.canvas, null), d.tabs);
});

test('beside the stack whose tab the reader last clicked', () => {
  /**
   * Golden Layout's own focus is no guide: it moves on a tab click and from
   * code, and every draw focuses the Graph panel. What the reader clicked is
   * recorded apart from it. Mutation: ignore the stack clicked -- this fails.
   */
  const d = dock();
  assert.equal(stackForNewPanel(d.root, d.canvas, d.files.element), d.files);
});

test("a tab clicked in the canvas's own stack does not put the window over the canvas", () => {
  /**
   * Click the Graph tab, then add a window: in the canvas's stack its tab
   * hides the graph. Mutation: drop the `!== canvas` guard -- this fails.
   */
  const d = dock();
  assert.equal(stackForNewPanel(d.root, d.canvas, d.canvas.element), d.tabs);
});

test("the canvas's stack is not the fullest, however many tabs it holds", () => {
  /** Mutation: drop the `!== canvas` guard -- this fails as well. */
  const canvas = stack('canvas', 'graph', 'cargo-panel', 'topology-panel', 'overview-panel');
  const files = stack('files', 'file-tree');
  const root = row(canvas, files);
  assert.equal(stackForNewPanel(root, canvas, null), files);
});

test('a stack clicked and since closed is passed over', () => {
  /** Its tabs closed or dragged away, the stack is gone; its element names nothing. */
  const d = dock();
  assert.equal(stackForNewPanel(d.root, d.canvas, { name: 'gone' }), d.tabs);
});

test('with the canvas the only stack, Golden Layout places it', () => {
  const canvas = stack('canvas', 'graph');
  assert.equal(stackForNewPanel(row(canvas), canvas, canvas.element), null);
  assert.equal(stackForNewPanel(undefined, null, null), null);
});

test("a click on a tab is its stack's; on a tab's close button, or off the tabs, nothing", () => {
  const at = (...inside) => ({
    closest: (selector) => (inside.includes(selector) ? { selector } : null),
  });
  assert.deepEqual(stackOfTabClicked(at('.lm_tab', '.lm_stack')), { selector: '.lm_stack' });
  assert.equal(stackOfTabClicked(at('.lm_close_tab', '.lm_tab', '.lm_stack')), null, 'closing a tab chooses nothing');
  assert.equal(stackOfTabClicked(at('.lm_stack')), null, 'a click in a panel is not a tab');
  assert.equal(stackOfTabClicked(null), null);
});
