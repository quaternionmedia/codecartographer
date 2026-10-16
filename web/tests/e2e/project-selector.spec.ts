/**
 * The project selector offers Rust first, and its bundled example opens with
 * everything a recorded workspace shows -- offline.
 *
 * The GitHub examples are not clicked here: they need the network, and what
 * they draw is the same streaming path every repository takes. The bundled one
 * is read from this checkout, so it is clicked, and what it promises is
 * checked: a code map whose memory regions are measured, and a Cargo panel that
 * comes forward holding the workspace.
 */

import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;

test('the bundled Rust example leads, and opens with its records', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Repository' }).click();

  const rust = page.locator('.panel-source__example-chips[data-language="rust"]');
  await expect(rust.locator('button').first()).toHaveText('blinky (recorded)', { timeout: SETTLED });
  await expect(rust.locator('button')).toHaveCount(6);
  await rust.locator('[data-example="blinky (recorded)"]').click();

  // The code map, measured by the map rust-lld recorded.
  const flash = page.locator('.graph-node[data-node-id*="region::FLASH"]');
  await expect(flash).toHaveCount(1, { timeout: SETTLED });
  await expect(flash.locator('title')).toContainText('of 512.0 KiB used');
  await page.screenshot({ path: test.info().outputPath('bundled-example.png'), fullPage: true });

  // The Cargo panel comes forward holding the workspace: nothing to type,
  // nothing to read, nothing to open. A source that loads data for a panel
  // brings that panel forward.
  // Mutation: do not load the reading on click -- the panel opens empty and this fails.
  // Mutation: do not open the panel -- it is not on screen and this fails.
  const cargo = page.locator('.gl-panel--cargo');
  await expect(cargo.locator('.estate__row[data-crate="blinky"]')).toBeVisible({ timeout: SETTLED });
  await expect(cargo).toContainText('blinky.map');
  // ...and the code map the same click drew stays in view beside it.
  await expect(page.locator('.graph-node').first()).toBeVisible();
});
