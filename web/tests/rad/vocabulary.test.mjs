/**
 * This host's obligations under the rad host integration standard §5.
 *
 * §5.2 extend the vocabulary, never repurpose it
 * §5.3 every chord-bound verb is also reachable in the menu
 *
 * These are clauses in a document; the standard's own revision triggers note
 * that a host found violating them means "§5 needs a check rather than a
 * clause". This file is that check, offered upstream as one.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { CHORD_MAP, CHORD_WORDS, ALL_VERBS, HOST_VERBS } from '../../dist-rad/host/vocabulary.js';
import { resolveGraphMenu, allMenuVerbs } from '../../dist-rad/host/resolve.js';
import { prefixCollisions } from '../../dist-rad/core/chord.js';
import { MAX_ITEMS } from '../../dist-rad/core/geometry.js';

/** The verbs the contract reserves. A host may omit; it may not redefine. */
const STANDARD = new Set([
  'pin', 'hide', 'delete', 'expand', 'collapse', 'select-neighbors',
  'reverse', 'edit-label',
  'add-node', 'fit', 'relayout', 'toggle-physics',
  'spread', 'cluster',
  // Not named in the contract's §1 lists but used by the reference
  // implementation's own canvas/selection rings.
  'show-hidden', 'clear-selection',
]);

test('§5.3 every chord-bound verb is reachable in the menu', () => {
  const menu = new Set(allMenuVerbs());
  const unreachable = Object.values(CHORD_MAP).filter((v) => !menu.has(v));
  assert.deepEqual(unreachable, [], 'chords must be accelerators, not private functions');
});

test('the chord vocabulary is prefix-free', () => {
  assert.deepEqual(prefixCollisions(CHORD_WORDS), []);
});

test('§5.2 every verb is either standard, a colour token, or a declared host verb', () => {
  const hostVerbs = new Set(Object.values(HOST_VERBS));
  const stray = allMenuVerbs().filter(
    (v) => !STANDARD.has(v) && !v.startsWith('color:') && !hostVerbs.has(v),
  );
  assert.deepEqual(stray, [], 'an undeclared verb is a repurposed one until it is declared');
});

