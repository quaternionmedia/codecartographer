/**
 * The Open panel's plots draw only the latest one's answer.
 *
 * **WHAT THIS HOLDS THAT ONE ANSWER CANNOT SHOW.** The defect is an order: a
 * plot asked for, another asked for after it, and the first answering last.
 * The answers are promises the test resolves in whatever order a slow network
 * would. `tests/state/open-plots-drop-a-superseded-answer.test.mjs` holds
 * `actions.ts` to plotting through this.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { LatestPlot } from '../../dist-pure/state/latest_plot.js';

function harness() {
  const shown = [];
  let cleared = 0;
  const plots = new LatestPlot(() => { cleared++; });
  /** A request whose answer the test gives, or refuses, when it chooses. */
  const pending = () => {
    let answer, refuse;
    const promise = new Promise((resolve, reject) => { answer = resolve; refuse = reject; });
    return { ask: () => promise, answer, refuse };
  };
  const plot = (request) => plots.plot(request.ask, (a) => shown.push(a));
  return { plots, shown, pending, plot, get cleared() { return cleared; } };
}

test('Plot over files, then Load Demo: the files answering last are not drawn over the demo', async () => {
  /** Mutation: show the answer without asking whether the ticket is current -- this fails. */
  const h = harness();
  const files = h.pending();
  const demo = h.pending();
  const filesPlotted = h.plot(files);
  const demoPlotted = h.plot(demo);
  demo.answer('demo');
  assert.equal(await demoPlotted, true);
  files.answer('files');
  assert.equal(await filesPlotted, false);
  assert.deepEqual(h.shown, ['demo']);
  assert.equal(h.cleared, 2, 'each plot clears the canvas when it is asked for');
});

test('answers in the order asked are each drawn', async () => {
  const h = harness();
  const first = h.pending();
  first.answer('first');
  assert.equal(await h.plot(first), true);
  const second = h.pending();
  second.answer('second');
  assert.equal(await h.plot(second), true);
  assert.deepEqual(h.shown, ['first', 'second']);
});

test('a stream begun drops an answer still out', async () => {
  const h = harness();
  const files = h.pending();
  const plotted = h.plot(files);
  h.plots.supersede();
  files.answer('files');
  assert.equal(await plotted, false);
  assert.deepEqual(h.shown, []);
});

test("a superseded plot's failure is dropped with it, and the latest's is thrown", async () => {
  /** Mutation: rethrow every failure -- "Error plotting" is said over the demo, and this fails. */
  const h = harness();
  const files = h.pending();
  const filesPlotted = h.plot(files);
  const demo = h.pending();
  const demoPlotted = h.plot(demo);
  files.refuse(new Error('parse/unified failed'));
  assert.equal(await filesPlotted, false);
  demo.refuse(new Error('plotter/demo failed'));
  await assert.rejects(demoPlotted, /plotter\/demo failed/);
  assert.deepEqual(h.shown, []);
});
