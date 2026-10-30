/**
 * How a map looks: the QM theme the window opens in, a map's nodes drawn at
 * `MAP_NODE_SCALE`, and a code map's names, which come in as zooming in draws
 * their nodes large enough to read.
 *
 * Every showgraph exported for the corpus's docs site is drawn this way, so a
 * page of pictures is the window as it opens. The index is drawn from the
 * pinned corpus; the code map's views and its stream are stubbed, so nothing
 * here needs the host.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal, stubWideCodeMap } from './helpers';

const SETTLED = 30_000;

/** The deep blue the QM theme draws the canvas on, and its names' light yellow. */
const QM_GROUND = 'rgb(11, 26, 61)';
const QM_NAMES = 'rgb(251, 241, 199)';

async function drawEveryFamily(page: Page): Promise<void> {
  await page.goto('/?show');
  await dismissOnboardingModal(page);
  await expect(page.locator('.compound-group circle').first()).toBeAttached({ timeout: SETTLED });
}

test('the window opens in the QM theme: a deep blue canvas, and a map named in light yellow', async ({ page }) => {
  // Mutation: open in Forest, as the window did -- the theme is not QM, and
  // this fails. Mutation: draw the canvas's names in Graph Settings' starting
  // colour as given -- they are the Terminal theme's green, and this fails.
  await drawEveryFamily(page);
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'qm');
  const ground = await page.locator('.graphRenderer > svg').first().evaluate((svg) => {
    let paper = '';
    for (let el: Element | null = svg.parentElement; el; el = el.parentElement) {
      paper = getComputedStyle(el).backgroundColor;
      if (!/rgba\(0, 0, 0, 0\)|transparent/.test(paper)) break;
    }
    return paper;
  });
  expect(ground).toBe(QM_GROUND);
  const fills = await page.locator('.graphRenderer svg .labels text').evaluateAll(
    (texts) => [...new Set(texts.map((t) => getComputedStyle(t).fill))]);
  expect(fills).toEqual([QM_NAMES]);
});

test('a map draws its nodes two and a half times the size a code graph does', async ({ page }) => {
  // The smallest node a map draws is a member at the canvas's default node
  // size, 4, drawn ten units across its middle at the map's scale. Mutation:
  // draw a map's nodes at a code graph's size -- the smallest is four, and
  // this fails.
  await drawEveryFamily(page);
  const sizes = await page.locator('.graphRenderer svg g.graph-node path').evaluateAll(
    (paths) => paths.map((p) => {
      const box = (p as SVGPathElement).getBBox();
      return Math.max(box.width, box.height);
    }));
  expect(sizes.length).toBeGreaterThan(10);
  expect(Math.min(...sizes)).toBeGreaterThanOrEqual(18);
});

test('a code map draws every node it is sent, and names none its zoom draws too small to read', async ({ page }) => {
  // Nine hundred nodes, framed whole: each file a fraction of a pixel. The
  // directories' outlines name the map; a file's name comes in once zooming in
  // draws the file large enough to be read.
  test.setTimeout(120_000);
  const count = await stubWideCodeMap(page, 30, 29);
  await page.goto('/?show=project:carlos&view=code');
  await dismissOnboardingModal(page);
  await expect(page.locator('.graphRenderer svg g.graph-node')).toHaveCount(count, { timeout: SETTLED });
  // Framed whole once the last is drawn. Mutation: name every node whose name
  // has room -- the files' names are spread over the map, and this fails.
  const view = page.locator('.graphRenderer > svg').first();
  await expect.poll(() => view.evaluate((svg) => {
    const k = (svg.querySelector('g')?.getAttribute('transform') ?? '').match(/scale\(([0-9.e-]+)\)/);
    return k ? Number(k[1]) : 1;
  }), { timeout: SETTLED }).toBeLessThan(0.1);
  await expect.poll(() => page.locator('.graphRenderer svg .labels text').evaluateAll((texts) => texts
    .filter((t) => (t.getAttribute('data-node-id') ?? '').startsWith('file::'))
    .filter((t) => getComputedStyle(t).display !== 'none' && t.getAttribute('visibility') !== 'hidden')
    .length), { timeout: SETTLED }).toBe(0);
  // Its directories are still named, by their outlines.
  await expect(page.locator('.graphRenderer svg .compound-backgrounds text', { hasText: /^d0$/ })).toHaveCount(1);
});

