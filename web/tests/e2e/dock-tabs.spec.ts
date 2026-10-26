/**
 * A dock tab's title ends before its ✕, and its ✕ before the header's controls.
 *
 * Golden Layout draws a tab's ✕ absolutely, at the tab's right edge, and keeps
 * it clear of the title with the tab's right padding. A theme that narrows that
 * padding runs every title under its ✕ ("Grap✕"). The first test opens every
 * window, one at a time so each is the active tab in its strip once, and
 * measures every tab in every strip.
 *
 * The strip ends where the header's controls begin, and a tab past that edge
 * has its ✕ under them, where a click reaches the control instead. The second
 * test narrows a stack of many tabs and a stack of one, and asks of every ✕
 * that it is left of the controls and is what a pointer at it reaches.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

interface TabGap {
  title: string;
  gap: number;
  /** The title runs onto a second line, which a tab squeezed narrower than it does. */
  wrapped: boolean;
}

/**
 * Each tab in a strip that shows a ✕: its title, and the ✕'s left edge less
 * the title's right edge.
 *
 * **A TAB THAT CANNOT BE CLOSED IS PASSED OVER.** Golden Layout removes an
 * unclosable tab's ✕, and a hidden one measures at the page's left edge, so
 * either would read as a ✕ far inside its title. Mutation: make Topology
 * `isClosable: false` in `panel_registry.ts` and read every tab -- reading its
 * missing ✕ throws.
 */
async function tabGaps(page: Page): Promise<TabGap[]> {
  return page.locator('.lm_tabs > .lm_tab').evaluateAll((tabs) =>
    tabs.flatMap((tab) => {
      const title = tab.querySelector('.lm_title') as HTMLElement;
      const close = tab.querySelector<HTMLElement>('.lm_close_tab');
      if (!close || getComputedStyle(close).display === 'none') return [];
      const box = title.getBoundingClientRect();
      return [{
        title: title.textContent ?? '',
        gap: close.getBoundingClientRect().left - box.right,
        wrapped: box.height > 1.5 * parseFloat(getComputedStyle(title).fontSize),
      }];
    }),
  );
}

/**
 * Open every window the + menu offers, until it says none is left, with one
 * click on + each time, and call `opened` after each.
 *
 * Mutation: drop the disarm from `add_panel_menu.ts`'s `onremove` -- the
 * item's click leaves the outside-click listener armed, it closes the next
 * menu as it opens, and this waits for a menu that never shows.
 */
async function openEveryWindow(page: Page, opened: () => Promise<void>): Promise<void> {
  for (;;) {
    await page.locator('.gl-app-header__add-btn').click();
    const menu = page.locator('.gl-add-panel-menu');
    await expect(menu).toBeVisible();
    if (await menu.locator('.gl-add-panel-menu__empty').count()) {
      await page.keyboard.press('Escape');
      await expect(menu).toBeHidden();
      return;
    }
    await menu.locator('.gl-add-panel-menu__item').first().click();
    await opened();
  }
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
  await openEveryWindow(page, measure);

  // Mutation: narrow the tab's right padding back to the left padding's 10px
  // -- the ✕ starts 7px inside every title, and this fails.
  const overlapping = [...measured].filter(([, gap]) => gap < 0);
  expect(overlapping, 'tabs whose ✕ starts inside the title').toEqual([]);
});

interface Clearance {
  title: string;
  /** The header controls' left edge less the ✕'s right edge. */
  clear: number;
  /** Whether a pointer at the ✕'s centre reaches the ✕. */
  reached: boolean;
}

/** Each tab in a strip that shows a ✕, against its header's controls. */
async function controlClearances(page: Page): Promise<Clearance[]> {
  return page.locator('.lm_header').evaluateAll((headers) =>
    headers.flatMap((header) => {
      const controls = header.querySelector<HTMLElement>('.lm_controls');
      const edge = controls && controls.offsetWidth > 0
        ? controls.getBoundingClientRect().left
        : Infinity;
      return [...header.querySelectorAll<HTMLElement>('.lm_tabs > .lm_tab')].flatMap((tab) => {
        const close = tab.querySelector<HTMLElement>('.lm_close_tab');
        if (!close || getComputedStyle(close).display === 'none') return [];
        const box = close.getBoundingClientRect();
        const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
        return [{
          title: tab.querySelector('.lm_title')?.textContent ?? '',
          clear: edge - box.right,
          reached: hit === close,
        }];
      });
    }),
  );
}

/** Drag the splitter between the Files stack and the one beside it to `x`. */
async function dragSplitterTo(page: Page, x: number): Promise<void> {
  const at = await page.locator('.lm_splitter').evaluateAll((splitters) => {
    const upright = splitters.map((s) => s.getBoundingClientRect()).find((r) => r.height > r.width);
    return upright ? { x: upright.left + upright.width / 2, y: upright.top + upright.height / 2 } : null;
  });
  expect(at, 'the bottom row has an upright splitter').not.toBeNull();
  await page.mouse.move(at!.x, at!.y);
  await page.mouse.down();
  await page.mouse.move(x, at!.y, { steps: 20 });
  await page.mouse.up();
  await page.evaluate(() => new Promise<void>((resolve) =>
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
}

test("every tab's ✕ is clear of its header's controls, in a narrow stack too", async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await expect(page.locator('.lm_tabs > .lm_tab').first()).toBeVisible();
  await openEveryWindow(page, async () => {});

  // A tab squeezed to fit the strip wraps its title or runs it under its ✕,
  // so each state is also read for those.
  const covered: string[] = [];
  const check = async (state: string): Promise<void> => {
    for (const { title, clear, reached } of await controlClearances(page)) {
      if (clear < 0 || !reached) covered.push(`${state}: ${title}'s ✕ (${Math.round(clear)}px clear)`);
    }
    for (const { title, gap, wrapped } of await tabGaps(page)) {
      if (gap < 0) covered.push(`${state}: ${title}'s title (${Math.round(gap)}px clear)`);
      if (wrapped) covered.push(`${state}: ${title}'s title wraps`);
    }
  };
  await check('every window open');
  // Mutation: drop `flex-shrink: 0` from a tab in the strip -- without the
  // strip's width limit, the stack beside Files, 720px wide, keeps a sixth tab
  // that does not fit and its ✕ runs under the header's dropdown; with it, the
  // strip squeezes every tab and their titles wrap.
  await dragSplitterTo(page, 558);
  await check('the stack beside Files narrowed');
  // Mutation: drop the shrink from a tab alone in its strip -- the Files tab,
  // wider than what its 100px stack leaves beside the controls, runs its ✕
  // under them.
  await dragSplitterTo(page, 102);
  await check('the Files stack narrowed');

  expect(covered, "a ✕ under its header's controls, or a title squeezed").toEqual([]);
});
