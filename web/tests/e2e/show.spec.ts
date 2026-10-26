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

/**
 * The names a map draws, how many of them are hidden until a zoom gives them
 * room, the smallest shown on screen in pixels, and each pair shown that
 * overlap.
 */
async function names(page: Page): Promise<{ drawn: number; hidden: number; count: number; smallest: number; overlaps: string[] }> {
  return page.locator('.graphRenderer svg').first().evaluate((svg) => {
    const drawn = [...svg.querySelectorAll<SVGTextElement>('.labels text')]
      .filter((t) => getComputedStyle(t).display !== 'none');
    const shown = drawn.filter((t) => t.getAttribute('visibility') !== 'hidden');
    const boxes = shown.map((t) => ({ name: t.textContent ?? '', box: t.getBoundingClientRect() }));
    const overlaps: string[] = [];
    boxes.forEach((a, i) => boxes.slice(i + 1).forEach((b) => {
      if (a.box.left < b.box.right && b.box.left < a.box.right
        && a.box.top < b.box.bottom && b.box.top < a.box.bottom) overlaps.push(`${a.name} / ${b.name}`);
    }));
    const onScreen = shown.map((t) => Number(t.getAttribute('font-size')) * (t.getScreenCTM()?.a ?? 1));
    return {
      drawn: drawn.length, hidden: drawn.length - shown.length,
      count: shown.length, smallest: Math.min(...onScreen), overlaps,
    };
  });
}

/** The ids of the nodes on the canvas now, sorted (`drawnIds` waits for them to land). */
async function idsNow(page: Page): Promise<string[]> {
  return page.locator('.graphRenderer svg .graph-node[data-node-id]').evaluateAll(
    (els) => els.map((el) => el.getAttribute('data-node-id') as string).sort());
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
  // Every family answers late, so the Show panel has read the corpus, and
  // would draw its default, before the page's own drawing is on the canvas.
  await page.route('**/show/index/gjgf*', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1_500));
    await route.continue();
  });
  await drawEveryFamily(page);
  // The fit is a transition, and the names are sorted once it settles.
  await expect.poll(async () => {
    const drawn = await names(page);
    return drawn.count > 0 && drawn.smallest >= 9.9 && drawn.overlaps.length === 0;
  }, { timeout: SETTLED }).toBe(true);
  // An overlap is removed by hiding a name, so none overlapping is no proof
  // the names are readable: here 4 of 38 are hidden at the fit.
  // Mutation: hide every name but the first -- none overlaps, and this fails.
  const drawn = await names(page);
  expect(drawn.hidden, `${drawn.hidden} of ${drawn.drawn} names hidden`).toBeLessThanOrEqual(drawn.drawn / 4);
  // The page's address and the Show panel's default both open the index at
  // boot; it is asked for once. **NOT BY `openShow`'s GUARD**, which merges
  // a second ask for a drawing still opening: `_openShow` sets the address
  // before it opens the panel, and the panel draws its default only with no
  // address, so at boot nothing asks twice. The guard is held by "a drawing
  // asked for again while it is opening is asked for once".
  // Mutation: drop both the address `_openShow` sets first and the guard --
  // the panel, its corpus read before every family answers, asks again, and
  // this fails. Either alone keeps it green.
  expect(asked).toHaveLength(1);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('every family');
});

/** Wait for a drawing other than `before` to land on the canvas, and give its ids. */
async function nextDrawing(page: Page, before: string[]): Promise<string[]> {
  await expect.poll(() => idsNow(page), { timeout: SETTLED }).not.toEqual(before);
  return drawnIds(page);
}

