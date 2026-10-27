/**
 * The Graph window's ⧉: a copy of the graph in a window of its own, a tab that
 * moves and zooms apart from the canvas (`graph_copy_panel.ts`).
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;

async function loadDemo(page: Page): Promise<number> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  const main = page.locator('.gl-panel--graph:not(.gl-panel--graph-copy)');
  await expect(main.locator('.graph-legend__header')).toContainText(/\d+ nodes/, { timeout: SETTLED });
  return Number((await main.locator('.graph-legend__header').textContent())?.match(/(\d+) nodes/)?.[1]);
}

const transformOf = (page: Page, panel: string) => page.locator(`${panel} .graphRenderer > svg > g`).first()
  .getAttribute('transform');

/** Wait until a canvas's transform reads the same twice, half a second apart. */
async function settled(page: Page, panel: string): Promise<void> {
  let last: string | null = '';
  await expect.poll(async () => {
    const now = await transformOf(page, panel);
    const still = now === last;
    last = now;
    return still;
  }, { intervals: [500], timeout: SETTLED }).toBe(true);
}

test('the ⧉ button opens a copy of the graph in a tab of its own, which zooms apart from the canvas', async ({ page }) => {
  const count = await loadDemo(page);
  await page.getByRole('button', { name: 'Duplicate the graph into a window of its own' }).click();

  await expect(page.locator('.lm_tab', { hasText: '◈ Graph 2' })).toHaveCount(1);
  const copy = page.locator('.gl-panel--graph-copy');
  await expect(copy.locator('g.graph-node')).toHaveCount(count, { timeout: SETTLED });
  // Its own key, and the canvas keeps its own and its ring. Mutation: announce
  // the copy as the canvas -- the canvas's key goes to the copy, and this fails.
  await expect(copy.locator('.graph-legend__header')).toContainText(`${count} nodes`);
  await expect(page.locator('.gl-panel--graph:not(.gl-panel--graph-copy) .graph-legend')).toHaveCount(1);

  // Zoomed, the copy moves and the canvas does not, once both have settled.
  await settled(page, '.gl-panel--graph:not(.gl-panel--graph-copy)');
  await settled(page, '.gl-panel--graph-copy');
  const mainBefore = await transformOf(page, '.gl-panel--graph:not(.gl-panel--graph-copy)');
  const copyBefore = await transformOf(page, '.gl-panel--graph-copy');
  const box = await copy.locator('.graphRenderer > svg').first().boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.wheel(0, -400);
  await expect.poll(() => transformOf(page, '.gl-panel--graph-copy')).not.toBe(copyBefore);
  expect(await transformOf(page, '.gl-panel--graph:not(.gl-panel--graph-copy)')).toBe(mainBefore);

  // Each copy is a window of its own.
  await page.locator('.lm_tab', { hasText: /^◈ Graph$/ }).click();
  await page.getByRole('button', { name: 'Duplicate the graph into a window of its own' }).click();
  await expect(page.locator('.lm_tab', { hasText: '◈ Graph 3' })).toHaveCount(1);
});

