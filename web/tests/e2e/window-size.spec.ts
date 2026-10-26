/**
 * The dock fills the window as the window is resized, and so does a drawing.
 *
 * Golden Layout sizes every stack in pixels, and follows its container's size
 * by itself only when the container is the page's body. The shell's dock is
 * its own element, so a window narrowed from 1600 to 1200 pixels left the
 * dock 1600 wide: its right third, with the controls of the stacks there, ran
 * past the window's edge. Widened, the window showed a band of nothing beside
 * the dock. Step 4's maximised canvas kept its size the same way, and the
 * drawing with it.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;

test.use({ viewport: { width: 1600, height: 1000 } });

/**
 * How far each part misses the space it is given, as [width, height] in
 * pixels: the dock and a maximised stack against the shell's body, which the
 * page's own layout sizes to the window, and the drawing's svg against its
 * canvas. Null for a part that is not there.
 */
async function misfit(page: Page) {
  return page.evaluate(() => {
    const miss = (el: Element | null, room: Element | null): [number, number] | null => {
      if (!el || !room) return null;
      const a = el.getBoundingClientRect();
      const b = room.getBoundingClientRect();
      return [Math.round(a.width - b.width), Math.round(a.height - b.height)];
    };
    const host = document.querySelector('.gl-shell__body');
    return {
      dock: miss(document.querySelector('.lm_root'), host),
      maximised: miss(document.querySelector('.lm_maximised'), host),
      drawing: miss(document.querySelector('.graphRenderer > svg'), document.querySelector('.graphRenderer')),
    };
  });
}

test('the dock and the drawing follow the window as it narrows, shortens and widens', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  await expect(page.locator('.graph-node[data-node-id]').first()).toBeVisible({ timeout: SETTLED });
  const fits = { dock: [0, 0], maximised: null, drawing: [0, 0] };
  await expect.poll(() => misfit(page)).toEqual(fits);

  // Mutation: drop `resizeWithContainerAutomatically` from the shell -- the
  // dock keeps the window's first size, and this fails.
  for (const size of [{ width: 1200, height: 800 }, { width: 1800, height: 1050 }]) {
    await page.setViewportSize(size);
    await expect.poll(() => misfit(page), { message: `at ${size.width} × ${size.height}` }).toEqual(fits);
  }

  // Step 4's canvas, maximised, fills the dock at the window's new size.
  await page.locator('.gl-steps__step[data-step="read"]').click();
  await expect(page.locator('.lm_maximised')).toHaveCount(1);
  await page.setViewportSize({ width: 1300, height: 850 });
  await expect.poll(() => misfit(page)).toEqual({ ...fits, maximised: [0, 0] });
});
