/**
 * The four steps from opening source to reading its graph.
 *
 * The header's rail numbers them -- 1 Open, 2 Browse, 3 Tune, 4 Read -- fills
 * the one the reader is on and says what comes next, and the walkthrough card
 * is a page per step. Entering a step brings its windows forward and leaves
 * the canvas in view; step 4 maximises the canvas and hides every other
 * window. A window the reader chooses says which step they are on; a window
 * that comes forward by itself does not. `web/src/layout/steps.ts` decides
 * what each step owns and brings forward, and `tests/pure/steps.test.mjs`
 * asserts it without a browser; this sees it in one.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;

test.use({ viewport: { width: 1600, height: 1000 } });

const rail = (page: Page) => page.locator('nav.gl-steps');
const step = (page: Page, label: string) => rail(page).locator('.gl-steps__step', { hasText: label });
const current = (page: Page) => rail(page).locator('[aria-current="step"]');
const next = (page: Page) => rail(page).locator('.gl-steps__next');
const card = (page: Page) => page.locator('.cc-modal');

/**
 * The windows a reader can see, each by its panel's class (`open`,
 * `file-tree`, `controls-graph-settings`, ...): a window counts when a pointer
 * at its centre reaches it.
 *
 * **NOT `toBeVisible`.** Golden Layout maximises a stack by laying it over the
 * others, which keep their size and their place underneath, so a window step 4
 * hid is still visible to Playwright. Hit-testing is what a reader's eye does.
 */
async function windowsInView(page: Page): Promise<string[]> {
  return page.locator('.gl-panel').evaluateAll((panels) =>
    panels.flatMap((el) => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return [];
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      if (!hit || !el.contains(hit)) return [];
      const name = [...el.classList].filter((c) => c.startsWith('gl-panel--') && c !== 'gl-panel--controls').pop();
      return name ? [name.slice('gl-panel--'.length)] : [];
    }).sort());
}

/** The title of the tab in front of each stack, under the card where one is open. */
async function frontTabs(page: Page): Promise<string[]> {
  return page.locator('.lm_tab.lm_active').allTextContents();
}

test('a first visit opens on step 1, and the walkthrough turns the steps with the rail', async ({ page }) => {
  await page.goto('/');
  await expect(card(page)).toHaveAttribute('data-step', 'open');
  await expect(card(page)).toContainText('Step 1 of 4 · Open');
  await expect(current(page)).toHaveText('1Open');

  // Mutation: let the card keep a page of its own again -- the rail stays
  // on Open as the card turns, and this fails.
  await card(page).getByRole('button', { name: 'Next: Browse →' }).click();
  await expect(card(page)).toHaveAttribute('data-step', 'browse');
  await expect(current(page)).toHaveText('2Browse');

  // The card's Next enters the step: its window comes forward behind it.
  await card(page).getByRole('button', { name: 'Next: Tune →' }).click();
  await expect(current(page)).toHaveText('3Tune');
  await expect.poll(() => frontTabs(page)).toContain('Graph Settings');

  await card(page).getByRole('button', { name: 'Next: Read →' }).click();
  await expect(card(page)).toHaveAttribute('data-step', 'read');
  await expect(page.locator('.lm_maximised .gl-panel--graph')).toHaveCount(1);
  await expect(card(page).getByRole('button', { name: /^Next/ })).toHaveCount(0);
  await expect(card(page).getByRole('button', { name: 'Got it!' })).toBeVisible();

  await card(page).getByRole('button', { name: '← Back' }).click();
  await expect(current(page)).toHaveText('3Tune');
  await expect(page.locator('.lm_maximised')).toHaveCount(0);

  // A dot is a step too.
  await card(page).locator('.cc-modal__dot').first().click();
  await expect(current(page)).toHaveText('1Open');
  await expect.poll(() => frontTabs(page)).toContain('⬇ Open');

  // Closed, it leaves the reader on the step it showed; ? opens it on the step they are on.
  await dismissOnboardingModal(page);
  await step(page, 'Tune').click();
  await page.locator('.gl-app-header__help-btn').click();
  await expect(card(page)).toHaveAttribute('data-step', 'tune');
  await expect(card(page)).toContainText('Step 3 of 4 · Tune');
});

test('each step brings its windows forward, says what comes next, and Read hides the rest', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await expect(current(page)).toHaveText('1Open');
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
  await expect(next(page)).toHaveText('Next 2 Browse →');

  await step(page, 'Tune').click();
  await expect(current(page)).toHaveText('3Tune');
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);
  await expect(next(page)).toHaveText('Next 4 Read →');

  // Mutation: set Read's `alone` to false in steps.ts -- Files and Graph
  // Settings stay in view, and this fails.
  await step(page, 'Read').click();
  await expect(current(page)).toHaveText('4Read');
  await expect.poll(() => windowsInView(page)).toEqual(['graph']);
  await expect(next(page)).toHaveCount(0);
  // With the Open panel hidden, the empty canvas names the step that has it.
  await expect(page.locator('.plot__empty-text')).toContainText('Step 1, Open, is where one starts');

  // Mutation: drop `dock.restore()` from steps.enterStep -- the canvas stays
  // over everything, and this fails.
  await step(page, 'Browse').click();
  await expect(current(page)).toHaveText('2Browse');
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);

  await next(page).click();
  await expect(current(page)).toHaveText('3Tune');
  await step(page, 'Open').click();
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
});

