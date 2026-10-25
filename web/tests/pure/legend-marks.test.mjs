/**
 * The legend describes the graph that was drawn.
 *
 * **WHAT THIS IS FOR, AND WHAT A DOM TEST WOULD MISS.** Asserting that a key
 * renders six rows is easy and proves nothing: the key this replaces rendered
 * six rows unconditionally, naming node kinds whether or not the graph held
 * any. The question worth testing is whether every row corresponds to something
 * on screen and every thing on screen is covered by a row — which is these
 * functions, and nothing to do with markup.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  DEFAULT_EDGE_COLOR,
  DEFAULT_EDGE_KIND,
  DEFAULT_NODE_COLOR,
  DEFAULT_NODE_KIND,
  drawnFill,
  edgeMarks,
  layerMarks,
  marksCover,
  nodeLabel,
  nodeMarks,
  readable,
  swatchPath,
} from '../../dist-pure/features/graph/extensions/legend_marks.js';
import {
  KNOWN_SHAPES,
  canvasPath,
  nodePath,
} from '../../dist-pure/features/graph/services/node_shapes.js';

// --- what the key covers -------------------------------------------------------

test('every node is accounted for by exactly one mark', () => {
  const nodes = [
    { kind: 'function', shape: 'hexagon', color: '#a' },
    { kind: 'function', shape: 'hexagon', color: '#a' },
    { kind: 'class', shape: 'square', color: '#b' },
    {},
  ];

  const marks = nodeMarks(nodes);

  // Mutation: drop the `else seen.set(...)` branch and this fails — the
  // unkinded node stops being counted and the key silently describes 3 of 4.
  assert.equal(marksCover(marks), nodes.length);
});

test('a node with no kind is counted under a default rather than dropped', () => {
  const marks = nodeMarks([{}]);
  assert.equal(marks.length, 1);
  assert.equal(marks[0].kind, DEFAULT_NODE_KIND);
  assert.equal(marks[0].color, DEFAULT_NODE_COLOR);
  assert.equal(marks[0].shape, undefined);
});

test('one kind drawn two ways is two rows', () => {
  /** A reader matches a swatch against what is on screen, not against an average. */
  const marks = nodeMarks([
    { kind: 'file', shape: 'square', color: '#aaa' },
    { kind: 'file', shape: 'diamond', color: '#aaa' },
  ]);

  // Mutation: key on `kind` alone and this collapses to one row.
  assert.equal(marks.length, 2);
  assert.deepEqual(marks.map((m) => m.shape).sort(), ['diamond', 'square']);
});

test('marks come back most common first', () => {
  const marks = nodeMarks([
    { kind: 'rare', shape: 'square', color: '#a' },
    { kind: 'common', shape: 'square', color: '#b' },
    { kind: 'common', shape: 'square', color: '#b' },
    { kind: 'common', shape: 'square', color: '#b' },
  ]);
  assert.equal(marks[0].kind, 'common');
  assert.equal(marks[0].count, 3);
});

// --- edges ---------------------------------------------------------------------

test('edge kind is read before edge label', () => {
  /** A label is per-edge and would give one row per edge. `kind` is the class. */
  const marks = edgeMarks([
    { kind: 'CALLS', label: 'alpha->beta', color: '#f90' },
    { kind: 'CALLS', label: 'beta->gamma', color: '#f90' },
  ]);

  // Mutation: read `label` first and this becomes two rows.
  assert.equal(marks.length, 1);
  assert.equal(marks[0].kind, 'CALLS');
  assert.equal(marks[0].count, 2);
});

test('an edge with neither kind nor label still counts', () => {
  const marks = edgeMarks([{}, {}]);
  assert.equal(marks.length, 1);
  assert.equal(marks[0].kind, DEFAULT_EDGE_KIND);
  assert.equal(marks[0].color, DEFAULT_EDGE_COLOR);
  assert.equal(marksCover(marks), 2);
});

test('an empty graph produces no rows rather than a default one', () => {
  assert.deepEqual(nodeMarks([]), []);
  assert.deepEqual(edgeMarks([]), []);
});

// --- display -------------------------------------------------------------------

test('schema words are made readable without becoming a different word', () => {
  assert.equal(readable('async_function'), 'Async function');
  assert.equal(readable('file'), 'File');
  assert.equal(readable(''), '');
});

