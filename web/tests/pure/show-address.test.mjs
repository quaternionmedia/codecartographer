/**
 * A showgraph's address: what each query string opens, and what it refuses.
 *
 *   npm run test:pure
 *
 * The cases worth reading are the refusals. A name with a separator would reach
 * a route as a path, and a view a family does not have would draw something the
 * address never asked for.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  crumbLabel, formatShow, fromNode, parseShow, sameShow, trail,
} from '../../dist-pure/features/show/show_address.js';

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

test("the index's full view is the whole corpus with no names", () => {
  // Mutation: read `full` as no view of the index's -- it opens as every
  // family, and this fails.
  assert.deepEqual(parseShow('?show=index&view=full'), { kind: 'index', name: '', view: 'full' });
  assert.equal(formatShow({ kind: 'index', name: '', view: 'full' }), '?show=index&view=full');
  assert.equal(crumbLabel({ kind: 'index', name: '', view: 'full' }), 'every node, no names');
  assert.deepEqual(trail({ kind: 'index', name: '', view: 'full' }, null).map((level) => level.map(crumbLabel)),
    [['every family'], ['every node, no names']]);
  // A project has no full view.
  assert.equal(parseShow('?show=project:carlos&view=full').view, 'estate');
});

test("the index's code view is the whole corpus", () => {
  // Mutation: read a view for a project alone -- the whole corpus opens as
  // every family, and this fails.
  assert.deepEqual(parseShow('?show=index&view=code'), { kind: 'index', name: '', view: 'code' });
  assert.deepEqual(parseShow('?show&view=code'), { kind: 'index', name: '', view: 'code' });
  assert.equal(parseShow('?show=index&view=system').view, 'estate');
  assert.equal(formatShow({ kind: 'index', name: '', view: 'code' }), '?show=index&view=code');
  assert.equal(crumbLabel({ kind: 'index', name: '', view: 'code' }), 'the whole corpus');
  // Its trail steps back to every family alone.
  assert.deepEqual(trail({ kind: 'index', name: '', view: 'code' }, null).map((level) => level.map(crumbLabel)),
    [['every family'], ['the whole corpus']]);
});

test("a family's code view is the family with its projects' code, and a view it has not is its estate", () => {
  // Mutation: give a family its estate alone, whatever is asked -- its code
  // view is never opened, and this fails.
  assert.deepEqual(parseShow('?show=family:core&view=code'), { kind: 'family', name: 'core', view: 'code' });
  assert.equal(parseShow('?show=family:core&view=system').view, 'estate');
  assert.equal(parseShow('?show=family:core&view=full').view, 'estate');
  assert.equal(parseShow('?show=project:carlos&view=nonsense').view, 'estate');
  assert.equal(parseShow('?show=project:carlos&view=system').view, 'system');
});

test('formatting and parsing agree, and the estate view is left out', () => {
  for (const search of ['?show=index', '?show=index&view=code', '?show=family:show-control',
    '?show=family:core&view=code',
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

// The corpus as the breadcrumb sees it: instruments sits within performing,
// and stomp is claimed by instruments and by irl.
const SUBJECTS = {
  families: [
    { name: 'performing', within: null },
    { name: 'instruments', within: 'performing' },
    { name: 'irl', within: null },
    { name: 'loop-a', within: 'loop-b' },
    { name: 'loop-b', within: 'loop-a' },
  ],
  projects: [
    { name: 'stomp', families: ['instruments', 'irl'] },
    { name: 'carlos', families: ['instruments'] },
    { name: 'loner', families: [] },
  ],
};

const names = (levels) => levels.map((level) => level.map(crumbLabel).join(' · ')).join(' › ');

test('the trail steps down from every family to what is drawn', () => {
  assert.equal(names(trail(parseShow('?show'), SUBJECTS)), 'every family');
  assert.equal(names(trail(parseShow('?show=family:instruments'), SUBJECTS)),
    'every family › performing › instruments');
  assert.equal(names(trail(parseShow('?show=project:carlos&view=code'), SUBJECTS)),
    'every family › performing › instruments › carlos');
  // The last step is the address itself, view and all.
  assert.deepEqual(trail(parseShow('?show=project:carlos&view=code'), SUBJECTS).at(-1),
    [{ kind: 'project', name: 'carlos', view: 'code' }]);
});

test('a project two families claim is reached from both, as the index draws it', () => {
  assert.equal(names(trail(parseShow('?show=project:stomp'), SUBJECTS)),
    'every family › performing › instruments · irl › stomp');
});

test('a project no family claims, or a corpus not yet read, is one step from every family', () => {
  assert.equal(names(trail(parseShow('?show=project:loner'), SUBJECTS)), 'every family › loner');
  assert.equal(names(trail(parseShow('?show=project:carlos'), null)), 'every family › carlos');
  assert.equal(names(trail(parseShow('?show=family:irl'), null)), 'every family › irl');
});

test('families that sit within each other end the trail rather than loop it', () => {
  assert.equal(names(trail(parseShow('?show=family:loop-a'), SUBJECTS)), 'every family › loop-b › loop-a');
});

test('two addresses are the same drawing only when every part agrees', () => {
  assert.ok(sameShow(parseShow('?show'), parseShow('?show=index')));
  assert.ok(!sameShow(parseShow('?show=project:carlos'), parseShow('?show=project:carlos&view=code')));
  assert.ok(!sameShow(parseShow('?show=family:irl'), null));
});

test("a family's code view ends its trail as itself, named as the family", () => {
  // Mutation: end it with the family's estate -- a step back to the code view
  // draws the estate, and this fails.
  assert.deepEqual(trail(parseShow('?show=family:instruments&view=code'), SUBJECTS).at(-1),
    [{ kind: 'family', name: 'instruments', view: 'code' }]);
  assert.equal(names(trail(parseShow('?show=family:instruments&view=code'), SUBJECTS)),
    'every family › performing › instruments');
});
