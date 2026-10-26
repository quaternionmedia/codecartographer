/**
 * scripts/node-test.mjs runs what `node --test <dir>` ran on Node 20.
 *
 * **THE DEFECT THIS PINS.** The script listed the top level of each directory
 * it was given and kept `*.test.mjs`. Node's runner, which the suites used
 * before it, searches a directory recursively, skips node_modules, and takes
 * `test`, `test-*`, `*.test`, `*-test` and `*_test` as `.js`, `.cjs` or
 * `.mjs`, and every such file under a directory named `test`. A test added at
 * tests/pure/sub/x.test.mjs would never have run, and the suite would still
 * have passed.
 *
 * Each case runs the script on a tree made for it, from inside that tree: a
 * script that handed `node --test` no files would have it search the working
 * directory, and from web/ that is this suite, running itself. The trees'
 * files append their own names to a log, so what ran is read rather than
 * inferred from a count.
 */

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const SCRIPT = fileURLToPath(new URL('../../scripts/node-test.mjs', import.meta.url));

/** A file that logs its name when it runs, in the syntax its extension is read in. */
function logs(name) {
  const line = `appendFileSync(process.env.RAN_LOG, ${JSON.stringify(`${name}\n`)});`;
  return name.endsWith('.mjs')
    ? `import { appendFileSync } from 'node:fs';\n${line}\n`
    : `const { appendFileSync } = require('node:fs');\n${line}\n`;
}

/** A directory holding `files`, removed when the test ends. */
function tree(t, files) {
  const root = mkdtempSync(join(tmpdir(), 'node-test-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const [name, body] of Object.entries(files)) {
    const path = join(root, name);
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, body ?? logs(name));
  }
  return root;
}

/** Run the script on `root`; what ran, by name, and how it exited. */
function run(root) {
  const log = join(root, 'ran.log');
  const env = { ...process.env, RAN_LOG: log };
  // This file runs under the test runner, which marks its children; the
  // script's own runner must not take itself for one of them.
  delete env.NODE_TEST_CONTEXT;
  const result = spawnSync(process.execPath, [SCRIPT, root], { cwd: root, env, encoding: 'utf8' });
  const ran = existsSync(log) ? readFileSync(log, 'utf8').split('\n').filter(Boolean).sort() : [];
  return { status: result.status, ran, output: `${result.stdout}${result.stderr}` };
}

const TESTS = [
  'sub/deep.test.mjs',
  'sub/deeper/deepest.test.mjs',
  'sub/test/anything.mjs',
  'test-lead.mjs',
  'test.mjs',
  'top.test.mjs',
  'trail-test.mjs',
  'under_test.mjs',
  'x.test.js',
  'y.test.cjs',
];
const NOT_TESTS = [
  'a.spec.mjs',
  'contest.mjs',
  'helper.mjs',
  'node_modules/pkg/z.test.mjs',
  'testing.mjs',
];

test('runs every file Node\'s runner finds in a directory, and no other', (t) => {
  const root = tree(t, Object.fromEntries([...TESTS, ...NOT_TESTS].map((name) => [name, null])));
  const { status, ran, output } = run(root);
  assert.deepEqual(ran, [...TESTS].sort(), output);
  assert.equal(status, 0, output);
});

test('a failing test in a subdirectory fails the run', (t) => {
  const root = tree(t, {
    'passes.test.mjs': null,
    'sub/fails.test.mjs':
      "import assert from 'node:assert/strict';\nimport { test } from 'node:test';\n"
      + "test('fails', () => assert.fail('a nested test ran and failed'));\n",
  });
  const { status, output } = run(root);
  assert.equal(status, 1, output);
});

test('a directory with no test file in it fails rather than passing on nothing', (t) => {
  const root = tree(t, { 'helper.mjs': null, 'sub/notes.json': '{}' });
  const { status, ran, output } = run(root);
  assert.deepEqual(ran, []);
  assert.equal(status, 1, output);
  assert.match(output, /no test file/);
});