// --- the swatch and the canvas cannot disagree ---------------------------------

/**
 * A polygon path's vertices about their centre, scaled to unit radius; null
 * for a path with curves (the circle).
 *
 * **TWO PATHS ARE ONE MARK WHEN THEY HAVE ONE OUTLINE, NOT ONE STRING.** A
 * four-sided polygon inscribed in radius `s` and the square of half-side `s`
 * are different strings and the same square on screen, so comparing strings
 * passes exactly the collisions a reader cannot see past.
 */
function outline(path) {
  if (/[AaCcQq]/.test(path)) return null;
  const nums = path.match(/-?\d+(\.\d+)?/g).map(Number);
  const points = [];
  for (let i = 0; i < nums.length; i += 2) points.push([nums[i], nums[i + 1]]);
  const cx = points.reduce((t, [x]) => t + x, 0) / points.length;
  const cy = points.reduce((t, [, y]) => t + y, 0) / points.length;
  const r = Math.max(...points.map(([x, y]) => Math.hypot(x - cx, y - cy)));
  return points.map(([x, y]) => [(x - cx) / r, (y - cy) / r]);
}

function sameMark(a, b) {
  const pa = outline(a);
  const pb = outline(b);
  if (pa === null || pb === null) return pa === pb;
  if (pa.length !== pb.length) return false;
  return pa.every(([x, y]) => pb.some(([u, v]) => Math.hypot(x - u, y - v) < 0.03));
}

test('every known shape draws a mark no other shape draws', () => {
  /**
   * The key's whole job is that a swatch matches a node. An unknown shape falls
   * through to a circle, which is indistinguishable from a node that asked for
   * one — so a shape silently dropped from the switch would produce a key that
   * confidently draws the wrong mark.
   *
   * `rectangle` drew `square`'s path, so three constructs (an impl, a foreign
   * block, a linker section) were a class's or a field's mark. Mutation: put
   * `case 'rectangle':` back under `square` -- this fails naming the pair; delete
   * the `diamond` case and it fails naming diamond and circle.
   */
  for (const a of KNOWN_SHAPES) {
    for (const b of KNOWN_SHAPES) {
      if (a < b) assert.ok(!sameMark(nodePath(a, 8), nodePath(b, 8)), `${a} and ${b} draw one mark`);
    }
  }
});

test("a record's polygon is no other shape's mark, whatever its side count", () => {
  /**
   * A regular polygon with a vertex at the top is `diamond` at four sides and
   * `hexagon` at six, so every four-field struct, every C union and every Rust
   * unit struct was drawn as a function. Mutation: draw the polygon with a
   * vertex at the top again -- this fails at four and six.
   */
  for (let sides = 3; sides <= 12; sides++) {
    const record = nodePath('ngon', 8, sides);
    for (const other of KNOWN_SHAPES.filter((s) => s !== 'ngon')) {
      assert.ok(!sameMark(record, nodePath(other, 8)), `a ${sides}-sided record draws as ${other}`);
    }
  }
});

test('the canvas draws the side count it is sent, from three up', () => {
  /**
   * The range is the server's (`construct_service.NGON_SIDES`), stated once:
   * the canvas restated it as 3..12 while the parsers clamped 3..10. Mutation:
   * clamp to 12 here again -- fourteen fails.
   */
  const corners = (path) => outline(path).length;
  assert.equal(corners(nodePath('ngon', 8, 7)), 7);
  assert.equal(corners(nodePath('ngon', 8, 14)), 14);
  assert.equal(corners(nodePath('ngon', 8, 2)), 3, 'fewer than three is not a polygon');
  assert.equal(corners(nodePath('ngon', 8)), 5, 'no count is the pentagon default');
  assert.notEqual(nodePath('ngon', 8, 6), nodePath('circle', 8));
});

test('a shape nobody registered falls back to the circle', () => {
  assert.equal(nodePath('trapezoid', 8), nodePath('circle', 8));
});

