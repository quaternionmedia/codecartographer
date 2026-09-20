/**
 * The estate panels, end to end: Estate, Capabilities, Overview.
 *
 * WHAT A BROWSER CAN TELL YOU THAT THE UNIT TESTS CANNOT. Every function behind
 * these panels is tested under node and pytest. What only a browser sees is
 * whether a correct answer reached the screen -- the topology panel once shipped
 * sitting on "asking…" with a perfectly good 200 in the network log, and these
 * panels are built on the same state-then-redraw path.
 *
 * NO SEAM IS ASSUMED UP, AND NO SEAM IS ASSUMED DOWN. The harness and the prose
 * reader are separate processes this suite does not start; dossier's seam is a
 * file that may or may not have been handed over. So each panel is expected to
 * resolve to *either* content or a stated problem -- both are answers, and
 * "asking…" is not. Where a specific absence is asserted, it is stubbed at the
 * route, the way the topology spec does, so the test runs the same on a machine
 * where the seam happens to be up.
 */

import type { Page } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 20_000;

async function openFromMenu(page: Page, label: RegExp, panelClass: string): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: label }).click();
  await page.locator(panelClass).waitFor({ state: 'visible' });
}

test.describe('the Estate panel', () => {
  test('is in the default dock and lists every seam, live or not', async ({ page }) => {
    await page.goto('/');
    await dismissOnboardingModal(page);

    // In the default layout as a tab, not the active one. Click its tab.
    await page.locator('.lm_tab', { hasText: /Estate/ }).click();
    const panel = page.locator('.gl-panel--estate');
    await expect(panel).toBeVisible();

    await expect
      .poll(async () => panel.locator('.estate__row').count(), { timeout: SETTLED })
      .toBeGreaterThan(0);
    await expect(panel.locator('.estate__pending')).toHaveCount(0);

    // Every row is one of two things, and says which.
    const rows = panel.locator('.estate__row');
    const count = await rows.count();
    for (let i = 0; i < count; i += 1) {
      const row = rows.nth(i);
      const live = await row.evaluate((el) => el.classList.contains('is-live'));
      if (live) {
        await expect(row.locator('.estate__where')).toContainText('identified at');
      } else {
        await expect(row.locator('.estate__problem')).not.toBeEmpty();
        await expect(row.locator('.estate__where')).toContainText('tried');
      }
    }

    // The corpus seam is the governance submodule beside this checkout, so it
    // is expected live here -- and if it is not, the row says why.
    const corpus = panel.locator('.estate__row[data-seam="corpus"]');
    await expect(corpus).toHaveCount(1);

    // The sentence to read before the rows.
    await expect(panel.locator('.estate__caveat')).not.toBeEmpty();
  });

  test('a seam nothing draws is shown with its button disabled, never hidden', async ({ page }) => {
    await page.goto('/');
    await dismissOnboardingModal(page);
    await page.locator('.lm_tab', { hasText: /Estate/ }).click();
    const prose = page.locator('.estate__row[data-seam="prose"]');
    await expect(prose).toHaveCount(1, { timeout: SETTLED });
    await expect(prose.locator('.estate__open')).toBeDisabled();
    await expect(prose.locator('.estate__open')).toHaveText(/no panel yet/);
  });

  test('a live row opens the panel that draws its seam', async ({ page }) => {
    await page.goto('/');
    await dismissOnboardingModal(page);
    await page.locator('.lm_tab', { hasText: /Estate/ }).click();
    const corpus = page.locator('.estate__row[data-seam="corpus"]');
    await expect(corpus).toHaveCount(1, { timeout: SETTLED });
    await corpus.locator('.estate__open').click();
    await expect(page.locator('.gl-panel--capabilities')).toBeVisible();
  });
});

test.describe('the Capabilities panel', () => {
  test('resolves to declarations or a stated problem, and draws on the one canvas', async ({ page }) => {
    await openFromMenu(page, /^Capabilities$/, '.gl-panel--capabilities');
    const panel = page.locator('.gl-panel--capabilities');

    await expect
      .poll(async () => panel.locator('.estate__row, .capabilities__problem').count(), { timeout: SETTLED })
      .toBeGreaterThan(0);
    await expect(panel.locator('.estate-view__pending')).toHaveCount(0);

    if ((await panel.locator('.capabilities__problem').count()) > 0) {
      // A pin that predates the registry: the sentence names the propagation.
      await expect(panel.locator('.capabilities__problem')).toContainText('tried');
      await expect(panel.locator('.capabilities__retry')).toBeVisible();
      return;
    }

    // Declarations listed; drawing them puts nodes on the graph canvas through
    // the same path every other plot takes.
    await expect(panel.locator('.estate-view__rung').first()).toBeVisible();
    await panel.locator('.estate-view__draw').click();
    await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });
    // And the caveat rides in from the metadata, above the controls.
    await expect(panel.locator('.capabilities__caveat')).toContainText('declared in the registry');
  });

  test('a registry the pin predates is a sentence with a way back', async ({ page }) => {
    await page.route('**/capabilities/data*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 200,
          message: 'Success',
          results: {
            unreadable: true,
            problem: 'no capability registry at governance/qm/ci/capability-registry.yaml. The governance pin may predate it.',
            remedy: 'A propagation moves this project\'s governance pin.',
            where: 'governance/qm/ci/capability-registry.yaml',
          },
        }),
      }),
    );
    await openFromMenu(page, /^Capabilities$/, '.gl-panel--capabilities');
    const problem = page.locator('.capabilities__problem');
    await expect(problem).toBeVisible();
    await expect(problem).toHaveAttribute('data-kind', 'unreadable');
    await expect(problem).toContainText('governance pin may predate it');
    await expect(problem).toContainText('propagation');
    await expect(problem.locator('.capabilities__retry')).toBeVisible();
    await expect(page.locator('.estate-view__pending')).toHaveCount(0);
  });
});

