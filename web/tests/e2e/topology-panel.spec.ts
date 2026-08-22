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
  await openTopologyPanel(page);

  const problem = page.locator('.topology__problem');
  if (!(await problem.count())) {
    test.skip(true, 'the harness answered, so there is no problem state to check');
  }

  // A harness is usually started *after* somebody finds this down. Without a
  // retry they would have to know to close and reopen the panel.
  await expect(problem.locator('.topology__retry')).toBeVisible();
  await expect(problem).toContainText(/tried/);
});
