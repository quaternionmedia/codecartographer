/**
 * View ▸ Source and a double-click open a node's source through one opener.
 *
 * A node from a GitHub repository opens its file's page at the node's line;
 * a node read from this checkout has no page to open, so a badge names the
 * file and line beside it. Both routes call the same opener and are offered on
 * the same rule: the node names a file. The fixture workspace is read from
 * disk, so what is seen here is the badge.
 */

import type { Locator, Page } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;
const WORKSPACE = 'tests/fixtures/cargo/workspace';

/**
 * A point of the node that a pointer there reaches, as the browser hit-tests
 * it. A file node's centre is often under one of its symbols or its label,
 * which is where a double-click aimed at the centre waited out the test.
 */
async function pointOn(node: Locator): Promise<{ x: number; y: number }> {
  const point = await node.evaluate((el) => {
    const r = el.getBoundingClientRect();
    const steps = [0.5, 0.35, 0.65, 0.2, 0.8, 0.1, 0.9];
    for (const fy of steps) {
      for (const fx of steps) {
        const x = r.left + r.width * fx;
        const y = r.top + r.height * fy;
        const hit = document.elementFromPoint(x, y);
        if (hit && el.contains(hit)) return { x, y };
      }
    }
    return null;
  });
  expect(point, 'no point of the node is reached by a pointer').not.toBeNull();
  return point!;
}

async function drawWorkspace(page: Page): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.panel-source__url-input input').fill(WORKSPACE);
  await page.locator('.panel-source__url-input button.primary').click();
  await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });
  await expect(page.locator('.panel-source__url-input button.primary')).toHaveText(/Fetch/, { timeout: SETTLED });
}

test('a double-click and View ▸ Source name the same file and line', async ({ page }) => {
  await drawWorkspace(page);
  const badge = page.locator('.source-badge');

  // `delay` in the blinky crate, at main.rs line 21.
  const delay = page.locator('.graph-node[data-node-id*="function::delay"]').first();
  await delay.dblclick();
  await expect(badge).toHaveText(/^delay\s+.*main\.rs:21$/);
  await expect(badge).toBeInViewport({ ratio: 1 });
  const fromDoubleClick = await badge.textContent();
  // The badge leaves after a few seconds; the next one is the menu's.
  await expect(badge).toHaveCount(0, { timeout: 10_000 });

  await delay.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
  await delay.click({ button: 'right' });
  // View is the sixth wedge; Source is the first in its ring.
  for (let i = 0; i < 6; i++) await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');

  // Mutation: route View ▸ Source to the toast it showed -- no badge, and this fails.
  await expect(badge).toHaveText(fromDoubleClick ?? '');
  await expect(badge).toHaveCount(1);
  await expect(badge).toBeInViewport({ ratio: 1 });
});

test('the badge stays inside the canvas, its path shortened and whole in its title', async ({ page }) => {
  // A canvas narrower than the badge's path, wherever this checkout is.
  await page.setViewportSize({ width: 560, height: 720 });
  await drawWorkspace(page);
  const canvas = page.locator('.graphRenderer svg').first();
  const area = (await canvas.boundingBox())!;
  const delay = page.locator('.graph-node[data-node-id*="function::delay"]').first();
  await expect(delay).toBeAttached();
  // The double-click lands at the canvas's top right corner.
  await delay.dispatchEvent('dblclick', { clientX: area.x + area.width - 2, clientY: area.y + 2 });

  const badge = page.locator('.source-badge');
  await expect(badge).toBeVisible();
  const title = (await badge.getAttribute('title')) ?? '';
  expect(title).toMatch(/^delay\s+.*main\.rs:21$/);
  // Mutation: place the badge at the pointer, unclamped and whole -- it runs
  // off the canvas's right edge, and this fails.
  const b = (await badge.boundingBox())!;
  expect(b.x).toBeGreaterThanOrEqual(area.x);
  expect(b.x + b.width).toBeLessThanOrEqual(area.x + area.width);
  expect(b.y).toBeGreaterThanOrEqual(area.y);
  expect(b.y + b.height).toBeLessThanOrEqual(area.y + area.height);
  // Shortened from the middle: the name and the file and line stay.
  const shown = (await badge.textContent()) ?? '';
  expect(shown.length).toBeLessThan(title.length);
  expect(shown).toMatch(/^delay\s+….*main\.rs:21$/);
  // Nothing of it is cut off unseen.
  expect(await badge.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
});

test('a file opens from a double-click at the top, as a symbol opens at its line', async ({ page }) => {
  await drawWorkspace(page);
  const file = page.locator('.graph-node[data-node-id^="file::"][data-node-id$="blinky/src/main.rs"]').first();
  // Mutation: open only symbols with a line, as the double-click did -- a
  // file node shows nothing, and this fails.
  // A real double-click, hit-tested where the pointer is: a synthetic event
  // dispatched to the node reaches it whatever is drawn over it, and carries
  // no pointer position, so the badge it raised sat above the top of the page
  // and the case still passed.
  await expect(file).toBeVisible();
  const at = await pointOn(file);
  await page.mouse.dblclick(at.x, at.y);
  const badge = page.locator('.source-badge');
  await expect(badge).toHaveText(/^main\.rs\s+.*main\.rs$/);
  await expect(badge).toBeInViewport({ ratio: 1 });
});
