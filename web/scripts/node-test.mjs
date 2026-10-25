// Run the test files in the directories named, with Node's own test runner.
//
// `node --test tests/pure/` runs a directory on Node 20 and fails on Node 22,
// which reads the argument as a module path. A glob works on 22 and not on 20,
// and npm on Windows runs scripts through cmd, which expands nothing. Naming
// the files works on every version and every shell. The working directory
// stays web/, which some suites read files relative to.
//
// The files are the ones Node's runner finds in a directory: searched
// recursively, node_modules skipped, a .js, .cjs or .mjs file named `test`,
// `test-*`, `*.test`, `*-test` or `*_test`, and any of those three kinds under
// a directory named `test`. tests/pure/node-test-runner.test.mjs holds it to
// that.
import { readdirSync } from 'node:fs';
import { basename, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const SCRIPT = /\.(c|m)?js$/;
const NAMED = /^(test|test-.+|.+[._-]test)\.(c|m)?js$/;

function testFiles(dir, underTest) {
  return readdirSync(dir, { withFileTypes: true })
    .sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))
    .flatMap((entry) => {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === 'node_modules') return [];
        return testFiles(path, underTest || entry.name === 'test');
      }
      return (underTest ? SCRIPT : NAMED).test(entry.name) ? [path] : [];
    });
}

const dirs = process.argv.slice(2);
const files = dirs.flatMap((dir) => testFiles(dir, basename(resolve(dir)) === 'test'));

if (files.length === 0) {
  console.error(`node-test: no test file in ${dirs.join(', ') || '(no directory given)'}`);
  process.exit(1);
}

const run = spawnSync(process.execPath, ['--test', ...files], { stdio: 'inherit' });
process.exit(run.status ?? 1);
