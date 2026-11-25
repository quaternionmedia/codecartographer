/**
 * The harness's run states, joined to the boxes on the canvas.
 *
 *   npm run test:pure
 *
 * Each test names the mutation it was seen to fail under.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { addressOf, heldBack, joinStates, repoOf } from '../../dist-pure/features/estate/run_state.js';

const active = { project: 'alpha', state: 'active', because: 'instruction i-1 is acting' };
const failed = { project: 'beta', state: 'failed', because: 'instruction i-2 is failed' };

test('an address names its repository, with or without a kind and an id', () => {
  // Mutation: return parts[0] -- every case here fails.
  assert.equal(repoOf('org/alpha'), 'alpha');
  assert.equal(repoOf('org/alpha/delta/the-work'), 'alpha');
  assert.equal(repoOf('alpha'), '');
  assert.equal(repoOf(''), '');
});

test('a node carries its address at the top level or in its metadata', () => {
  // Mutation: read only `node.address` -- the metadata case fails.
  assert.equal(addressOf({ id: 'a', address: 'org/alpha' }), 'org/alpha');
  assert.equal(addressOf({ id: 'a', metadata: { address: 'org/alpha' } }), 'org/alpha');
  assert.equal(addressOf({ id: 'a' }), '');
  assert.equal(addressOf({ id: 'a', address: 7 }), '');
});

test('a state goes to every box whose address names its project', () => {
  // Mutation: break after the first matching node -- the second box is bare.
  const joined = joinStates([active], [
    { id: 'subject', metadata: { address: 'org/alpha' } },
    { id: 'r0', metadata: { address: 'org/alpha/delta/the-work' } },
    { id: 'gate', metadata: { address: '' } },
  ]);
  assert.deepEqual(joined.byNode, { subject: active, r0: active });
  assert.deepEqual(joined.unmatched, []);
});

test('a state no box names is returned, never dropped', () => {
  // Mutation: return `unmatched: []` -- this fails.
  const joined = joinStates([active, failed], [{ id: 'subject', address: 'org/alpha' }]);
  assert.deepEqual(joined.byNode, { subject: active });
  assert.deepEqual(joined.unmatched, [failed]);
});

test('with nothing drawn every state is unmatched', () => {
  assert.deepEqual(joinStates([active, failed], []).unmatched, [active, failed]);
});

test('a state the channel does not have marks no box and is not reported as unmatched', () => {
  // Mutation: drop the STATES check -- the box takes a state the canvas cannot draw.
  const joined = joinStates([{ project: 'alpha', state: 'paused', because: '' }],
    [{ id: 'subject', address: 'org/alpha' }]);
  assert.deepEqual(joined.byNode, {});
  assert.deepEqual(joined.unmatched, []);
});

test('rows held back are stated, and a full page is stated as a floor', () => {
  // Mutation: ignore `more_is_floor` -- the second sentence loses "at least".
  assert.equal(heldBack({ more: 0, more_is_floor: false }), '');
  assert.match(heldBack({ more: 7, more_is_floor: false }), /^7 more the harness holds/);
  assert.match(heldBack({ more: 480, more_is_floor: true }), /^at least 480 more/);
});