/** Nodes as the canvas holds them once drawn: records of two sizes, layered and not. */
const DRAWN = [
  { kind: 'struct', shape: 'ngon', color: '#4a9eff', meta: { sides: 4 } },
  { kind: 'struct', shape: 'ngon', color: '#4a9eff', meta: { sides: 7 } },
  { kind: 'struct', shape: 'ngon', color: '#4a9eff', meta: { sides: 7 }, language: 'c',
    layer_ordinal: 2, layer_color: '#eab308' },
  { kind: 'function', shape: 'diamond', color: '#ff9d3d', language: 'c',
    layer_ordinal: 0, layer_color: '#ef4444' },
  { kind: 'function', shape: 'diamond', color: '#ff9d3d' },
  { kind: 'token', shape: 'circle', color: '#95a5a6', layer_ordinal: 1 },
  { kind: 'field', shape: 'square' },
];

for (const colorBy of ['auto', 'layer']) {
  test(`every node's row draws the path and fill the canvas draws it with (${colorBy})`, () => {
    /**
     * The key drew every record as a pentagon, because a mark carried no side
     * count, and kept each node's own colour while "Color By: Abstraction
     * Layer" painted the canvas by layer. Mutation: drop `sides` from the mark,
     * or key the fill on `node.color` -- this fails.
     */
    const marks = nodeMarks(DRAWN, colorBy);
    assert.equal(marksCover(marks), DRAWN.length);
    for (const node of DRAWN) {
      const [own] = nodeMarks([node], colorBy);
      assert.equal(swatchPath(own, 8), canvasPath(node, 8), `${node.kind} swatch`);
      assert.equal(own.color, drawnFill(node, colorBy), `${node.kind} fill`);
      assert.ok(marks.some((m) => swatchPath(m, 8) === swatchPath(own, 8) && m.color === own.color
        && m.kind === own.kind), `${node.kind} has a row`);
    }
  });
}

test('the canvas paints a layer only where the server sent its colour', () => {
  /** A node the server placed on a layer but sent no colour for keeps its own. */
  assert.equal(drawnFill({ color: '#123456', layer_ordinal: 1 }, 'layer'), '#123456');
  assert.equal(drawnFill({ color: '#123456', layer_color: '#ef4444' }, 'layer'), '#ef4444');
  assert.equal(drawnFill({ color: '#123456', layer_color: '#ef4444' }, 'auto'), '#123456');
  assert.equal(drawnFill({}, 'layer'), DEFAULT_NODE_COLOR);
});

test("a record's row says how many sides it is drawn with", () => {
  const [four, seven] = nodeMarks(DRAWN.slice(0, 2), 'auto').sort((a, b) => a.sides - b.sides);
  assert.equal(nodeLabel(four), 'Struct · 4 sides');
  assert.equal(nodeLabel(seven), 'Struct · 7 sides');
  assert.equal(nodeLabel(nodeMarks([{ kind: 'function', shape: 'diamond' }])[0]), 'Function');
});

// --- abstraction layers ----------------------------------------------------------

const C_STORAGE = { kind: 'keyword', layer_ordinal: 0, layer_name: 'Storage & memory placement', group: 'storage class' };
const C_AGGREGATE = { kind: 'keyword', layer_ordinal: 2, layer_name: 'Aggregate & user-defined types', group: 'aggregate' };

test('the layers key counts only nodes the canvas paints by layer, machine-facing first', () => {
  const marks = layerMarks([
    { language: 'c', layer_ordinal: 2, layer_color: '#eab308', meta: { lexicon_layers: [C_AGGREGATE] } },
    { language: 'c', layer_ordinal: 0, layer_color: '#ef4444', meta: { lexicon_layers: [C_STORAGE] } },
    { language: 'c', layer_ordinal: 2, layer_color: '#eab308', meta: { lexicon_layers: [C_AGGREGATE] } },
    { kind: 'function' },
    { layer_ordinal: -1 },
  ], 'layer');
  assert.deepEqual(marks.map((m) => [m.label, m.color, m.count]), [
    ['L0 Storage & memory placement', '#ef4444', 1],
    ['L2 Aggregate & user-defined types', '#eab308', 2],
  ]);
});

test('the layers key names a layer only where the canvas paints a node in its colour', () => {
  /**
   * In "Auto" the canvas draws each node's own colour, and the key listed layer
   * swatches nothing on screen was painted with. Mutation: ignore `colorBy` in
   * `layerMarks` -- this fails.
   */
  const nodes = DRAWN.filter((n) => n.layer_color);
  assert.deepEqual(layerMarks(nodes, 'auto'), []);
  assert.equal(layerMarks(nodes, 'layer').length, 2);
});

