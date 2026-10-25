/**
 * The Cargo panel's workspace field follows `cargoPath` when it is set from
 * outside the panel, as a bundled example's click sets it.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { FollowedDraft } from '../../dist-pure/features/cartography/followed_draft.js';

const EXAMPLE = '/checkout/examples/rust-firmware';

test('a field made before any path names the example once its click sets one', () => {
  /* Mutation: return the text without following the value -- the field stays
     empty under the example's crates, and this fails. */
  const draft = new FollowedDraft('');
  assert.equal(draft.shown(''), '');
  assert.equal(draft.shown(EXAMPLE), EXAMPLE);
});

test('a field holding an earlier path gives it up for the one now shown', () => {
  const draft = new FollowedDraft('/work/other');
  assert.equal(draft.shown('/work/other'), '/work/other');
  assert.equal(draft.shown(EXAMPLE), EXAMPLE);
});

test('an edit stands while the path is unchanged, and gives way when it changes', () => {
  /* Mutation: follow the value on every look rather than on a change -- the
     person's typing is replaced as they type, and this fails. */
  const draft = new FollowedDraft(EXAMPLE);
  draft.edit('/work/mine');
  assert.equal(draft.shown(EXAMPLE), '/work/mine');
  assert.equal(draft.shown(EXAMPLE), '/work/mine');
  draft.edit('');
  assert.equal(draft.shown(EXAMPLE), '', 'a field cleared by hand stays cleared');
  draft.edit('/work/mine');
  assert.equal(draft.shown('/work/read'), '/work/read');
});
