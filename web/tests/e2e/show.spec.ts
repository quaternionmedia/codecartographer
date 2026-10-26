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

/**
 * The ids of the nodes on the canvas, sorted, once they have stopped
 * arriving: a drawing streams its nodes in over animation frames, so the
 * same ids read twice 400 ms apart is a drawing that has landed.
 */
async function drawnIds(page: Page): Promise<string[]> {
  let last = '';
  let ids: string[] = [];
  await expect.poll(async () => {
    ids = await page.locator('.graphRenderer svg .graph-node[data-node-id]').evaluateAll(
      (els) => els.map((el) => el.getAttribute('data-node-id') as string).sort());
    const now = ids.join('\n');
    const still = ids.length > 0 && now === last;
    last = now;
    return still;
  }, { intervals: [400], timeout: SETTLED }).toBe(true);
  return ids;
}

/** Open a page at a family no corpus declares: the Show panel lists everything, and nothing is drawn. */
async function openOnNothing(page: Page): Promise<void> {
  await page.goto('/?show=family:nowhere');
  await dismissOnboardingModal(page);
  await expect(page.locator('.show__family').first()).toBeVisible({ timeout: SETTLED });
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

test('a drawing asked for after another is the one drawn, however late the first answers', async ({ page }) => {
  await openOnNothing(page);
  const family = (await page.locator('.show__family').first().getAttribute('data-family'))!;

  // Every family answers 1.5 s late: a cold index, which takes about 2 s.
  await page.route('**/show/index/gjgf*', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1_500));
    await route.continue();
  });
  const index = page.waitForResponse((r) => r.url().includes('/show/index/gjgf'));
  await page.locator('button.estate-view__draw', { hasText: 'draw every family' }).click();
  await page.locator(`.show__family[data-family="${family}"]`).click();
  await expect(page).toHaveURL(new RegExp(`\\?show=family:${family}$`));
  await (await index).finished();
  // Time for an answer that was not dropped to be drawn.
  await page.waitForTimeout(1_000);
  const raced = await drawnIds(page);

  await page.goto(`/?show=family:${family}`);
  const direct = await drawnIds(page);
  // Mutation: draw a show without the latest-plot ticket, and set its address
  // when it answers -- every family, answering last, is drawn over the
  // family, and this fails.
  expect(raced).toEqual(direct);
  await expect(page.locator('.show__crumb.is-current')).toHaveText(family);
});

test("a project's views are the panel's only while it is the drawing asked for", async ({ page }) => {
  await openOnNothing(page);
  const rows = page.locator('.show__project');
  const [first, second] = [
    (await rows.nth(0).getAttribute('data-project'))!,
    (await rows.nth(1).getAttribute('data-project'))!,
  ];
  // Each project's views, the first answering 1.5 s late, each saying whose they are.
  await page.route('**/show/project/*/views', async (route) => {
    const name = decodeURIComponent(route.request().url().split('/project/')[1].split('/')[0]);
    if (name === first) await new Promise((resolve) => setTimeout(resolve, 1_500));
    const closed = { available: false, problem: `${name} has no such view here`, remedy: '' };
    await route.fulfill({ json: { status: 200, message: 'stubbed', results: {
      name, estate: { available: true }, code: closed, system: closed,
    } } });
  });
  const late = page.waitForResponse((r) => r.url().includes(`/show/project/${first}/views`));
  await rows.nth(0).locator('.estate__name').click();
  await rows.nth(1).locator('.estate__name').click();
  await expect(page).toHaveURL(new RegExp(`\\?show=project:${second}$`));
  await (await late).finished();
  await page.waitForTimeout(1_000);
  // Mutation: settle a views answer whichever project is asked for since --
  // the first project's views, answering last, are shown under the second's
  // trail, and this fails.
  await expect(page.locator('.show__now')).toContainText(`${second} has no such view here`);
  await expect(page.locator('.show__now')).not.toContainText(`${first} has no such view here`);
  await expect(page.locator('.show__crumb.is-current')).toHaveText(second);
  const raced = await drawnIds(page);
  await page.goto(`/?show=project:${second}`);
  expect(raced).toEqual(await drawnIds(page));
});

/**
 * Start streaming a one-file repository whose stream the test holds open
 * until it calls the function this resolves to; the stream then answers,
 * unless the page has ended it.
 */
async function holdAStream(page: Page): Promise<() => Promise<void>> {
  await page.route('**/repo/tree?**', (route) => route.fulfill({
    json: {
      status: 200,
      message: 'stubbed',
      results: {
        info: { owner: 'example', name: 'small', url: '/work/small' },
        size: 1,
        root: { name: '', size: 0, folders: [], files: [{ name: 'a.rs', size: 1, raw: '', url: '/work/small/a.rs' }] },
        is_partial: false,
      },
    },
  }));
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  let answered!: () => void;
  const done = new Promise<void>((resolve) => { answered = resolve; });
  const frame = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  await page.route('**/parse/stream-url', async (route) => {
    await held;
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: [
        frame('meta', { nodeCount: 1, edgeCount: 0, layout: 'spring' }),
        frame('node', { id: 'dir::src', label: 'src', kind: 'directory', depth: 0, x: 0, y: 0, file: '', line: 0 }),
        frame('done', { elapsed_ms: 1 }),
      ].join(''),
    }).catch(() => undefined); // Ended by the page: there is no one to answer.
    answered();
  });
  const asked = page.waitForRequest((r) => r.url().includes('/parse/stream-url'));
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.panel-source__url-input input').fill('/work/small');
  await page.locator('.panel-source__url-input button.primary').click();
  await asked;
  await expect(page.locator('button.panel-plotbar__cancel')).toBeEnabled();
  return async () => { release(); await done; };
}

test('the Show panel opened while a repository streams draws nothing over it', async ({ page }) => {
  const asked: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/show/index/gjgf')) asked.push(request.url());
  });
  const release = await holdAStream(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Show$/ }).click();
  await expect(page.locator('.show__family').first()).toBeVisible({ timeout: SETTLED });
  await page.waitForTimeout(1_000);
  // Mutation: draw every family whenever no graph is recorded, as the panel
  // did -- a stream records its graph only when it ends, so every family is
  // drawn over it, and this fails.
  expect(asked).toEqual([]);
  await expect(page.locator('button.panel-plotbar__cancel')).toBeEnabled();
  await release();
});

test('a showgraph opened while a repository streams ends the stream', async ({ page }) => {
  const release = await holdAStream(page);
  const ended = page.waitForEvent('requestfailed', (r) => r.url().includes('/parse/stream-url'));
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Show$/ }).click();
  await page.locator('button.estate-view__draw', { hasText: 'draw every family' }).click({ timeout: SETTLED });
  // Mutation: open a showgraph without cancelling the stream -- it runs on,
  // its end records the repository as the graph drawn and gives rad its
  // renderer, one no longer on the canvas, and this fails.
  await ended;
  await expect(page.locator('button.panel-plotbar__cancel')).toBeDisabled();
  const drawn = await drawnIds(page);
  await release();
  await page.waitForTimeout(1_000);
  expect(await drawnIds(page)).toEqual(drawn);
  // The panel reads the drawing's own caveat, which the stream did not replace.
  await expect(page.locator('.show__about')).toBeVisible();
  // And the radial menu is on the canvas drawn.
  await page.locator('.graphRenderer svg').first().click({ button: 'right', position: { x: 8, y: 8 } });
  await expect(page.locator('.rad-root')).toHaveAttribute('aria-label', 'canvas');
});
