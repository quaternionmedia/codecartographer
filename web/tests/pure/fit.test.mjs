/**
 * The fit frames the bounding box of what is drawn, inside a margin.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { FIT_DEFAULTS, boundsOf, fitTransform, framedExtents } from '../../dist-pure/features/graph/services/fit.js';

const VIEW = { width: 1600, height: 600 };
const EPS = 1e-6;

/** Where a circle's box lands on screen under a transform. */
function onScreen(t, { x, y, r }) {
  return {
    left: (x - r) * t.k + t.x,
    right: (x + r) * t.k + t.x,
    top: (y - r) * t.k + t.y,
    bottom: (y + r) * t.k + t.y,
  };
}

function assertInside(t, circles, view = VIEW, margin = FIT_DEFAULTS.margin) {
  for (const c of circles) {
    const s = onScreen(t, c);
    assert.ok(s.left >= margin - EPS && s.right <= view.width - margin + EPS,
      `circle at (${c.x}, ${c.y}) r ${c.r} spans x ${s.left}..${s.right} on a ${view.width} canvas`);
    assert.ok(s.top >= margin - EPS && s.bottom <= view.height - margin + EPS,
      `circle at (${c.x}, ${c.y}) r ${c.r} spans y ${s.top}..${s.bottom} on a ${view.height} canvas`);
  }
}

test("the frame is centred on the bounding box, not the nodes' average", () => {
  /* Mutation: centre on the average of the circles' centres -- the crowd on
     the left pulls the frame off the box's middle, and this fails. */
  const circles = [
    ...Array.from({ length: 9 }, (_, i) => ({ x: -100 + i, y: 0, r: 4 })),
    { x: 300, y: 0, r: 4 },
  ];
  const t = fitTransform(circles, VIEW);
  const box = boundsOf(circles);
  assert.ok(Math.abs(((box.minX + box.maxX) / 2) * t.k + t.x - VIEW.width / 2) < EPS);
  assert.ok(Math.abs(((box.minY + box.maxY) / 2) * t.k + t.y - VIEW.height / 2) < EPS);
  assertInside(t, circles);
});

test('a group outline wider than its nodes is framed whole', () => {
  /* Mutation: frame the circles' centres and not their extents -- the outline
     runs off the canvas, and this fails. */
  const nodes = [{ x: -50, y: -20, r: 4 }, { x: 50, y: 20, r: 4 }];
  const outline = { x: 0, y: 0, r: 180 };
  const t = fitTransform([...nodes, outline], VIEW);
  assertInside(t, [...nodes, outline]);
  assert.ok(t.k < fitTransform(nodes, VIEW).k, 'the outline widens the frame');
});

test('the tighter axis fills the canvas up to the margin', () => {
  /* Mutation: scale by 0.85 of the fit instead of to the margin -- the frame
     stops short of it, and this fails. */
  const circles = [{ x: 0, y: -100, r: 10 }, { x: 40, y: 100, r: 10 }];
  const t = fitTransform(circles, VIEW);
  const top = Math.min(...circles.map((c) => onScreen(t, c).top));
  const bottom = Math.max(...circles.map((c) => onScreen(t, c).bottom));
  assert.ok(Math.abs(top - FIT_DEFAULTS.margin) < EPS, `top edge at ${top}`);
  assert.ok(Math.abs(bottom - (VIEW.height - FIT_DEFAULTS.margin)) < EPS, `bottom edge at ${bottom}`);
});

test('one small node is framed at the most a fit zooms in, centred', () => {
  /* Mutation: drop the upper limit -- one 4px node fills the canvas, and this
     fails. */
  const t = fitTransform([{ x: 30, y: -12, r: 4 }], VIEW);
  assert.equal(t.k, FIT_DEFAULTS.maxScale);
  assert.ok(Math.abs(30 * t.k + t.x - VIEW.width / 2) < EPS);
  assert.ok(Math.abs(-12 * t.k + t.y - VIEW.height / 2) < EPS);
});

test('a graph too large for the canvas is held at the zoom limit', () => {
  const t = fitTransform([{ x: -1e6, y: 0, r: 1 }, { x: 1e6, y: 0, r: 1 }], VIEW);
  assert.equal(t.k, FIT_DEFAULTS.minScale);
});

test('nothing to frame, or nothing with a place, gives no transform', () => {
  assert.equal(fitTransform([], VIEW), null);
  assert.equal(fitTransform([{ x: NaN, y: 0, r: 4 }], VIEW), null);
  assert.equal(boundsOf([]), null);
});

