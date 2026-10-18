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

/**
 * Load the demo, and wait for *its* canvas.
 *
 * A canvas already on screen has nodes too, so waiting for a node alone can
 * finish before the new plot has even cleared the old one -- and before any
 * error that clearing logs. So the canvas that was there is waited out first.
 * The Graph tab is then brought forward: a Graph panel added from the menu
 * joins whichever stack Golden Layout has focused, which can be Upload's.
 */
async function loadDemo(page: Page): Promise<void> {
  const previous = await page.locator('.gl-panel--graph .graph_content').elementHandles();
  await tab(page, '↑ Upload').click();
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  if (previous.length > 0) {
    await page.waitForFunction((canvases) => canvases.every((canvas) => !canvas.isConnected), previous);
  }
  await tab(page, '◈ Graph').click();
  await expect(page.locator('.gl-panel--graph .graph-node').first()).toBeVisible({ timeout: 20_000 });
}

/** The shell's dock element and Golden Layout's root in it, rounded. */
async function dockSizes(page: Page): Promise<{ host: number[]; root: number[] }> {
  return page.evaluate(() => {
    const host = document.querySelector('.gl-shell__body') as HTMLElement;
    const root = host.querySelector(':scope > .lm_root') as HTMLElement;
    const size = (element: HTMLElement) => {
      const box = element.getBoundingClientRect();
      return [Math.round(box.width), Math.round(box.height)];
    };
    return { host: size(host), root: size(root) };
  });
}

/**
 * Two frames and a task: the frame whose layout sees the new size, which is
 * when the browser tells Golden Layout, and one more, with Golden Layout's
 * zero-delay timer between them. Its default is a 100ms timer, restarted by
 * every resize that arrives inside it, so a dock that waited would still be
 * the old size here.
 */
async function aMomentLater(page: Page): Promise<void> {
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 20)))),
  );
}

test.describe('the dock follows the window', () => {
  test('taller, narrower and wider, the dock is the size of its element at once', async ({ page }) => {
    /**
     * Golden Layout follows its container by itself only when the container
     * is <body>. This shell's is not, and the dock kept the size it was built
     * at -- 1280 by 675 inside an element of 900 by 555, panels cut off at
     * the edge -- however long anyone waited.
     */
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/');
    await dismissOnboardingModal(page);
    const first = await dockSizes(page);
    expect(first.root).toEqual(first.host);

    for (const [width, height] of [[1280, 1000], [900, 600], [1440, 800]]) {
      await page.setViewportSize({ width, height });
      await aMomentLater(page);
      const now = await dockSizes(page);
      // The element moved with the window; the dock moved with the element.
      expect(now.host).not.toEqual(first.host);
      // Mutation: drop `resizeWithContainerAutomatically = true` from
      // golden_layout_shell.ts and the root stays 1280x675; leave it and drop
      // the two debounce lines, and it is still the previous size here.
      expect(now.root, `at ${width}x${height}`).toEqual(now.host);
    }
  });
});

test.describe('no panel offers to pop out', () => {
  test('no stack header has a popout control, in the default dock or after adding a panel', async ({ page }) => {
    /**
     * Every panel is a Mithril root this window mounts, and Golden Layout
     * does not run the component factories again in a popout window. Each of
     * the default dock's three stacks offered the control anyway; pressing it
     * opened a window with nothing in it and took the panel out of the dock.
     */
    await page.goto('/');
    await dismissOnboardingModal(page);
    // The headers are drawn, with the controls that do work: the count below
    // is of a control that is absent, not of a dock that never loaded.
    await expect(page.locator('.lm_header .lm_controls .lm_maximise')).toHaveCount(3);

    // Mutation: put back `popout: 'Pop out'` in default_layout.ts and this
    // finds one per stack.
    await expect(page.locator('.lm_popout')).toHaveCount(0);

    // A panel added from the menu lands in a stack under the same header.
    await openFromMenu(page, 'Overview');
    await expect(page.locator('.gl-panel--overview')).toBeVisible();
    await expect(page.locator('.lm_popout')).toHaveCount(0);
  });
});

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

    await loadDemo(page);

    await tab(page, '◈ Graph').locator('.lm_close_tab').click();
    await expect(page.locator('.gl-panel--graph')).toHaveCount(0);
    await openFromMenu(page, 'Graph');
    // Opened again, it shows the graph that is drawn.
    await expect(page.locator('.gl-panel--graph .graph-node').first()).toBeVisible({ timeout: 20_000 });

    await loadDemo(page);
    await expect(page.locator('.gl-panel--graph')).toHaveCount(1);

    // Mutation: as above -- two NotFoundErrors, one for clearing the canvas
    // and one for drawing the new graph.
    expect(errors).toEqual([]);
  });
});
