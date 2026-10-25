/**
 * The Topology, Capabilities and Overview panels bring the canvas forward only
 * when their draw drew.
 *
 * **THE DEFECT THIS PINS.** Their draws resolved `void` whether the seam
 * answered a graph or a problem, and each panel brought the Graph panel to the
 * front when the draw resolved -- so a seam that was down put the canvas, and
 * whatever it held before, over the panel's own problem view, which says what
 * is wrong and how to try again. The Cargo and Chrestomathy panels already
 * asked (`cartography_actions.ts`'s draws resolve whether a graph reached the
 * canvas). `docs/ui.md` says the panels bring the canvas forward when they
 * have drawn.
 *
 * Read as text: `actions.ts` and the panels are application code no test build
 * compiles. The draws' `Promise<boolean>` makes the compiler hold every path
 * to an answer.
 *
 *   npm run test:state
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const actions = readFileSync('src/state/actions.ts', 'utf8');

const PANELS = {
  loadTopology: 'src/layout/panels/topology_panel.ts',
  drawCapabilities: 'src/layout/panels/capabilities_panel.ts',
  drawOverview: 'src/layout/panels/overview_panel.ts',
};

for (const [action, file] of Object.entries(PANELS)) {
  test(`${action} resolves whether it drew`, () => {
    /** Mutation: declare it `Promise<void>` again -- this fails. */
    const declared = new RegExp(`\\n  async ${action}\\([^)]*\\): Promise<(\\w+)>`).exec(actions);
    assert.ok(declared, `${action} was not found in actions.ts; the pattern is stale`);
    assert.equal(declared[1], 'boolean');
  });

  test(`${file.split('/').pop()} brings the canvas forward only when the draw drew`, () => {
    /** Mutation: `.then(() => ctx.focusDockPanel('graph'))` -- the canvas covers the problem view, and this fails. */
    const source = readFileSync(file, 'utf8');
    const focuses = source.match(/focusDockPanel\('graph'\)/g) ?? [];
    assert.ok(focuses.length > 0, `${file} brings the canvas forward nowhere; the pattern is stale`);
    const gated = source.match(/\.then\(\(drawn\) => \{ if \(drawn\) ctx\.focusDockPanel\('graph'\); \}\)/g) ?? [];
    assert.equal(gated.length, focuses.length, `${file} brings the canvas forward over a problem it was answered with`);
  });
}

test('drawShow resolves whether it drew, and the Show path brings the canvas forward only then', () => {
  /** Mutation: let drawShow resolve void again, or focus the canvas after it unconditionally -- this fails. */
  const declared = /\n  async drawShow\([^)]*\): Promise<(\w+)>/.exec(actions);
  assert.ok(declared, 'drawShow was not found in actions.ts; the pattern is stale');
  assert.equal(declared[1], 'boolean');
  const layout = readFileSync('src/layout/layout_context.ts', 'utf8');
  const call = /(\S.*)await this\.plotWith\(\(\) => this\.actions\.plot\.drawShow\(address\)\);\s*\n\s*(.+)\n/.exec(layout);
  assert.ok(call, 'the Show path does not call drawShow as this test reads it; the pattern is stale');
  assert.match(call[1], /const drawn = $/, 'the Show path does not keep whether drawShow drew');
  assert.match(call[2], /^if \(drawn\) this\.focusDockPanel\('graph'\);/, 'the Show path brings the canvas forward over a problem');
});

test('a seam\'s draw answers false when it holds a problem, and true when it drew', () => {
  /** Mutation: return true from `_draw` whatever it was answered -- this fails. */
  const found = /\n {2}private _draw\([^)]*\): boolean \{([\s\S]*?)\n {2}\}\n/.exec(actions);
  assert.ok(found, '_draw was not found in actions.ts, or does not answer a boolean; the pattern is stale');
  const [problem, drew] = found[1].split(/\n {4}\}\n/);
  assert.match(problem, /if \(isProblem\(found\)\)[\s\S]*return false;/);
  assert.match(drew, /handlePlotData[\s\S]*return true;/);
});

test("the topology's draw answers false when the harness answers a problem, and true when it drew", () => {
  /** Mutation: return true from the problem branch -- this fails. */
  const found = /\n {2}async loadTopology\([^)]*\): Promise<boolean> \{([\s\S]*?)\n {2}\}\n/.exec(actions);
  assert.ok(found, 'loadTopology was not found in actions.ts; the pattern is stale');
  const branch = /if \(TopologyService\.isProblem\(found\)\) \{([\s\S]*?)\n {6}\}\n/.exec(found[1]);
  assert.ok(branch, "loadTopology's problem branch was not found; the pattern is stale");
  assert.match(branch[1], /return false;\s*$/);
  assert.match(found[1].slice(branch.index + branch[0].length), /handlePlotData[\s\S]*return true;/);
});
