/**
 * One entry point to graphs: the Open panel.
 *
 * Every source sits in it, with the parse options once and one Plot / Cancel
 * bar. These check what only a browser shows: that the bundled example opens
 * from it and plots again from its bar, that Plot draws every added file, and
 * that the recent graphs are listed there and nowhere else.
 */

import { expect, test } from '@playwright/test';

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

test('Plot draws every added file, not the first', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  const open = page.locator('.gl-panel--open');

  // Paths resolve from web/, where the browser suite runs.
  await open.locator('#file-upload-input').setInputFiles([
    'tests/e2e/fixtures/uploads/first.py',
    'tests/e2e/fixtures/uploads/second.py',
  ]);
  await expect(open.locator('.panel-source__upload-summary')).toContainText('2 file(s)');
  await open.locator('button.panel-plotbar__plot').click();

  // Mutation: plot only the first added file -- second.py is not drawn, and this fails.
  await expect(page.locator('.graph-node[data-node-id$="first.py"]')).toHaveCount(1, { timeout: SETTLED });
  await expect(page.locator('.graph-node[data-node-id$="second.py"]')).toHaveCount(1);
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
  const open = page.locator('.gl-panel--open');

  // Mutation: the box as a div with only a click handler -- no role names it,
  // it is not in the tab order, and this fails.
  const box = open.getByRole('button', { name: /browse/i });
  await expect(box).toHaveAttribute('tabindex', '0');
  await box.focus();
  await expect(box).toBeFocused();
  const chooser = page.waitForEvent('filechooser');
  await page.keyboard.press('Enter');
  await (await chooser).setFiles([
    'tests/e2e/fixtures/uploads/first.py',
    'tests/e2e/fixtures/uploads/second.py',
  ]);
  await expect(open.locator('.panel-source__upload-summary')).toContainText('2 file(s)');
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

  test('the local files, Load Demo and the lexicons are in view without scrolling', async ({ page }) => {
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
    // Mutation: put the examples back above Local files -- the dropzone and
    // Load Demo sit below the column's fold, and this fails.
    await expect(open.locator('.panel-upload__dropzone')).toBeInViewport({ ratio: 1 });
    await expect(open.getByRole('button', { name: /Load Demo/i })).toBeInViewport({ ratio: 1 });
    // Mutation: stack the dropzone's icon over its text with its full padding
    // again -- the first lexicon runs past the fold, and this fails.
    for (const lexicon of await lexicons.all()) {
      await expect(lexicon).toBeInViewport({ ratio: 1 });
    }
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
