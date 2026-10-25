/**
 * The Open panel says a repository is loaded when the Files panel shows one.
 *
 * **THE DEFECT THIS PINS.** The Open panel judged a repository loaded by its
 * tree's `size`. Expand All's tree carries its root folder's own file count
 * there, 0 for a repository with only folders at its root, so after Expand
 * All the loaded line and its ✕ went, and Plot said it would fetch the URL in
 * the field, while the Files panel, which asks `hasTree`, still showed the
 * tree. The loaded line asks `hasTree`, and the Plot bar asks `plotTarget`,
 * which `onPlot` asks; `tests/pure/plot-target.test.mjs` asserts that, compiled.
 *
 * Read as text: `control_panel.ts` renders Mithril, and no test build compiles it.
 *
 *   npm run test:state
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync('src/components/codecarto/control_panel/control_panel.ts', 'utf8');

/** The body of the render helper `name`, as `ControlPanel` writes it. */
function helperBody(name) {
  const found = new RegExp(`\\n  const ${name} = \\(\\) => \\{([\\s\\S]*?)\\n  \\};`).exec(source);
  return found ? found[1] : null;
}

test("the Open panel never judges a tree loaded by its size", () => {
  /** Mutation: `content.repoDirectory.size > 0` in either helper -- this fails. */
  assert.doesNotMatch(source, /repoDirectory\??\.size\s*>\s*0/,
    "control_panel.ts judges a tree loaded by its size, which an Expand All tree's root with only folders sets to 0");
});

test('the loaded line asks hasTree, as the Files panel does', () => {
  const body = helperBody('renderUrlSection');
  assert.ok(body, 'renderUrlSection was not found in control_panel.ts; the pattern is stale');
  assert.match(body, /hasTree\(content\.repoDirectory\)/);
});

test('the Plot bar names what Plot draws by asking plotTarget, as onPlot does', () => {
  const body = helperBody('renderPlotBar');
  assert.ok(body, 'renderPlotBar was not found in control_panel.ts; the pattern is stale');
  assert.match(body, /plotTarget\(content\.repoDirectory, /);
});
