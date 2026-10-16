/**
 * A dock tab's title ends before its ✕.
 *
 * Golden Layout draws a tab's ✕ absolutely, at the tab's right edge, and keeps
 * it clear of the title with the tab's right padding. A theme that narrows that
 * padding runs every title under its ✕ ("Grap✕"). This opens every window, one
 * at a time so each is the active tab in its strip once, and measures every
 * tab in every strip.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

interface TabGap {
  title: string;
  gap: number;
}

/** Each tab in a strip: its title, and the ✕'s left edge less the title's right edge. */
async function tabGaps(page: Page): Promise<TabGap[]> {
  return page.locator('.lm_tabs > .lm_tab').evaluateAll((tabs) =>
    tabs.map((tab) => {
      const title = tab.querySelector('.lm_title') as HTMLElement;
      const close = tab.querySelector('.lm_close_tab') as HTMLElement;
      return {
        title: title.textContent ?? '',
        gap: close.getBoundingClientRect().left - title.getBoundingClientRect().right,
      };
    }),
  );
}

test("every tab's title ends before its ✕", async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await expect(page.locator('.lm_tabs > .lm_tab').first()).toBeVisible();

  const measured = new Map<string, number>();
  const measure = async (): Promise<void> => {
    for (const { title, gap } of await tabGaps(page)) {
      measured.set(title, Math.min(gap, measured.get(title) ?? Infinity));
    }
  };
  await measure();

  // Open every window the + menu offers, until it says none is left.
  for (;;) {
    // Choosing a window leaves the menu's outside-click listener armed, and it
    // closes the next menu the + opens; a click on the title spends it first.
    await page.locator('.gl-app-header__title').click();
    await page.locator('.gl-app-header__add-btn').click();
    const menu = page.locator('.gl-add-panel-menu');
    await expect(menu).toBeVisible();
    if (await menu.locator('.gl-add-panel-menu__empty').count()) {
      await page.keyboard.press('Escape');
      break;
    }
    await menu.locator('.gl-add-panel-menu__item').first().click();
    await measure();
  }

  // Mutation: narrow the tab's right padding back to the left padding's 10px
  // -- the ✕ starts 7px inside every title, and this fails.
  const overlapping = [...measured].filter(([, gap]) => gap < 0);
  expect(overlapping, 'tabs whose ✕ starts inside the title').toEqual([]);
});
