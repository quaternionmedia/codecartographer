/**
 * One entry point to graphs: the Open panel.
 *
 * Every source sits in it, with the parse options once and one Plot / Cancel
 * bar. These check what only a browser shows: that the bundled example opens
 * from it and plots again from its bar, that Plot draws every added file, and
 * that the recent graphs are listed there and nowhere else.
 */

import { expect, test, type Locator, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;

test('the bundled example opens from the Open panel, and Plot draws it again', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  const open = page.locator('.gl-panel--open');
  await expect(open).toBeVisible();

  await open.locator('[data-example="blinky (recorded)"]').click();
  const flash = page.locator('.graph-node[data-node-id*="region::FLASH"]');
  await expect(flash).toHaveCount(1, { timeout: SETTLED });

  // The Cargo panel came forward beside Open; back to Open for its bar.
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  const plot = open.locator('button.panel-plotbar__plot');
  await expect(plot).toBeEnabled({ timeout: SETTLED });
  // Mutation: send Plot to the uploads only -- no repository stream is asked
  // for, and this fails.
  const replot = page.waitForRequest((r) => r.url().includes('/parse/stream-url') && r.method() === 'POST');
  await plot.click();
  await replot;
  await expect(open.locator('.panel-plotbar__status-text')).toHaveText(/(Served from cache|Done in \d+ms) \(\d+ nodes\)/, { timeout: SETTLED });
  await expect(flash).toHaveCount(1);
  await page.screenshot({ path: test.info().outputPath('open-panel.png'), fullPage: true });
});

/** The Files panel, brought to the front of its stack. */
async function filesPanel(page: Page) {
  await page.locator('.lm_tab', { hasText: 'Files' }).click();
  const files = page.locator('.gl-panel--file-tree');
  await expect(files).toBeVisible();
  return files;
}

/** The paths the Files panel lists as added. */
function addedPaths(files: Locator) {
  return files.locator('.gl-file-tree__file');
}

test('Plot draws every added file, not the first', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  const files = await filesPanel(page);

  // Paths resolve from web/, where the browser suite runs.
  await files.locator('#local-files-input').setInputFiles([
    'tests/e2e/fixtures/uploads/first.py',
    'tests/e2e/fixtures/uploads/second.py',
  ]);
  await expect(addedPaths(files)).toHaveText(['first.py', 'second.py']);
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.gl-panel--open button.panel-plotbar__plot').click();

  // Mutation: plot only the first added file -- second.py is not drawn, and this fails.
  await expect(page.locator('.graph-node[data-node-id$="first.py"]')).toHaveCount(1, { timeout: SETTLED });
  await expect(page.locator('.graph-node[data-node-id$="second.py"]')).toHaveCount(1);
});

test('the local files are added in the Files panel, not in Open', async ({ page }) => {
  // Mutation: keep the box in the Open panel -- and this fails.
  await page.goto('/');
  await dismissOnboardingModal(page);
  await expect(page.locator('.gl-panel--open .panel-upload__dropzone')).toHaveCount(0);
  const files = await filesPanel(page);
  await expect(files.locator('.panel-upload__dropzone')).toBeVisible();
  await expect(files.getByRole('button', { name: /Choose a folder/ })).toBeVisible();
});

test("a folder is added as its folders, less what is not its source, and Plot draws them", async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  const files = await filesPanel(page);
  // Mutation: read every file a folder holds -- target/'s is added, and this
  // fails.
  await files.locator('#local-folder-input').setInputFiles('tests/e2e/fixtures/uploads-folder/proj');
  await expect(addedPaths(files)).toHaveText([
    'proj/main.py', 'proj/src/__init__.py', 'proj/src/shapes.py', 'proj/tests/__init__.py',
  ]);
  await expect(page.locator('.gl-panel--open .panel-plotbar__status-text'))
    .toContainText('4 file(s) added, 1 left out');
  // Plot draws them as the folders they were added in. Mutation: draw the
  // added files as one flat folder -- no folder src is drawn, and this fails.
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.gl-panel--open button.panel-plotbar__plot').click();
  await expect(page.locator('.graph-node[data-node-id$="shapes.py"]')).toHaveCount(1, { timeout: SETTLED });
  await expect(page.locator('.graph-node[data-node-id^="dir::"][data-node-id$="/src"]')).toHaveCount(1);
});

test('two files of one name from two folders are both added', async ({ page }) => {
  // Mutation: know an added file by its name -- tests' __init__.py is taken
  // for src's, left out, and this fails.
  await page.goto('/');
  await dismissOnboardingModal(page);
  const files = await filesPanel(page);
  await files.locator('#local-folder-input').setInputFiles('tests/e2e/fixtures/uploads-folder/proj/src');
  await expect(addedPaths(files)).toHaveText(['src/__init__.py', 'src/shapes.py']);
  await files.locator('#local-folder-input').setInputFiles('tests/e2e/fixtures/uploads-folder/proj/tests');
  await expect(addedPaths(files)).toHaveText(['src/__init__.py', 'src/shapes.py', 'tests/__init__.py']);
});

