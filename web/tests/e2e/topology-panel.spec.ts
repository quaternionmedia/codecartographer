/**
 * The Topology panel, end to end.
 *
 * **THIS EXISTS BECAUSE THE PANEL SHIPPED STUCK.** It opened, printed
 * "asking the harness…", and stayed there — the request had already answered
 * and nothing repainted, because `StateController.update` changes state without
 * redrawing and an `oninit` that awaits resolves outside any DOM event handler,
 * which is what Mithril repaints after.
 *
 * No unit test would have caught it: every function involved was correct. Only
 * a browser can tell you that a correct answer never reached the screen.
 *
 * THE HARNESS IS NOT ASSUMED TO BE RUNNING. `qmcp` is a separate project and
 * the e2e run does not start it, so the panel is expected to resolve to *either*
 * a list of flows or a stated problem. Both are answers; "asking…" is not.
 */

import type { Page } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

/** Long enough for a request that fails to fail. The panel's own client gives
 *  up well before this, so a timeout here means nothing repainted. */
const SETTLED = 20_000;

async function openTopologyPanel(page: Page): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);

  // **BY THE REAL SELECTORS, NOT A GUESS AT THEM.** The first version of this
  // looked for a button whose accessible name matched /add|window|panel/i. The
  // button's text is `+`, so it matched nothing, the panel never opened, and
  // both tests *skipped* — reporting green while asserting nothing, which is
  // the failure this whole exercise keeps finding.
  await page.locator('.gl-app-header__add-btn').click();
  await page
    .locator('.gl-add-panel-menu__item', { hasText: /^Topology$/ })
    .click();
  await page.locator('.gl-panel--topology').waitFor({ state: 'visible' });
}

test('the topology panel resolves rather than sitting on "asking"', async ({ page }) => {
  await openTopologyPanel(page);

  const panel = page.locator('.gl-panel--topology');
  // Not a skip. `openTopologyPanel` waits for this, so an absent panel here
  // means the panel could not be opened at all, which is a failure.
  await expect(panel).toBeVisible();

  // THE ASSERTION THAT MATTERS. Either outcome is fine; being stuck is not.
  await expect
    .poll(async () => {
      const settled = await panel.locator('.topology__chip, .topology__problem').count();
      return settled;
    }, { timeout: SETTLED })
    .toBeGreaterThan(0);

  await expect(panel.locator('.topology__pending')).toHaveCount(0);
});

test('a harness that is not answering offers a way to try again', async ({ page }) => {
  /**
   * **STUBBED, NOT SKIPPED.** The first version of this checked for a problem
   * state and skipped when the harness happened to be up — so on a healthy
   * machine it asserted nothing, and on a busy one it flaked. A test that only
   * runs when something is already broken is not a test of the broken case.
   *
   * The harness is a separate process this suite does not start, so its being
   * down is stubbed here: the route answers exactly as the server does when it
   * cannot reach the harness.
   */
  await page.route('**/topology/available*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 200,
        message: 'Success',
        results: {
          unreachable: true,
          problem: 'nothing is answering at http://127.0.0.1:3141',
          remedy: 'start it with `uv run qm dashboard --start harness`',
          where: 'http://127.0.0.1:3141/v1/topology',
          topologies: [],
          layouts: ['Spring'],
        },
      }),
    }),
  );

  await openTopologyPanel(page);

  const problem = page.locator('.topology__problem');
  await expect(problem).toBeVisible();
  await expect(problem).toContainText('nothing is answering');
  await expect(problem).toContainText('qm dashboard --start harness');
  await expect(problem).toContainText('tried');

  // A harness is usually started *after* somebody finds this down. Without a
  // retry they would have to know to close and reopen the panel.
  await expect(problem.locator('.topology__retry')).toBeVisible();

  // And the pending state must be gone — "asking…" that never resolves is the
  // bug this whole file exists for.
  await expect(page.locator('.topology__pending')).toHaveCount(0);
});

test('an unmeasured edge is drawn dashed, never thin', async ({ page }) => {
  /**
   * **THE CHANNELS WERE SERVED AND NOT DRAWN.** The topology service puts
   * `style`, `size` and `color` on every edge and the serializer carries them
   * under `edge.metadata`; the canvas read `edge.color` at the top level, which
   * is never there, so every edge was one solid grey line at one width while
   * the caveat above the panel said "drawn dashed". Found in a live demo, not
   * by a test -- which is why this test exists.
   *
   * Stubbed at the two routes so it runs without a harness.
   */
  const envelope = (results: unknown) => ({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ status: 200, message: 'Success', results }),
  });
  await page.route('**/topology/available*', (route) =>
    route.fulfill(envelope({
      topologies: [{ topology: 'pair', caption: 'two boxes', status: 'runs', boxes: 2, arrows: 2 }],
      layouts: ['Spring'],
      encoding: [],
    })),
  );
  await page.route('**/topology/gjgf*', (route) =>
    route.fulfill(envelope({
      graph: {
        directed: true,
        nodes: {
          a: { label: 'a', kind: 'input', type: 'Input', x: 0, y: 0, color: '#6db2ff', size: 20 },
          b: { label: 'b', kind: 'worker', type: 'Worker', x: 200, y: 0, color: '#6db2ff', size: 20 },
        },
        edges: [
          { source: 'a', target: 'b', label: 'measured', metadata: { style: 'solid', size: 4.1, measured: true, color: '#5ac8b0' } },
          { source: 'b', target: 'a', label: 'unmeasured', metadata: { style: 'dashed', size: 1.6, measured: false, color: '#e06c75' } },
        ],
      },
      metadata: {
        kind: 'topology', layout: 'Spring', type: 'd3', nodeCount: 2, edgeCount: 2, palette_id: '0',
        topology: 'pair', measured: 1, unmeasured: 1, source: 'topology',
        caveat: '1 of 2 edge(s) measured; the rest are drawn dashed because nobody looked',
      },
    })),
  );

  await openTopologyPanel(page);
  await page.locator('.topology__chip', { hasText: /^pair$/ }).click();
  await expect(page.locator('.stream-edge')).toHaveCount(2, { timeout: SETTLED });

  const dashed = page.locator('.stream-edge[data-style="dashed"]');
  const solid = page.locator('.stream-edge[data-style="solid"]');
  await expect(dashed).toHaveCount(1);
  await expect(solid).toHaveCount(1);
  await expect(dashed).toHaveAttribute('stroke-dasharray', /\d/);
  expect(await solid.getAttribute('stroke-dasharray')).toBeNull();
  // Width is the strength channel; the unmeasured edge is off that scale and not the thinnest thing on the canvas.
  expect(Number(await solid.getAttribute('stroke-width'))).toBeCloseTo(4.1, 1);
  expect(Number(await dashed.getAttribute('stroke-width'))).toBeCloseTo(1.6, 1);
  // Colour is the relation kind, from the metadata, not the fallback grey.
  await expect(dashed).toHaveAttribute('stroke', '#e06c75');
  // And the caveat rides in above the controls.
  await expect(page.locator('.topology__caveat')).toContainText('drawn dashed');
});
