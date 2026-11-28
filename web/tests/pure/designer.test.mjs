/**
 * What the Designer panel says about a shape the harness declares.
 *
 * Each test names the mutation it was seen to fail under.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  couldRunShown, declaredRunShown, driftShown, haveShown, marksShown, optionShown, readingShown, runnableAttr,
  statusShown, valueShown,
} from '../../dist-pure/features/estate/designer.js';

const row = (over = {}) => ({ name: 'panel', declared: null, could_run: null, options: [], missing: '', ...over });

test('a mark is shown only when its field is exactly true', () => {
  // Mutation: show a mark whose field is truthy -- `"no"` and `1` read as stated.
  assert.deepEqual(marksShown({ spends: true, writes: false, decides: true }), ['spends', 'decides']);
  assert.deepEqual(marksShown({ spends: 'no', writes: 1 }), []);
  assert.deepEqual(marksShown({}), []);
  assert.deepEqual(marksShown(null), []);
});

test('a status is shown as written, the plane\'s first', () => {
  // Mutation: read the second document's status alone -- the plane's `half-built` is not shown.
  assert.equal(statusShown(row({ declared: { status: 'half-built' }, could_run: { status: 'runs' } })), 'half-built');
  assert.equal(statusShown(row({ could_run: { status: 'runs' } })), 'runs');
  assert.equal(statusShown(row()), '');
});

test('what the plane declares about running is said only when it states it', () => {
  // Mutation: read a missing `can_run` as false -- an entry that says nothing reads as unable.
  assert.equal(declaredRunShown({ can_run: true }), 'declared able to run');
  assert.equal(declaredRunShown({ can_run: false }), 'declared not able to run');
  assert.equal(declaredRunShown({}), '');
  assert.equal(declaredRunShown(null), '');
});

test('whether a shape could run now is the harness\'s account, with what is unmet', () => {
  // Mutation: read `declared.can_run` here -- a shape declared able and
  // lacking workers reads as able to run now.
  const lacking = row({
    declared: { can_run: true },
    could_run: { runnable: false, unmet: [{ key: 'workers' }, { key: 'budget' }] },
  });
  assert.equal(couldRunShown(lacking, true), 'could not run now: workers, budget unmet');
  assert.equal(runnableAttr(lacking, true), 'no');
  const able = row({ could_run: { runnable: true, unmet: [] } });
  assert.equal(couldRunShown(able, true), 'could run now');
  assert.equal(runnableAttr(able, true), 'yes');
  assert.equal(couldRunShown(row({ could_run: { runnable: false } }), true), 'could not run now');
});

test('nothing is said about running when the account was not read or does not name the shape', () => {
  // Mutation: say `could not run now` for a shape with no entry -- an unread account reads as a refusal.
  const able = row({ could_run: { runnable: true } });
  assert.equal(couldRunShown(able, false), '');
  assert.equal(runnableAttr(able, false), '');
  assert.equal(couldRunShown(row(), true), '');
  assert.equal(runnableAttr(row(), true), '');
  assert.equal(couldRunShown(row({ could_run: { runnable: 'maybe' } }), true), '');
});

test('what the harness has is every field it gave, and a null is said to be unstated', () => {
  // Mutation: drop a falsy value -- `workers 0`, `model false` and the unstated build vanish.
  assert.equal(haveShown({ workers: 0, budget: 0, model: false, built: null }),
    'workers 0 · budget 0 · model false · built not stated');
  assert.equal(haveShown(null), '');
  assert.equal(valueShown({ a: 1 }), '{"a":1}');
});

test('each drift list is under the harness\'s name for it, an empty one kept', () => {
  // Mutation: leave out an empty list -- the panel cannot say it is empty.
  assert.deepEqual(driftShown({ undeclared: [], stubs: ['chain', 'council'], note: 'not a list' }), [
    { name: 'undeclared', items: [] },
    { name: 'stubs', items: ['chain', 'council'] },
  ]);
});

test('the caveats are the harness\'s sentences as written', () => {
  // Mutation: return one fixed sentence -- the harness's own is not shown.
  assert.deepEqual(readingShown({ a: 'every field is a claim', b: '', c: 'second' }),
    ['every field is a claim', 'second']);
  assert.deepEqual(readingShown({}), []);
});

test('an option is its setting and the value that makes it', () => {
  // Mutation: print a false value as blank -- `arbiter_can_override = ` names no value.
  assert.equal(optionShown({ setting: 'arbiter_can_override', value: false, declared: {} }),
    'arbiter_can_override = false');
});