test('a double-click opens a family and then a project, and Back walks out again', async ({ page }) => {
  // The address and the trail are both set before any drawing is asked for,
  // so each step is held to the nodes on the canvas as well.
  await drawEveryFamily(page);
  const index = await drawnIds(page);
  const family = page.locator('.graph-node[data-node-id^="family::"]').first();
  const name = (await family.getAttribute('data-node-id'))!.slice('family::'.length);
  await family.dblclick();
  await expect(page).toHaveURL(new RegExp(`\\?show=family:${name}$`));
  await expect(page.locator('.show__crumb.is-current')).toHaveText(name);
  await expect(page.locator('a.show__crumb')).toHaveText('every family');
  const familyIds = await nextDrawing(page, index);

  // A project of that family: any public member, not a private one.
  const member = page.locator(`.graph-node[data-node-id^="repo::"]:not([data-node-id^="repo::private-"])`).first();
  await expect(member).toBeAttached({ timeout: SETTLED });
  const project = (await member.getAttribute('data-node-id'))!.slice('repo::'.length);
  await member.dblclick();
  await expect(page).toHaveURL(new RegExp(`\\?show=project:${project}$`));
  await expect(page.locator('.show__crumb.is-current')).toHaveText(project);
  await expect(page.locator('.show__view[data-view="estate"]')).toHaveClass(/is-current/);
  await nextDrawing(page, familyIds);

  // Mutation: let a popstate set the address and the trail and draw nothing
  // -- the project stays on the canvas, and this fails.
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`\\?show=family:${name}$`));
  await expect(page.locator('.show__crumb.is-current')).toHaveText(name);
  await expect.poll(() => idsNow(page), { timeout: SETTLED }).toEqual(familyIds);
  await page.goBack();
  await expect(page).toHaveURL(/\?show=index$/);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('every family');
  await expect.poll(() => idsNow(page), { timeout: SETTLED }).toEqual(index);
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
  const index = await drawnIds(page);
  const family = page.locator('.graph-node[data-node-id^="family::"]').first();
  await family.dblclick();
  await expect(page).toHaveURL(/\?show=family:/);
  await nextDrawing(page, index);
  // In this page, not by loading another: the link's address is for a new tab.
  await page.evaluate(() => { (window as unknown as { stayed: boolean }).stayed = true; });
  await page.locator('a.show__crumb', { hasText: 'every family' }).click();
  await expect(page).toHaveURL(/\?show=index$/);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('every family');
  // Mutation: let a crumb's click set the address and the trail and draw
  // nothing -- the family stays on the canvas, and this fails.
  await expect.poll(() => idsNow(page), { timeout: SETTLED }).toEqual(index);
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
 * Serve a one-file repository whose stream is held open until the test calls
 * the function this resolves to; the stream then answers, unless the page has
 * ended it.
 */
async function stubAStream(page: Page): Promise<() => Promise<void>> {
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
  return async () => { release(); await done; };
}

/** Fetch the stubbed repository from the Open panel, and wait for its stream to be asked for. */
async function fetchTheRepository(page: Page): Promise<void> {
  const asked = page.waitForRequest((r) => r.url().includes('/parse/stream-url'));
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.panel-source__url-input input').fill('/work/small');
  await page.locator('.panel-source__url-input button.primary').click();
  await asked;
}

/** Start streaming the stubbed repository on a fresh page, held open (`stubAStream`). */
async function holdAStream(page: Page): Promise<() => Promise<void>> {
  const release = await stubAStream(page);
  await page.goto('/');
  await dismissOnboardingModal(page);
  await fetchTheRepository(page);
  await expect(page.locator('button.panel-plotbar__cancel')).toBeEnabled();
  return release;
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

test('another plot drawn over a showgraph takes its address and its trail with it', async ({ page }) => {
  await drawEveryFamily(page);
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  await expect(page.locator('.graph-node[data-node-id]').first()).toBeAttached({ timeout: SETTLED });
  // Mutation: leave the address and the trail as they are when another plot
  // is drawn -- the page still says ?show=index over the demo, and this fails.
  await expect(page).not.toHaveURL(/[?&]show/);
  await expect(page.locator('.show__crumb.is-current')).toHaveCount(0);
  await expect(page.locator('.show__now')).toHaveCount(0);
});

test('a repository streamed over a showgraph takes its address with it', async ({ page }) => {
  const release = await stubAStream(page);
  await drawEveryFamily(page);
  await fetchTheRepository(page);
  await release();
  // Mutation: begin a stream without leaving the showgraph -- this fails.
  await expect(page).not.toHaveURL(/[?&]show/);
  await expect(page.locator('.show__crumb.is-current')).toHaveCount(0);
});

test('Back to an entry before any showgraph clears the trail', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  await expect(page.locator('.graph-node[data-node-id]').first()).toBeAttached({ timeout: SETTLED });
  // Opened over the demo, the panel draws nothing of its own.
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Show$/ }).click();
  const row = page.locator('.show__family').first();
  await expect(row).toBeVisible({ timeout: SETTLED });
  await expect(page).not.toHaveURL(/[?&]show/);
  await row.click();
  await expect(page).toHaveURL(/\?show=family:/);
  await expect(page.locator('.show__crumb.is-current')).toHaveCount(1);
  await drawnIds(page);

  await page.goBack();
  await expect(page).not.toHaveURL(/[?&]show/);
  // Mutation: do nothing on a popstate to an entry with no ?show -- the
  // trail still names the family, and this fails.
  await expect(page.locator('.show__crumb.is-current')).toHaveCount(0);
});

/** Answer every project's views as `views` says, in place of what this checkout can draw. */
async function stubViews(page: Page, views: (name: string) => Record<string, unknown>): Promise<void> {
  await page.route('**/show/project/*/views', (route) => {
    const name = decodeURIComponent(route.request().url().split('/project/')[1].split('/')[0]);
    return route.fulfill({ json: { status: 200, message: 'stubbed', results: { name, ...views(name) } } });
  });
}

