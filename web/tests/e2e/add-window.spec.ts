/**
 * One way to add a window: the header's "+" menu.
 *
 * The menu lists every registered window that is not open, closed ones
 * included, so neither a Restore strip in the header nor a second menu on a
 * Ctrl+right-click is needed to bring one back. A window opened from the menu,
 * or from a panel that loads data for it, lands in the dock and leaves the
 * canvas in view.
 */

import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

test('a closed window comes back from the + menu, and the header offers no other way', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);

  const estate = page.locator('.lm_tab', { hasText: 'Estate' });
  await estate.locator('.lm_close_tab').click();
  await expect(estate).toHaveCount(0);

  // Mutation: draw a Restore button per closed window again -- this fails.
  await expect(page.locator('.gl-app-header button', { hasText: /Restore/ })).toHaveCount(0);

  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Estate$/ }).click();
  await expect(estate).toBeVisible();
});

test('a Ctrl+right-click on the dock opens no menu', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);

  // Mutation: open the add-window menu on a Ctrl+right-click again -- this fails.
  await page.locator('.gl-panel--file-tree').click({ button: 'right', modifiers: ['Control'] });
  await expect(page.locator('.gl-add-panel-menu')).toHaveCount(0);
});

test('a window added from the + menu leaves the canvas in view', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  const node = page.locator('.graph-node[data-node-id]').first();
  await expect(node).toBeVisible({ timeout: 20_000 });

  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Cargo$/ }).click();
  await expect(page.locator('.gl-panel--cargo')).toBeVisible();
  // Mutation: place it with Golden Layout's default selectors -- with no tab
  // focused that is the Graph panel's own stack, the canvas goes behind the
  // new tab, and this fails.
  await expect(node).toBeVisible();
  // It joins the dock's tabs, not the narrow Files column.
  // Mutation: take the first stack that is not the canvas's -- that is the
  // Files column, and this fails.
  const stack = page.locator('.lm_stack', { has: page.locator('.lm_tab', { hasText: 'Cargo' }) });
  await expect(stack.locator('.lm_tab', { hasText: 'Graph Settings' })).toHaveCount(1);
});
