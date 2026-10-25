/**
 * Reading a folder into the Files panel's tree leaves the stream's state alone.
 *
 * **THE DEFECT THIS PINS.** `panelState.isLoading` and its status line are the
 * stream's: the Open panel's Plot bar shows Cancel and the progress bar while
 * it is set. The folder click set it, and when the read ended set it false with
 * "Ready" -- so a folder opened while a repository was still parsing took
 * Cancel and the progress bar away from a stream that was still running.
 * Expand All did the same.
 *
 * Read as text, as `graph-data-replacement.test.mjs` reads the controller:
 * `layout_context.ts` mounts Golden Layout and the DOM, and no test build
 * compiles it. What a read does to the tree is asserted, compiled, in
 * `tests/pure/repo-tree.test.mjs`.
 *
 *   npm run test:state
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync('src/layout/layout_context.ts', 'utf8');

/** The body of the panel callback `name`, as `panelCallbacks` writes it. */
function handlerBody(name) {
  const found = new RegExp(`\\n      ${name}: async \\([^)]*\\) => \\{([\\s\\S]*?)\\n      \\},`).exec(source);
  return found ? found[1] : null;
}

for (const name of ['onFolderExpand', 'onExpandAll']) {
  test(`${name} does not touch the stream's loading state`, () => {
    /** Mutation: set `isLoading` back to false when the read ends -- this fails. */
    const body = handlerBody(name);
    assert.ok(body, `${name} was not found in layout_context.ts; the pattern is stale`);
    assert.doesNotMatch(body, /updatePanelState|isLoading|statusMessage|progress/,
      `${name} writes the panel state a running stream shows`);
  });
}
