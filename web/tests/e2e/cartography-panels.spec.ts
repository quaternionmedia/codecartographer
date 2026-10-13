/**
 * The Cargo and Chrestomathy panels, end to end.
 *
 * WHAT A BROWSER SEES THAT THE UNIT TESTS CANNOT. The readings behind these
 * panels are tested under pytest and the table's meaning under node. What only
 * a browser sees is whether a correct answer reached the screen and the one
 * canvas -- both panels ride the same state-then-redraw path the estate panels
 * once shipped stuck on.
 *
 * NOTHING IS STUBBED WHERE NOTHING NEEDS TO BE. The backend runs from the
 * repository root (playwright.config.ts), so the Cargo panel reads the real
 * fixture workspace through the real route and serializer. Which engine the
 * server reports depends on whether the checkout left the recorded metadata
 * newer than the manifests, so either answer is accepted -- each is labelled.
 *
 * Each draw is recorded as a screenshot in the test's own output directory
 * (`test-results/`), so what it looked like is kept beside the run that drew it.
 */

import type { Locator, Page } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 20_000;
const WORKSPACE = 'tests/fixtures/cargo/workspace';

async function openFromMenu(page: Page, label: RegExp, panelClass: string): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: label }).click();
  await page.locator(panelClass).waitFor({ state: 'visible' });
}

async function saysOnce(panel: Locator, caveat: string): Promise<void> {
  const sentence = (await panel.locator(caveat).innerText()).trim();
  await expect(panel.getByText(sentence, { exact: true })).toHaveCount(1);
}

async function record(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: test.info().outputPath(`${name}.png`), fullPage: true });
}

test.describe('the Cargo panel', () => {
  test('reads a workspace, says which engine and documents, and draws it', async ({ page }) => {
    await openFromMenu(page, /^Cargo$/, '.gl-panel--cargo');
    const panel = page.locator('.gl-panel--cargo');

    await panel.locator('.cartography__input').fill(WORKSPACE);
    await panel.locator('.estate-view__draw', { hasText: 'read' }).click();

    await expect(panel.locator('.estate__row[data-crate]')).toHaveCount(3, { timeout: SETTLED });
    await expect(panel.locator('.estate-view__heading', { hasText: /Read from (cargo metadata|manifests)/ }))
      .toBeVisible();
    await expect(panel.locator('.estate__row[data-crate="blinky"]')).toContainText('no_std');
    await expect(panel.locator('.estate__row[data-crate="host-tool"]')).toContainText('links crc');
    // The device target and its runner are shown, and said never to be run.
    await expect(panel).toContainText('thumbv7em-none-eabihf');
    await expect(panel).toContainText('shown, never run');

    await panel.locator('.estate-view__draw', { hasText: 'draw the workspace' }).click();
    await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });
    await expect(page.locator('.graph-node[data-node-id="crate::hal"]')).toHaveCount(1);
    await expect(page.locator('.graph-node[data-node-id="native::crc"]')).toHaveCount(1);
    // The caveat rides in from the metadata, above the controls -- and is
    // said there once, not again below by the reading that carries the same
    // sentence.
    await expect(panel.locator('.cargo__caveat')).not.toBeEmpty();
    await saysOnce(panel, '.cargo__caveat');
    await record(page, 'cargo-panel');
  });

  test('a directory that is not a workspace is a sentence with a way on', async ({ page }) => {
    await openFromMenu(page, /^Cargo$/, '.gl-panel--cargo');
    const panel = page.locator('.gl-panel--cargo');
    await panel.locator('.cartography__input').fill('docs');
    await panel.locator('.estate-view__draw', { hasText: 'read' }).click();
    const problem = panel.locator('.cargo__problem');
    await expect(problem).toBeVisible({ timeout: SETTLED });
    await expect(problem).toContainText('no Cargo.toml');
    await expect(problem).toContainText('cargo record');
  });
});

test.describe('the Chrestomathy panel', () => {
  test('sets one construct beside itself across languages, silent ones included', async ({ page }) => {
    await openFromMenu(page, /^Chrestomathy$/, '.gl-panel--chrestomathy');
    const panel = page.locator('.gl-panel--chrestomathy');

    // The default construct, a record, is spelled `struct` in C and Rust.
    await expect(panel.locator('tr[data-language="rust"]')).toContainText('struct', { timeout: SETTLED });
    await expect(panel.locator('tr[data-language="c"]')).toContainText('struct');

    // Rust has no keyword for a volatile access: the row says so rather than vanishing.
    await panel.locator('.cartography__select').selectOption('memory.volatile');
    const rust = panel.locator('tr[data-language="rust"]');
    await expect(rust).toHaveClass(/is-silent/, { timeout: SETTLED });
    await expect(rust).toContainText('read_volatile');
    await expect(panel.locator('tr[data-language="c"]')).toContainText('volatile');

    await panel.locator('.estate-view__draw', { hasText: 'draw the construct' }).click();
    await expect(page.locator('.graph-node[data-node-id="construct:memory.volatile"]'))
      .toHaveCount(1, { timeout: SETTLED });
    await expect(page.locator('.graph-node[data-node-id="token:c:volatile"]')).toHaveCount(1);

    await saysOnce(panel, '.chrestomathy__caveat');

    // Tokens carry their abstraction layer, and the key names it.
    await page.locator('.graph-legend__header').click();
    await expect(page.locator('.graph-legend__section', { hasText: 'Abstraction layers' })).toBeVisible();
    await record(page, 'chrestomathy-panel');
  });
});
