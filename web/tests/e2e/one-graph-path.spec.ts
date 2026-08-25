import { test, expect } from '@playwright/test';
import { dismissOnboardingModal } from './helpers';

/**
 * One D3 canvas, and everything mounted on it.
 *
 * **THIS IS THE OBSERVABLE HALF OF ADR §7.** Before the merge this application
 * had two D3 renderers. Load Demo went through `handlePlotData` and the renderer
 * registry into `graph_renderer.ts`; a repository plot streamed into
 * `StreamingGraphRenderer`. The radial menu and the legend attached only to the
 * second, so the path most readers reach first had a bespoke menu and no key.
 *
 * Nothing in a typecheck or a unit suite can see that. What can see it is
 * opening the demo and asking whether the fittings are there — which is what
 * this does. The registry path now builds a streaming renderer and announces it
 * through `GraphSurface`, so the demo gets the same menu and key a repository
 * plot gets.
 */

/**
 * The number of nodes on the canvas, once it has stopped changing.
 *
 * **THE CANVAS CONVERGES ON THE GRAPH; IT DOES NOT START THERE.** The streaming
 * renderer draws a few nodes per animation frame, so a count taken when the
 * first node appears is a count of the frame, not of the graph. Sampling until
 * two consecutive reads agree is what makes "the key matches the canvas" a
 * question about the key rather than about timing — an assertion taken early
 * fails against a legend that is entirely correct.
 */
async function settledNodeCount(page: import('@playwright/test').Page): Promise<number> {
  let last = -1;
  for (let attempt = 0; attempt < 40; attempt++) {
    const now = await page.locator('.graph-node').count();
    if (now > 0 && now === last) return now;
    last = now;
    await page.waitForTimeout(250);
  }
  return last;
}

test.describe('the demo renders on the one canvas', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await dismissOnboardingModal(page);
    await page.getByRole('button', { name: /Load Demo/i }).first().click();
    await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: 20_000 });
  });

  test('the legend is mounted and counts what was drawn', async ({ page }) => {
    const legend = page.locator('.graph-legend');
    await expect(legend).toBeVisible();

    // The header states the totals. They must match the canvas once it has
    // settled, because the key reads the scene rather than describing an
    // expected one.
    const drawn = await settledNodeCount(page);
    expect(drawn).toBeGreaterThan(0);
    await expect(legend.locator('.graph-legend__header'))
      .toContainText(new RegExp(`^${drawn} nodes`));

    // Mutation: stop publishing through GraphSurface in d3_renderer.render and
    // this fails — the graph still draws, with nothing attached to it.
  });

  test('the legend opens and its rows account for every node', async ({ page }) => {
    await page.locator('.graph-legend__header').click();

    const body = page.locator('.graph-legend__body');
    await expect(body).toBeVisible();

    const counts = await page
      .locator('.graph-legend__section')
      .filter({ has: page.getByRole('heading', { name: 'Nodes' }) })
      .locator('.graph-legend__count')
      .allTextContents();

    const total = counts.reduce((sum, n) => sum + Number(n), 0);
    expect(total).toBe(await settledNodeCount(page));
  });

  test('rad is mounted, so a node carries the id its menu resolves against', async ({ page }) => {
    /**
     * `RadExtension` finds the node under the pointer by walking up to the
     * nearest `[data-node-id]`. The attribute is set by the streaming renderer
     * alone — the registry's old renderer never emitted it — so its presence
     * on a demo node is what says the demo is on the streaming canvas.
     *
     * Mutation: point D3GraphRenderer back at a non-streaming renderer and
     * this fails.
     */
    const first = page.locator('.graph-node').first();
    await expect(first).toHaveAttribute('data-node-id', /.+/);
  });

  test('the retired radial menu leaves nothing behind', async ({ page }) => {
    // The legacy ring rendered into `.radial-menu`. Nothing should build one.
    await expect(page.locator('.radial-menu')).toHaveCount(0);
  });
});