test('a copy dragged beside the canvas is drawn there, both in sight at once', async ({ page }) => {
  // The copy is a tab of the dock: dropped on the right of the canvas's stack,
  // it splits it, and the canvas and the copy are seen side by side.
  const count = await loadDemo(page);
  await page.getByRole('button', { name: 'Duplicate the graph into a window of its own' }).click();
  const tab = page.locator('.lm_tab', { hasText: '◈ Graph 2' });
  await expect(tab).toHaveCount(1);
  const area = await page.locator('.gl-panel--graph-copy').locator('xpath=ancestor::div[contains(@class,"lm_stack")][1]')
    .locator('.lm_items').boundingBox();
  const from = await tab.boundingBox();
  await page.mouse.move(from!.x + from!.width / 2, from!.y + from!.height / 2);
  await page.mouse.down();
  await page.mouse.move(area!.x + area!.width * 0.92, area!.y + area!.height / 2, { steps: 25 });
  await page.mouse.up();

  const main = page.locator('.gl-panel--graph:not(.gl-panel--graph-copy)');
  const copy = page.locator('.gl-panel--graph-copy');
  await expect(main).toBeVisible();
  await expect(copy).toBeVisible();
  const apart = await page.evaluate(() => {
    const stackOf = (sel: string) => document.querySelector(sel)?.closest('.lm_stack');
    const a = stackOf('.gl-panel--graph:not(.gl-panel--graph-copy)');
    const b = stackOf('.gl-panel--graph-copy');
    return !!a && !!b && a !== b;
  });
  expect(apart, 'the copy sits in a stack of its own').toBe(true);
  await expect(copy.locator('g.graph-node')).toHaveCount(count, { timeout: SETTLED });
});

test("⧉ is among the Graph window's controls, not over the canvas, and in sight while the canvas is in front", async ({ page }) => {
  // On the canvas, ⧉ covered a corner where the wheel then zoomed nothing.
  // Mutation: draw ⧉ on the canvas, as it was -- it is not among the stack's
  // controls, its box lies on the canvas, and this fails.
  await loadDemo(page);
  const duplicate = page.getByRole('button', { name: 'Duplicate the graph into a window of its own' });
  const graphStack = page.locator('.lm_stack').filter({ has: page.locator('.gl-panel--graph:not(.gl-panel--graph-copy)') });
  await expect(graphStack.locator('.lm_header .lm_controls').getByRole('button', { name: 'Duplicate the graph into a window of its own' })).toHaveCount(1);
  const button = (await duplicate.boundingBox())!;
  const canvas = (await page.locator('.gl-panel--graph:not(.gl-panel--graph-copy)').boundingBox())!;
  const overlaps = button.x < canvas.x + canvas.width && canvas.x < button.x + button.width
    && button.y < canvas.y + canvas.height && canvas.y < button.y + button.height;
  expect(overlaps, '⧉ lies on the canvas').toBe(false);

  // A copy in front of the canvas has no ⧉ of its own; back on the canvas, it is there again.
  await duplicate.click();
  await expect(page.locator('.lm_tab', { hasText: '◈ Graph 2' })).toHaveCount(1);
  await expect(duplicate).toBeHidden();
  await page.locator('.lm_tab', { hasText: /^◈ Graph$/ }).click();
  await expect(duplicate).toBeVisible();
});

test('with nothing drawn, there is nothing to duplicate', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await expect(page.getByRole('button', { name: 'Duplicate the graph into a window of its own' })).toBeDisabled();
});

test('a saved layout holding a copy is kept', async ({ page }) => {
  // Mutation: leave the copy's type out of the saved layout's known windows --
  // the layout is dropped for the default on the reload, and this fails.
  await loadDemo(page);
  await page.getByRole('button', { name: 'Duplicate the graph into a window of its own' }).click();
  await expect(page.locator('.lm_tab', { hasText: '◈ Graph 2' })).toHaveCount(1);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: 'Save current as default' }).click();
  await page.reload();
  await dismissOnboardingModal(page);
  await expect(page.locator('.lm_tab', { hasText: '◈ Graph 2' })).toHaveCount(1);

  // The next copy is named past it. Mutation: count copies from nothing on
  // each visit -- the new copy is a second Graph 2, and this fails.
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  const duplicate = page.getByRole('button', { name: 'Duplicate the graph into a window of its own' });
  await expect(duplicate).toBeEnabled({ timeout: SETTLED });
  await page.locator('.lm_tab', { hasText: /^◈ Graph$/ }).click();
  await duplicate.click();
  await expect(page.locator('.lm_tab', { hasText: '◈ Graph 3' })).toHaveCount(1);
  await expect(page.locator('.lm_tab', { hasText: '◈ Graph 2' })).toHaveCount(1);
});
