/**
 * The derived layout and replay, tested as pure functions.
 *
 * `layoutNodes` turns a composed document into fractional positions, and the
 * two properties that matter are the ones a glance at a working demo cannot
 * check: every position stays inside [0,1] whatever the component count, and
 * a role column with more entries than fit splits sideways instead of
 * compressing into an unreadable stack. moat's real shape — twenty-one charts
 * in one role — is the case that found the need for both.
 *
 *   npm run test:system
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  layoutNodes,
  layoutEdges,
  demoFrom,
  MAX_ROWS,
  SystemDefinitionRegistry,
} from '../../dist-system/system_core.js';

function composed(components, edges = []) {
  return { system: 't', commit: 'abc1234', components, edges };
}

function chart(id, role = 'chart') {
  return { id, name: id.split('/').pop(), role, group: 'charts',
           version: '1.0.0', upstreams: [] };
}

// ─── layoutNodes ─────────────────────────────────────────────────────────────

test('every position is inside the unit square, at moat scale and beyond', () => {
  const many = composed([
    ...Array.from({ length: 40 }, (_, i) => chart(`charts/c${i}`)),
    chart('infra', 'infrastructure'),
    chart('deploy', 'deployer'),
    chart('tower', 'application'),
  ]);
  for (const [id, node] of Object.entries(layoutNodes(many))) {
    assert.ok(node.px >= 0 && node.px <= 1, `${id} px=${node.px}`);
    assert.ok(node.py >= 0 && node.py <= 1, `${id} py=${node.py}`);
  }
});

test('a crowded role splits into columns instead of stacking', () => {
  const many = composed(
    Array.from({ length: MAX_ROWS * 2 }, (_, i) => chart(`charts/c${i}`)));
  const xs = new Set(Object.values(layoutNodes(many)).map(n => n.px));
  assert.ok(xs.size >= 2,
    `${MAX_ROWS * 2} charts landed in ${xs.size} column(s)`);
});

test('a single node in a role sits centred, not at the top', () => {
  const nodes = layoutNodes(composed([chart('infra', 'infrastructure')]));
  assert.equal(nodes['infra'].py, 0.5);
});

test('an unknown role still lands on the canvas', () => {
  const nodes = layoutNodes(composed([chart('x', 'mystery-role')]));
  assert.ok(nodes['x'].px > 0 && nodes['x'].px < 1);
});

// ─── layoutEdges ─────────────────────────────────────────────────────────────

test('deploy edges are dashed and dependency edges dim, both labelled', () => {
  const edges = layoutEdges(composed([], [
    { source: 'a', target: 'b', kind: 'deploys' },
    { source: 'b', target: 'c', kind: 'depends' },
  ]));
  assert.deepEqual(edges.map(e => [e.style, e.label]),
    [['dashed', 'deploys'], ['dim', 'depends']]);
});

// ─── demoFrom ────────────────────────────────────────────────────────────────

test('the demo replays history oldest-first with monotonic timestamps', () => {
  const demo = demoFrom({
    changes: [
      { sha: 'a', when: '2026-01-01', subject: 'first', components: ['x'] },
      { sha: 'b', when: '2026-01-02', subject: 'second', components: [] },
    ],
    in_flight: [{ branch: 'wip', commits: 2, components: ['x'] }],
  });
  const stamps = demo.map(ev => ev.timestamp);
  assert.deepEqual([...stamps].sort((a, b) => a - b), stamps);
  assert.equal(demo[0].subject, 'first');
  assert.equal(demo.at(-1).event_type, 'replay_done');
});

test('every demo frame says it is a replay', () => {
  const demo = demoFrom({
    changes: [{ sha: 'a', when: 'd', subject: 's', components: [] }],
    in_flight: [],
  });
  assert.ok(demo.every(ev => ev.replay === true),
    'a frame without replay:true would let history read as a live tail');
});

// ─── the registry ────────────────────────────────────────────────────────────

test('the registry serves whichever definitions register, none hard-wired', () => {
  const a = { id: 'a', name: 'A', description: '', wsPath: '',
              httpStatusPath: '', getNodes: () => ({}), getEdges: () => [],
              getDemoEvents: () => [], handleEvent: () => {} };
  const b = { ...a, id: 'b', name: 'B' };
  SystemDefinitionRegistry.register(a);
  SystemDefinitionRegistry.register(b);
  assert.equal(SystemDefinitionRegistry.get('a'), a);
  assert.equal(SystemDefinitionRegistry.get('b'), b);
  assert.equal(SystemDefinitionRegistry.all().length, 2);
  assert.equal(SystemDefinitionRegistry.default(), a);
});
