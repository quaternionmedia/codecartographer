/**
 * Graph data is replaced, never merged.
 *
 * **THE DEFECT THIS PINS.** `StateController.update` applies a `mergerino`
 * patch, and mergerino deep-merges. `graphData.graph.nodes` is an object keyed
 * by node id, so `update({ graphData: next })` produced the *union* of the new
 * graph and every graph drawn before it. Switching between two harness
 * topologies showed it plainly — they share ids like `in` and `out`, so
 * delegation (6 nodes) became 9, then 11, and switching back still showed 11.
 * Between two repositories it would have looked like an oddly large graph.
 *
 * **WHY THIS IS HERE AND NOT IN THE BROWSER SUITE.** An end-to-end version
 * depends on the Graph panel being open in whatever layout the run happens to
 * have, which is a property of the dock and not of this bug. This asserts the
 * merge semantics directly: fast, deterministic, and about the actual defect.
 *
 *   node --test tests/state/
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import mergerino from 'mergerino';

const merge = mergerino.default ?? mergerino;

/** Two graphs whose node ids overlap, exactly as two topologies do. */
const DELEGATION = { graph: { nodes: { in: {}, route: {}, w1: {}, w2: {}, none: {}, out: {} } } };
const PIPELINE = { graph: { nodes: { in: {}, s1: {}, s2: {}, s3: {}, out: {} } } };

const nodeCount = (state) => Object.keys(state.graphData.graph.nodes).length;

test('a plain patch merges graphs, which is the bug', () => {
  // Documented rather than desired: this is what the codebase did, and the
  // test exists so nobody reintroduces it believing patches replace.
  let state = merge({ graphData: null }, { graphData: DELEGATION });
  assert.equal(nodeCount(state), 6);

  state = merge(state, { graphData: PIPELINE });
  assert.equal(nodeCount(state), 9, 'a plain patch is a union, not a replacement');
});

test('a function patch replaces, which is the fix', () => {
  let state = merge({ graphData: null }, { graphData: () => DELEGATION });
  assert.equal(nodeCount(state), 6);

  state = merge(state, { graphData: () => PIPELINE });
  assert.equal(nodeCount(state), 5, 'pipeline has five nodes and only five');

  state = merge(state, { graphData: () => DELEGATION });
  assert.equal(nodeCount(state), 6, 'going back must give the original graph');
});

test('clearing sets the data to null rather than leaving it', () => {
  // `clear()` emptied the rendered vnodes and left `graphData` behind, so the
  // next plot merged into a graph nothing was showing.
  let state = merge({ graphData: null }, { graphData: () => DELEGATION });
  state = merge(state, { graphContent: [], graphData: null });
  assert.equal(state.graphData, null);

  state = merge(state, { graphData: () => PIPELINE });
  assert.equal(nodeCount(state), 5);
});

test('StateController replaces rather than patching graph data', async () => {
  // The guard that matters for the source: `renderGraphData` must not go
  // through a plain patch. Read as text because compiling the TypeScript here
  // would need a build step this suite does not have.
  const { readFileSync } = await import('node:fs');
  const actions = readFileSync('src/state/actions.ts', 'utf8');
  const controller = readFileSync('src/state/state_controller.ts', 'utf8');

  assert.ok(
    !/update\(\{\s*graphData\s*\}\)/.test(actions),
    'graph data is being set with a plain patch, which merges',
  );
  assert.ok(
    controller.includes('replaceGraphData'),
    'the replacing setter is missing',
  );
  assert.ok(
    /graphData:\s*\(\)\s*=>/.test(controller),
    'replaceGraphData does not use a function patch',
  );
});