test("a project's system view leaves the renderer as it found it for the next plot", async ({ page }) => {
  await stubViews(page, () => ({
    estate: { available: true },
    code: { available: false, problem: 'not here', remedy: '' },
    system: { available: true, components: 1 },
  }));
  // The diagram is derived from a moat clone beside the backend, which CI has
  // none of (system-monitor.spec.ts skips its moat replay there): answer the
  // derivation here, one component and no history, as /system/compose and
  // /system/events would.
  await page.route('**/system/compose?**', (route) => route.fulfill({
    json: {
      system: 'moat', commit: '0000000',
      components: [{ id: 'app', name: 'app', role: 'application', group: 'apps', version: '1', upstreams: [] }],
      edges: [],
    },
  }));
  await page.route('**/system/events?**', (route) => route.fulfill({ json: { changes: [], in_flight: [] } }));
  await page.goto('/?show=project:moat&view=system');
  await dismissOnboardingModal(page);
  await expect(page.locator('.sys-title').first()).toBeAttached({ timeout: SETTLED });

  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  // Mutation: leave the system monitor chosen after the system view -- the
  // demo is drawn as the system monitor's diagram, with no graph node, and
  // this fails.
  await expect(page.locator('.graphRenderer svg .graph-node[data-node-id]').first()).toBeAttached({ timeout: SETTLED });
  await expect(page.locator('.sys-title')).toHaveCount(0);
});

test("a code map drawn again in another layout is drawn at its own depth, under its own address", async ({ page }) => {
  await stubViews(page, () => ({
    estate: { available: true },
    code: { available: true, url: '/work/small', depth: 1 },
    system: { available: false, problem: 'not here', remedy: '' },
  }));
  const bodies: Array<Record<string, unknown>> = [];
  const frame = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  await page.route('**/parse/stream-url', (route) => {
    bodies.push(route.request().postDataJSON());
    return route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: [
        frame('meta', { nodeCount: 1, edgeCount: 0, layout: 'spring' }),
        frame('node', { id: 'dir::src', label: 'src', kind: 'directory', depth: 0, x: 0, y: 0, file: '', line: 0 }),
        frame('done', { elapsed_ms: 1 }),
      ].join(''),
    });
  });
  await page.goto('/?show=project:moat&view=code');
  await dismissOnboardingModal(page);
  await expect(page.locator('.graph-node[data-node-id="dir::src"]')).toBeAttached({ timeout: SETTLED });
  expect(bodies).toHaveLength(1);

  await page.locator('.lm_tab', { hasText: /Graph Settings/ }).click();
  const select = page.locator('.panel-settings__group', { hasText: 'Algorithm' }).locator('select');
  await select.selectOption('circular_layout');
  await expect.poll(() => bodies.length, { timeout: SETTLED }).toBe(2);
  // Mutation: store the code view's stream without its depth, so a layout
  // change streams it at the Open panel's -- the second asks for 2, and this
  // fails.
  expect(bodies.map((body) => body.depth)).toEqual([1, 1]);
  // Mutation: stream the code view as any other stream -- it leaves the
  // address it was opened at, and this fails.
  await expect(page).toHaveURL(/\?show=project:moat&view=code$/);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('moat');
});

/** The canvas's zoom transform, once it has stopped moving: the fit is a 700 ms transition. */
async function settledTransform(page: Page): Promise<{ x: number; y: number; k: number }> {
  const view = page.locator('.graphRenderer svg').first();
  let last: string | null = null;
  let now = '';
  await expect.poll(async () => {
    now = await view.evaluate((svg) => svg.querySelector('g')?.getAttribute('transform') ?? '');
    const still = now === last;
    last = now;
    return still;
  }, { intervals: [400], timeout: SETTLED }).toBe(true);
  const [x, y, k] = (/translate\(([-\d.e]+),\s*([-\d.e]+)\)\s*scale\(([-\d.e]+)\)/.exec(now) ?? []).slice(1).map(Number);
  return { x, y, k };
}

/**
 * What a map's names do wrong where they are drawn: an outline's name across
 * its rim, outline names over each other, and any name off the canvas.
 */
