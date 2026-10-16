// Run every *.test.mjs in the directories named, with Node's own test runner.
//
// `node --test tests/pure/` runs a directory on Node 20 and fails on Node 22,
// which reads the argument as a module path. A glob works on 22 and not on 20,
// and npm on Windows runs scripts through cmd, which expands nothing. Naming
// the files works on every version and every shell. The working directory
// stays web/, which some suites read files relative to.
import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

const dirs = process.argv.slice(2);
const files = dirs.flatMap((dir) =>
  readdirSync(dir)
    .filter((name) => name.endsWith('.test.mjs'))
    .sort()
    .map((name) => join(dir, name)),
);

if (files.length === 0) {
  console.error(`node-test: no *.test.mjs in ${dirs.join(', ') || '(no directory given)'}`);
  process.exit(1);
}

const run = spawnSync(process.execPath, ['--test', ...files], { stdio: 'inherit' });
process.exit(run.status ?? 1);
