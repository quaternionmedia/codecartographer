/**
 * rad conformance — this host replaying the governed vectors.
 *
 * Obligation 4 of the rad host integration standard §5. Run with:
 *   npm run test:rad
 * which compiles the platform-free half of src/features/graph/rad to
 * dist-rad/ and then runs this file under node:test. No browser, no new
 * dependency: the core is pure, so it is tested as pure code.
 *
 * The pinned vector version is carried in the FILENAME of the vector file, so
 * a bump is visible in a diff rather than buried in a constant.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { runConformanceWith, checkGeometryBlock } from '../../dist-rad/conformance/run.js';
import { createSession } from '../../dist-rad/session.js';
// The vocabulary this host actually binds, not a copy of it. One governed
// vector (`source: "CHORD_MAP"`) asserts it is prefix-free, so importing the
// real thing is what makes that vector mean something here.
import { CHORD_WORDS as HOST_CHORD_WORDS } from '../../dist-rad/host/vocabulary.js';

const here = dirname(fileURLToPath(import.meta.url));

/** The version this host claims. Must match the vector file it loads. */
const PINNED = '0.4.0';

const vectors = JSON.parse(readFileSync(join(here, `vectors.v${PINNED}.json`), 'utf8'));

test('the vector file on disk is the version this host claims', () => {
  assert.equal(vectors.version, PINNED);
});

test('declared constants match the vector set', () => {
  const r = checkGeometryBlock(vectors);
  assert.ok(r.pass, r.why);
});

test('every governed vector passes against this port', () => {
  const results = runConformanceWith(vectors, { chordWords: HOST_CHORD_WORDS });

  assert.equal(
    results.length,
    vectors.cases.length,
    `ran ${results.length} of ${vectors.cases.length} cases`,
  );

  const failed = results.filter((r) => !r.pass);
  assert.deepEqual(
    failed.map((f) => `${f.name}: ${f.why}`),
    [],
    `${failed.length} of ${results.length} vectors failed`,
  );
});

/**
 * A negative control for the runner itself.
 *
 * A conformance runner that reports success on a broken implementation is
 * worse than no runner, and that failure is invisible from a green run — so
 * the suite watches itself fail before it is believed. Corrupting one
 * expectation must turn the run red.
 */
test('the runner fails when an expectation is wrong (negative control)', () => {
  const trace = vectors.cases.find((c) => c.trace && c.expect);
  assert.ok(trace, 'expected at least one behavioural trace case');

  const sabotaged = {
    ...vectors,
    cases: [{ ...trace, expectHighlights: [...(trace.expectHighlights ?? []), 999] }],
  };
  const [result] = runConformanceWith(sabotaged, { chordWords: HOST_CHORD_WORDS });
  assert.equal(result.pass, false, 'runner reported a pass on a corrupted expectation');
});

/**
 * Standard §1: "rad never reaches the host's scene … nothing in it takes a
 * scene, an element, or a store."
 *
 * Asserted by driving a full release-select against a synthetic host whose
 * scene is a plain object, then checking the scene is byte-identical. This
 * mirrors rad's own integration.spec.mjs so a divergence shows up here rather
 * than in review.
 */
test('a full release-select commits an intent and leaves the host scene untouched', () => {
  const scene = { nodes: [{ id: 'a', x: 1, y: 2 }], edges: [] };
  const before = JSON.stringify(scene);
  const intents = [];

  const session = createSession({
    resolve: () => ({
      title: 'node',
      items: [
        { id: 'expand', label: 'Expand', action: 'expand' },
        { id: 'hide', label: 'Hide', action: 'hide' },
        { id: 'pin', label: 'Pin', action: 'pin' },
        { id: 'del', label: 'Delete', action: 'delete', destructive: true },
      ],
    }),
    onIntent: (i) => intents.push(i),
  });

  const ctx = { type: 'node', targetIds: ['a'], position: { x: 400, y: 300 } };
  session.openAt(ctx, { width: 1200, height: 800 }, 'tracking');
  session.input({ type: 'move', r: 70, thetaDeg: -90 }); // straight up → index 0
  session.input({ type: 'up', r: 70, thetaDeg: -90 });

  assert.equal(intents.length, 1);
  assert.equal(intents[0].action, 'expand');
  assert.equal(intents[0].itemId, 'expand');
  assert.deepEqual(intents[0].context, ctx);
  assert.equal(JSON.stringify(scene), before, 'rad mutated the host scene');
  assert.equal(session.isOpen, false, 'session still open after commit');
});

/** Standard §4: an intent is plain, serializable data — no closures. */
test('a committed intent survives a JSON round trip unchanged', () => {
  let captured = null;
  const session = createSession({
    resolve: () => ({ items: [{ id: 'fit', label: 'Fit', action: 'fit' }] }),
    onIntent: (i) => { captured = i; },
  });
  session.openAt({ type: 'canvas', targetIds: [], position: { x: 0, y: 0 } }, { width: 900, height: 700 });
  session.input({ type: 'key', key: 'ArrowRight' });
  session.input({ type: 'key', key: 'Enter' });

  assert.ok(captured, 'no intent committed');
  assert.deepEqual(JSON.parse(JSON.stringify(captured)), captured);
});

/** Standard §4: an unknown context type is opaque and passed through. */
test('an unknown context type reaches resolve unchanged', () => {
  let seen = null;
  const session = createSession({
    resolve: (c) => { seen = c; return { items: [{ id: 'x', label: 'X', action: 'noop' }] }; },
    onIntent: () => {},
  });
  const ctx = { type: 'compound-group', targetIds: ['dir:src'], position: { x: 5, y: 6 } };
  session.openAt(ctx, { width: 800, height: 600 });
  assert.deepEqual(seen, ctx);
});
