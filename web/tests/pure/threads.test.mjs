/**
 * How the Threads panel words the harness's archive and one conversation.
 *
 * Each test names the mutation it was seen to fail under.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  chosenOf, drawnIs, drawnShown, followDue, followShown, listQuery, moreShown, readingShown, rolesShown,
  threadQuery, titleShown, turnsShown,
} from '../../dist-pure/features/estate/threads.js';

test('the archive is asked for by a source and a text, each only when given', () => {
  // Mutation: send a blank text -- every list is asked for with `titled=`.
  assert.equal(listQuery('', ''), '');
  assert.equal(listQuery(' ink ', ''), '?source=ink');
  assert.equal(listQuery('ink', ' the shed '), '?source=ink&titled=the%20shed');
});

test('a conversation is asked for by its two words, quoted, with a layout only when one is named', () => {
  // Mutation: join the id unquoted -- an id holding `&` names another parameter.
  assert.equal(threadQuery({ source: 'ink', id: 't-1' }), '?source=ink&id=t-1');
  assert.equal(threadQuery({ source: 'a b', id: 'x&y' }, 'Circular'), '?source=a%20b&id=x%26y&layout=Circular');
});

test('a row names a conversation only when the archive gives it a source and an id', () => {
  // Mutation: answer a conversation with a blank id -- its control asks for nothing.
  assert.deepEqual(chosenOf({ source: 'ink', id: 't-1' }), { source: 'ink', id: 't-1' });
  assert.equal(chosenOf({ source: 'ink', id: null }), null);
  assert.equal(chosenOf({ source: '', id: 't-1' }), null);
});

test('a title, a count of turns and a held-back count are worded, and a missing one is not invented', () => {
  // Mutations: show a blank title as blank -- a row has no name to read;
  // word one turn as `1 turns`; say `0 more` under a list shown whole.
  assert.equal(titleShown('Tidy the Shed'), 'Tidy the Shed');
  assert.equal(titleShown('  '), 'no title');
  assert.equal(titleShown(null), 'no title');
  assert.equal(turnsShown(1), '1 turn');
  assert.equal(turnsShown(12), '12 turns');
  assert.equal(turnsShown(undefined), '');
  assert.equal(moreShown(0), '');
  assert.match(moreShown(7), /^7 more the archive lists are not shown/);
});

test('roles are listed in the order given, each with its count', () => {
  // Mutation: sort the roles by name -- the role that opens is no longer first.
  assert.equal(rolesShown({ helper: 2, asker: 1 }), 'helper 2 · asker 1');
  assert.equal(rolesShown({}), '');
});

test('how many turns are drawn is said, and whether that is all of them', () => {
  // Mutation: say `all` whenever any are drawn -- a cut picture reads as whole.
  assert.equal(drawnShown(5, 5), 'all 5 turns are drawn');
  assert.equal(drawnShown(150, 156), 'the newest 150 of 156 turns are drawn');
  assert.equal(drawnShown(0, 0), 'this conversation holds no turn');
});

test('what the archive says of itself is each sentence as given', () => {
  // Mutation: join the keys in -- a field name is printed as prose.
  assert.deepEqual(readingShown({ a: 'it counts what was indexed', b: '', c: null, d: 'refresh it' }),
    ['it counts what was indexed', 'refresh it']);
});

test('a graph is this conversation\'s only when its metadata names both words', () => {
  // Mutations: match the kind alone -- another conversation's graph is taken
  // for this one; match the id alone -- the same id under another source is.
  const metadata = { kind: 'thread', thread: { source: 'ink', id: 't-1' } };
  assert.equal(drawnIs(metadata, { source: 'ink', id: 't-1' }), true);
  assert.equal(drawnIs(metadata, { source: 'ink', id: 't-2' }), false);
  assert.equal(drawnIs(metadata, { source: 'quill', id: 't-1' }), false);
  assert.equal(drawnIs({ kind: 'interactions', thread: metadata.thread }, { source: 'ink', id: 't-1' }), false);
  assert.equal(drawnIs(metadata, null), false);
  assert.equal(drawnIs(undefined, { source: 'ink', id: 't-1' }), false);
});

test('the graph is drawn again only when followed, on the canvas, marked otherwise and idle', () => {
  // Mutations: drop each condition in turn -- unticked, another graph on the
  // canvas, a graph that states no mark, the same mark, and a drawing still
  // out each draw again.
  assert.equal(followDue(true, true, 'a', 'b', false), true);
  assert.equal(followDue(false, true, 'a', 'b', false), false);
  assert.equal(followDue(true, false, 'a', 'b', false), false);
  assert.equal(followDue(true, true, undefined, 'b', false), false);
  assert.equal(followDue(true, true, 'a', 'a', false), false);
  assert.equal(followDue(true, true, 'a', 'b', true), false);
});

test('the hint says whether the graph follows the conversation or stays as drawn', () => {
  // Mutation: answer the followed sentence either way -- an unticked panel
  // says the graph is drawn again.
  assert.match(followShown(true, 15), /read again every 15 s, and drawn again when its turns change/);
  assert.match(followShown(false, 15), /stays as drawn until it is drawn again/);
});
