/**
 * A showgraph is a map to move through: its names readable where the fit
 * frames it, none drawn over another, a double-click into a family or a
 * project, and Back out again.
 *
 * Drawn against the corpus the browser suite's API reads -- the governance
 * pin, which CI checks out with the submodule. What the pin holds is not
 * asserted; only what any families document draws as. The packing that makes
 * room for the names is the server's, tested in tests/test_show_router.py,
 * and the trail's wording is pure (tests/pure/show-address.test.mjs).
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;

/** The smallest name drawn on screen, in pixels, and each pair of names that overlap. */
async function names(page: Page): Promise<{ count: number; smallest: number; overlaps: string[] }> {
  return page.locator('.graphRenderer svg').first().evaluate((svg) => {
    const shown = [...svg.querySelectorAll<SVGTextElement>('.labels text')]
      .filter((t) => getComputedStyle(t).display !== 'none' && t.getAttribute('visibility') !== 'hidden');
    const boxes = shown.map((t) => ({ name: t.textContent ?? '', box: t.getBoundingClientRect() }));
    const overlaps: string[] = [];
    boxes.forEach((a, i) => boxes.slice(i + 1).forEach((b) => {
      if (a.box.left < b.box.right && b.box.left < a.box.right
        && a.box.top < b.box.bottom && b.box.top < a.box.bottom) overlaps.push(`${a.name} / ${b.name}`);
    }));
    const onScreen = shown.map((t) => Number(t.getAttribute('font-size')) * (t.getScreenCTM()?.a ?? 1));
    return { count: shown.length, smallest: Math.min(...onScreen), overlaps };
  });
}

async function drawEveryFamily(page: Page): Promise<void> {
  await page.goto('/?show');
  await dismissOnboardingModal(page);
  await expect(page).toHaveURL(/\?show=index$/);
  await expect(page.locator('.compound-group circle').first()).toBeAttached({ timeout: SETTLED });
}

test('every family opens with each name readable at the fit, and none over another', async ({ page }) => {
  const asked: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/show/index/gjgf')) asked.push(request.url());
  });
  await drawEveryFamily(page);
  // The fit is a transition, and the names are sorted once it settles.
  await expect.poll(async () => {
    const drawn = await names(page);
    return drawn.count > 0 && drawn.smallest >= 9.9 && drawn.overlaps.length === 0;
  }, { timeout: SETTLED }).toBe(true);
  // The page's address and the Show panel's default both open the index at
  // boot; it is asked for once.
  expect(asked).toHaveLength(1);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('every family');
});

test('a double-click opens a family and then a project, and Back walks out again', async ({ page }) => {
  await drawEveryFamily(page);
  const family = page.locator('.graph-node[data-node-id^="family::"]').first();
  const name = (await family.getAttribute('data-node-id'))!.slice('family::'.length);
  await family.dblclick();
  await expect(page).toHaveURL(new RegExp(`\\?show=family:${name}$`));
  await expect(page.locator('.show__crumb.is-current')).toHaveText(name);
  await expect(page.locator('a.show__crumb')).toHaveText('every family');

  // A project of that family: any public member, not a private one.
  const member = page.locator(`.graph-node[data-node-id^="repo::"]:not([data-node-id^="repo::private-"])`).first();
  await expect(member).toBeAttached({ timeout: SETTLED });
  const project = (await member.getAttribute('data-node-id'))!.slice('repo::'.length);
  await member.dblclick();
  await expect(page).toHaveURL(new RegExp(`\\?show=project:${project}$`));
  await expect(page.locator('.show__crumb.is-current')).toHaveText(project);
  await expect(page.locator('.show__view[data-view="estate"]')).toHaveClass(/is-current/);

  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`\\?show=family:${name}$`));
  await expect(page.locator('.show__crumb.is-current')).toHaveText(name);
  await page.goBack();
  await expect(page).toHaveURL(/\?show=index$/);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('every family');
});

test('a drawing asked for again while it is opening is asked for once', async ({ page }) => {
  // A family no corpus declares: the panel opens, and nothing is drawn yet.
  await page.goto('/?show=family:nowhere');
  await dismissOnboardingModal(page);
  const draw = page.locator('button.estate-view__draw', { hasText: 'draw every family' });
  await expect(draw).toBeVisible({ timeout: SETTLED });
  const asked: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/show/index/gjgf')) asked.push(request.url());
  });
  await draw.click();
  await draw.click();
  await expect(page.locator('.compound-group circle').first()).toBeAttached({ timeout: SETTLED });
  expect(asked).toHaveLength(1);
});

test('a step of the trail opens what it names', async ({ page }) => {
  await drawEveryFamily(page);
  const family = page.locator('.graph-node[data-node-id^="family::"]').first();
  await family.dblclick();
  await expect(page).toHaveURL(/\?show=family:/);
  // In this page, not by loading another: the link's address is for a new tab.
  await page.evaluate(() => { (window as unknown as { stayed: boolean }).stayed = true; });
  await page.locator('a.show__crumb', { hasText: 'every family' }).click();
  await expect(page).toHaveURL(/\?show=index$/);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('every family');
  expect(await page.evaluate(() => (window as unknown as { stayed?: boolean }).stayed)).toBe(true);
});