/** A node's label as the renderer draws it: centred under the node, `size + 12` below, `width` wide. */
function labelBox(x, y, size, width, fontSize = 9) {
  const baseline = y + size + 12;
  return { minX: x - width / 2, maxX: x + width / 2, minY: baseline - fontSize, maxY: baseline + 0.25 * fontSize };
}

function assertBoxInside(t, b, view = VIEW, margin = FIT_DEFAULTS.margin) {
  const left = b.minX * t.k + t.x;
  const right = b.maxX * t.k + t.x;
  const top = b.minY * t.k + t.y;
  const bottom = b.maxY * t.k + t.y;
  assert.ok(left >= margin - EPS && right <= view.width - margin + EPS,
    `box ${b.minX}..${b.maxX} spans x ${left}..${right} on a ${view.width} canvas`);
  assert.ok(top >= margin - EPS && bottom <= view.height - margin + EPS,
    `box ${b.minY}..${b.maxY} spans y ${top}..${bottom} on a ${view.height} canvas`);
}

test('a shown label is framed whole, however far it runs past its node', () => {
  /* Mutation: frame the nodes without their labels -- the long labels at the
     graph's two ends run off the canvas, and this fails. */
  const nodes = [
    { id: 'left', x: -300, y: 0, reach: 6, label: labelBox(-300, 0, 4, 300) },
    { id: 'right', x: 300, y: 0, reach: 6, label: labelBox(300, 0, 4, 300) },
  ];
  const t = fitTransform(framedExtents(nodes, []), VIEW);
  for (const n of nodes) assertBoxInside(t, n.label);
  assertInside(t, nodes.map((n) => ({ x: n.x, y: n.y, r: n.reach })));
});

test('a label that is not shown is not framed', () => {
  const nodes = [
    { id: 'a', x: 0, y: 0, reach: 6, label: null },
    { id: 'b', x: 100, y: 0, reach: 6, label: null },
  ];
  assert.deepEqual(boundsOf(framedExtents(nodes, [])), { minX: -6, minY: -6, maxX: 106, maxY: 6 });
});

test('a hidden node is not framed, nor an outline that holds only hidden nodes', () => {
  /* Mutation: frame every node the renderer holds, hidden or not -- the
     hidden file far to the right, its label and its outline widen the frame,
     and this fails. Hide draws a node at opacity 0 and keeps it, so the fit
     is what has to leave it out. */
  const nodes = [
    { id: 'src', x: 0, y: 0, reach: 18, label: null },
    { id: 'main.rs', x: 60, y: 0, reach: 11, label: labelBox(60, 0, 7, 40) },
    { id: 'main', x: 90, y: 0, reach: 6, label: null },
    { id: 'far.rs', x: 900, y: 0, reach: 11, label: labelBox(900, 0, 7, 40) },
    { id: 'far', x: 940, y: 0, reach: 6, label: null },
  ];
  const outlines = [
    { nodeId: 'src', x: 0, y: 0, r: 150 },
    { nodeId: 'main.rs', x: 60, y: 0, r: 50 },
    { nodeId: 'far.rs', x: 900, y: 0, r: 60 },
  ];
  const children = new Map([['src', ['main.rs', 'main']], ['main.rs', ['main']], ['far.rs', ['far']]]);
  const hidden = new Set(['far.rs', 'far', 'main']);
  const extents = framedExtents(nodes, outlines, (id) => children.get(id) ?? [], (id) => hidden.has(id));
  // src's outline holds main.rs, which is shown; far.rs's holds only hidden nodes.
  assert.deepEqual(boundsOf(extents), { minX: -150, minY: -150, maxX: 150, maxY: 150 });
});

test("an outline whose own node is hidden is framed while it holds a shown node", () => {
  const nodes = [
    { id: 'src', x: 0, y: 0, reach: 18, label: null },
    { id: 'lib.rs', x: 300, y: 0, reach: 11, label: null },
  ];
  const outlines = [{ nodeId: 'src', x: 0, y: 0, r: 330 }];
  const extents = framedExtents(nodes, outlines, () => ['lib.rs'], (id) => id === 'src');
  assert.deepEqual(boundsOf(extents), { minX: -330, minY: -330, maxX: 330, maxY: 330 });
});

test('an outline is framed with the nodes it is drawn around, and not with others', () => {
  const nodes = [{ id: 'file', x: 0, y: 0, reach: 6, label: null }];
  const around = { nodeId: 'file', x: 0, y: 0, r: 80 };
  const elsewhere = { nodeId: 'other', x: 900, y: 0, r: 80 };
  assert.deepEqual(boundsOf(framedExtents(nodes, [around, elsewhere])), { minX: -80, minY: -80, maxX: 80, maxY: 80 });
});
