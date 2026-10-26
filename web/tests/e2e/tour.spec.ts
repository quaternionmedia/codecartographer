/**
 * A screenshot tour of the window.
 *
 * Walks the states a reviewer looks at -- a first visit, the default dock and
 * the Open panel, the bundled example with the rings and the panels it brings
 * forward, the demo graph, and a layout saved before the Open panel -- and
 * attaches a screenshot of each to the HTML report, so how a pull request
 * looks can be read without running it:
 *
 *   cd web && npx playwright test tour && npx playwright show-report
 *
 * It fails on any page error or console error on the way, and otherwise
 * asserts only what it needs to reach each state. Whether a state looks right
 * is for the reader of the screenshots; the other specs check behaviour.
 */

import { expect, test, type Locator, type Page } from '@playwright/test';

import { dismissOnboardingModal, pointOn } from './helpers';

const SETTLED = 30_000;
const FLASH = '.graph-node[data-node-id*="region::FLASH"]';
const SAVED_LAYOUT_KEY = 'cc:gl-layout:default';

test.use({ viewport: { width: 1600, height: 1000 } });

let errors: string[] = [];

test.beforeEach(({ page }) => {
  errors = [];
  page.on('pageerror', (e) => errors.push(`page error: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(`console error: ${m.text()}`);
  });
});

test.afterEach(() => {
  expect(errors, 'page and console errors on the tour').toEqual([]);
});

/** Attach a screenshot of the window, or of one panel, to the report. */
async function shot(name: string, target: Page | Locator): Promise<void> {
  await test.info().attach(name, { body: await target.screenshot(), contentType: 'image/png' });
}

/**
 * Wait for the window's CSS animations to end -- a modal fading in, a tab's
 * panel sliding in -- leaving the endless ones (the header's pulse) running.
 */
async function animationsDone(page: Page): Promise<void> {
  await page.waitForFunction(() => document.getAnimations().every((a) =>
    a.playState !== 'running' || a.effect?.getComputedTiming().endTime === Infinity));
}

/**
 * The fit after a stream is a 700 ms d3 transition and the group outlines
 * fade in over 800 ms, which `getAnimations` does not see; a screenshot taken
 * sooner catches them half way.
 */
async function settle(page: Page): Promise<void> {
  await page.waitForTimeout(1_500);
  await animationsDone(page);
}

function wedge(page: Page, label: string): Locator {
  return page.locator(`.rad-root [role="menuitem"][aria-label="${label}"]`);
}

/**
 * The ring is drawn with `pointer-events: none` and the canvas reads the
 * press, so a wedge is picked with a press at its centre, as a person picks
 * it, not with `locator.click()`.
 */
async function pickWedge(page: Page, label: string): Promise<void> {
  const box = await wedge(page, label).boundingBox();
  expect(box, `the ring offers ${label}`).not.toBeNull();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2, { steps: 5 });
  await page.mouse.down();
  await page.mouse.up();
}

/** The ring listens for keys on the canvas; focus it, as a keyboard user would have. */
async function focusCanvas(page: Page): Promise<void> {
  await page.locator('.graphRenderer svg').first()
    .evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
}

/**
 * Right-click a node where a pointer reaches it, and wait for its ring. Its
 * centre can be under another node or its own label, and Playwright's click
 * waits for the centre to come clear (`pointOn` in helpers.ts says why).
 */
async function openNodeRing(page: Page, node: Locator): Promise<void> {
  await focusCanvas(page);
  const at = await pointOn(node);
  await page.mouse.click(at.x, at.y, { button: 'right' });
  await expect(page.locator('.rad-root')).toHaveAttribute('aria-label', 'node');
}

async function closeRing(page: Page): Promise<void> {
  const ring = page.locator('.rad-root');
  for (let i = 0; i < 3 && (await ring.count()) > 0; i++) await page.keyboard.press('Escape');
  await expect(ring).toHaveCount(0);
}

test('a first visit, the Open panel, and the bundled example', async ({ page }) => {
  // Playwright's 30s timeout is for the whole test, and five of these steps'
  // waits allow SETTLED each: a slow stream would end the test before its own
  // wait did. Those five, and a minute for the other waits, the presses and
  // the screenshots.
  test.setTimeout(5 * SETTLED + 60_000);
  await page.goto('/');
  const open = page.locator('.gl-panel--open');

  await test.step('01 a first visit, with the walkthrough', async () => {
    await expect(page.locator('.cc-modal-backdrop')).toBeVisible();
    await animationsDone(page);
    await shot('01 first visit, with the walkthrough', page);
  });
  await dismissOnboardingModal(page);

  await test.step('02 the default dock', async () => {
    // The bundled example and the lexicons arrive after the page.
    await expect(open.locator('[data-example="blinky (recorded)"]')).toBeAttached({ timeout: SETTLED });
    await expect(open.getByRole('button', { name: /Lexicon$/ }).first()).toBeAttached({ timeout: SETTLED });
    await shot('02 default dock', page);
  });

  await test.step('03 the Open panel', async () => {
    await shot('03 Open panel', open);
  });

  await test.step('04 the parse options, open', async () => {
    await open.locator('.panel-open__parse-toggle').click();
    await expect(open.getByText('Parse Depth')).toBeVisible();
    // Under a long Recent list the options open below the column's fold.
    await open.locator('.panel-open__parse').scrollIntoViewIfNeeded();
    await shot('04 parse options open', open);
    await open.locator('.panel-open__parse-toggle').click();
    await expect(open.getByText('Parse Depth')).toHaveCount(0);
  });

  await test.step('05 the + menu', async () => {
    await page.locator('.gl-app-header__add-btn').click();
    await expect(page.locator('.gl-add-panel-menu')).toBeVisible();
    await shot('05 + menu', page);
    await page.keyboard.press('Escape');
    await expect(page.locator('.gl-add-panel-menu')).toHaveCount(0);
  });

  await test.step('06 the bundled example drawn, and Cargo forward', async () => {
    await open.locator('[data-example="blinky (recorded)"]').click();
    await expect(page.locator(FLASH)).toHaveCount(1, { timeout: SETTLED });
    await expect(page.locator('.gl-panel--cargo')).toBeVisible();
    await settle(page);
    await shot('06 bundled example drawn, Cargo forward', page);
  });

  await test.step('07 the node ring', async () => {
    await openNodeRing(page, page.locator(FLASH));
    await expect(wedge(page, 'View')).toBeAttached();
    await shot('07 node ring', page);
  });

  await test.step('08 the View submenu', async () => {
    await pickWedge(page, 'View');
    await expect(wedge(page, 'Compare')).toBeAttached();
    await shot('08 View submenu', page);
  });

  await test.step('09 View ▸ Compare opens Chrestomathy', async () => {
    await pickWedge(page, 'Compare');
    await expect(page.locator('.gl-panel--chrestomathy')).toBeVisible({ timeout: SETTLED });
    await expect(page.locator('.chrestomathy__canvas tr[data-construct]').first()).toBeVisible({ timeout: SETTLED });
    await settle(page);
    await shot('09 Compare opens Chrestomathy', page);
  });

  await test.step('10 the canvas ring', async () => {
    await closeRing(page).catch(() => undefined);
    const svg = page.locator('.graphRenderer svg').first();
    const box = (await svg.boundingBox())!;
    await focusCanvas(page);
    await svg.click({ button: 'right', position: { x: 12, y: box.height - 12 } });
    await expect(page.locator('.rad-root')).toHaveAttribute('aria-label', 'canvas');
    await shot('10 canvas ring', page);
    await closeRing(page);
  });

  await test.step('11 View ▸ Source on a file read from disk', async () => {
    const file = page.locator('.graph-node[data-node-id^="file::"][data-node-id$=".rs"]').first();
    await openNodeRing(page, file);
    await pickWedge(page, 'View');
    await expect(wedge(page, 'Source')).toBeAttached();
    await pickWedge(page, 'Source');
    await expect(page.locator('.source-badge')).toBeVisible();
    await shot('11 View ▸ Source, the local badge', page);
    await closeRing(page).catch(() => undefined);
  });

  await test.step('12 Graph Settings', async () => {
    await page.locator('.lm_tab', { hasText: 'Graph Settings' }).click();
    const settings = page.locator('.gl-panel--controls-graph-settings');
    await expect(settings).toBeVisible();
    await animationsDone(page);
    await shot('12 Graph Settings', settings);
  });

  await test.step('13 the Files panel', async () => {
    const files = page.locator('.gl-panel--file-tree');
    await expect(files.locator('.file').first()).toBeVisible();
    await shot('13 Files panel', files);
  });
});

test('the demo graph', async ({ page }) => {
  // Its one SETTLED wait, and half a minute for the page, the walkthrough and
  // the settle around it.
  test.setTimeout(SETTLED + 30_000);
  await page.goto('/');
  await dismissOnboardingModal(page);

  await test.step('14 Load Demo', async () => {
    await page.getByRole('button', { name: /Load Demo/i }).first().click();
    await expect(page.locator('.graph-node[data-node-id]').first()).toBeVisible({ timeout: SETTLED });
    // Off the button, which a hover would otherwise show in the screenshot.
    await page.mouse.move(800, 300);
    await settle(page);
    await shot('14 demo graph', page);
  });
});

test('a layout saved before the Open panel', async ({ page }) => {
  await page.addInitScript(({ key }) => {
    // Once, not on every navigation: the app rewrites what it migrates.
    if (sessionStorage.getItem('seeded')) return;
    sessionStorage.setItem('seeded', '1');
    localStorage.setItem(key, JSON.stringify({
      root: {
        type: 'row',
        content: [
          { type: 'component', componentType: 'graph', title: 'Graph', id: 'graph' },
          {
            type: 'stack',
            content: [
              { type: 'component', componentType: 'upload-panel', title: 'Upload', id: 'upload-panel' },
              { type: 'component', componentType: 'repo-panel', title: 'Repository', id: 'repo-panel' },
              { type: 'component', componentType: 'plotbar', title: 'Actions', id: 'plotbar' },
            ],
          },
        ],
      },
    }));
  }, { key: SAVED_LAYOUT_KEY });
  await page.goto('/');
  await dismissOnboardingModal(page);

  await test.step('15 migrated to one Open window', async () => {
    // Mutation: drop the renames -- the layout is dropped for the default,
    // which has an Open window too, the toast says the saved layout was not
    // loaded, a Graph Settings tab appears, and this fails.
    await expect(page.locator('.cc-toast__msg', { hasText: 'are the Open window in this version' })).toHaveText(
      "The saved layout's 'upload-panel', 'repo-panel', 'plotbar' window(s) are the Open window in this version.",
    );
    await expect(page.locator('.lm_tab', { hasText: 'Open' })).toHaveCount(1);
    await expect(page.locator('.lm_tab', { hasText: 'Graph Settings' })).toHaveCount(0);
    await expect(page.locator('.gl-panel--open')).toBeVisible();
    await shot('15 old saved layout migrated', page);
  });
});