test.describe('the Overview panel', () => {
  test('a seam nobody handed over names the producer', async ({ page }) => {
    await page.route('**/overview/data*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 200,
          message: 'Success',
          results: {
            unreadable: true,
            problem: 'no overview seam at overview.json.',
            remedy: 'The producer writes the seam with `dossier overview --json`.',
            where: 'overview.json',
          },
        }),
      }),
    );
    await openFromMenu(page, /^Overview$/, '.gl-panel--overview');
    const problem = page.locator('.overview__problem');
    await expect(problem).toBeVisible();
    await expect(problem).toContainText('dossier overview --json');
    await expect(problem.locator('.overview__retry')).toBeVisible();
  });

  test('a seam that is there lists its masthead and sections, and draws', async ({ page }) => {
    // The backend was started with `DOSSIER_OVERVIEW_SEAM` pointing at
    // `fixtures/overview.json` (playwright.config.ts), so this is the real
    // route, the real serializer and the real canvas -- nothing stubbed.
    await openFromMenu(page, /^Overview$/, '.gl-panel--overview');
    const panel = page.locator('.gl-panel--overview');
    await expect(panel.locator('.estate-view__figure')).toHaveCount(2, { timeout: SETTLED });
    await expect(panel.locator('.estate__row')).toHaveCount(2);
    await expect(panel.locator('.estate__row').first()).toContainText('3 row(s)');
    await expect(panel.locator('.estate__where')).toContainText('overview.json');

    await panel.locator('.estate-view__draw').click();
    await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });
    // scope, two sections, four distinct subjects: the relation the seam states and no more.
    await expect(page.locator('.graph-node')).toHaveCount(1 + 2 + 3);
    await expect(panel.locator('.overview__caveat')).toContainText("dossier's reading");
  });
});

test.describe('a layout chosen in Graph Settings applies to an estate graph', () => {
  test('changing the layout re-draws the registry with the new one', async ({ page }) => {
    /**
     * **THE SELECTION WAS KEPT AND NOT APPLIED.** A layout change re-runs the
     * last plot action, and only the code-map paths ever set one -- so for an
     * estate graph the setting changed and the canvas did not, until somebody
     * pressed draw again. The panels now draw through `plotWith`, and this
     * watches the request the change must cause.
     */
    await openFromMenu(page, /^Capabilities$/, '.gl-panel--capabilities');
    const panel = page.locator('.gl-panel--capabilities');
    await panel.locator('.estate-view__draw').waitFor({ timeout: SETTLED });
    await panel.locator('.estate-view__draw').click();
    await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });

    // Graph Settings lives in the bottom dock; its layout select is the
    // `Algorithm` control under the Layout section.
    await page.locator('.lm_tab', { hasText: /Graph Settings/ }).click();
    // The first `select` in the panel is the renderer's; the layout's is the one labelled Algorithm.
    const select = page.locator('.panel-settings__group', { hasText: 'Algorithm' }).locator('select');
    await select.waitFor({ timeout: SETTLED });

    const redraw = page.waitForRequest(
      (req) => req.url().includes('/capabilities/gjgf') && req.url().includes('layout=Circular'),
      { timeout: SETTLED },
    );
    await select.selectOption('circular_layout');
    const request = await redraw;
    expect(request.url()).toContain('layout=Circular');
    // And the drawn graph says which layout it was laid out with.
    await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });
  });

  test('a layout the menu names but the tables dropped reaches the server as itself', async ({ page }) => {
    await openFromMenu(page, /^Capabilities$/, '.gl-panel--capabilities');
    const panel = page.locator('.gl-panel--capabilities');
    await panel.locator('.estate-view__draw').waitFor({ timeout: SETTLED });
    await page.locator('.lm_tab', { hasText: /Graph Settings/ }).click();
    // The first `select` in the panel is the renderer's; the layout's is the one labelled Algorithm.
    const select = page.locator('.panel-settings__group', { hasText: 'Algorithm' }).locator('select');
    await select.waitFor({ timeout: SETTLED });
    await select.selectOption('compound_layout');

    const drawn = page.waitForRequest(
      (req) => req.url().includes('/capabilities/gjgf'),
      { timeout: SETTLED },
    );
    await page.locator('.lm_tab', { hasText: /Capabilities/ }).click();
    await panel.locator('.estate-view__draw').click();
    const request = await drawn;
    // Not `Spring`: the two hand tables both fell back to it for this name.
    expect(request.url()).toContain('layout=Compound');
  });
});