test("the whole corpus is the index's code view, a switch away from every family", async ({ page }) => {
  // The pinned corpus holds no code maps, so it is the index's families with
  // the caveat saying so; what is held here is the address, the route asked
  // and the way back. Mutation: ask the index's route for its code view --
  // every family is drawn again for the whole corpus, and this fails.
  const asked: string[] = [];
  page.on('request', (request) => {
    const url = request.url();
    if (url.includes('/show/corpus/gjgf') || url.includes('/show/index/gjgf')) asked.push(new URL(url).pathname);
  });
  await page.goto('/?show=index&view=code');
  await dismissOnboardingModal(page);
  await expect(page.locator('.compound-group circle').first()).toBeAttached({ timeout: SETTLED });
  expect(asked).toEqual(['/show/corpus/gjgf']);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('the whole corpus');
  const switches = page.locator('.show__now .show__view');
  await expect(switches.filter({ hasText: "with each project's code" })).toHaveAttribute('aria-pressed', 'true');
  await switches.filter({ hasText: 'every family' }).click();
  await expect(page).toHaveURL(/\?show=index$/);
  await expect.poll(() => asked[asked.length - 1]).toBe('/show/index/gjgf');
  await expect(page.locator('.show__crumb.is-current')).toHaveText('every family');
});

test("a family's code view is the family with each project's code, a switch away from the family", async ({ page }) => {
  // The corpus drawn a family at a time. Mutation: ask the family's estate
  // route for its code view -- the family is drawn with no code, and this fails.
  const asked: string[] = [];
  page.on('request', (request) => {
    const url = request.url();
    if (url.includes('/show/family/')) asked.push(new URL(url).pathname);
  });
  await page.goto('/?show=family:performing&view=code');
  await dismissOnboardingModal(page);
  await expect(page.locator('.compound-group circle').first()).toBeAttached({ timeout: SETTLED });
  expect(asked).toEqual(['/show/family/performing/code/gjgf']);
  // Mutation: give a family no switch -- its code view cannot be reached
  // from the panel, and this fails.
  const switches = page.locator('.show__now .show__view');
  await expect(switches.filter({ hasText: "with each project's code" })).toHaveAttribute('aria-pressed', 'true');
  await switches.filter({ hasText: 'the family' }).click();
  await expect(page).toHaveURL(/\?show=family:performing$/);
  await expect.poll(() => asked[asked.length - 1]).toBe('/show/family/performing/gjgf');
  await switches.filter({ hasText: "with each project's code" }).click();
  await expect(page).toHaveURL(/\?show=family:performing&view=code$/);
});

