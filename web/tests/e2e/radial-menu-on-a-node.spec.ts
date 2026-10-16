/**
 * A right-click on a node opens the radial menu for that node.
 *
 * WHY THIS IS A BROWSER TEST. rad's routing and rings are tested without a
 * browser, and all of it passed while no node could open its ring by mouse:
 * the renderer's own right-click handler on every node stopped the event
 * before rad, which listens on the canvas, could hear it. Only a real click on
 * a real node shows whether the ring opens.
 */

import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

test('a right-click on a node opens its ring, and Escape closes it', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  const node = page.locator('.graph-node[data-node-id]').first();
  await expect(node).toBeVisible({ timeout: 20_000 });

  await expect(page.locator('.rad-root')).toHaveCount(0);
  // Mutation: stop the right-click on the node again -- no ring, and this fails.
  await node.click({ button: 'right' });
  await expect(page.locator('.rad-root')).toHaveCount(1);

  await page.keyboard.press('Escape');
  await expect(page.locator('.rad-root')).toHaveCount(0);
});
