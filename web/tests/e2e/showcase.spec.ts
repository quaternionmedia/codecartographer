/**
 * The Showcase: a layout chosen in Graph Settings, with its settings beneath
 * it, that draws every node a dot and the links between them in their own
 * colours -- calls, uses and flows on, a file's imports off -- and no line
 * that only says what holds what.
 *
 * The parse is stubbed: a directory holding a file, its functions and their
 * variables, a module imported from outside, and one link of each kind. The
 * dots' sizes, the layout's name the window asks for, and what a setting
 * changes in place or asks for again are what is held here.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;

const frame = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;

/** What the server streams for a small package laid out as a Showcase. */
function showcaseStream(): string {
  const node = (id: string, kind: string, depth: number, x: number, y: number, extra: object = {}) =>
    frame('node', { id, label: id.split(/[:./]/).pop(), kind, depth, x, y, file: '', line: 0, ...extra });
  const edge = (source: string, target: string, kind: string) => frame('edge', { source, target, kind });
  return [
    frame('meta', { nodeCount: 8, edgeCount: 11, layout: 'Showcase(dot=2,gap=0.5,nest=true,sized=true)' }),
    node('dir::pkg', 'directory', 0, 0, 0),
    node('file::pkg/a.py', 'file', 1, 20, 0),
    node('external::os', 'external_module', 1, -40, 0),
    node('a.run', 'function', 2, 26, 0, { dot_scale: 2.5 }),
    node('a.helper', 'function', 2, 20, 6, { color: '#00ff41' }),
    node('a.total', 'name', 3, 14, 0),
    node('a.step', 'argument', 3, 20, -6),
    node('a.LIMIT', 'constant', 3, 26, 6),
    edge('dir::pkg', 'file::pkg/a.py', 'contains'),
    edge('file::pkg/a.py', 'a.run', 'contains'),
    edge('file::pkg/a.py', 'a.helper', 'contains'),
    edge('file::pkg/a.py', 'a.LIMIT', 'contains'),
    edge('a.run', 'a.total', 'contains'),
    edge('a.run', 'a.step', 'contains'),
    edge('a.run', 'a.helper', 'calls'),
    edge('a.run', 'a.LIMIT', 'uses'),
    edge('a.step', 'a.total', 'flows'),
    edge('a.LIMIT', 'a.total', 'flows'),
    edge('file::pkg/a.py', 'external::os', 'depends_on'),
    frame('done', { elapsed_ms: 1 }),
  ].join('');
}

/** Choose the Showcase, plot the stubbed package, and return the layouts the window asked for. */
async function drawShowcase(page: Page): Promise<string[]> {
  const asked: string[] = [];
  await page.route('**/repo/tree?**', (route) => route.fulfill({
    json: {
      status: 200,
      message: 'stubbed',
      results: {
        info: { owner: 'example', name: 'pkg', url: '/work/pkg' },
        size: 1,
        root: { name: '', size: 0, folders: [], files: [{ name: 'a.py', size: 1, raw: '', url: '/work/pkg/a.py' }] },
        is_partial: false,
      },
    },
  }));
  await page.route('**/parse/stream-url', (route) => {
    asked.push(String(route.request().postDataJSON()?.layout));
    return route.fulfill({ status: 200, contentType: 'text/event-stream', body: showcaseStream() });
  });
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Graph Settings' }).click();
  await page.locator('select', { has: page.locator('option[value=showcase_layout]') }).selectOption('showcase_layout');
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.panel-source__url-input input').fill('/work/pkg');
  await page.locator('.panel-source__url-input button.primary').click();
  await expect(page.locator('.graphRenderer svg g.graph-node')).toHaveCount(8, { timeout: SETTLED });
  await expect(page.locator('.graphRenderer svg line[data-kind]')).toHaveCount(5);
  return asked;
}

const toggle = (page: Page, label: string) =>
  page.locator('label.panel-settings__toggle', { has: page.locator(`input[aria-label="${label}"]`) });

test('the Showcase is a layout in Graph Settings, its settings shown beneath it while it is chosen', async ({ page }) => {
  // Mutation: show the Showcase's settings with no layout chosen -- and this
  // fails. Mutation: show none -- and this fails.
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Graph Settings' }).click();
  const settings = page.locator('.panel-settings__showcase');
  const layout = page.locator('select', { has: page.locator('option[value=showcase_layout]') });
  await layout.selectOption('map_layout');
  await expect(settings).toHaveCount(0);
  await layout.selectOption('showcase_layout');
  await expect(settings).toBeVisible();
  for (const label of ['Dot Size', 'Dot Spacing', 'Link Opacity']) {
    await expect(settings.locator(`input[type=range][aria-label="${label}"]`)).toHaveCount(1);
  }
  for (const label of ['Cluster by Symbol', 'Size by Code', 'Links: calls', 'Links: uses', 'Links: flows',
    'Links: imports', 'Dot Names']) {
    await expect(settings.locator(`input[type=checkbox][aria-label="${label}"]`)).toHaveCount(1);
  }
  await expect(settings.locator('input[aria-label="Links: imports"]')).not.toBeChecked();
});