test('Read fills the dock with the canvas when a focus has scrolled it', async ({ page }) => {
  /**
   * The dock's host clips and does not scroll, but a focus or a
   * scrollIntoView inside it scrolls it anyway -- Playwright's own click on
   * Load Demo did, by 8 pixels -- and Golden Layout pins a maximised stack to
   * the top of the host's content. Chrome's scroll anchoring then moved the
   * host by another 336 to keep the focused button in place, and step 4 drew
   * the canvas 344 pixels up, with Files and Open showing under it.
   * Mutation: drop the scroll reset from the step dock's `maximise` -- this
   * fails.
   */
  await page.goto('/');
  await dismissOnboardingModal(page);
  const body = page.locator('.gl-shell__body');
  await body.evaluate((el) => { el.scrollTop = 8; });
  await page.getByRole('button', { name: /Load Demo/i }).first().focus();

  await step(page, 'Read').click();
  await expect(page.locator('.lm_maximised')).toHaveCount(1);
  const [dock, canvas] = await Promise.all([body.boundingBox(), page.locator('.lm_maximised').boundingBox()]);
  expect(canvas, 'the maximised canvas').not.toBeNull();
  expect(Math.round(canvas!.y - dock!.y), 'how far the canvas starts from the top of the dock').toBe(0);
  expect(Math.round(canvas!.height - dock!.height), 'how much of the dock the canvas leaves').toBe(0);
  await expect.poll(() => windowsInView(page)).toEqual(['graph']);
});

test("a step opens its window again when it was closed, and a stack maximised by Golden Layout's own control gives way", async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);

  const settings = page.locator('.lm_tab', { hasText: 'Graph Settings' });
  await settings.locator('.lm_close_tab').click();
  await expect(settings).toHaveCount(0);
  await step(page, 'Tune').click();
  await expect(settings).toHaveCount(1);
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);

  // The step already on is a button too: Estate put in front, Tune again.
  await page.locator('.lm_tab', { hasText: 'Estate' }).click();
  await expect.poll(() => windowsInView(page)).toContain('estate');
  await step(page, 'Tune').click();
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);

  const files = page.locator('.lm_stack', { has: page.locator('.lm_tab', { hasText: 'Files' }) });
  await files.locator('.lm_maximise').click();
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree']);
  await step(page, 'Open').click();
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
});

test('choosing a tab says which step the reader is on, and moves no other window', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);

  // Mutation: stop `noteClick` following the tab's window -- the rail stays
  // on Open, and this fails.
  await page.locator('.lm_tab', { hasText: 'Graph Settings' }).click();
  await expect(current(page)).toHaveText('3Tune');
  await page.locator('.lm_tab', { hasText: 'Files' }).click();
  await expect(current(page)).toHaveText('2Browse');
  await page.locator('.lm_tab', { hasText: 'Estate' }).click();
  await expect(current(page)).toHaveText('1Open');

  // The canvas's tab says Read, and maximises nothing: only the rail's step does.
  await page.locator('.lm_tab', { hasText: '◈ Graph' }).click();
  await expect(current(page)).toHaveText('4Read');
  await expect(page.locator('.lm_maximised')).toHaveCount(0);
  await expect.poll(() => windowsInView(page)).toEqual(['estate', 'file-tree', 'graph']);

  // Closing a window chooses nothing.
  await page.locator('.lm_tab', { hasText: 'Estate' }).locator('.lm_close_tab').click();
  await expect(page.locator('.lm_tab', { hasText: 'Estate' })).toHaveCount(0);
  await expect(current(page)).toHaveText('4Read');
});

test('a draw leaves the step where it is, and a window chosen over the canvas comes into view', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);

  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  const node = page.locator('.graph-node[data-node-id]').first();
  await expect(node).toBeVisible({ timeout: SETTLED });
  await expect(current(page)).toHaveText('1Open');

  await step(page, 'Read').click();
  await expect.poll(() => windowsInView(page)).toEqual(['graph']);
  await expect(node).toBeVisible();

  // A window added from + comes into view over step 4's canvas -- Golden
  // Layout restores a maximised stack before it adds an item -- and the rail
  // follows it. Mutation: have the + menu call `openPanel` rather than
  // `chooseWindow` -- the rail stays on Read, and this fails.
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Cargo$/ }).click();
  await expect.poll(() => windowsInView(page)).toContain('cargo');
  await expect(page.locator('.lm_maximised')).toHaveCount(0);
  await expect(current(page)).toHaveText('1Open');

  // A reset puts the dock back as a page opens it, on step 1.
  await step(page, 'Read').click();
  await expect(page.locator('.lm_maximised')).toHaveCount(1);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: 'Reset to built-in default' }).click();
  await expect(current(page)).toHaveText('1Open');
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
});

test("a draw brings the canvas into view over a stack maximised with Golden Layout's own control", async ({ page }) => {
  /**
   * The Overview panel brings the canvas forward when it has drawn
   * (`focusDockPanel('graph')`). With the panel's own stack maximised, the
   * canvas was brought to the front of a stack nobody could see, and the
   * drawing stayed out of sight behind the panel that asked for it.
   * Mutation: drop `this._restoreAllBut(stack)` from focusDockPanel -- this
   * fails. The backend serves `fixtures/overview.json` (playwright.config.ts).
   */
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Overview$/ }).click();
  const panel = page.locator('.gl-panel--overview');
  await panel.locator('.estate-view__draw').waitFor({ timeout: SETTLED });

  const overview = page.locator('.lm_stack', { has: page.locator('.lm_tab', { hasText: 'Overview' }) });
  await overview.locator('.lm_maximise').click();
  await expect.poll(() => windowsInView(page)).toEqual(['overview']);

  await panel.locator('.estate-view__draw').click();
  await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });
  await expect(page.locator('.lm_maximised')).toHaveCount(0);
  await expect.poll(() => windowsInView(page)).toContain('graph');
});
