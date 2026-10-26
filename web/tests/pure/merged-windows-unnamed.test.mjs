/**
 * No code or test names a window this version folded into Open.
 *
 * **THE DEFECT THIS PINS.** Upload, Repository and Actions are one Open
 * window, and a merge from main brought back comments and docstrings that
 * named them: "the Repository panel's URL field", "the Actions panel shows
 * Cancel". A sentence naming a window the dock cannot draw sends its reader
 * looking for it. `saved_layout.ts` names their ids, which a saved layout may
 * still hold; that is the one place they belong. `docs/ui.md` is read against
 * the registry by `tests/test_docs_routes.py`.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';

/** The windows Open replaced, by the label each had in the "+" menu. */
const MERGED = ['Upload', 'Repository', 'Actions'];

const registry = readFileSync('src/layout/panel_registry.ts', 'utf8');
const LABELS = [...registry.matchAll(/menuLabel: '([^']+)'/g)].map((m) => m[1]);

/** Every source and test file under the roots given, relative to web/, but this one, which quotes them. */
function files(...roots) {
  return roots.flatMap((root) => readdirSync(root, { recursive: true, withFileTypes: true })
    .filter((e) => e.isFile() && /\.(ts|mjs|js|py)$/.test(e.name))
    .map((e) => join(e.parentPath ?? e.path, e.name))
    .filter((p) => !/node_modules|dist-|__pycache__|merged-windows-unnamed/.test(p)));
}

test('the windows Open replaced are not in the registry', () => {
  assert.ok(LABELS.includes('Open'), 'no menu labels read from panel_registry.ts; the pattern is stale');
  assert.deepEqual(MERGED.filter((name) => LABELS.includes(name)), []);
});

test('no code or test names a window Open replaced as one the dock has', () => {
  /** Mutation: say "the Repository panel's URL field" in repo_tree.ts -- this fails naming it. */
  const named = new RegExp(`\\b(${MERGED.join('|')}) (panel|window|tab)\\b`);
  const found = files('src', 'tests', '../tests', '../codecarto')
    .flatMap((path) => readFileSync(path, 'utf8').split('\n')
      .map((line, i) => [path, i + 1, line])
      .filter(([, , line]) => named.test(line))
      .map(([p, n, line]) => `${p.replaceAll('\\', '/')}:${n}: ${line.trim()}`));
  assert.ok(files('src').length > 50, 'no source files read; the pattern is stale');
  assert.deepEqual(found, []);
});
