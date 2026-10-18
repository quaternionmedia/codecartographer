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

// ── The saved layout ────────────────────────────────────────────────────────

const SAVED_LAYOUT_KEY = 'cc:gl-layout:default';

/** The default dock's tabs, by title. */
const DEFAULT_TABS = ['◈ Graph', '◉ Files', '↑ Upload', '⬇ Repository', 'Graph Settings', '▶ Actions', '⌂ Estate'];

const panel = (id: string) => ({ type: 'component', componentType: id, id });

/**
 * What "Save current as default" stored before it converted what it saved:
 * Golden Layout's `toConfig()`, its *resolved* form, with sizes as numbers and
 * the header of the time, which offered popouts. Recorded from that menu with
 * Estate, Repository, Graph Settings and Upload closed.
 */
const SAVED_BY_TO_CONFIG = {
  root: {
    type: 'column',
    content: [
      {
        type: 'stack',
        content: [{
          type: 'component', content: [], size: 65, sizeUnit: '%', minSizeUnit: 'px', id: 'graph',
          maximised: false, isClosable: true, reorderEnabled: true, title: '◈ Graph',
          componentType: 'graph', componentState: {},
        }],
        size: 65, sizeUnit: '%', minSizeUnit: 'px', id: 'graph', isClosable: true, maximised: false,
        activeItemIndex: 0,
      },
      {
        type: 'row',
        content: [
          {
            type: 'stack',
            content: [{
              type: 'component', content: [], size: 22, sizeUnit: '%', minSizeUnit: 'px', id: 'file-tree',
              maximised: false, isClosable: true, reorderEnabled: true, title: '◉ Files',
              componentType: 'file-tree', componentState: {},
            }],
            size: 22, sizeUnit: '%', minSizeUnit: 'px', id: 'file-tree', isClosable: true, maximised: false,
            activeItemIndex: 0,
          },
          {
            type: 'stack',
            content: [{
              type: 'component', content: [], size: 1, sizeUnit: 'fr', minSizeUnit: 'px', id: 'plotbar',
              maximised: false, isClosable: true, reorderEnabled: true, title: '▶ Actions',
              componentType: 'plotbar', componentState: {},
            }],
            size: 78, sizeUnit: '%', minSizeUnit: 'px', id: 'dock-tab-stack', isClosable: true,
            maximised: false, activeItemIndex: 0,
          },
        ],
        size: 35, sizeUnit: '%', minSizeUnit: 'px', id: '', isClosable: true,
      },
    ],
    size: 1, sizeUnit: 'fr', minSizeUnit: 'px', id: '', isClosable: true,
  },
  openPopouts: [],
  settings: {
    constrainDragToContainer: true, reorderEnabled: true, popoutWholeStack: false,
    blockedPopoutsThrowError: false, closePopoutsOnUnload: true, responsiveMode: 'none',
    tabOverlapAllowance: 0, reorderOnTabMenuClick: true, tabControlOffset: 10, popInOnClose: true,
  },
  dimensions: {
    borderWidth: 4, borderGrabWidth: 8, defaultMinItemHeight: 60, defaultMinItemHeightUnit: 'px',
    defaultMinItemWidth: 80, defaultMinItemWidthUnit: 'px', headerHeight: 20, dragProxyWidth: 300,
    dragProxyHeight: 200,
  },
  header: {
    show: 'top', popout: 'Pop out', dock: 'Pop in', close: 'Close', maximise: 'Maximise',
    minimise: 'Minimise', tabDropdown: 'More tabs',
  },
  resolved: true,
};

/** Put `text` under the saved-layout key before the page first loads -- once. */
async function seedSavedLayout(page: Page, text: string): Promise<void> {
  await page.addInitScript(
    ({ key, value }) => {
      // Once per test, not on every navigation: a check reads the key back
      // after the page has had its chance to forget it.
      if (sessionStorage.getItem('cc-test-seeded')) return;
      sessionStorage.setItem('cc-test-seeded', '1');
      localStorage.setItem(key, value);
    },
    { key: SAVED_LAYOUT_KEY, value: text },
  );
}

const savedLayout = (page: Page) =>
  page.evaluate((key) => localStorage.getItem(key), SAVED_LAYOUT_KEY);

const refusalToast = (page: Page) =>
  page.locator('.cc-toast__msg', { hasText: 'The saved layout could not be used' });

