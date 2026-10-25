/**
 * Any graph on the canvas can be read as a chrestomathy, end to end.
 *
 * WHAT ONLY A BROWSER SEES. The census, the stamping and the menu's routing are
 * tested without one. What only a browser sees is the loop they make: a graph
 * a parse or a panel drew reaches the Chrestomathy panel as the constructs it
 * holds, a row there points back at the nodes on the canvas, the canvas can be
 * coloured by what each node is, and a node's own menu opens the chrestomathy
 * at what that node is.
 *
 * NOTHING IS STUBBED. The backend runs from the repository root
 * (playwright.config.ts), so the fixture workspace is parsed and read through
 * the real routes.
 */

import type { Page } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;
const WORKSPACE = 'tests/fixtures/cargo/workspace';

async function drawCodeMap(page: Page): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.panel-open__parse-toggle').click();
  await page.locator('button', { hasText: /^deep$/i }).first().click();
  await page.locator('.panel-source__url-input input').fill(WORKSPACE);
  await page.locator('.panel-source__url-input button.primary').click();
  await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });
  await expect(page.locator('.panel-source__url-input button.primary')).toHaveText(/Fetch/, { timeout: SETTLED });
}

async function addPanel(page: Page, label: RegExp, panelClass: string): Promise<void> {
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: label }).click();
  await page.locator(panelClass).waitFor({ state: 'visible' });
}

async function record(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: test.info().outputPath(`${name}.png`), fullPage: true });
}

test('a code map is read as the constructs it holds, and points back at them', async ({ page }) => {
  await drawCodeMap(page);
  await addPanel(page, /^Chrestomathy$/, '.gl-panel--chrestomathy');
  const canvas = page.locator('.chrestomathy__canvas');

  const functions = canvas.locator('tr[data-construct="callable.function"]');
  await expect(functions).toContainText('Rust', { timeout: SETTLED });
  await expect(canvas.locator('tr[data-construct="type.product"]')).toHaveCount(1);
  // What the vocabulary could not place is said, not dropped.
  await expect(canvas.locator('.chrestomathy__gap').first()).toBeVisible();

  // A row is a way into the comparison...
  await functions.locator('.cartography__link').click();
  await expect(page.locator('.gl-panel--chrestomathy tr[data-language="rust"]')).toContainText('fn');
  await expect(functions).toHaveClass(/is-chosen/);
  await record(page, 'census');

  // ...and back onto the graph.
  await functions.locator('.cartography__show').click();
  await page.locator('.lm_tab', { hasText: 'Chrestomathy' }).click();
  await expect(canvas.locator('.chrestomathy__shown')).toHaveText(/^[1-9]\d* Function node\(s\) framed and selected$/);
});

test('the crate graph is coloured by what each node is', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await addPanel(page, /^Cargo$/, '.gl-panel--cargo');
  const panel = page.locator('.gl-panel--cargo');
  await panel.locator('.cartography__input').fill(WORKSPACE);
  await panel.locator('.estate-view__draw', { hasText: 'read' }).click();
  await panel.locator('.estate__row[data-crate]').first().waitFor({ timeout: SETTLED });
  await panel.locator('.estate-view__draw', { hasText: 'draw the workspace' }).click();
  const hal = page.locator('.graph-node[data-node-id="crate::hal"] path').first();
  await expect(hal).toBeVisible({ timeout: SETTLED });
  const own = await hal.getAttribute('fill');

  await page.locator('.lm_tab', { hasText: 'Graph Settings' }).click();
  await page.getByText('Visual', { exact: true }).click();
  await page.locator('select.panel-settings__select', { has: page.locator('option[value="construct"]') })
    .selectOption('construct');
  // A crate is a package, the colour every package is in every language.
  // Mutation: drop the construct branch from `paintedColor`, which the
  // renderer and the key share -- the fill stays the crate graph's own and
  // this fails.
  await expect(hal).toHaveAttribute('fill', '#6d28d9');
  expect(own).not.toBe('#6d28d9');

  await page.locator('.graph-legend__header').click();
  await expect(page.locator('.graph-legend__row[data-construct="namespace.package"]')).toBeVisible();
  await record(page, 'construct-colours');
});

test("a node's menu opens the chrestomathy at what that node is", async ({ page }) => {
  await drawCodeMap(page);
  // The `delay` function in the fixture's blinky crate.
  const node = page.locator('.graph-node[data-node-id*="function::delay"]').first();
  await expect(node).toBeVisible({ timeout: SETTLED });
  // The ring listens for keys on the canvas; focus it, as a keyboard user
  // who tabbed there would have, so the keys below cannot land elsewhere.
  await node.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
  await node.click({ button: 'right' });

  // The ring has eight wedges and View is the sixth; its children are
  // Source, Info, Compare, Focus. From no highlight, ArrowRight lands on 0.
  for (let i = 0; i < 6; i++) await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  for (let i = 0; i < 3; i++) await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');

  // Mutation: route `compare` to nothing -- the panel never opens and this fails.
  const panel = page.locator('.gl-panel--chrestomathy');
  await expect(panel).toBeVisible({ timeout: SETTLED });
  await expect(panel.locator('select.cartography__select')).toHaveValue('callable.function');
  await expect(panel.locator('tr[data-language="rust"]')).toContainText('fn');
});
