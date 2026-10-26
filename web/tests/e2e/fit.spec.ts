/**
 * The fit frames the whole graph: every node and every group outline drawn.
 *
 * fit.ts's arithmetic is tested without a browser (tests/pure/fit.test.mjs).
 * What only a browser shows is what the renderer hands it: that the group
 * outlines are drawn before the fit and framed with the nodes, after a stream
 * and on the canvas ring's Fit, and that the census's show frames the nodes it
 * selects; and that Collapse redraws the outlines around what remains, as
 * outlines-after-removal.test.mjs computes them.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal, pointOn } from './helpers';

const SETTLED = 30_000;

/** What lies outside the canvas: each node or outline whose box crosses its edge. */
async function outsideTheCanvas(page: Page, selector: string): Promise<string[]> {
  return page.locator('.graphRenderer svg').first().evaluate((svg, sel) => {
    const c = svg.getBoundingClientRect();
    return [...svg.querySelectorAll(sel)]
      .filter((el) => {
        const b = el.getBoundingClientRect();
        return b.left < c.left - 0.5 || b.right > c.right + 0.5 || b.top < c.top - 0.5 || b.bottom > c.bottom + 0.5;
      })
      .map((el) => el.closest('[data-node-id]')?.getAttribute('data-node-id') ?? el.parentElement?.getAttribute('class') ?? '?');
  }, selector);
}

async function drawBundledExample(page: Page): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-panel--open [data-example="blinky (recorded)"]').click();
  await expect(page.locator('.graph-node[data-node-id*="region::FLASH"]')).toHaveCount(1, { timeout: SETTLED });
  await expect(page.locator('.compound-group circle').first()).toBeAttached();
}

test('after a stream, and on Fit, every node and group outline is in view', async ({ page }) => {
  await drawBundledExample(page);
  // The fit is a 700 ms transition; poll until it lands.
  // Mutation: frame the nodes without their outlines -- the directories'
  // outlines run off the canvas, and this fails.
  await expect.poll(() => outsideTheCanvas(page, '.compound-group circle'), { timeout: 5_000 }).toEqual([]);
  await expect.poll(() => outsideTheCanvas(page, '.graph-node'), { timeout: 5_000 }).toEqual([]);

  // Zoom in on a corner, so the graph runs off the canvas, then Fit.
  const svg = page.locator('.graphRenderer svg').first();
  const box = (await svg.boundingBox())!;
  const corner = { x: box.width - 30, y: 30 };
  await page.mouse.move(box.x + corner.x, box.y + corner.y);
  for (let i = 0; i < 4; i++) await page.mouse.wheel(0, -300);
  await expect.poll(() => outsideTheCanvas(page, '.graph-node').then((o) => o.length)).toBeGreaterThan(0);

  // The ring listens for keys on the canvas; focus it, as a keyboard user
  // who tabbed there would have.
  await svg.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
  await svg.click({ button: 'right', position: corner });
  const ring = page.locator('.rad-root');
  await expect(ring).toHaveAttribute('aria-label', 'canvas');
  // Fit is the canvas ring's first wedge; from no highlight ArrowRight lands on it.
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  await expect(ring).toHaveCount(0);
  await expect.poll(() => outsideTheCanvas(page, '.compound-group circle'), { timeout: 5_000 }).toEqual([]);
  await expect.poll(() => outsideTheCanvas(page, '.graph-node'), { timeout: 5_000 }).toEqual([]);
});

test("the census's show frames the nodes it selects", async ({ page }) => {
  await drawBundledExample(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Chrestomathy$/ }).click();
  const functions = page.locator('.chrestomathy__canvas tr[data-construct="callable.function"]');
  await expect(functions).toContainText('Rust', { timeout: SETTLED });

  const ids = await page.locator('.graph-node').evaluateAll((els) => els
    .filter((el) => (el as unknown as { __data__?: { construct?: string } }).__data__?.construct === 'callable.function')
    .map((el) => el.getAttribute('data-node-id') as string));
  expect(ids.length).toBeGreaterThan(1);
  const selector = ids.map((id) => `.graph-node[data-node-id=${JSON.stringify(id)}]`).join(', ');

  // Zoom in on a corner, so the functions are off the canvas.
  await page.locator('.lm_tab', { hasText: 'Graph' }).first().click();
  const svg = page.locator('.graphRenderer svg').first();
  const box = (await svg.boundingBox())!;
  await page.mouse.move(box.x + box.width - 30, box.y + 30);
  for (let i = 0; i < 4; i++) await page.mouse.wheel(0, -300);
  await expect.poll(() => outsideTheCanvas(page, selector).then((o) => o.length)).toBeGreaterThan(0);

  // Mutation: let show select without framing -- the functions stay off the
  // canvas, and this fails.
  await page.locator('.lm_tab', { hasText: 'Chrestomathy' }).click();
  await functions.locator('.cartography__show').click();
  await expect.poll(() => outsideTheCanvas(page, selector), { timeout: 5_000 }).toEqual([]);
});

test("Collapse takes a file's outline away with its symbols", async ({ page }) => {
  await drawBundledExample(page);
  const outline = page.locator('.compound-group', { hasText: /^main\.rs$/ });
  await expect(outline).toHaveCount(1);
  const nodes = page.locator('.graph-node');
  const drawn = await nodes.count();
  const file = page.locator('.graph-node[data-node-id^="file::"][data-node-id$="blinky/src/main.rs"]').first();
  await file.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
  const at = await pointOn(file);
  await page.mouse.click(at.x, at.y, { button: 'right' });
  const ring = page.locator('.rad-root');
  await expect(ring).toHaveAttribute('aria-label', 'node');
  await expect(ring.locator('[role="menuitem"][aria-label="Collapse"]')).not.toHaveAttribute('aria-disabled', 'true');
  // Collapse is the node ring's second wedge, after Expand.
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  await expect(ring).toHaveCount(0);
  await expect.poll(() => nodes.count()).toBeLessThan(drawn);
  // Mutation: leave the outlines as drawn after a removal -- main.rs keeps
  // its outline around nothing, and this fails.
  await expect(outline).toHaveCount(0);
});