test('local files are added from the keyboard: Enter on the box opens the file chooser', async ({ page }) => {
  // Chromium intercepts the chooser only once Playwright has asked it to, and
  // Playwright asks when the first 'filechooser' listener is added, without
  // waiting for the answer. Added just before the key, it lost: Chromium
  // answered the Enter before the request to intercept in 2 runs of 8, the
  // chooser opened unintercepted, and no event came. A click hides that gap
  // behind its actionability checks; a key press does not. So a listener is
  // added before the page loads, and the one awaited below only listens.
  page.on('filechooser', () => undefined);
  await page.goto('/');
  await dismissOnboardingModal(page);
  const files = await filesPanel(page);

  // Mutation: the box as a div with only a click handler -- no role names it,
  // it is not in the tab order, and this fails.
  const box = files.getByRole('button', { name: /choose files/i });
  await expect(box).toHaveAttribute('tabindex', '0');
  await box.focus();
  await expect(box).toBeFocused();
  const chooser = page.waitForEvent('filechooser');
  await page.keyboard.press('Enter');
  await (await chooser).setFiles([
    'tests/e2e/fixtures/uploads/first.py',
    'tests/e2e/fixtures/uploads/second.py',
  ]);
  await expect(addedPaths(files)).toHaveText(['first.py', 'second.py']);
});

test('the recent graphs are listed in Open, and not in Graphbase', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await expect(page.locator('.gl-panel--open .panel-source__cached')).toContainText('Recent');

  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Graphbase$/ }).click();
  const graphbase = page.locator('.gl-graphbase-panel');
  await expect(graphbase).toBeVisible();
  // Mutation: keep Graphbase's own Recent list -- this fails.
  await expect(graphbase).not.toContainText(/Recent \(/);
});

test.describe('in the default dock at 1600×1000', () => {
  test.use({ viewport: { width: 1600, height: 1000 } });

  test('Load Demo and the lexicons are in view without scrolling', async ({ page }) => {
    await page.goto('/');
    await dismissOnboardingModal(page);
    const open = page.locator('.gl-panel--open');
    await expect(open).toBeVisible();
    // The bundled examples and the lexicons arrive after the page; wait for
    // both, so the column is measured at its full height.
    await expect(open.locator('[data-example="blinky (recorded)"]')).toBeAttached({ timeout: SETTLED });
    const lexicons = open.getByRole('button', { name: /Lexicon$/ });
    await expect(lexicons.first()).toBeAttached({ timeout: SETTLED });

    // In view means unclipped by the column that scrolls, not only inside the
    // window: the intersection Playwright measures is clipped by every
    // scrolling ancestor.
    // Mutation: put the examples back above the quick starts -- Load Demo
    // sits below the column's fold, and this fails.
    await expect(open.getByRole('button', { name: /Load Demo/i })).toBeInViewport({ ratio: 1 });
    for (const lexicon of await lexicons.all()) {
      await expect(lexicon).toBeInViewport({ ratio: 1 });
    }
  });

  test('the parse options are in view above a full Recent list', async ({ page }) => {
    // More recent graphs than the list shows, whatever this server's cache holds.
    const entries = Array.from({ length: 12 }, (_, i) => ({
      key: `k${i}`, label: `example/repo-${i}`, url: `https://github.com/example/repo-${i}`,
      mode: 'symbols', layout: 'spring_layout', ts: 0, age_seconds: 3600 * (i + 1), size_bytes: 1,
    }));
    await page.route('**/parse/cache', (route) => route.fulfill({
      json: { status: 200, message: 'stubbed', results: { entries } },
    }));
    await page.goto('/');
    await dismissOnboardingModal(page);
    const open = page.locator('.gl-panel--open');
    await expect(open.locator('.panel-source__cached-chip')).not.toHaveCount(0, { timeout: SETTLED });

    // Mutation: put the parse options back under Recent -- the eight recent
    // graphs push them below the column's fold, and this fails.
    await expect(open.locator('.panel-open__parse-summary')).toBeInViewport({ ratio: 1 });
    // Opened, they push Recent down, and their first choices are in view.
    await open.locator('.panel-open__parse-toggle').click();
    await expect(open.locator('.panel-settings__chip').first()).toBeInViewport({ ratio: 1 });
  });
});

test('the parse options are folded to one line until opened', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  const open = page.locator('.gl-panel--open');
  await expect(open.locator('.panel-open__parse-summary')).toHaveText('Symbols · every language');
  await expect(open.getByText('Parse Depth')).toHaveCount(0);
  await open.locator('.panel-open__parse-toggle').click();
  await open.locator('button', { hasText: /^Deep$/ }).click();
  await expect(open.locator('.panel-open__parse-summary')).toHaveText('Deep · every language');
  // Once in the window: the options are not drawn anywhere else.
  await expect(page.getByText('Parse Depth')).toHaveCount(1);
});
