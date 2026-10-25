/**
 * An unread folder in the Files panel reads itself once per click, and a read
 * that fails leaves it to be clicked again.
 *
 * The folder's spinner ended only when contents arrived, so a read that
 * failed -- GitHub's unauthenticated limit, or a submodule's path, which the
 * server answers with `GithubNoDataError` -- spun for good, and a folder that
 * was loading would not be read again.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { readStub } from '../../dist-pure/components/qm_comp_lib/directory/stub_read.js';

function folder() {
  const state = { isOpen: false, isLoading: false };
  let redraws = 0;
  let settle;
  let reads = 0;
  const read = () => {
    reads++;
    return new Promise((resolve, reject) => { settle = { resolve, reject }; });
  };
  return {
    state,
    get reads() { return reads; },
    get redraws() { return redraws; },
    click: () => readStub(state, read, () => { redraws++; }),
    get settle() { return settle; },
  };
}

test('a read in flight shows the folder open and loading', () => {
  const f = folder();
  void f.click();
  assert.deepEqual(f.state, { isOpen: true, isLoading: true });
  assert.equal(f.reads, 1);
  assert.ok(f.redraws >= 1, 'drawn open before the answer');
});

test('a read that fails ends the spinner and closes the folder, so a click reads it again', async () => {
  /** Mutation: end the spinner only when contents arrive -- this fails. */
  const f = folder();
  const first = f.click();
  f.settle.reject(new Error('Could not read Github url'));
  await first;
  assert.deepEqual(f.state, { isOpen: false, isLoading: false });

  void f.click();
  assert.equal(f.reads, 2, 'the second click read the folder again');
});

test('a read that put nothing in the tree closes the folder too', async () => {
  /** The tree it was read for has gone, or the read was refused by its caller. */
  const f = folder();
  const first = f.click();
  f.settle.resolve(false);
  await first;
  assert.deepEqual(f.state, { isOpen: false, isLoading: false });
});

test('a read that filled the folder leaves it open, and the spinner ends', async () => {
  const f = folder();
  const first = f.click();
  f.settle.resolve(true);
  await first;
  assert.deepEqual(f.state, { isOpen: true, isLoading: false });
});

test('a folder being read is not asked again', () => {
  const f = folder();
  void f.click();
  void f.click();
  assert.equal(f.reads, 1);
});
