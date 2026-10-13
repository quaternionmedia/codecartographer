/**
 * View → Info says something on every use; View → Source and a double-click
 * open one place, decided here.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { infoLine, sourceLine, sourceTarget } from '../../dist-pure/features/graph/services/node_info.js';

test('Info names the node, what its parser called it, and where it is', () => {
  const node = { id: 'rust::x', label: 'delay', language: 'rust', kind: 'function', file: 'src/main.rs', line: 12 };
  assert.equal(infoLine(node), 'delay · rust function · src/main.rs:12');
});

test('Info says what the node is across languages, and what else it is', () => {
  const node = {
    id: 'x', label: 'SysTick', language: 'rust', kind: 'function', file: 'src/main.rs', line: 28,
    construct_name: 'Function', meta: { facets: ['firmware.interrupt'] },
  };
  assert.equal(infoLine(node), 'SysTick · rust function · Function (firmware.interrupt) · src/main.rs:28');
});

test('a node from no file is still described, by what is known', () => {
  assert.equal(infoLine({ id: 'crate::hal', label: 'hal', kind: 'crate' }), 'hal · crate');
  assert.equal(infoLine({ id: 'bare' }), 'bare');
});

test('Source is the file and line, or nothing to show', () => {
  assert.equal(sourceLine({ id: 'a', file: 'main', line: 3 }), 'main:3');
  assert.equal(sourceLine({ id: 'a', file: 'main' }), 'main');
  assert.equal(sourceLine({ id: 'a' }), null);
});

test('Source opens the file on its forge, at the line when one is known and at the top when not', () => {
  /* Mutation: offer a target only for a node with a line, as the double-click
     did -- a file node opens nothing, and this fails. */
  const raw = 'https://raw.githubusercontent.com/tokio-rs/mini-redis/master/src/db.rs';
  assert.deepEqual(sourceTarget({ id: 'a', file: raw, line: 40 }),
    { kind: 'forge', href: 'https://github.com/tokio-rs/mini-redis/blob/master/src/db.rs#L40' });
  assert.deepEqual(sourceTarget({ id: 'a', file: raw, line: 0 }),
    { kind: 'forge', href: 'https://github.com/tokio-rs/mini-redis/blob/master/src/db.rs' });
});

test('a file read from disk is named beside the node, with its line when known', () => {
  assert.deepEqual(sourceTarget({ id: 'x', label: 'delay', file: '/ws/src/main.rs', line: 21 }),
    { kind: 'local', text: 'delay  /ws/src/main.rs:21' });
  assert.deepEqual(sourceTarget({ id: 'file::src/main.rs', label: 'main.rs', file: '/ws/src/main.rs', line: 0 }),
    { kind: 'local', text: 'main.rs  /ws/src/main.rs' });
});

test('a node from no file offers no source', () => {
  assert.equal(sourceTarget({ id: 'dir::src', file: '', line: 0 }), null);
  assert.equal(sourceTarget({ id: 'crate::hal' }), null);
});