test('the whole corpus with no names draws every node and writes nothing on the canvas', async ({ page }) => {
  // The index's third view: the code view's graph, every node drawn, and no
  // node's name or outline's. Mutation: draw it as the code view is, named --
  // the families' and projects' names are written over it, and this fails.
  const nodes: Record<string, unknown> = {
    'family::core': { label: 'core', metadata: { label: 'core', kind: 'family', depth: 0, x: 0, y: 0 } },
  };
  const edges: unknown[] = [];
  for (let r = 0; r < 3; r++) {
    nodes[`repo::r${r}`] = { label: `r${r}`, metadata: { label: `r${r}`, kind: 'repository', depth: 1,
      x: 300 * r, y: 0 } };
    edges.push({ source: 'family::core', target: `repo::r${r}`, metadata: { kind: 'contains' } });
    for (let f = 0; f < 6; f++) {
      const id = `code::r${r}::file::f${f}.py`;
      nodes[id] = { label: `f${f}.py`, metadata: { label: `f${f}.py`, kind: 'file', depth: 2, code: true,
        x: 300 * r + 40 * Math.cos(f), y: 40 * Math.sin(f) } };
      edges.push({ source: `repo::r${r}`, target: id, metadata: { kind: 'contains' } });
    }
  }
  await page.route('**/show/corpus/gjgf*', (route) => route.fulfill({ json: { status: 200, results: {
    graph: { nodes, edges },
    metadata: { kind: 'show', subject: 'corpus', bases: {}, caveat: '', notes: [], provenance: {} },
  } } }));
  const written = () => page.locator('.graphRenderer svg').first().evaluate((svg) =>
    [...svg.querySelectorAll('text')].filter((t) => (t.textContent ?? '').trim()
      && getComputedStyle(t).display !== 'none' && t.getAttribute('visibility') !== 'hidden').length);

  await page.goto('/?show=index&view=full');
  await dismissOnboardingModal(page);
  await expect(page.locator('.graphRenderer svg g.graph-node')).toHaveCount(22, { timeout: SETTLED });
  await expect(page.locator('.graphRenderer svg').first()).toHaveAttribute('data-drawn', 'true', { timeout: SETTLED });
  expect(await written(), 'a name was written on the whole corpus drawn with none').toBe(0);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('every node, no names');
  await expect(page.locator('.show__now .show__view').filter({ hasText: 'every node, no names' }))
    .toHaveAttribute('aria-pressed', 'true');

  // The code view of the same graph is named.
  await page.locator('.show__now .show__view').filter({ hasText: "with each project's code" }).click();
  await expect(page).toHaveURL(/\?show=index&view=code$/);
  await expect.poll(written, { timeout: SETTLED }).toBeGreaterThan(0);
});

test("an imports view is a switch away from the index's and a family's estate, and asks its own route", async ({ page }) => {
  // What the projects import in common is read from their clones, which CI
  // has none of: each imports route is answered here with two members and a
  // module both import. Mutations: ask the estate's route for an imports
  // view, or give the index or a family no switch to one -- it cannot be
  // reached, or draws the estate -- and this fails.
  const asked: string[] = [];
  page.on('request', (request) => {
    const url = request.url();
    if (url.includes('/show/') && url.includes('/gjgf')) asked.push(new URL(url).pathname);
  });
  const nodes = {
    'family::core': { label: 'core', metadata: { label: 'core', kind: 'family', depth: 0, x: 0, y: 0 } },
    'repo::alpha': { label: 'alpha', metadata: { label: 'alpha', kind: 'repository', depth: 1, x: -60, y: 0 } },
    'repo::beta': { label: 'beta', metadata: { label: 'beta', kind: 'repository', depth: 1, x: 60, y: 0 } },
    'module::python:fastapi': { label: 'fastapi', metadata: {
      label: 'fastapi', kind: 'external_module', x: 0, y: 200 } },
  };
  const dotted = { kind: 'imports', basis: 'imported', style: 'dotted', color: '#b48ead', size: 1.25 };
  const edges = [
    { source: 'family::core', target: 'repo::alpha', metadata: { kind: 'contains' } },
    { source: 'family::core', target: 'repo::beta', metadata: { kind: 'contains' } },
    { source: 'repo::alpha', target: 'module::python:fastapi', metadata: dotted },
    { source: 'repo::beta', target: 'module::python:fastapi', metadata: dotted },
  ];
  await page.route('**/show/**/imports/gjgf*', (route) => route.fulfill({ json: { status: 200, results: {
    graph: { nodes, edges },
    metadata: { kind: 'show', subject: 'index', caveat: '', notes: [], provenance: {},
      bases: { imported: { style: 'dotted', color: '#b48ead', size: 1.25 } } },
  } } }));

  await page.goto('/?show=index&view=imports');
  await dismissOnboardingModal(page);
  await expect(page.locator('.graphRenderer svg g.graph-node')).toHaveCount(4, { timeout: SETTLED });
  expect(asked).toEqual(['/show/index/imports/gjgf']);
  await expect(page.locator('.graphRenderer svg line[stroke-dasharray="2,3"]')).toHaveCount(2);
  await expect(page.locator('.show__crumb.is-current')).toHaveText('shared imports');
  const switches = page.locator('.show__now .show__view');
  await expect(switches.filter({ hasText: 'shared imports' })).toHaveAttribute('aria-pressed', 'true');
  await switches.filter({ hasText: 'every family' }).click();
  await expect(page).toHaveURL(/\?show=index$/);
  await expect.poll(() => asked[asked.length - 1]).toBe('/show/index/gjgf');

  await page.goto('/?show=family:performing');
  await dismissOnboardingModal(page);
  await expect(page.locator('.compound-group circle').first()).toBeAttached({ timeout: SETTLED });
  await page.locator('.show__now .show__view').filter({ hasText: 'shared imports' }).click();
  await expect(page).toHaveURL(/\?show=family:performing&view=imports$/);
  await expect.poll(() => asked[asked.length - 1]).toBe('/show/family/performing/imports/gjgf');
});