test('a Showcase draws every node a dot, borderless, and asks the server for it by its settings', async ({ page }) => {
  const asked = await drawShowcase(page);
  // Mutation: ask for the Showcase by its bare name -- the server lays it out
  // at its defaults whatever is set, and this fails.
  expect(asked).toEqual(['Showcase(dot=2,gap=0.5,nest=true,sized=true)']);
  const dots = await page.locator('.graphRenderer svg g.graph-node').evaluateAll((groups) => groups.map((g) => {
    const path = g.querySelector('path')!;
    const box = (path as SVGPathElement).getBBox();
    return { id: g.getAttribute('data-node-id'), d: path.getAttribute('d') ?? '',
      across: Math.max(box.width, box.height), border: path.getAttribute('stroke-width'),
      fill: path.getAttribute('fill'), opacity: path.getAttribute('fill-opacity') };
  }));
  // A dot whatever its kind: a circle, its size by its depth (`DOT_SCALE`).
  // Mutation: draw a file as a Map does -- it is a square, and this fails.
  const across = Object.fromEntries(dots.map((d) => [d.id, d.across]));
  for (const d of dots) expect(d.d, `${d.id} is a circle`).toMatch(/^M \S+ 0 A /);
  expect(across['dir::pkg']).toBeCloseTo(8, 1);
  expect(across['file::pkg/a.py']).toBeCloseTo(6, 1);
  // A dot the server sized by its source is drawn at that size (`dot_scale`).
  // Mutation: draw it by its depth -- a member's four, and this fails.
  expect(across['a.run']).toBeCloseTo(10, 1);
  expect(across['a.total']).toBeCloseTo(4, 1);
  // A little see-through, and the parse's neon green muted. Mutation: draw
  // the dots opaque, or the green as given -- and this fails.
  expect(new Set(dots.map((d) => d.opacity))).toEqual(new Set(['0.85']));
  expect(dots.find((d) => d.id === 'a.helper')?.fill).toBe('#31d85b');
  // No border: a white one a unit wide is a ring round a dot two across. The
  // ring paints each node's view state after every verb, so one is taken:
  // Fit, from the canvas's ring. Mutation: clear a node's border when the
  // view state is painted, as it was -- SVG draws its default, and this fails.
  const svg = (await page.locator('.graphRenderer svg').first().boundingBox())!;
  await page.mouse.click(svg.x + 20, svg.y + 20, { button: 'right' });
  const ring = page.locator('.rad-root');
  await expect(ring).toHaveAttribute('aria-label', 'canvas');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  await expect(ring).toHaveCount(0);
  const borders = await page.locator('.graphRenderer svg g.graph-node path').evaluateAll(
    (paths) => paths.map((p) => p.getAttribute('stroke-width')));
  expect(new Set(borders)).toEqual(new Set(['0']));
});

test("a Showcase draws each link in its kind's colour, a file's imports hidden, and nothing that only holds", async ({ page }) => {
  await drawShowcase(page);
  const lines = await page.locator('.graphRenderer svg line.stream-edge').evaluateAll((all) => all.map((l) => ({
    from: l.getAttribute('data-from'), to: l.getAttribute('data-to'), kind: l.getAttribute('data-kind'),
    colour: l.getAttribute('stroke'), shown: getComputedStyle(l).display !== 'none',
    opacity: l.getAttribute('stroke-opacity'),
  })));
  // Mutation: draw the holding edges as a Map does -- five more lines, and
  // this fails.
  expect(lines.map((l) => l.kind).sort()).toEqual(['calls', 'flows', 'flows', 'imports', 'uses']);
  const colourOf = Object.fromEntries(lines.map((l) => [l.kind, l.colour]));
  expect(colourOf).toEqual({ calls: '#f2aa4c', uses: '#74a8f6', flows: '#43c6bf', imports: '#9aa3b5' });
  expect(new Set(lines.map((l) => l.opacity))).toEqual(new Set(['0.25']));
  // Mutation: draw the imports at first -- and this fails.
  expect(lines.filter((l) => l.shown).map((l) => l.kind).sort()).toEqual(['calls', 'flows', 'flows', 'uses']);
});

test('a link toggled is hidden without asking the server; a dot size asks it for the layout again', async ({ page }) => {
  const asked = await drawShowcase(page);
  await page.locator('.lm_tab', { hasText: 'Graph Settings' }).click();
  // Each kind's lines, once all are drawn, and how many of them are shown: a
  // setting changed draws the graph again, and a count taken before its
  // lines are back says nothing.
  const lines = (kind: string) => page.locator(`.graphRenderer svg line[data-kind="${kind}"]`)
    .evaluateAll((all) => `${all.filter((l) => getComputedStyle(l).display !== 'none').length} of ${all.length}`);
  // Mutation: lay the graph out again for a link toggled -- it is asked for
  // twice, and this fails. Mutation: draw a link's line whether or not it
  // is toggled on -- the uses stay, and this fails.
  await toggle(page, 'Links: uses').click();
  await expect.poll(() => lines('uses')).toBe('0 of 1');
  await expect.poll(() => lines('flows')).toBe('2 of 2');
  expect(asked).toHaveLength(1);
  // Two settings changed before the panel is drawn again -- as when a large
  // graph's drawing holds the page -- both hold: the imports turned on, and
  // a dot size the server lays the graph out again for. Mutation: send the
  // panel's whole settings with each change, as it did -- the second sends
  // the imports back off, and this fails. Mutation: draw a dot size in place
  // -- nothing is asked, and this fails.
  await page.evaluate(() => {
    const imports = document.querySelector<HTMLInputElement>('input[aria-label="Links: imports"]')!;
    imports.checked = true;
    imports.dispatchEvent(new Event('change', { bubbles: true }));
    const dot = document.querySelector<HTMLInputElement>('input[type=range][aria-label="Dot Size"]')!;
    dot.value = '3';
    dot.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await expect.poll(() => asked.length, { timeout: SETTLED }).toBe(2);
  expect(asked[1]).toBe('Showcase(dot=3,gap=0.5,nest=true,sized=true)');
  await expect.poll(() => lines('imports'), { timeout: SETTLED }).toBe('1 of 1');
  await expect.poll(() => lines('uses')).toBe('0 of 1');
});
