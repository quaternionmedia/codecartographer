/**
 * Every dock tab a browser test clicks is one this version's registry draws.
 *
 * **THE DEFECT THIS PINS.** `file-tree.spec.ts` clicked the "Repository" tab
 * after the Open panel replaced Upload, Repository and Actions, so the case
 * could only time out. The browser suites bind fixed ports and are not run
 * everywhere the node suites are; this reads each spec's tab clicks against
 * `panel_registry.ts`'s titles without a browser. A tab the specs name only
 * to say it is gone (`toHaveCount(0)`) is not a click and is not read.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { test } from 'node:test';

const registry = readFileSync('src/layout/panel_registry.ts', 'utf8');
const TITLES = [...registry.matchAll(/config: \{[^}]*\btitle: '([^']+)'/g)].map((m) => m[1]);

const SPECS = readdirSync('tests/e2e').filter((f) => f.endsWith('.spec.ts'));

/** Each `.lm_tab` locator a spec clicks: its file, and the text it asks the tab to hold. */
function tabClicks() {
  const found = [];
  for (const file of SPECS) {
    const text = readFileSync(`tests/e2e/${file}`, 'utf8');
    const click = /locator\('\.lm_tab', \{ hasText: ('([^']+)'|\/((?:[^/\\]|\\.)+)\/) \}\)\.click\(\)/g;
    for (const m of text.matchAll(click)) {
      found.push({ file, asked: m[1], holds: m[2] !== undefined ? (t) => t.includes(m[2]) : (t) => new RegExp(m[3]).test(t) });
    }
  }
  return found;
}

test('the registry titles are read', () => {
  assert.ok(TITLES.length >= 5, 'no titles read from panel_registry.ts; the pattern is stale');
  assert.ok(TITLES.includes('⬇ Open'), 'the Open panel title was not read; the pattern is stale');
});

test('each tab a browser test clicks is one the registry draws', () => {
  /** Mutation: click `{ hasText: 'Repository' }` in file-tree.spec.ts -- this fails naming it. */
  const clicks = tabClicks();
  assert.ok(clicks.length > 0, 'no tab click found in tests/e2e; the pattern is stale');
  const missing = clicks.filter((c) => !TITLES.some(c.holds)).map((c) => `${c.file}: ${c.asked}`);
  assert.deepEqual(missing, [], 'a spec clicks a tab no registered panel is titled with');
});
