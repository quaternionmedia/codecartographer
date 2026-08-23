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

/**
 * Clear anything covering the app.
 *
 * `.cc-modal-backdrop` intercepts pointer events, and it can appear *during* a
 * run rather than only at first load — a click that "times out on a visible,
 * enabled, stable element" is this, and it reads like the element is broken.
 */
async function clearOverlays(page: Page): Promise<void> {
  const backdrop = page.locator('.cc-modal-backdrop');
  if ((await backdrop.count()) === 0) return;
  await page.keyboard.press('Escape');
  if ((await backdrop.count()) > 0) {
    await backdrop.locator('button', { hasText: '×' }).first()
      .click({ force: true }).catch(() => undefined);
  }
}

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