test('colour intents name palette tokens, never literals', () => {
  const colours = allMenuVerbs().filter((v) => v.startsWith('color:'));
  assert.ok(colours.length > 0, 'expected colour verbs');
  for (const c of colours) {
    assert.doesNotMatch(c, /#|rgb|hsl/, `${c} smuggles a literal into the portable vocabulary`);
  }
});

test('ALL_VERBS is complete — nothing the menu offers is missing from it', () => {
  const declared = new Set(ALL_VERBS);
  const missing = allMenuVerbs().filter((v) => !declared.has(v));
  assert.deepEqual(missing, []);
});

test('every ring, in every state, respects the 8-item ceiling', () => {
  const factSets = [
    {},
    { depth: 0, hasRenderedChildren: true, hasSource: true, hasGroup: true, physicsAvailable: true, anyHidden: true, selectionCount: 3 },
    { depth: 2, pinned: true },
  ];
  for (const type of ['node', 'canvas', 'selection']) {
    for (const facts of factSets) {
      const spec = resolveGraphMenu({ type, targetIds: ['a'], position: { x: 0, y: 0 } }, facts);
      assert.ok(
        spec.items.length >= 1 && spec.items.length <= MAX_ITEMS,
        `${type} ring has ${spec.items.length} items`,
      );
      for (const item of spec.items) {
        if (item.children) {
          assert.ok(
            item.children.length >= 1 && item.children.length <= MAX_ITEMS,
            `${type}/${item.id} submenu has ${item.children.length} items`,
          );
        }
      }
    }
  }
});

test('a sub-symbol cannot be expanded, a symbol can, and a childless node cannot be collapsed', () => {
  const ring = (facts) => Object.fromEntries(resolveGraphMenu(
    { type: 'node', targetIds: ['a'], position: { x: 0, y: 0 } }, facts,
  ).items.map((i) => [i.id, i]));
  /* Mutation: gate expand at depth 2 -- a struct's fields and an impl's
     methods, which every parser here emits at depth 3, cannot be reached from
     a graph parsed at the default depth, and this fails. */
  assert.equal(ring({ depth: 2, hasRenderedChildren: false }).expand.enabled, true,
    'a depth-2 symbol holds depth-3 sub-symbols');
  assert.equal(ring({ depth: 3, hasRenderedChildren: false }).expand.enabled, false,
    'depth 3 is the deepest tier a parser emits');
  assert.equal(ring({ depth: 2, hasRenderedChildren: false }).collapse.enabled, false);
});

test('View → Compare is offered disabled on a node the vocabulary did not place', () => {
  // Mutation: enable Compare unconditionally -- a node with no construct opens
  // a chrestomathy of nothing, and this fails.
  const compare = (facts) => resolveGraphMenu(
    { type: 'node', targetIds: ['a'], position: { x: 0, y: 0 } }, facts,
  ).items.find((i) => i.id === 'view').children.find((i) => i.id === 'compare');
  assert.equal(compare({ hasConstruct: false }).enabled, false);
  assert.equal(compare({ hasConstruct: true }).enabled, true);
  assert.equal(compare({ hasConstruct: true }).action, 'compare');
});

test('expand takes the 12 o\'clock wedge', () => {
  const spec = resolveGraphMenu(
    { type: 'node', targetIds: ['a'], position: { x: 0, y: 0 } },
    { depth: 1 },
  );
  assert.equal(spec.items[0].action, 'expand', 'index 0 is what a straight-up flick reaches');
});

/**
 * The check that was missing, and that let three verbs alias to one.
 *
 * `intents.test.mjs` proves every verb reaches a named operation. It cannot
 * prove the operation does anything — the host's op bodies are application
 * code and never enter the conformance build. So `spread`, `cluster` and
 * `focus-group` all shipped pointing at `fitView()` and the suite stayed
 * green: three verbs claiming three things, doing one.
 *
 * A host cannot assert "this op is meaningful" from here. What it can assert
 * is the decision that replaced the aliases: a capability the host does not
 * have is offered DISABLED, never quietly substituted. The wedge stays so
 * indices do not shift; the item goes grey so the menu stops lying.
 */
test('a capability the host lacks is disabled, not silently substituted', () => {
  const facts = {
    depth: 0,
    hasRenderedChildren: true,
    selectionCount: 2,
    physicsAvailable: false,
    layoutAvailable: false,
  };
  const gated = { spread: 'layoutAvailable', cluster: 'layoutAvailable',
                  'toggle-physics': 'physicsAvailable' };

  let found = 0;
  for (const type of ['node', 'canvas', 'selection']) {
    const spec = resolveGraphMenu({ type, targetIds: ['x'], position: { x: 0, y: 0 } }, facts);
    for (const item of spec.items) {
      if (!(item.action in gated)) continue;
      found++;
      assert.equal(item.enabled, false,
        `${type} ring offers '${item.action}' as enabled while ${gated[item.action]} is false`);
    }
  }
  assert.ok(found >= 3, `expected the gated verbs to still occupy their wedges, saw ${found}`);
});

test('the same verbs come back enabled on a host that does have them', () => {
  const facts = { selectionCount: 2, physicsAvailable: true, layoutAvailable: true };
  const canvas = resolveGraphMenu({ type: 'canvas', targetIds: [], position: { x: 0, y: 0 } }, facts);
  const byId = Object.fromEntries(canvas.items.map((i) => [i.id, i]));
  assert.notEqual(byId.spread.enabled, false);
  assert.notEqual(byId.cluster.enabled, false);
  assert.equal(byId.physics.enabled, true);
});

test('every label a ring offers is spelled the American way, as Color is', () => {
  /* Mutation: label the select-neighbors item 'Neighbours' again -- it sits
     beside 'Color' in the node ring, and this fails. */
  const BRITISH = /neighbour|colour|centre|grey|behaviour|favour/i;
  const labels = [];
  const walk = (items) => {
    for (const item of items) {
      labels.push(item.label);
      if (item.children) walk(item.children);
    }
  };
  const facts = { depth: 1, hasRenderedChildren: true, selectionCount: 2 };
  for (const type of ['node', 'canvas', 'selection']) {
    walk(resolveGraphMenu({ type, targetIds: ['a', 'b'], position: { x: 0, y: 0 } }, facts).items);
  }
  assert.ok(labels.includes('Color'), `expected the node ring's Color among ${labels}`);
  assert.deepEqual(labels.filter((label) => BRITISH.test(label)), []);
});

test('the canvas ring offers no verb that needs a target', () => {
  /* Mutation: put Color back on the canvas ring -- it commits with no target
     ids and colours nothing, and this fails. */
  const canvas = resolveGraphMenu({ type: 'canvas', targetIds: [], position: { x: 0, y: 0 } }, {});
  const needsTarget = canvas.items.filter((i) => i.children || /^color:/.test(i.action ?? ''));
  assert.deepEqual(needsTarget.map((i) => i.id), []);
});

test('there is no edge ring: nothing opens an edge context', () => {
  /* Mutation: restore the edge ring -- this fails. */
  const spec = resolveGraphMenu({ type: 'edge', targetIds: ['e'], position: { x: 0, y: 0 } }, {});
  assert.equal(spec.title, 'canvas');
});
