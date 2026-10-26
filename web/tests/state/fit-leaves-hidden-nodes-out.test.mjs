/**
 * Every canvas a plot announces is told which nodes are hidden, so its fit
 * leaves them out.
 *
 * **THE DEFECT THIS PINS.** Hide is view state the layout context keeps and
 * rad paints: a hidden node is drawn at opacity 0 and stays in the renderer's
 * `nodeById`, so the fit after a stream, and Fit, framed it, and the frame was
 * centred off what is drawn. What a fit frames is asserted, compiled, in
 * `tests/pure/fit.test.mjs`; this holds the renderer to the host's view
 * state, on the one subscription every path that draws announces its canvas
 * to.
 *
 * Read as text, as `folder-reads-leave-the-stream.test.mjs` reads the
 * controller: `layout_context.ts` mounts Golden Layout and the DOM, and no
 * test build compiles it.
 *
 *   npm run test:state
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync('src/layout/layout_context.ts', 'utf8');

test('each announced canvas reads hidden nodes from the view state before rad mounts', () => {
  /** Mutation: drop the setHiddenTest call -- the fit frames hidden nodes again, and this fails. */
  const found = /GraphSurface\.subscribe\(\((\w+)\) => \{([\s\S]*?)\n    \}\);/.exec(source);
  assert.ok(found, 'the GraphSurface subscription was not found in layout_context.ts; the pattern is stale');
  const [, renderer, body] = found;
  const told = body.indexOf(`${renderer}.setHiddenTest(`);
  assert.ok(told >= 0, 'the announced renderer is never told which nodes are hidden');
  assert.match(body.slice(told), /^[^\n]*this\._nodeViewState\[\w+\]\?\.hidden/,
    'the hidden test does not read the view state Hide writes');
  assert.ok(told < body.indexOf('this._mountRad('), 'the hidden test is set after rad mounts');
});
