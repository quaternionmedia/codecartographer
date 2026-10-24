/**
 * A showgraph's address: what each query string opens, and what it refuses.
 *
 *   npm run test:pure
 *
 * The cases worth reading are the refusals. A name with a separator would reach
 * a route as a path, and a view on a family would draw something the address
 * never asked for.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { formatShow, fromNode, parseShow } from '../../dist-pure/features/show/show_address.js';

test('each kind of address opens what it names', () => {
  assert.deepEqual(parseShow('?show=index'), { kind: 'index', name: '', view: 'estate' });
  // The default showgraph is every family at once.
  assert.deepEqual(parseShow('?show'), { kind: 'index', name: '', view: 'estate' });
  assert.deepEqual(parseShow('?show='), { kind: 'index', name: '', view: 'estate' });
  assert.deepEqual(parseShow('?show=family:performing'),
    { kind: 'family', name: 'performing', view: 'estate' });
  assert.deepEqual(parseShow('show=project:carlos&view=code'),
    { kind: 'project', name: 'carlos', view: 'code' });
});

test('no address, or a malformed one, opens nothing', () => {
  for (const search of ['', '?x=1', '?show=carlos', '?show=team:core',
    '?show=project:../etc', '?show=project:a/b', '?show=family:.hidden']) {
    assert.equal(parseShow(search), null, `${search} opened something`);
  }
});

test('only a project has views, and an unknown view is its estate', () => {
  assert.equal(parseShow('?show=family:core&view=code').view, 'estate');
  assert.equal(parseShow('?show=project:carlos&view=nonsense').view, 'estate');
  assert.equal(parseShow('?show=project:carlos&view=system').view, 'system');
});

test('formatting and parsing agree, and the estate view is left out', () => {
  for (const search of ['?show=index', '?show=family:show-control',
    '?show=project:Cuelist-python', '?show=project:moat&view=system']) {
    assert.equal(formatShow(parseShow(search)), search);
  }
  assert.equal(formatShow({ kind: 'project', name: 'qm', view: 'estate' }), '?show=project:qm');
});

test('a node names its own address', () => {
  assert.deepEqual(fromNode('family:core'), { kind: 'family', name: 'core', view: 'estate' });
  assert.equal(fromNode(undefined), null);
  assert.equal(fromNode('nothing'), null);
});
