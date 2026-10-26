/**
 * The Open panel's Plot draws the repository the Files panel shows.
 *
 * **THE DEFECT THIS PINS.** With a repository loaded, Plot streamed
 * `panelState.repoUrl` -- the URL field, which follows every keystroke. Fetch
 * A, type B and press ▶ Plot, and B was streamed while the Files panel showed
 * A; `_lastPlotAction` re-ran it on the next layout change or Relayout, so B
 * came back each time. `plot_target.ts` decides what Plot draws from the shown
 * tree, and `tests/pure/plot-target.test.mjs` asserts that decision, compiled.
 * This asserts that `onPlot` asks it and reads the field nowhere else.
 *
 * Read as text, as `folder-reads-leave-the-stream.test.mjs` reads the
 * controller: `layout_context.ts` mounts Golden Layout and the DOM, and no test
 * build compiles it.
 *
 *   npm run test:state
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync('src/layout/layout_context.ts', 'utf8');

/** The body of `onPlot`, as `_buildCallbacks` writes it. */
function onPlotBody() {
  const found = /\n {6}onPlot: \(\) => \{([\s\S]*?)\n {6}\},/.exec(source);
  return found ? found[1] : null;
}

test('Plot asks plot_target.ts what to draw, and reads the URL field only as its last resort', () => {
  /** Mutation: stream `this.panelState.repoUrl` when a tree is loaded -- this fails. */
  const body = onPlotBody();
  assert.ok(body, 'onPlot was not found in layout_context.ts; the pattern is stale');
  const asked = /plotTarget\(([^;]*)\);/.exec(body);
  assert.ok(asked, 'onPlot does not ask plotTarget what to draw');
  const rest = body.replace(asked[0], '');
  assert.doesNotMatch(rest, /repoUrl/,
    'onPlot reads the URL field beside plotTarget, which follows every keystroke and need not name the tree shown');
});

test('a Plot of the loaded repository is re-run as it was drawn, not as Plot would now decide', () => {
  /**
   * Mutation: remember `() => this.panelCallbacks.onPlot()` -- a Relayout after
   * the tree was cleared and another URL typed fetched that URL, and this fails.
   */
  const body = onPlotBody();
  assert.ok(body, 'onPlot was not found in layout_context.ts; the pattern is stale');
  assert.doesNotMatch(body, /_lastPlotAction = \(\) => \{ this\.panelCallbacks\.onPlot\(\); \}/,
    'onPlot remembers itself, so a re-run decides again from whatever is loaded and typed by then');
});