test.describe('a saved layout', () => {
  test('saved from the menu, it is what the next visit opens', async ({ page }) => {
    /**
     * The menu saved `toConfig()`, which reports sizes as numbers, and
     * `loadLayout` reads them as strings: the next visit threw "value.trimStart
     * is not a function" and opened with no panels at all.
     */
    await page.goto('/');
    await dismissOnboardingModal(page);
    await tab(page, '⌂ Estate').locator('.lm_close_tab').click();
    await expect(tab(page, '⌂ Estate')).toHaveCount(0);
    await page.locator('.gl-app-header__add-btn').click();
    await page.locator('.gl-add-panel-menu__item', { hasText: 'Save current as default' }).click();
    await expect(page.locator('.cc-toast__msg', { hasText: 'Layout saved as default' })).toBeVisible();

    // What is kept is the form Golden Layout loads, not the resolved form it
    // reports a layout in, which it marks `resolved` and cannot load as it
    // stands. Reading converts that form too, for layouts saved before this,
    // so the reload below would pass either way: this is what tells them
    // apart. Mutation: save `toConfig()` again in layout_context.ts.
    const stored = JSON.parse((await savedLayout(page)) ?? 'null');
    expect(stored?.root?.type).toBe('column');
    expect(stored).not.toHaveProperty('resolved');

    const errors = collectErrors(page);
    await page.reload();
    await dismissOnboardingModal(page);

    // Mutation: take the conversion away on both sides and the default comes
    // back instead, with a toast saying Golden Layout refused the saved one;
    // take the guard away as well and there are no tabs at all.
    for (const title of DEFAULT_TABS.filter((t) => t !== '⌂ Estate')) {
      await expect(tab(page, title), title).toHaveCount(1);
    }
    await expect(tab(page, '⌂ Estate')).toHaveCount(0);
    await expect(refusalToast(page)).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test('saved in the form the menu used to save, it is still the reader\'s, under today\'s header', async ({ page }) => {
    /**
     * Golden Layout converts its own resolved form back, so an arrangement
     * saved before the menu did that itself is loaded as it was saved. Its
     * header is the one of its day, which offered popouts; the layout loads
     * under today's settings instead.
     */
    const errors = collectErrors(page);
    await seedSavedLayout(page, JSON.stringify(SAVED_BY_TO_CONFIG));
    await page.goto('/');

    // Mutation: drop the `LayoutConfig.fromResolved` conversion on reading
    // and the default loads instead, Golden Layout having refused this.
    for (const title of ['◈ Graph', '◉ Files', '▶ Actions']) await expect(tab(page, title), title).toHaveCount(1);
    for (const title of ['↑ Upload', '⬇ Repository', 'Graph Settings', '⌂ Estate']) {
      await expect(tab(page, title), title).toHaveCount(0);
    }
    // Mutation: load the saved header instead of LAYOUT_SETTINGS' and this
    // finds the popout control on every stack again.
    await expect(page.locator('.lm_popout')).toHaveCount(0);
    await expect(refusalToast(page)).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  const unusable: Array<[string, string, string]> = [
    ['text that is not JSON', '{not json', 'it is not JSON'],
    [
      'a panel this version does not have',
      // `source-panel` is a panel an earlier version of this shell had.
      JSON.stringify({ root: { type: 'row', content: [panel('graph'), panel('source-panel')] } }),
      'it names "source-panel", which this version does not have',
    ],
    [
      'panels in windows of their own',
      JSON.stringify({ root: panel('graph'), openPopouts: [{ root: panel('plotbar') }] }),
      'it has panels in windows of their own',
    ],
  ];
  for (const [name, text, why] of unusable) {
    test(`holding ${name}, it gives way to the default, which says why`, async ({ page }) => {
      /**
       * Golden Layout throws on a panel nobody registered, and the shell loads
       * the saved layout as it starts: a layout naming one was a page with no
       * panels, on every visit. Each is caught before Golden Layout sees it
       * (saved_layout.ts, whose unit tests cover every refusal); the default
       * loads, the reader is told why, and the saved layout is forgotten.
       */
      const errors = collectErrors(page);
      await seedSavedLayout(page, text);
      await page.goto('/');

      for (const title of DEFAULT_TABS) await expect(tab(page, title), title).toHaveCount(1);
      await expect(refusalToast(page)).toContainText(why);
      expect(errors).toEqual([]);
      expect(await savedLayout(page)).toBeNull();
    });
  }

  test('one Golden Layout refuses after the check, the default boots and nothing of it is left drawing', async ({ page }) => {
    /**
     * A stack whose `activeItemIndex` is past its last tab passes the check,
     * and Golden Layout throws on it only after it has built the panels in
     * it. The shell loads the default instead -- and takes down the panels
     * the failed attempt mounted, which are in no layout and would never be
     * released. Left up, its Graph panel drew the canvas vnode beside the
     * real one, and the second plot logged NotFoundErrors as a closed and
     * reopened Graph panel did.
     */
    const errors = collectErrors(page);
    await seedSavedLayout(page, JSON.stringify({
      root: {
        type: 'row',
        content: [
          { type: 'stack', activeItemIndex: 4, content: [panel('graph'), panel('plotbar')] },
          { type: 'stack', content: [panel('file-tree')] },
        ],
      },
    }));
    await page.goto('/');
    await dismissOnboardingModal(page);

    // Mutation: load the saved layout without the try/catch in
    // golden_layout_shell.ts and there are no tabs, and a page error.
    for (const title of DEFAULT_TABS) await expect(tab(page, title), title).toHaveCount(1);
    await expect(refusalToast(page)).toContainText('Golden Layout refused it (ActiveItemIndex out of range');
    expect(await savedLayout(page)).toBeNull();

    // Mutation: keep the guard and drop the loop that unmounts what the
    // failed attempt mounted -- the first plot is drawn twice, once into an
    // element in no layout, and the second logs two NotFoundErrors.
    await loadDemo(page);
    await loadDemo(page);
    expect(errors).toEqual([]);
  });
});
