/**
 * A saved layout that names a window this build does not register still boots.
 *
 * The reader's arrangement is kept in localStorage under
 * `cc:gl-layout:default`. Golden Layout throws a `BindError` on a component
 * type nobody registered, so a layout naming a window this version lacks,
 * loaded unchecked, boots a page with no tabs, no canvas and an exception in
 * the console. The page drops such a layout and loads the default.
 */

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
