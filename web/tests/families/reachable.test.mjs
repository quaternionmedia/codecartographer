/**
 * The families are reachable here, as data rather than as an import.
 *
 * `records/DRAFT-a-family-is-bordered-by-what-it-drives.md` in the governance
 * corpus states which repositories are one working system. This host draws
 * maps, so it has to be able to reach that list and render it.
 *
 * NOT AN IMPORT. Pulling a governance tool into a front end to draw a picture
 * is the coupling `records/DRAFT-seams-on-standard-protocols.md` prevents. The
 * seam is a schema and a path: `families.json`, generated beside this clone,
 * read as JSON.
 *
 * What it cannot say: whether anybody is working on a family. That is
 * `attention`, a different claim, and the artifact carries a `do_not` saying so.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const FAMILIES = join(here, '..', '..', '..', '..', 'qm', 'families.json');

function families() {
  if (!existsSync(FAMILIES)) return null;
  return JSON.parse(readFileSync(FAMILIES, 'utf8'));
}

test('the artifact is shaped the way this host reads it', (t) => {
  const doc = families();
  if (!doc) return t.skip(`the governance corpus is not beside this clone (${FAMILIES})`);
  assert.equal(doc.schema, 1);
  for (const f of doc.families) {
    assert.ok(f.name, 'a family has a name');
    assert.ok(Array.isArray(f.members), `${f.name} has members`);
    assert.ok(f.drives, `${f.name} says what it drives`);
  }
});

test('this host is in the core family', (t) => {
  const doc = families();
  if (!doc) return t.skip('the governance corpus is not beside this clone');
  const core = doc.families.find((f) => f.name === 'core');
  assert.ok(core, 'a core family is declared');
  assert.ok(core.members.includes('codecartographer'));
  assert.ok(core.members.includes('dossier'));
});

test('unstated is carried, never folded into a family', (t) => {
  const doc = families();
  if (!doc) return t.skip('the governance corpus is not beside this clone');
  assert.ok(Array.isArray(doc.unstated));
  const placed = new Set(doc.families.flatMap((f) => f.members));
  for (const name of doc.unstated) {
    assert.ok(!placed.has(name), `${name} is both placed and unstated`);
  }
});

test('the artifact states what it must not be read as', (t) => {
  const doc = families();
  if (!doc) return t.skip('the governance corpus is not beside this clone');
  assert.match(doc.reading.do_not, /attention/);
});
