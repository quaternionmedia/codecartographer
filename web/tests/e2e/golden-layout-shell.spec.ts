/**
 * The dock around the panels: what Golden Layout does with them, as a reader
 * meets it.
 *
 * WHAT A BROWSER SEES THAT NOTHING ELSE CAN. Each behaviour here is a line of
 * configuration or a call into Golden Layout, and each was wrong in a way that
 * typechecked and built: a closed panel went on drawing into an element that
 * had left the page. alfred's workspace copied this shell, found each of these
 * in its own browser suite, and fixed them there first; these are the same
 * fixes, asked of this shell.
 */

import type { Locator, Page } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

/** The tab whose title is exactly `title` -- "◈ Graph" is not "Graph Settings". */
function tab(page: Page, title: string): Locator {
  return page.locator('.lm_tab').filter({
    has: page.locator('.lm_title', { hasText: new RegExp(`^${title}$`) }),
  });
}

/**
 * Console errors and page errors from here on, less failed resource loads.
 *
 * A request that fails is reported by the browser as a console error, and on
 * a machine without MongoDB every plot asks `/db/` for bookmarks and is
 * refused. Whether those requests should fail is demo-graph.spec.ts's
 * question; this file is about what the dock draws.
 */
function collectErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !msg.text().startsWith('Failed to load resource')) {
      errors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  return errors;
}

async function openFromMenu(page: Page, label: string): Promise<void> {
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: new RegExp(`^${label}$`) }).click();
}

test.describe('a closed panel is taken down with its tab', () => {
  test('it stops drawing, though what it drew from goes on changing', async ({ page }) => {
    /**
     * Golden Layout removes a closed panel's element from the page; the
     * Mithril root mounted in it is unmounted only if the shell says so. If it
     * is not, every redraw still draws the panel into the detached element.
     * The Actions panel shows the status line and offers Plot once a file is
     * there, so an upload after it is closed is what would redraw it.
     */
    await page.goto('/');
    await dismissOnboardingModal(page);
    await tab(page, '▶ Actions').click();
    const released = await page
      .locator('.gl-actions-panel')
      .evaluateHandle((panel) => panel.parentElement as HTMLElement);

    await tab(page, '▶ Actions').locator('.lm_close_tab').click();
    await expect(page.locator('.gl-actions-panel')).toHaveCount(0);

    await tab(page, '↑ Upload').click();
    // Dropped, as a reader drops a file, and built in the page: the specs are
    // typechecked without Node's types, so there is no Buffer to hand over.
    await page.locator('.panel-upload__dropzone').evaluate((dropzone) => {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(new File(['def answer():\n    return 42\n'], 'sample.py'));
      dropzone.dispatchEvent(new DragEvent('drop', { dataTransfer, bubbles: true, cancelable: true }));
    });
    // The Files panel draws in the same redraw a stale Actions root would.
    await expect(page.locator('.gl-file-tree__file', { hasText: 'sample.py' })).toBeVisible();

    // Mutation: drop the `m.mount(container.element, null)` from the release
    // handler in golden_layout_shell.ts and the closed panel is still in its
    // element, redrawn after it closed: "▶Plot1 file(s) added".
    expect(await released.evaluate((element) => element.isConnected)).toBe(false);
    expect(await released.evaluate((element) => element.textContent)).toBe('');
    expect(await released.evaluate((element) => element.childElementCount)).toBe(0);
  });

  test('the Graph panel closed and opened again draws the next plot cleanly', async ({ page }) => {
    /**
     * The canvas is a vnode the state holds, and every root that draws the
     * Graph panel draws that same vnode. A Graph panel closed and opened again
     * while a graph is drawn left two roots holding it -- the closed one and
     * the new one -- and the next plot had each remove it from its own parent:
     * Mithril logged a NotFoundError from `removeChild` for every change of
     * graph, for the rest of the session.
     */
    await page.goto('/');
    await dismissOnboardingModal(page);
    const errors = collectErrors(page);

    await page.getByRole('button', { name: /Load Demo/i }).first().click();
    await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: 20_000 });

    await tab(page, '◈ Graph').locator('.lm_close_tab').click();
    await expect(page.locator('.gl-panel--graph')).toHaveCount(0);
    await openFromMenu(page, 'Graph');
    // Opened again, it shows the graph that is drawn.
    await expect(page.locator('.gl-panel--graph .graph-node').first()).toBeVisible({ timeout: 20_000 });

    await tab(page, '↑ Upload').click();
    await page.getByRole('button', { name: /Load Demo/i }).first().click();
    await expect(page.locator('.gl-panel--graph .graph-node').first()).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('.gl-panel--graph')).toHaveCount(1);

    // Mutation: as above -- two NotFoundErrors, one for clearing the canvas
    // and one for drawing the new graph.
    expect(errors).toEqual([]);
  });
});