async function namesAsDrawn(page: Page): Promise<{ outlines: number; acrossRims: string[]; overlapping: string[]; outside: string[] }> {
  return page.locator('.graphRenderer svg').first().evaluate((svg) => {
    const canvas = svg.getBoundingClientRect();
    const shown = (t: Element) => getComputedStyle(t).display !== 'none'
      && t.getAttribute('visibility') !== 'hidden' && Number(getComputedStyle(t).opacity) > 0;
    const groups = [...svg.querySelectorAll('.compound-group')];
    const acrossRims: string[] = [];
    for (const g of groups) {
      const c = g.querySelector('circle')!.getBoundingClientRect();
      const l = g.querySelector('text')!.getBoundingClientRect();
      const [cx, cy, r] = [c.left + c.width / 2, c.top + c.height / 2, c.width / 2];
      const corners = [[l.left, l.top], [l.right, l.top], [l.left, l.bottom], [l.right, l.bottom]];
      const inside = corners.every(([x, y]) => Math.hypot(x - cx, y - cy) <= r + 0.5);
      // The box's nearest point to the centre is outside the circle.
      const near = Math.hypot(Math.max(l.left - cx, 0, cx - l.right), Math.max(l.top - cy, 0, cy - l.bottom));
      if (!inside && near < r - 0.5) acrossRims.push(g.querySelector('text')!.textContent ?? '');
    }
    const outlines = groups.map((g) => ({ name: g.querySelector('text')!.textContent ?? '', box: g.querySelector('text')!.getBoundingClientRect() }));
    const overlapping: string[] = [];
    outlines.forEach((a, i) => outlines.slice(i + 1).forEach((b) => {
      if (a.box.left < b.box.right && b.box.left < a.box.right
        && a.box.top < b.box.bottom && b.box.top < a.box.bottom) overlapping.push(`${a.name} / ${b.name}`);
    }));
    const outside = [...svg.querySelectorAll('.compound-group text, .labels text')].filter(shown)
      .filter((t) => {
        const b = t.getBoundingClientRect();
        return b.left < canvas.left - 0.5 || b.right > canvas.right + 0.5 || b.top < canvas.top - 0.5 || b.bottom > canvas.bottom + 0.5;
      })
      .map((t) => t.textContent ?? '');
    return { outlines: outlines.length, acrossRims, overlapping, outside };
  });
}

test.describe('in a small window', () => {
  test.use({ viewport: { width: 700, height: 450 } });

  test("a map's names are placed and framed at the size they are drawn, and a second fit keeps the frame", async ({ page }) => {
    await drawEveryFamily(page);
    await page.locator('.lm_tab', { hasText: 'Graph' }).first().click();
    const fitted = await settledTransform(page);
    const drawn = await namesAsDrawn(page);
    expect(drawn.outlines).toBeGreaterThan(1);
    // Mutation: place the outline names once, at the size they have at zoom 1,
    // and leave them where they are when a zoom resizes them -- each is set
    // for a name a third the size, inside its rim, and drawn across it, and
    // this fails.
    expect(drawn.acrossRims).toEqual([]);
    expect(drawn.overlapping).toEqual([]);
    expect(drawn.outside).toEqual([]);

    // Fit again, from the canvas ring: the frame it lands on is the one it left.
    const svg = page.locator('.graphRenderer svg').first();
    await svg.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
    await svg.click({ button: 'right', position: { x: 4, y: 4 } });
    const ring = page.locator('.rad-root');
    await expect(ring).toHaveAttribute('aria-label', 'canvas');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');
    await expect(ring).toHaveCount(0);
    await page.waitForTimeout(300);
    const again = await settledTransform(page);
    // Mutation: fit with the names as they are drawn now rather than sized for
    // the fit's own zoom -- the second fit measures larger names than the
    // first did, frames further out, and this fails.
    expect(Math.abs(again.k - fitted.k) / fitted.k, `zoom ${fitted.k} then ${again.k}`).toBeLessThan(0.005);
    expect(Math.abs(again.x - fitted.x), `x ${fitted.x} then ${again.x}`).toBeLessThan(2);
    expect(Math.abs(again.y - fitted.y), `y ${fitted.y} then ${again.y}`).toBeLessThan(2);
    expect(await namesAsDrawn(page)).toEqual(drawn);
  });
});

test("the panel's rows are pressed from the keyboard, and its filter and views say what they are", async ({ page }) => {
  await openOnNothing(page);
  const row = page.locator('.show__family').first();
  const family = (await row.getAttribute('data-family'))!;
  // Mutation: draw the family rows as a div with only a click handler again --
  // the row takes no focus, Enter opens nothing, and this fails.
  await row.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(new RegExp(`\\?show=family:${family}$`));

  const project = page.locator('.show__project').first();
  const name = (await project.getAttribute('data-project'))!;
  await project.locator('.estate__name').focus();
  await page.keyboard.press(' ');
  await expect(page).toHaveURL(new RegExp(`\\?show=project:${name}$`));

  // Mutation: name the filter by its placeholder alone, or leave the views
  // without aria-pressed -- this fails.
  await expect(page.getByRole('searchbox', { name: 'filter projects by name or family' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'estate', exact: true, pressed: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'code map', exact: true, pressed: false })).toBeAttached();
  await expect(page.getByRole('button', { name: 'system', exact: true, pressed: false })).toBeAttached();
});
