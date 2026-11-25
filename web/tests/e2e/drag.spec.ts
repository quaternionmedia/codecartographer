/**
 * A dragged node takes its edges and its label with it, whatever its id holds.
 *
 * A symbol's id carries its file's key, and a local repository on Windows
 * keys a file by a path with backslashes in it. An id is data, so the canvas
 * escapes it before it goes into a selector, where a backslash begins an
 * escape and a quote ends the string. What is read here compares attributes
 * and builds no selector, so the test does not share the renderer's way.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal, pointOn } from './helpers';

const SETTLED = 30_000;

const FILE = 'file::src/a.lean';
const THEOREM = String.raw`lean::C:\work\small\src\a.lean::theorem::t::1`;
const DEF = String.raw`lean::C:\work\small\src\a.lean::def::d "quoted"::2`;

async function drawSmallMap(page: Page): Promise<void> {
  await page.route('**/repo/tree?**', (route) => route.fulfill({
    json: {
      status: 200,
      message: 'stubbed',
      results: {
        info: { owner: 'example', name: 'small', url: '/work/small' },
        size: 1,
        root: { name: '', size: 0, folders: [], files: [{ name: 'a.lean', size: 1, raw: '', url: '/work/small/a.lean' }] },
        is_partial: false,
      },
    },
  }));
  const frame = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  const symbol = { depth: 2, file: String.raw`C:\work\small\src\a.lean`, language: 'lean' };
  await page.route('**/parse/stream-url', (route) => route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    body: [
      frame('meta', { nodeCount: 3, edgeCount: 3, layout: 'spring' }),
      frame('node', { id: FILE, label: 'a.lean', kind: 'file', depth: 1, x: 0, y: 0, file: '/work/small/a.lean', line: 0 }),
      frame('node', { ...symbol, id: THEOREM, label: 't', kind: 'theorem', x: 120, y: -60, line: 1 }),
      frame('node', { ...symbol, id: DEF, label: 'd', kind: 'def', x: 120, y: 60, line: 2 }),
      frame('edge', { source: FILE, target: THEOREM, kind: 'contains' }),
      frame('edge', { source: FILE, target: DEF, kind: 'contains' }),
      frame('edge', { source: THEOREM, target: DEF, kind: 'uses' }),
      frame('done', { elapsed_ms: 1 }),
    ].join(''),
  }));
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.panel-source__url-input input').fill('/work/small');
  await page.locator('.panel-source__url-input button.primary').click();
  await page.locator('.lm_tab', { hasText: 'Graph' }).first().click();
  await expect(page.locator('line.stream-edge')).toHaveCount(3, { timeout: SETTLED });
}

/** Where the canvas says *id* is, where each edge end at it is, and where its label is. */
async function drawnAt(page: Page, id: string) {
  return page.locator('.graphRenderer svg').first().evaluate((svg, nodeId) => {
    const node = [...svg.querySelectorAll('g.graph-node')].find((g) => g.getAttribute('data-node-id') === nodeId)!;
    const [x, y] = /translate\(([^,]+),([^)]+)\)/.exec(node.getAttribute('transform') ?? '')!.slice(1).map(Number);
    const ends: Array<[number, number]> = [];
    for (const line of svg.querySelectorAll('line.stream-edge')) {
      if (line.getAttribute('data-from') === nodeId) ends.push([Number(line.getAttribute('x1')), Number(line.getAttribute('y1'))]);
      if (line.getAttribute('data-to') === nodeId) ends.push([Number(line.getAttribute('x2')), Number(line.getAttribute('y2'))]);
    }
    const label = [...svg.querySelectorAll('g.labels text')].find((t) => t.getAttribute('data-node-id') === nodeId);
    return { x, y, ends, labelX: label ? Number(label.getAttribute('x')) : null };
  }, id);
}

async function drag(page: Page, id: string, dx: number, dy: number): Promise<void> {
  const index = await page.locator('g.graph-node').evaluateAll(
    (nodes, nodeId) => nodes.findIndex((g) => g.getAttribute('data-node-id') === nodeId), id);
  const from = await pointOn(page.locator('g.graph-node').nth(index));
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(from.x + dx, from.y + dy, { steps: 8 });
  await page.mouse.up();
}

for (const [name, id] of [['a backslash', THEOREM], ['a quote', DEF]] as const) {
  test(`a dragged node whose id holds ${name} takes its edges and its label with it`, async ({ page }) => {
    await drawSmallMap(page);
    const before = await drawnAt(page, id);
    expect(before.ends, 'both of its edges are drawn').toHaveLength(2);
    await drag(page, id, 70, 45);
    const after = await drawnAt(page, id);
    expect(Math.hypot(after.x - before.x, after.y - before.y), 'the node moved').toBeGreaterThan(5);
    // Mutation: write the id into the selector as it comes -- no edge and no
    // label is matched, each stays where it was drawn, and both of these fail.
    for (const [x, y] of after.ends) {
      expect(x).toBeCloseTo(after.x, 3);
      expect(y).toBeCloseTo(after.y, 3);
    }
    expect(after.labelX! - before.labelX!, 'the label moved as far').toBeCloseTo(after.x - before.x, 3);
  });
}

test('a dragged file takes its symbols, and their edges, with it', async ({ page }) => {
  await drawSmallMap(page);
  const before = await drawnAt(page, THEOREM);
  await drag(page, FILE, -60, 40);
  const after = await drawnAt(page, THEOREM);
  expect(Math.hypot(after.x - before.x, after.y - before.y), 'the symbol moved with its file').toBeGreaterThan(5);
  for (const [x, y] of after.ends) {
    expect(x).toBeCloseTo(after.x, 3);
    expect(y).toBeCloseTo(after.y, 3);
  }
});