test('a showgraph of thousands of nodes is drawn in seconds, not a minute', async ({ page }) => {
  // Two thousand members on a grid, answered for every family at once.
  // Mutation: hand the canvas the graph without its total -- it draws one node
  // a frame, about a minute for these, and this fails.
  const nodes: Record<string, unknown> = {};
  for (let i = 0; i < 2000; i++) {
    nodes[`repo::m${i}`] = { label: `m${i}`, metadata: { label: `m${i}`, kind: 'repository', depth: 1,
      x: (i % 50) * 80, y: Math.floor(i / 50) * 80 } };
  }
  await page.route('**/show/index/gjgf*', (route) => route.fulfill({ json: { status: 200, results: {
    graph: { nodes, edges: [] },
    metadata: { kind: 'show', subject: 'index', bases: {}, caveat: '', notes: [], provenance: {} },
  } } }));
  await page.goto('/?show');
  await dismissOnboardingModal(page);
  await expect(page.locator('.graphRenderer svg g.graph-node')).toHaveCount(2000, { timeout: 10_000 });
});

test('a map drawn already framed names none of its small nodes as its last is drawn', async ({ page }) => {
  // Two thousand files spread further than the canvas can frame, so every
  // fit lands at the zoom limit, and Read pressed while they are drawn, as
  // an export presses it: the fit after the last node changes nothing. The
  // names drawn since the last zoom ended are tidied as the last node is
  // drawn. Mutation: tidy them only when a zoom ends -- every file drawn
  // after Read is named until the last fit's transition has run, and this
  // fails.
  const nodes: Record<string, unknown> = {};
  for (let i = 0; i < 2000; i++) {
    nodes[`code::wide::file::f${i}`] = { label: `f${i}.py`, metadata: { label: `f${i}.py`, kind: 'file', depth: 3,
      code: true, x: (i % 50) * 20000, y: Math.floor(i / 50) * 20000 } };
  }
  await page.route('**/show/index/gjgf*', (route) => route.fulfill({ json: { status: 200, results: {
    graph: { nodes, edges: [] },
    metadata: { kind: 'show', subject: 'index', bases: {}, caveat: '', notes: [], provenance: {} },
  } } }));
  await page.goto('/?show');
  await dismissOnboardingModal(page);
  await expect(page.locator('.graphRenderer svg g.graph-node').first()).toBeAttached({ timeout: SETTLED });
  await page.locator('.gl-steps__step[data-step="read"]').click();
  await page.waitForFunction(
    () => document.querySelectorAll('.graphRenderer svg g.graph-node').length === 2000,
    undefined, { polling: 'raf', timeout: SETTLED });
  const named = await page.locator('.graphRenderer svg .labels text').evaluateAll((texts) => texts
    .filter((t) => getComputedStyle(t).display !== 'none' && t.getAttribute('visibility') !== 'hidden').length);
  expect(named).toBe(0);
});
