/**
 * View → Source and View → Info say something on every use.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { infoLine, sourceLine } from '../../dist-pure/features/graph/services/node_info.js';

test('Info names the node, what its parser called it, and where it is', () => {
  const node = { id: 'rust::x', label: 'delay', language: 'rust', kind: 'function', file: 'src/main.rs', line: 12 };
  assert.equal(infoLine(node), 'delay · rust function · src/main.rs:12');
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
