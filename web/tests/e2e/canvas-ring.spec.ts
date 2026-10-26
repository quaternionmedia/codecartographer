/**
 * With nodes selected, a right-click off the nodes opens the canvas ring, and
 * its Deselect clears the selection.
 *
 * The selection's own ring opened wherever the pointer was, so the canvas
 * ring, and its Deselect, could not be reached while anything was selected.
 */

import { expect, test } from '@playwright/test';

import { dismissOnboardingModal, pointOn } from './helpers';

test("a greyed item's label is dimmed with its wedge", async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  await expect(page.locator('.graph-node[data-node-id]').first()).toBeVisible({ timeout: 20_000 });

  // With nothing selected or hidden, the canvas ring offers items greyed.
  await page.locator('.graphRenderer svg').first().click({ button: 'right', position: { x: 8, y: 8 } });
  const ring = page.locator('.rad-root');
  await expect(ring).toHaveAttribute('aria-label', 'canvas');

  // A wedge's label is the text drawn right after it.
  const drawn = await ring.locator('[role="menuitem"]').evaluateAll((wedges) =>
    wedges.map((wedge) => ({
      label: wedge.getAttribute('aria-label'),
      disabled: wedge.getAttribute('aria-disabled') === 'true',
      wedge: Number(getComputedStyle(wedge).opacity),
      text: Number(getComputedStyle(wedge.nextElementSibling as Element).opacity),
    })),
  );
  expect(drawn.filter((d) => d.disabled).length).toBeGreaterThan(0);
  for (const d of drawn) {
    // Mutation: draw every label at full opacity again -- a greyed item's
    // label reads as enabled, and this fails.
    expect(d.text, `${d.label}'s label`).toBe(d.wedge);
    expect(d.wedge < 1, `${d.label} is drawn greyed`).toBe(d.disabled);
  }
});

test('Deselect is reached from the canvas ring while nodes are selected', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  const node = page.locator('.graph-node[data-node-id]').first();
  await expect(node).toBeVisible({ timeout: 20_000 });

  // Select the node and its neighbors: Neighbors is the node ring's third wedge.
  // Pressed where a pointer reaches the node: its centre can be under another
  // node, and Playwright's click waits for the centre to come clear.
  await node.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
  const at = await pointOn(node);
  await page.mouse.click(at.x, at.y, { button: 'right' });
  await expect(page.locator('.rad-root')).toHaveAttribute('aria-label', 'node');
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