test("a node whose own colour is its layer's is keyed by layer in any colouring", () => {
  /**
   * The chrestomathy's tokens are coloured by their layer by the server
   * (`color` is `layer_color`), so "Auto" paints layers there and the key has to
   * name them. Mutation: return no rows unless `colorBy` is `layer` -- this
   * fails.
   */
  const token = { kind: 'token', language: 'c', color: '#ef4444', layer_ordinal: 0, layer_color: '#ef4444',
    meta: { lexicon_layers: [C_STORAGE] } };
  assert.deepEqual(layerMarks([token], 'auto').map((m) => m.label), ['L0 Storage & memory placement']);
  assert.deepEqual(layerMarks([token], 'layer').map((m) => m.label), ['L0 Storage & memory placement']);
});

test('a node placed on a layer but sent no colour is not keyed as one', () => {
  /**
   * The lexicon graph sent `layer_ordinal` and no `layer_color`; the canvas drew
   * those nodes in their own colours and the key listed each layer in a
   * steelblue it never drew. Mutation: count a node by `layer_ordinal` alone --
   * this fails.
   */
  const placed = { kind: 'token', color: '#95a5a6', layer_ordinal: 1 };
  assert.deepEqual(layerMarks([placed], 'layer'), []);
  assert.equal(nodeMarks([placed], 'layer')[0].color, '#95a5a6');
});

test('one ordinal in two languages is two layers, each named with its language', () => {
  /**
   * An ordinal is a rank within one lexicon, so C's layer 0 and Python's layer
   * 0 are different layers in one colour; the key keyed rows on the ordinal and
   * named whichever it saw first. Mutation: key `layerMarks` on the ordinal
   * alone -- this fails with one row.
   */
  const marks = layerMarks([
    { language: 'c', layer_ordinal: 0, layer_color: '#ef4444', meta: { lexicon_layers: [C_STORAGE] } },
    { language: 'python', layer_ordinal: 0, layer_color: '#ef4444',
      meta: { lexicon_layers: [{ kind: 'keyword', layer_ordinal: 0, layer_name: 'Control flow', group: 'loop' }] } },
  ], 'layer');
  assert.deepEqual(marks.map((m) => m.label), [
    'C · L0 Storage & memory placement',
    'Python · L0 Control flow',
  ]);
});

test("a lexicon's keyword and operator layers of one ordinal are two rows", () => {
  /** As `LexiconService.to_graph` sends them: one language, two hierarchies. */
  const operator = { kind: 'operator', layer_ordinal: 0, layer_name: 'Memory & address', group: 'address' };
  const marks = layerMarks([
    { language: 'c', kind: 'keywords', layer_ordinal: 0, layer_color: '#ef4444', meta: { lexicon_layers: [C_STORAGE] } },
    { language: 'c', kind: 'operators', layer_ordinal: 0, layer_color: '#ef4444', meta: { lexicon_layers: [operator] } },
    { language: 'c', kind: 'operators', layer_ordinal: 0, layer_color: '#ef4444', meta: { lexicon_layers: [operator] } },
  ], 'layer');
  assert.deepEqual(marks.map((m) => [m.label, m.count]), [
    ['L0 Memory & address', 2],
    ['L0 Storage & memory placement', 1],
  ]);
});

// --- constructs ------------------------------------------------------------------

test('the constructs key is one row per construct, whichever language drew it', async () => {
  /* Mutation: key the rows on language and construct -- a C struct and a Rust
     struct become two rows and this fails. */
  const { constructMarks } = await import('../../dist-pure/features/graph/extensions/legend_marks.js');
  const marks = constructMarks([
    { language: 'c', construct: 'type.product', construct_name: 'Product type', construct_color: '#4a9eff' },
    { language: 'rust', construct: 'type.product', construct_name: 'Product type', construct_color: '#4a9eff' },
    { language: 'rust', construct: 'callable.function', construct_name: 'Function', construct_color: '#ff9d3d' },
    { language: 'javascript', kind: 'function' },
  ]);
  assert.deepEqual(marks.map((m) => [m.construct, m.name, m.color, m.count]), [
    ['type.product', 'Product type', '#4a9eff', 2],
    ['callable.function', 'Function', '#ff9d3d', 1],
  ]);
});
