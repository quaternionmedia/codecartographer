/**
 * The group outlines are drawn around what remains once nodes leave the
 * canvas.
 *
 * **THE DEFECT THIS PINS.** Delete and Collapse take nodes off the canvas
 * through `removeNodes`, which touched neither the outlines the renderer
 * keeps for the fit nor the circles it drew. After a collapse a file's
 * outline kept its full radius around nothing, and Fit framed the empty
 * circle; after a delete an outline stayed drawn around a node that was gone.
 * The renderer now redraws the outlines `outlinesAfterRemoval` gives.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { CompoundLayoutManager, outlinesAfterRemoval } from '../../dist-pure/features/graph/services/compound_layout.js';

/**
 * The renderer's spacing at a node size of 4: each node reaches its drawn
 * extent, 1.5 × 4 × its depth's multiplier (`_extentOf`), and not the
 * `baseNodeSize` that `computeGroupBounds` falls back on.
 */
const EXTENT = [18, 10.8, 6, 3.6];
const SPACING = { padding: 40, baseNodeSize: 12, radiusOf: (n) => EXTENT[n.depth] };

/**
 * A directory holding two files, `main.rs` with two functions and `lib.rs`
 * with one, each joined to what holds it by a `contains` edge.
 */
function scene() {
  const nodes = [
    { id: 'src', depth: 0, x: 0, y: 0, label: 'src' },
    { id: 'main.rs', depth: 1, x: 200, y: 0, label: 'main.rs' },
    { id: 'main', depth: 2, x: 260, y: 0 },
    { id: 'init', depth: 2, x: 200, y: 90 },
    { id: 'lib.rs', depth: 1, x: -200, y: 0, label: 'lib.rs' },
    { id: 'run', depth: 2, x: -240, y: 0 },
  ];
  const edges = [
    ['src', 'main.rs'], ['src', 'lib.rs'], ['main.rs', 'main'], ['main.rs', 'init'], ['lib.rs', 'run'],
  ].map(([source, target]) => ({ source, target, kind: 'contains' }));
  return { nodes, edges };
}

const manager = new CompoundLayoutManager();

/** The outlines drawn on a fresh drawing, as `_drawCompoundBackgrounds` draws them. */
function drawn({ nodes, edges }) {
  return manager.computeGroupBounds(nodes, edges, SPACING.padding, SPACING.baseNodeSize, SPACING.radiusOf);
}

/** The scene without `gone`, as `removeNodes` leaves it: the nodes, and every edge not touching them. */
function without({ nodes, edges }, gone) {
  return {
    nodes: nodes.filter((n) => !gone.includes(n.id)),
    edges: edges.filter((e) => !gone.includes(e.source) && !gone.includes(e.target)),
  };
}

const radiusOf = (outlines, id) => outlines.find((b) => b.nodeId === id)?.radius;

test('a removal of nothing redraws every outline as it was drawn, each node by its drawn extent', () => {
  /** Mutation: compute the outlines after a removal without the spacing's
      radiusOf -- each node counts as baseNodeSize, every outline changes
      size, and this fails. */
  const { nodes, edges } = scene();
  const outlines = drawn({ nodes, edges });
  assert.deepEqual(outlinesAfterRemoval(manager, outlines, nodes, edges, SPACING), outlines);
});

test("deleting a node outside a file's group leaves that file's outline as it was", () => {
  // A file at the origin with a symbol 100 to its right, beside a lone
  // directory: its outline is 78.4 drawn, and was 82 after the delete.
  const nodes = [
    { id: 'f', depth: 1, x: 0, y: 0, label: 'f.rs' },
    { id: 's', depth: 2, x: 100, y: 0 },
    { id: 'other', depth: 0, x: 500, y: 500, label: 'other' },
  ];
  const edges = [{ source: 'f', target: 's', kind: 'contains' }];
  const outlines = drawn({ nodes, edges });
  assert.ok(Math.abs(radiusOf(outlines, 'f') - 78.4) < 1e-9, `drawn at ${radiusOf(outlines, 'f')}`);
  const after = without({ nodes, edges }, ['other']);
  const left = outlinesAfterRemoval(manager, outlines, after.nodes, after.edges, SPACING);
  assert.equal(radiusOf(left, 'f'), radiusOf(outlines, 'f'));
});

test("collapsing a file drops its outline, and its directory's is drawn around what remains", () => {
  /** Mutation: leave the outlines as drawn -- main.rs keeps its outline around nothing, and this fails. */
  const before = scene();
  const outlines = drawn(before);
  assert.ok(radiusOf(outlines, 'main.rs') > 0, 'the scene draws an outline around main.rs');
  const after = without(before, ['main', 'init']);
  const left = outlinesAfterRemoval(manager, outlines, after.nodes, after.edges, SPACING);
  assert.equal(radiusOf(left, 'main.rs'), undefined, "main.rs's outline was left around its collapsed functions");
  assert.ok(radiusOf(left, 'src') < radiusOf(outlines, 'src'), "src's outline kept the reach of what was collapsed");
  assert.deepEqual(left, drawn(after));
});

test("deleting a file's only function drops that file's outline", () => {
  const before = scene();
  const after = without(before, ['run']);
  const left = outlinesAfterRemoval(manager, drawn(before), after.nodes, after.edges, SPACING);
  assert.equal(radiusOf(left, 'lib.rs'), undefined);
  assert.ok(radiusOf(left, 'main.rs') > 0, "main.rs's outline went with lib.rs's");
});

test("deleting one function shrinks its file's outline to the one left", () => {
  const before = scene();
  const outlines = drawn(before);
  const after = without(before, ['init']);
  const left = outlinesAfterRemoval(manager, outlines, after.nodes, after.edges, SPACING);
  assert.ok(radiusOf(left, 'main.rs') < radiusOf(outlines, 'main.rs'));
});

test('deleting the directory drops the outline drawn around it', () => {
  const before = scene();
  const after = without(before, ['src']);
  const left = outlinesAfterRemoval(manager, drawn(before), after.nodes, after.edges, SPACING);
  assert.equal(radiusOf(left, 'src'), undefined);
});

test('with no outline drawn, as with Group Outlines off, a removal draws none', () => {
  const after = without(scene(), ['init']);
  assert.deepEqual(outlinesAfterRemoval(manager, [], after.nodes, after.edges, SPACING), []);
});
