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

// The schemas `codecarto/services/show_service.py` reads. Schema 2 lets a
// family sit within another and a repository claim several families; a schema
// this list does not name is one the window would misdraw, so it fails here.
const KNOWN = [1, 2];

test('the artifact is shaped the way this host reads it', (t) => {
  const doc = families();
  if (!doc) return t.skip(`the governance corpus is not beside this clone (${FAMILIES})`);
  assert.ok(KNOWN.includes(doc.schema), `schema ${doc.schema} is not one of ${KNOWN}`);
  const names = new Set(doc.families.map((f) => f.name));
  for (const f of doc.families) {
    assert.ok(f.name, 'a family has a name');
    assert.ok(Array.isArray(f.members), `${f.name} has members`);
    assert.ok(f.drives, `${f.name} says what it drives`);
    if (doc.schema < 2) continue;
    assert.ok(f.within === null || names.has(f.within), `${f.name} is within a declared family`);
    assert.ok(Array.isArray(f.subfamilies), `${f.name} lists its subfamilies`);
    for (const sub of f.subfamilies) {
      assert.equal(doc.families.find((g) => g.name === sub)?.within, f.name,
        `${sub} is listed under ${f.name} and says so itself`);
    }
    for (const m of f.members) {
      assert.ok(f.all_members.includes(m), `${f.name}'s own member ${m} is in all_members`);
    }
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
