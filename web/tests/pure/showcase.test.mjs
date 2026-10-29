/**
 * The Showcase's settings: what each is by default, which the server lays out
 * by and which the canvas draws in place, the layout's name they ride on, and
 * how each edge and member is drawn.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { layoutSpec } from '../../dist-pure/features/graph/services/layout_names.js';
import {
  LINK_KINDS, SHOWCASE_DEFAULTS, SHOWCASE_LAYOUT, dotRadius, laysOutAgain, linkOf, memberColour,
  showcaseOf, showcasePadding, showcaseSpec, withShowcase,
} from '../../dist-pure/features/graph/services/showcase.js';

test('the layout is asked for by its name with the settings the server lays it out by', () => {
  // Mutation: ask for the Showcase by its bare name -- the server lays it
  // out at its defaults whatever is set, and this fails.
  assert.equal(layoutSpec({ layout: SHOWCASE_LAYOUT, showcase: { dot: 3, nest: false } }),
    'Showcase(dot=3,gap=0.5,nest=false)');
  assert.equal(layoutSpec({ layout: SHOWCASE_LAYOUT }), 'Showcase(dot=2,gap=0.5,nest=true)');
  // Every other layout is asked for by its name alone.
  assert.equal(layoutSpec({ layout: 'map_layout', showcase: { dot: 3 } }), 'Map');
});

test('only a setting the server lays out by asks it to lay the graph out again', () => {
  // Mutation: lay out again for every change -- a link toggled asks the
  // server again, and this fails.
  const before = showcaseOf({});
  assert.equal(laysOutAgain(before, showcaseOf({ showcase: { dot: 3 } })), true);
  assert.equal(laysOutAgain(before, showcaseOf({ showcase: { gap: 1 } })), true);
  assert.equal(laysOutAgain(before, showcaseOf({ showcase: { nest: false } })), true);
  assert.equal(laysOutAgain(before, showcaseOf({ showcase: { linkOpacity: 0.9, names: true } })), false);
  assert.equal(laysOutAgain(before, showcaseOf({ showcase: { links: { ...before.links, uses: false } } })), false);
});

test('a setting left unset is its default, a link toggled keeps the others', () => {
  assert.deepEqual(showcaseOf(undefined), SHOWCASE_DEFAULTS);
  const one = showcaseOf({ showcase: { links: { flows: false } } });
  assert.deepEqual(one.links, { ...SHOWCASE_DEFAULTS.links, flows: false });
  assert.equal(showcaseSpec(one), 'Showcase(dot=2,gap=0.5,nest=true)');
});

test('a change is made to the settings held, every other setting and link as it was', () => {
  // The panel sends what changed alone. Mutation: make it to the defaults
  // -- a link turned on before is turned off again by a dot size, and this
  // fails.
  const held = withShowcase(undefined, { links: { uses: false } });
  const imports = withShowcase(held, { links: { imports: true } });
  assert.deepEqual(imports.links, { calls: true, uses: false, flows: true, imports: true });
  const larger = withShowcase(imports, { dot: 3 });
  assert.equal(larger.dot, 3);
  assert.deepEqual(larger.links, imports.links);
  assert.deepEqual(withShowcase(larger, {}), larger);
});

test('the links between code are drawn and a file\'s imports are not, at first', () => {
  // Mutation: draw the imports at first -- every file's runs the width of
  // the map to the modules beside it, and this fails.
  assert.deepEqual(SHOWCASE_DEFAULTS.links, { calls: true, uses: true, flows: true, imports: false });
  assert.deepEqual([...LINK_KINDS], ['calls', 'uses', 'flows', 'imports']);
});

test('an edge is drawn as its kind of link, and one that only holds is not drawn', () => {
  // Mutation: draw a dependency in the canvas's grey, as no link -- no
  // toggle hides it, and this fails.
  assert.equal(linkOf('contains'), null);
  assert.equal(linkOf('field_of'), null);
  assert.equal(linkOf('calls'), 'calls');
  assert.equal(linkOf('uses'), 'uses');
  assert.equal(linkOf('flows'), 'flows');
  for (const kind of ['imports', 'depends_on', 'declares', 'includes']) assert.equal(linkOf(kind), 'imports', kind);
});

test('a dot is a member\'s size, a file\'s half again and a directory\'s twice', () => {
  // The server lays them out at these sizes (test_showcase_layout.py holds
  // `DOT_SCALE` to its own). Mutation: draw a file at a member's size -- and
  // this fails.
  assert.equal(dotRadius(0, 2), 4);
  assert.equal(dotRadius(1, 2), 3);
  assert.equal(dotRadius(2, 2), 2);
  assert.equal(dotRadius(5, 2), 2);
  assert.equal(dotRadius(undefined, 2), 2);
  assert.equal(showcasePadding(showcaseOf({ showcase: { dot: 3 } })), 12);
});

test('a member the canvas would draw grey is given its kind\'s colour, and nothing else is', () => {
  // Mutation: colour no member -- three in four of a Showcase's dots are
  // grey, and this fails.
  for (const kind of ['name', 'constant', 'argument', 'symbol', 'string']) {
    assert.match(memberColour(kind) ?? '', /^#[0-9a-f]{6}$/, kind);
  }
  assert.equal(memberColour('function'), undefined);
  assert.equal(memberColour('toString'), undefined);
  assert.equal(memberColour(undefined), undefined);
});
