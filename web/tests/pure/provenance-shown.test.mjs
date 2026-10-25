/**
 * A panel leaves out its reading's caveat only when the strip above it is
 * saying that same sentence.
 *
 * The Cargo, Chrestomathy, Capabilities and Overview panels each hold a
 * reading with its caveat, and the provenance strip shows the drawn graph's.
 * Once a graph was drawn they said it twice, so the panel's copy is left out
 * while the strip says it -- but reading another workspace does not redraw:
 * draw A, read B, and the strip still says A's caveat. Leaving out B's because
 * the strip says *a* caveat hid the one sentence about what is listed.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { caveatShown, stripShown } from '../../dist-pure/features/estate/provenance_shown.js';

const A = 'read from the manifests of /ws/a: cargo was not run, so features are not resolved';
const B = 'read from the manifests of /ws/b: cargo was not run, so features are not resolved';

test('the strip says the caveat of the graph that is drawn, so the same reading says it once', () => {
  assert.equal(caveatShown({ kind: 'cargo', caveat: A }, 'cargo', A), true);
});

test("another reading's caveat is said while the strip says the drawn graph's", () => {
  assert.equal(caveatShown({ kind: 'cargo', caveat: A }, 'cargo', B), false);
});

test('before a draw, or under a graph of another seam, the panel says it', () => {
  assert.equal(caveatShown(null, 'cargo', A), false);
  assert.equal(caveatShown({ kind: 'cargo' }, 'cargo', A), false);
  assert.equal(caveatShown({ kind: 'overview', caveat: A }, 'cargo', A), false);
});

test('the strip is drawn for its own seam, or for metadata that names none', () => {
  assert.equal(stripShown({ kind: 'cargo' }, 'cargo'), true);
  assert.equal(stripShown({}, 'cargo'), true);
  assert.equal(stripShown({ kind: 'overview' }, 'cargo'), false);
  assert.equal(stripShown(undefined, 'cargo'), false);
});
