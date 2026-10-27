/**
 * A saved layout that names a window this build does not register still boots.
 *
 * The reader's arrangement is kept in localStorage under
 * `cc:gl-layout:default`. Golden Layout throws a `BindError` on a component
 * type nobody registered, so a layout naming a window this version lacks,
 * loaded unchecked, boots a page with no tabs, no canvas and an exception in
 * the console. The page drops such a layout and loads the default.
 *
 * "Save current as default" (the + menu) keeps the layout as Golden Layout
 * loads one, so the next visit opens it; one kept as Golden Layout resolves a
 * layout, as this page saved them before, is read through its conversion.
 */

import { readFileSync } from 'node:fs';

import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const KEY = 'cc:gl-layout:default';

test('a saved layout naming an unknown window is dropped, and the default loads', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));

  await page.addInitScript(({ key }) => {
    // Once per test, not on every navigation: the check below reads the key
    // back after the page has had its chance to drop it.
    if (sessionStorage.getItem('seeded')) return;
    sessionStorage.setItem('seeded', '1');
    localStorage.setItem(key, JSON.stringify({
      root: {
        type: 'row',
        content: [
          { type: 'component', componentType: 'graph', title: 'Graph', id: 'graph' },
          { type: 'component', componentType: 'a-window-nobody-registered', title: 'Gone', id: 'gone' },
        ],
      },
    }));
  }, { key: KEY });

  await page.goto('/');
  await dismissOnboardingModal(page);

  // Mutation: load the saved layout with neither the check nor the fallback --
  // Golden Layout throws, no tab is drawn, and this fails. Either one alone
  // keeps it green; tests/pure/saved-layout.test.mjs holds the check.
  await expect(page.locator('.lm_tab', { hasText: 'Graph Settings' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Load Demo/i }).first()).toBeVisible();
  expect(errors).toEqual([]);
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toBeNull();
});

test('a saved layout naming only known windows is loaded as saved', async ({ page }) => {
  await page.addInitScript(({ key }) => {
    if (sessionStorage.getItem('seeded')) return;
    sessionStorage.setItem('seeded', '1');
    localStorage.setItem(key, JSON.stringify({
      root: {
        type: 'row',
        content: [
          { type: 'component', componentType: 'graph', title: '◈ Graph', id: 'graph' },
          { type: 'component', componentType: 'estate-panel', title: '⌂ Estate', id: 'estate-panel' },
        ],
      },
    }));
  }, { key: KEY });

  await page.goto('/');
  await dismissOnboardingModal(page);

  await expect(page.locator('.lm_tab', { hasText: 'Estate' })).toBeVisible();
  // The default's other tabs are absent: this is the saved arrangement.
  await expect(page.locator('.lm_tab', { hasText: 'Graph Settings' })).toHaveCount(0);
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).not.toBeNull();
});

test('a saved layout with Upload, Repository and Actions boots with one Open window', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.addInitScript(({ key }) => {
    if (sessionStorage.getItem('seeded')) return;
    sessionStorage.setItem('seeded', '1');
    localStorage.setItem(key, JSON.stringify({
      root: {
        type: 'column',
        content: [
          { type: 'component', componentType: 'graph', title: '◈ Graph', id: 'graph' },
          {
            type: 'stack',
            content: [
              { type: 'component', componentType: 'upload-panel', title: '↑ Upload', id: 'upload-panel' },
              { type: 'component', componentType: 'repo-panel', title: '⬇ Repository', id: 'repo-panel' },
              { type: 'component', componentType: 'plotbar', title: '▶ Actions', id: 'plotbar' },
              { type: 'component', componentType: 'estate-panel', title: '⌂ Estate', id: 'estate-panel' },
            ],
          },
        ],
      },
    }));
  }, { key: KEY });

  await page.goto('/');
  await dismissOnboardingModal(page);

  // Mutation: drop the renames -- the layout is dropped for the default,
  // whose Graph Settings tab appears, and this fails.
  await expect(page.locator('.lm_tab', { hasText: 'Open' })).toHaveCount(1);
  await expect(page.locator('.lm_tab', { hasText: 'Estate' })).toHaveCount(1);
  await expect(page.locator('.lm_tab', { hasText: 'Graph Settings' })).toHaveCount(0);
  await expect(page.locator('.lm_tab', { hasText: /Upload|Repository|Actions/ })).toHaveCount(0);
  expect(errors).toEqual([]);
  // Saved back renamed, so the next boot reads it as it is.
  expect(await page.evaluate((key) => localStorage.getItem(key), KEY)).toContain('"componentType":"open"');
});

