/**
 * A group outline is the smallest circle round its group, plus padding, and
 * its label sits inside it where no other label is.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { CompoundLayoutManager } from '../../dist-pure/features/graph/services/compound_layout.js';
import { placeOutlineLabels } from '../../dist-pure/features/graph/services/outline_labels.js';

const EPS = 1e-6;
const PADDING = 40;
const R = 3;

const contains = (source, target) => ({ source, target, kind: 'contains' });

/** A directory at the origin holding two files far to its right, each with a symbol. */
function farDirectory() {
  const nodes = [
    { id: 'dir', label: 'src', depth: 0, x: 0, y: 0 },
    { id: 'a', label: 'a.rs', depth: 1, x: 300, y: 0 },
    { id: 'b', label: 'b.rs', depth: 1, x: 400, y: 0 },
    { id: 'a1', label: 'f', depth: 2, x: 300, y: 30 },
    { id: 'b1', label: 'g', depth: 2, x: 400, y: -30 },
  ];
  const edges = [contains('dir', 'a'), contains('dir', 'b'), contains('a', 'a1'), contains('b', 'b1')];
  return { nodes, edges };
}

function outlines() {
  const { nodes, edges } = farDirectory();
  const bounds = new CompoundLayoutManager().computeGroupBounds(nodes, edges, PADDING, R, () => R);
  return { nodes, bounds, byId: Object.fromEntries(bounds.map((b) => [b.nodeId, b])) };
}

const inside = (b, x, y, r) => Math.hypot(x - b.cx, y - b.cy) + r <= b.radius + EPS;

test('a directory outline is centred on its group, not on its node', () => {
  /* Mutation: centre the outline on the directory's node again -- it reaches
     from the node to the farthest file, and this fails. */
  const { byId } = outlines();
  const dir = byId.dir;
  // The group spans from the node at x=0 to b.rs's outline round x=400.
  assert.ok(dir.cx > 150 && dir.cx < 250, `centred at x=${dir.cx}`);
  // Centred on the node, the radius would be over 400 plus padding.
  assert.ok(dir.radius < 300, `radius ${dir.radius}`);
});

test('every outline holds its whole group, its own node included', () => {
  const { nodes, byId } = outlines();
  const at = Object.fromEntries(nodes.map((n) => [n.id, n]));
  for (const [file, symbol] of [['a', 'a1'], ['b', 'b1']]) {
    assert.ok(inside(byId[file], at[file].x, at[file].y, R), `${file} inside its outline`);
    assert.ok(inside(byId[file], at[symbol].x, at[symbol].y, R), `${symbol} inside ${file}'s outline`);
  }
  assert.ok(inside(byId.dir, 0, 0, R), 'the directory node inside its outline');
  for (const file of ['a', 'b']) {
    const f = byId[file];
    assert.ok(inside(byId.dir, f.cx, f.cy, f.radius), `${file}'s outline inside the directory's`);
  }
});

test('an outline is the smallest circle round its group, plus its padding', () => {
  /* Mutation: pad a file's outline by the whole padding -- it is not the
     enclosing circle plus half, and this fails. */
  const { byId } = outlines();
  // a.rs at (300, 0) and its symbol at (300, 30), each r=3: the smallest
  // circle has its centre between them and radius 15 + 3.
  const a = byId.a;
  assert.ok(Math.abs(a.cx - 300) < EPS && Math.abs(a.cy - 15) < EPS, `a.rs at (${a.cx}, ${a.cy})`);
  assert.ok(Math.abs(a.radius - (18 + PADDING / 2)) < EPS, `a.rs radius ${a.radius}`);
});

test('labels of nearly concentric outlines are not written over one another', () => {
  /* Mutation: set every label at the top of its outline -- they stack, and
     this fails. */
  const outlines = [0, 1, 2, 3, 4].map((i) => ({ cx: i, cy: -i, r: 200 - i * 3, w: 60, h: 11 }));
  const places = placeOutlineLabels(outlines);
  const boxes = places.map((p, i) => ({
    l: p.x - outlines[i].w / 2, r: p.x + outlines[i].w / 2, t: p.y - outlines[i].h / 2, b: p.y + outlines[i].h / 2,
  }));
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      assert.ok(!(a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b), `labels ${i} and ${j} overlap`);
    }
  }
  // Each stays inside its own outline, corners included.
  boxes.forEach((b, i) => {
    const o = outlines[i];
    for (const [x, y] of [[b.l, b.t], [b.r, b.t], [b.l, b.b], [b.r, b.b]]) {
      assert.ok(Math.hypot(x - o.cx, y - o.cy) <= o.r + EPS, `label ${i} leaves its outline`);
    }
  });
});

test('a label moves off a node that sits at the top of its outline', () => {
  /* Mutation: place labels without regard to the nodes -- the label covers
     the node at the top, and this fails. */
  const outline = { cx: 0, cy: 0, r: 100, w: 40, h: 10 };
  const node = { x: 0, y: -89, r: 6 };
  const [p] = placeOutlineLabels([outline], [node]);
  const box = { l: p.x - 20, r: p.x + 20, t: p.y - 5, b: p.y + 5 };
  const clear = box.r < node.x - node.r || box.l > node.x + node.r || box.b < node.y - node.r || box.t > node.y + node.r;
  assert.ok(clear, `label at (${p.x}, ${p.y}) covers the node`);
  assert.ok(Math.hypot(p.x, p.y) < 100, 'and stays inside its outline');
});

test('a lone label sits at the top of its outline, inside the rim', () => {
  const [p] = placeOutlineLabels([{ cx: 10, cy: 20, r: 100, w: 40, h: 10 }]);
  assert.ok(Math.abs(p.x - 10) < EPS, `at x=${p.x}`);
  assert.ok(Math.abs(p.y - (20 - 100 + 6 + 5)) < EPS, `at y=${p.y}`);
});
