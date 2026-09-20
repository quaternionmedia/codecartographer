/**
 * The four things a seam can answer, told apart.
 *
 * **WHY FOUR, AND WHY IT MATTERS THAT THEY STAY FOUR.** The window's own API
 * not answering sends a reader to this server; the seam unreachable sends them
 * to start another one; the seam present and unreadable sends them to move a
 * pin or regenerate a file; a document is drawn. The topology panel learned
 * these one bug at a time, and a classifier that merged any two would send the
 * next reader to the wrong place while reporting a sentence.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { classify, isProblem, query, read } from '../../dist-pure/features/estate/seam_client.js';

const URL = 'http://window/capabilities/gjgf';

test('null from the request handler is the window\'s own API being down', () => {
  const found = classify(null, URL);
  assert.equal(found.kind, 'api-down');
  assert.equal(found.problem.kind, 'api-down');
  assert.match(found.problem.problem, /own API/);
  assert.equal(found.problem.where, URL);
});

test('undefined reads the same as null', () => {
  assert.equal(classify(undefined, URL).kind, 'api-down');
});

test('an unreachable envelope carries the seam\'s own sentence', () => {
  const found = classify({
    unreachable: true,
    problem: 'nothing is answering at http://127.0.0.1:3141',
    remedy: 'start it with `uv run qm dashboard --start harness`',
    where: 'http://127.0.0.1:3141/v1/topology',
  }, URL);
  assert.equal(found.kind, 'unreachable');
  assert.equal(found.problem.remedy, 'start it with `uv run qm dashboard --start harness`');
  // The seam's `where` wins over the window's URL: it names the far side.
  assert.equal(found.problem.where, 'http://127.0.0.1:3141/v1/topology');
});

test('an unreadable envelope is the other absence, not the same one', () => {
  const found = classify({ unreadable: true, problem: 'no capability registry', remedy: 'propagate' }, URL);
  assert.equal(found.kind, 'unreadable');
  assert.notEqual(found.kind, 'unreachable');
  // No `where` sent: the window's URL stands in, so something is always named.
  assert.equal(found.problem.where, URL);
});

test('a document is a document', () => {
  const found = classify({ graph: { nodes: {}, edges: [] }, metadata: { kind: 'capabilities' } }, URL);
  assert.equal(found.kind, 'ok');
  assert.equal(found.document.metadata.kind, 'capabilities');
  assert.equal(isProblem(found), false);
});

test('a non-object 200 is unreadable, never drawn', () => {
  const found = classify('<html>', URL);
  assert.equal(found.kind, 'unreadable');
  assert.equal(isProblem(found), true);
});

test('a getter that throws becomes a visible api-down, not a pending state', async () => {
  const found = await read(async () => { throw new Error('boom'); }, URL);
  assert.equal(found.kind, 'api-down');
  assert.equal(found.problem.remedy, 'boom');
});

test('a getter that answers is classified like any other answer', async () => {
  const found = await read(async () => ({ unreachable: true, problem: 'p', remedy: '', where: 'w' }), URL);
  assert.equal(found.kind, 'unreachable');
});

test('query drops undefined, null and empty values and keeps zero', () => {
  assert.equal(query({}), '');
  assert.equal(query({ layout: 'Spring', palette_id: undefined, seam: null, kind: '' }), '?layout=Spring');
  assert.equal(query({ level: 0 }), '?level=0');
});