test('a saved layout holding the Show window loads it, and it draws every family onto the empty canvas', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  const asked: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/show/index/gjgf')) asked.push(request.url());
  });
  await page.addInitScript(({ key }) => {
    if (sessionStorage.getItem('seeded')) return;
    sessionStorage.setItem('seeded', '1');
    localStorage.setItem(key, JSON.stringify({
      root: {
        type: 'row',
        content: [
          { type: 'component', componentType: 'graph', title: '◈ Graph', id: 'graph' },
          { type: 'component', componentType: 'show-panel', title: '❖ Show', id: 'show-panel' },
        ],
      },
    }));
  }, { key: KEY });

  await page.goto('/');
  await dismissOnboardingModal(page);

  // Mutation: register no Show window -- the saved layout is dropped for the
  // default, which has none, and this fails.
  await expect(page.locator('.lm_tab', { hasText: 'Show' })).toHaveCount(1);
  await expect(page.locator('.lm_tab', { hasText: 'Graph Settings' })).toHaveCount(0);
  // Mounted with the dock, before the page's address is read: with nothing
  // drawn, it draws its default once, and says so in the address.
  await expect(page).toHaveURL(/\?show=index$/, { timeout: 30_000 });
  await expect(page.locator('.compound-group circle').first()).toBeAttached({ timeout: 30_000 });
  await expect(page.locator('.show__crumb.is-current')).toHaveText('every family');
  expect(asked).toHaveLength(1);
  expect(errors).toEqual([]);
});

test('a layout saved as the default is the one the next visit opens', async ({ page }) => {
  // "Save current as default" kept the layout as Golden Layout resolves it,
  // which Golden Layout refuses to load: the next visit said "the saved layout
  // was not loaded" and showed the default. Mutation: save `toConfig()` as it
  // is -- the Estate window closed here is back after the reload, and this fails.
  await page.goto('/');
  await dismissOnboardingModal(page);
  const estate = page.locator('.lm_tab', { hasText: 'Estate' });
  await expect(estate).toHaveCount(1);
  await estate.locator('.lm_close_tab').click();
  await expect(estate).toHaveCount(0);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: 'Save current as default' }).click();
  // Kept as `loadLayout` reads one, not as `toConfig` resolves it.
  const kept = await page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? 'null'), KEY);
  expect(kept, 'a layout is saved').not.toBeNull();
  expect(kept.resolved, 'saved as Golden Layout loads a layout').not.toBe(true);
  await page.reload();
  await dismissOnboardingModal(page);
  await expect(page.locator('.lm_tab', { hasText: 'Open' })).toHaveCount(1);
  await expect(estate).toHaveCount(0);
  await expect(page.locator('.cc-toast__msg', { hasText: 'was not loaded' })).toHaveCount(0);
});

test('a layout saved before, as Golden Layout resolves one, is read too', async ({ page }) => {
  // `fixtures/layout-saved-resolved.json` is what "Save current as default"
  // kept until it saved as Golden Layout loads one, with Estate closed. It is read through Golden
  // Layout's own conversion rather than dropped. Mutation: load it as it is --
  // it is refused, the default shows with Estate in it, and this fails.
  const saved = readFileSync('tests/e2e/fixtures/layout-saved-resolved.json', 'utf8');
  await page.addInitScript(({ key, layout }) => {
    if (!sessionStorage.getItem('seeded')) {
      localStorage.setItem(key, layout);
      sessionStorage.setItem('seeded', '1');
    }
  }, { key: KEY, layout: saved });
  await page.goto('/');
  await dismissOnboardingModal(page);
  await expect(page.locator('.lm_tab', { hasText: 'Open' })).toHaveCount(1);
  await expect(page.locator('.lm_tab', { hasText: 'Estate' })).toHaveCount(0);
  await expect(page.locator('.cc-toast__msg', { hasText: 'was not loaded' })).toHaveCount(0);
});
