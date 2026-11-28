/**
 * How a panel words what `/harness/interactions` returned.
 *
 *   npm run test:pure
 *
 * Each test names the mutation it was seen to fail under.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  NOBODY, actShown, answersShown, cellLevel, followDue, followShown, instanceShown, moreNamesShown, mostInACell,
  readingMark, undatedShown, whoShown,
} from '../../dist-pure/features/estate/interactions.js';

test('a row that names nobody is worded as naming nobody, never as a blank', () => {
  // Mutation: return `who ?? ''` from `whoShown` -- the empty and null cases fail.
  assert.equal(whoShown('ada'), 'ada');
  assert.equal(whoShown(null), NOBODY);
  assert.equal(whoShown(undefined), NOBODY);
  assert.equal(whoShown(''), NOBODY);
  assert.equal(NOBODY, 'nobody named');
});

test('an act carries its way in only when the row names one', () => {
  // Mutation: always append the way -- `answered · null` appears.
  assert.equal(actShown('instructed', 'voice'), 'instructed · voice');
  assert.equal(actShown('answered', null), 'answered');
  assert.equal(actShown('ran', undefined), 'ran');
  assert.equal(actShown('asked', ''), 'asked');
});

test('a span with one interaction is shaded beside a span with many', () => {
  // Mutations: round the level with no lower bound of 1 -- 1 of 60 becomes 0,
  // an empty span; drop the upper bound -- 9 of 4 becomes 9.
  assert.equal(cellLevel(0, 60), 0);
  assert.equal(cellLevel(1, 60), 1);
  assert.equal(cellLevel(15, 60), 1);
  assert.equal(cellLevel(16, 60), 2);
  assert.equal(cellLevel(31, 60), 3);
  assert.equal(cellLevel(60, 60), 4);
  assert.equal(cellLevel(9, 4), 4);
  assert.equal(cellLevel(3, 0), 0);
  assert.equal(cellLevel(-1, 5), 0);
});

test('every lane is shaded on one scale: the largest count in any span', () => {
  // Mutation: return the first lane's largest -- the second lane's 7 is missed.
  assert.equal(mostInACell([
    { act: 'instructed', way: 'voice', count: 3, cells: [1, 2, 0] },
    { act: 'ran', way: null, count: 8, cells: [0, 7, 1] },
  ]), 7);
  assert.equal(mostInACell([]), 0);
});

test('the instance is each field as the harness stated it, and a missing one says so', () => {
  // Mutation: word a null as an empty string -- `session ` ends bare.
  const stated = {
    identified: true, where: 'http://h/health', pid: 4242, port: 3999,
    database_fingerprint: '0123456789abcdef', started_at: '2026-01-01T00:00:00+00:00',
    session: null, version: '0.1.0', problem: '', remedy: '',
  };
  const when = (value) => `<${value}>`;
  assert.equal(
    instanceShown(stated, when),
    'pid 4242 · port 3999 · database 0123456789abcdef · started <2026-01-01T00:00:00+00:00>'
      + ' · session not stated · version 0.1.0',
  );
  assert.match(instanceShown({ ...stated, session: 'review', started_at: null }, when),
    /started not stated · session review/);
});

test('answers the server did not read are counted in a sentence, and none is no sentence', () => {
  // Mutation: return '' whatever the count -- the sentence is absent.
  assert.equal(answersShown({ read: 20, unread: 0, limit: 20 }), '');
  assert.equal(
    answersShown({ read: 20, unread: 3, limit: 20 }),
    'answered questions whose answer was not read: 3. An answer is one read of the harness each,'
      + ' and at most 20 are read.',
  );
});

test('interactions with no time and names not shown are each said only when there are some', () => {
  // Mutation: compare with `>= 0` in either -- the zero case gains a sentence.
  assert.equal(undatedShown(0), '');
  assert.equal(undatedShown(2), 'interactions with no readable time, in no span: 2.');
  assert.equal(moreNamesShown(0), '');
  assert.equal(moreNamesShown(4), "4 more the harness's rows give and this panel does not show");
});

const listed = (rows, more = 0, read = 0) => ({
  interactions: { rows, shown: rows.length, more, more_is_floor: false },
  answers: { read, unread: 0, limit: 20 },
});
const ROW = { act: 'instructed', ref: 'ins-1', at: '2026-01-01T00:00:20' };

test('two readings share a mark only when they list the same rows', () => {
  // Mutations: mark a reading by its count alone -- an answer in place of a
  // question, the count unchanged, is the same mark; leave the count out --
  // a row arriving behind the listed ones is not seen.
  const mark = readingMark(listed([ROW]));
  assert.equal(readingMark(listed([{ ...ROW }])), mark);
  assert.notEqual(readingMark(listed([{ ...ROW, ref: 'ins-2' }])), mark);
  assert.notEqual(readingMark(listed([{ ...ROW, act: 'asked' }])), mark);
  assert.notEqual(readingMark(listed([{ ...ROW, at: '2026-01-01T00:00:21' }])), mark);
  assert.notEqual(readingMark(listed([ROW], 1)), mark);
  assert.notEqual(readingMark(listed([ROW], 0, 1)), mark);
  assert.equal(readingMark(listed([{ ...ROW, at: null }])), readingMark(listed([{ ...ROW, at: null }])));
});

test('the graph is drawn again only when followed, this seam\'s, drawn here, changed and idle', () => {
  // Mutations: drop each condition in turn -- unticked, another seam's graph,
  // a graph this panel never drew, the same rows, and a drawing still out
  // each draw again.
  assert.equal(followDue(true, 'interactions', 'a', 'b', false), true);
  assert.equal(followDue(false, 'interactions', 'a', 'b', false), false);
  assert.equal(followDue(true, 'topology', 'a', 'b', false), false);
  assert.equal(followDue(true, undefined, 'a', 'b', false), false);
  assert.equal(followDue(true, 'interactions', null, 'b', false), false);
  assert.equal(followDue(true, 'interactions', 'a', 'a', false), false);
  assert.equal(followDue(true, 'interactions', 'a', 'b', true), false);
});

test('the hint says whether the graph follows the harness or stays as drawn', () => {
  // Mutation: answer the followed sentence either way -- an unticked panel
  // says the graph is drawn again.
  assert.match(followShown(true), /drawn again when the rows the harness lists change/);
  assert.match(followShown(false), /stays as drawn until it is drawn again/);
});
