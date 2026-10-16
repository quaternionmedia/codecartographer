/**
 * With nodes selected, a right-click off the nodes opens the canvas ring, and
 * its Deselect clears the selection.
 *
 * The selection's own ring opened wherever the pointer was, so the canvas
 * ring, and its Deselect, could not be reached while anything was selected.
 */

import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

test('Deselect is reached from the canvas ring while nodes are selected', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  const node = page.locator('.graph-node[data-node-id]').first();
  await expect(node).toBeVisible({ timeout: 20_000 });

  // Select the node and its neighbours: Neighbours is the node ring's third wedge.
  await node.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
  await node.click({ button: 'right' });
  for (let i = 0; i < 3; i++) await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  await expect(page.locator('.rad-root')).toHaveCount(0);

  const svg = page.locator('.graphRenderer svg').first();
  const offTheNodes = { x: 8, y: 8 };
  // Mutation: let the selection's ring open off the nodes too -- the ring is
  // "N selected", not the canvas, and this fails.
  await svg.click({ button: 'right', position: offTheNodes });
  const ring = page.locator('.rad-root');
  await expect(ring).toHaveAttribute('aria-label', 'canvas');
  const deselect = ring.locator('[role="menuitem"][aria-label="Deselect"]');
  await expect(deselect).not.toHaveAttribute('aria-disabled', 'true');
  await expect(ring.locator('[role="menuitem"][aria-label="Color"]')).toHaveCount(0);

  // Deselect clears it: the next canvas ring offers it disabled. It is the
  // canvas ring's last wedge, and from no highlight ArrowLeft lands on it.
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('Enter');
  await expect(ring).toHaveCount(0);
  await svg.click({ button: 'right', position: offTheNodes });
  await expect(page.locator('.rad-root [role="menuitem"][aria-label="Deselect"]'))
    .toHaveAttribute('aria-disabled', 'true');
});
