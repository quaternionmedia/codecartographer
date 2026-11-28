/**
 * What the window says about an instruction typed in it.
 *
 * Each test names the mutation it was seen to fail under.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { instructOutcome, recordedShown, sendable, standingOf } from '../../dist-pure/features/estate/instruct.js';

const URL = 'http://window/harness/instructions';
const ROW = { id: 'ins-1', text: 'draw the gallery', project: 'codecartographer', status: 'recorded' };

test('the harness\'s row is a recorded instruction', () => {
  // Mutation: return `refused` for every answer -- a recorded instruction reads as lost.
  const found = instructOutcome({ recorded: true, instruction: ROW, where: 'http://harness/v1/instructions' }, URL);
  assert.equal(found.kind, 'recorded');
  assert.deepEqual(found.instruction, ROW);
  assert.equal(found.where, 'http://harness/v1/instructions');
});

test('recorded with no row is not called recorded', () => {
  // Mutation: trust `recorded` alone -- the panel then prints a row that is not there.
  assert.equal(instructOutcome({ recorded: true }, URL).kind, 'refused');
  assert.equal(instructOutcome({ recorded: true, instruction: null }, URL).kind, 'refused');
});

test('no answer is this window\'s own API being down', () => {
  // Mutation: read a missing answer as a refusal -- the reader is sent to the harness.
  for (const nothing of [null, undefined, 'a string']) {
    const found = instructOutcome(nothing, URL);
    assert.equal(found.kind, 'api-down');
    assert.match(found.problem, /own API/);
    assert.equal(found.where, URL);
  }
});

test('a harness that is not answering is told apart from a refusal', () => {
  // Mutation: drop the `unreachable` test -- a harness that is down reads as one that said no.
  const down = instructOutcome({ unreachable: true, problem: 'nothing is answering', remedy: 'start it', where: 'h' }, URL);
  assert.deepEqual(down, { kind: 'unreachable', problem: 'nothing is answering', remedy: 'start it', where: 'h' });
  const no = instructOutcome({ refused: true, problem: 'the harness refused: 422', remedy: '', where: 'h' }, URL);
  assert.equal(no.kind, 'refused');
  assert.equal(no.problem, 'the harness refused: 422');
});

test('a refusal that gives no reason says that it gave none', () => {
  assert.match(instructOutcome({ refused: true }, URL).problem, /did not say why/);
});

test('the form is offered only when the API says an instruction is taken', () => {
  // Mutation: default `available` to true -- the form is offered where its press is refused.
  assert.deepEqual(standingOf({ available: true, problem: '', remedy: '' }), { available: true, problem: '', remedy: '' });
  assert.equal(standingOf({ available: false, problem: 'another machine', remedy: 'a terminal' }).available, false);
  assert.equal(standingOf({ available: 'yes' }).available, false);
  assert.equal(standingOf({}).available, false);
  const none = standingOf(null);
  assert.equal(none.available, false);
  assert.match(none.problem, /own API/);
});

test('a press sends only text that is not blank, and one at a time', () => {
  // Mutations: drop the trim -- spaces send; drop `sending` -- a second press posts a second row.
  assert.equal(sendable('draw the gallery', false), true);
  assert.equal(sendable('   \n ', false), false);
  assert.equal(sendable('', false), false);
  assert.equal(sendable('draw the gallery', true), false);
});

test('a recorded row is one sentence that says nothing ran', () => {
  assert.equal(recordedShown(ROW),
    'the harness recorded ins-1 for codecartographer, status recorded. Nothing ran.');
  // Mutation: print the project unconditionally -- an unresolved row reads "for ".
  assert.equal(recordedShown({ id: 'ins-2', project: null, status: 'unresolved' }),
    'the harness recorded ins-2 with no project resolved, status unresolved. Nothing ran.');
});
