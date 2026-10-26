/**
 * The Open panel's plots draw only the answer to the latest one asked for.
 *
 * **THE DEFECT THIS PINS.** `plotUploads` took no ticket: press Plot over
 * added files, then Load Demo, and a slow `/parse/unified` answer arrived
 * after the demo and replaced it. `latest_plot.ts` holds the order, and
 * `tests/pure/latest-plot.test.mjs` asserts it, compiled; this asserts that
 * added files, the demo and a lexicon are plotted through it, and that a
 * stream, which draws by another way, drops what is still out.
 *
 * Read as text, as `folder-reads-leave-the-stream.test.mjs` reads the
 * controller: `actions.ts` and `layout_context.ts` are application code no
 * test build compiles.
 *
 *   npm run test:state
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const actions = readFileSync('src/state/actions.ts', 'utf8');
const layout = readFileSync('src/layout/layout_context.ts', 'utf8');

/** The body of PlotActions' method `name`. */
function methodBody(name) {
  const found = new RegExp(`\\n  async ${name}\\([^)]*\\): [^{]+\\{([\\s\\S]*?)\\n  \\}\\n`).exec(actions);
  return found ? found[1] : null;
}

for (const name of ['plotUploads', 'loadDemo', 'loadLexicon']) {
  test(`${name} asks and draws through the one latest-plot ticket`, () => {
    /** Mutation: ask /parse/unified and draw its answer directly in plotUploads -- this fails. */
    const body = methodBody(name);
    assert.ok(body, `${name} was not found in actions.ts; the pattern is stale`);
    assert.match(body, /this\.plots\.plot\(/, `${name} draws without taking a ticket`);
    assert.doesNotMatch(body, /stateController\.clear\(\)/,
      `${name} clears the canvas itself, beside the ticket that clears it`);
  });
}

/** The body of the panel callback or private method `name` in layout_context.ts. */
function layoutBody(name) {
  const found = new RegExp(`\\n {2,6}(?:private async )?${name}(?:: async)? ?\\([^)]*\\)(?:: Promise<void>)?(?: =>)? \\{([\\s\\S]*?)\\n {2,6}\\},?\\n`).exec(layout);
  return found ? found[1] : null;
}

for (const name of ['_plotUploads', 'onDemo', 'onLoadLexicon']) {
  test(`${name} says "Ready" only for a plot that drew`, () => {
    /**
     * A dropped plot set `isLoading` false and "Ready" when it answered, over
     * the stream that replaced it: Cancel and the progress bar went while it
     * ran. Mutation: say "Ready" whether or not it drew -- this fails.
     */
    const body = layoutBody(name);
    assert.ok(body, `${name} was not found in layout_context.ts; the pattern is stale`);
    const ready = body.split('\n').filter((line) => line.includes("statusMessage: 'Ready'"));
    assert.ok(ready.length > 0, `${name} says "Ready" nowhere; the pattern is stale`);
    for (const line of ready) assert.match(line, /^\s*if \(/, `${name} says "Ready" for a plot that was dropped`);
  });
}

test('a stream begun drops an answer the Open panel is still waiting for', () => {
  /** Mutation: no `supersedePlots()` in `_mountAndStream` -- a slow parse replaces the streamed graph, and this fails. */
  const found = /\n {2}private _mountAndStream\([\s\S]*?\n {2}\}\n/.exec(layout);
  assert.ok(found, '_mountAndStream was not found in layout_context.ts; the pattern is stale');
  assert.match(found[0], /this\.actions\.plot\.supersedePlots\(\)/);
});
