/**
 * View ▸ Source and a double-click open a node's source through one opener.
 *
 * A node from a GitHub repository opens its file's page at the node's line;
 * a node read from this checkout has no page to open, so a badge names the
 * file and line beside it. Both routes call the same opener and are offered on
 * the same rule: the node names a file. The fixture workspace is read from
 * disk, so what is seen here is the badge.
 */

import type { Page } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;
const WORKSPACE = 'tests/fixtures/cargo/workspace';

async function drawWorkspace(page: Page): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Repository' }).click();
  await page.locator('.panel-source__url-input input').fill(WORKSPACE);
  await page.locator('.panel-source__url-input button.primary').click();
  await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });
  await expect(page.locator('.panel-source__url-input button.primary')).toHaveText(/Fetch/, { timeout: SETTLED });
}

test('a double-click and View ▸ Source name the same file and line', async ({ page }) => {
  await drawWorkspace(page);
  const badge = page.locator('.source-badge');

  // `delay` in the blinky crate, at main.rs line 21.
  const delay = page.locator('.graph-node[data-node-id*="function::delay"]').first();
  await delay.dblclick();
  await expect(badge).toHaveText(/^delay\s+.*main\.rs:21$/);
  const fromDoubleClick = await badge.textContent();
  // The badge leaves after a few seconds; the next one is the menu's.
  await expect(badge).toHaveCount(0, { timeout: 10_000 });

  await delay.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
  await delay.click({ button: 'right' });
  // View is the sixth wedge; Source is the first in its ring.
  for (let i = 0; i < 6; i++) await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');

  // Mutation: route View ▸ Source to the toast it showed -- no badge, and this fails.
  await expect(badge).toHaveText(fromDoubleClick ?? '');
  await expect(badge).toHaveCount(1);
});

test('a file opens from a double-click at the top, as a symbol opens at its line', async ({ page }) => {
  await drawWorkspace(page);
  const file = page.locator('.graph-node[data-node-id^="file::"][data-node-id$="blinky/src/main.rs"]').first();
  // Mutation: open only symbols with a line, as the double-click did -- a
  // file node shows nothing, and this fails.
  // Dispatched to the node: a pointer aimed at its centre once waited out the
  // test's time for the node to receive it, and the node's own handler is
  // what is under test here.
  await expect(file).toBeVisible();
  await file.dispatchEvent('dblclick');
  await expect(page.locator('.source-badge')).toHaveText(/^main\.rs\s+.*main\.rs$/);
});
