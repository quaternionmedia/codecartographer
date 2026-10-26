/**
 * The fit frames the whole graph: every node and every group outline drawn.
 *
 * fit.ts's arithmetic is tested without a browser (tests/pure/fit.test.mjs).
 * What only a browser shows is what the renderer hands it: that the group
 * outlines are drawn before the fit and framed with the nodes, after a stream
 * and on the canvas ring's Fit, and that the census's show frames the nodes it
 * selects; and that Collapse redraws the outlines around what remains, as
 * outlines-after-removal.test.mjs computes them, each label placed again
 * where it covers nothing.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal, pointOn } from './helpers';

const SETTLED = 30_000;

/** What lies outside the canvas: each node or outline whose box crosses its edge. */
async function outsideTheCanvas(page: Page, selector: string): Promise<string[]> {
  return page.locator('.graphRenderer svg').first().evaluate((svg, sel) => {
    const c = svg.getBoundingClientRect();
    return [...svg.querySelectorAll(sel)]
      .filter((el) => {
        const b = el.getBoundingClientRect();
        return b.left < c.left - 0.5 || b.right > c.right + 0.5 || b.top < c.top - 0.5 || b.bottom > c.bottom + 0.5;
      })
      .map((el) => el.closest('[data-node-id]')?.getAttribute('data-node-id') ?? el.parentElement?.getAttribute('class') ?? '?');
  }, selector);
}

/**
 * Resolve once the view's zoom transform has stopped moving, so the fit's
 * 700 ms transition has landed. A graph drawn small near the origin is in
 * view before the fit as well as after it, so polling for "in view" alone
 * passes before the fit has moved anything.
 */
async function viewSettled(page: Page): Promise<void> {
  const view = page.locator('.graphRenderer svg').first();
  let last: string | null = null;
  await expect.poll(async () => {
    const now = await view.evaluate((svg) => svg.querySelector('g')?.getAttribute('transform') ?? '');
    const still = now === last;
    last = now;
    return still;
  }, { intervals: [300], timeout: 5_000 }).toBe(true);
}

async function drawBundledExample(page: Page): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-panel--open [data-example="blinky (recorded)"]').click();
  await expect(page.locator('.graph-node[data-node-id*="region::FLASH"]')).toHaveCount(1, { timeout: SETTLED });
  await expect(page.locator('.compound-group circle').first()).toBeAttached();
}

test('after a stream, and on Fit, every node and group outline is in view', async ({ page }) => {
  await drawBundledExample(page);
  // The fit is a 700 ms transition; poll until it lands.
  // Mutation: frame the nodes without their outlines -- the directories'
  // outlines run off the canvas, and this fails.
  await expect.poll(() => outsideTheCanvas(page, '.compound-group circle'), { timeout: 5_000 }).toEqual([]);
  await expect.poll(() => outsideTheCanvas(page, '.graph-node'), { timeout: 5_000 }).toEqual([]);

  // Zoom in on a corner, so the graph runs off the canvas, then Fit.
  const svg = page.locator('.graphRenderer svg').first();
  const box = (await svg.boundingBox())!;
  const corner = { x: box.width - 30, y: 30 };
  await page.mouse.move(box.x + corner.x, box.y + corner.y);
  for (let i = 0; i < 4; i++) await page.mouse.wheel(0, -300);
  await expect.poll(() => outsideTheCanvas(page, '.graph-node').then((o) => o.length)).toBeGreaterThan(0);

  // The ring listens for keys on the canvas; focus it, as a keyboard user
  // who tabbed there would have.
  await svg.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
  await svg.click({ button: 'right', position: corner });
  const ring = page.locator('.rad-root');
  await expect(ring).toHaveAttribute('aria-label', 'canvas');
  // Fit is the canvas ring's first wedge; from no highlight ArrowRight lands on it.
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  await expect(ring).toHaveCount(0);
  await expect.poll(() => outsideTheCanvas(page, '.compound-group circle'), { timeout: 5_000 }).toEqual([]);
  await expect.poll(() => outsideTheCanvas(page, '.graph-node'), { timeout: 5_000 }).toEqual([]);
});

test("the census's show frames the nodes it selects", async ({ page }) => {
  await drawBundledExample(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Chrestomathy$/ }).click();
  const functions = page.locator('.chrestomathy__canvas tr[data-construct="callable.function"]');
  await expect(functions).toContainText('Rust', { timeout: SETTLED });

  const ids = await page.locator('.graph-node').evaluateAll((els) => els
    .filter((el) => (el as unknown as { __data__?: { construct?: string } }).__data__?.construct === 'callable.function')
    .map((el) => el.getAttribute('data-node-id') as string));
  expect(ids.length).toBeGreaterThan(1);
  const selector = ids.map((id) => `.graph-node[data-node-id=${JSON.stringify(id)}]`).join(', ');

  // Zoom in on a corner, so the functions are off the canvas.
  await page.locator('.lm_tab', { hasText: 'Graph' }).first().click();
  const svg = page.locator('.graphRenderer svg').first();
  const box = (await svg.boundingBox())!;
  await page.mouse.move(box.x + box.width - 30, box.y + 30);
  for (let i = 0; i < 4; i++) await page.mouse.wheel(0, -300);
  await expect.poll(() => outsideTheCanvas(page, selector).then((o) => o.length)).toBeGreaterThan(0);

  // Mutation: let show select without framing -- the functions stay off the
  // canvas, and this fails.
  await page.locator('.lm_tab', { hasText: 'Chrestomathy' }).click();
  await functions.locator('.cartography__show').click();
  await expect.poll(() => outsideTheCanvas(page, selector), { timeout: 5_000 }).toEqual([]);
});

/**
 * Draw a directory holding one file, streamed as the server streams a graph:
 * the directory's name is far wider than its outline, so its label cannot
 * sit inside it.
 */
async function drawWideNamedDirectory(page: Page, name: string): Promise<void> {
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
  const frame = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  await page.route('**/parse/stream-url', (route) => route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    body: [
      frame('meta', { nodeCount: 2, edgeCount: 1, layout: 'spring' }),
      frame('node', { id: 'dir::src', label: name, kind: 'directory', depth: 0, x: 0, y: 0, file: '', line: 0 }),
      frame('node', { id: 'file::src/a.rs', label: 'a.rs', kind: 'file', depth: 1, x: 60, y: 0, file: '/work/small/a.rs', line: 0 }),
      frame('edge', { source: 'dir::src', target: 'file::src/a.rs', kind: 'contains' }),
      frame('done', { elapsed_ms: 1 }),
    ].join(''),
  }));
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.panel-source__url-input input').fill('/work/small');
  await page.locator('.panel-source__url-input button.primary').click();
  await page.locator('.lm_tab', { hasText: 'Graph' }).first().click();
  await expect(page.locator('.compound-group text')).toHaveText(name, { timeout: SETTLED });
}

test("an outline's label too wide to sit inside it is set outside it, and framed with it", async ({ page }) => {
  const name = 'a_directory_whose_name_is_far_wider_than_its_outline';
  await drawWideNamedDirectory(page, name);
  await viewSettled(page);
  const drawn = await page.locator('.compound-group').evaluate((g) => {
    const c = g.querySelector('circle')!.getBoundingClientRect();
    const l = g.querySelector('text')!.getBoundingClientRect();
    return { label: { width: l.width, bottom: l.bottom }, outline: { width: c.width, top: c.top } };
  });
  expect(drawn.label.width, 'the label is wider than its outline').toBeGreaterThan(drawn.outline.width);
  // Mutation: set the label at the top inside the rim whatever its width --
  // it hangs across the rim, and this fails.
  expect(drawn.label.bottom, 'the label is set above the outline, not across its rim').toBeLessThanOrEqual(drawn.outline.top + 0.5);
  // Mutation: frame the outlines without their labels -- the label, set
  // above the outline, runs off the canvas's top, and this fails.
  expect(await outsideTheCanvas(page, '.compound-group text')).toEqual([]);
  expect(await outsideTheCanvas(page, '.compound-group circle')).toEqual([]);
});

/** Outline labels that cover another label or a node, by name. */
async function crowdedLabels(page: Page): Promise<string[]> {
  return page.locator('.graphRenderer svg').first().evaluate((svg) => {
    const hit = (a: DOMRect, b: DOMRect) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
    const labels = [...svg.querySelectorAll('.compound-group text')].map((t) => ({ name: t.textContent ?? '', box: t.getBoundingClientRect() }));
    const nodes = [...svg.querySelectorAll('.graph-node')].map((n) => n.getBoundingClientRect());
    const crowded: string[] = [];
    labels.forEach((l, i) => {
      if (labels.some((o, j) => j !== i && hit(l.box, o.box))) crowded.push(`${l.name} over a label`);
      if (nodes.some((n) => hit(l.box, n))) crowded.push(`${l.name} over a node`);
    });
    return crowded;
  });
}

test('no outline label covers another, or a node, in the bundled example or the demo', async ({ page }) => {
  await drawBundledExample(page);
  // Mutation: set every label at the top of its outline -- the nearly
  // concentric directories' labels are written over one another, and this fails.
  await expect.poll(() => crowdedLabels(page), { timeout: 5_000 }).toEqual([]);

  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  await expect(page.locator('.graph-node[data-node-id*="region::FLASH"]')).toHaveCount(0, { timeout: SETTLED });
  await expect(page.locator('.compound-group text').first()).toBeAttached({ timeout: SETTLED });
  await expect.poll(() => crowdedLabels(page), { timeout: 5_000 }).toEqual([]);
});

/**
 * Collapse the bundled example's blinky/src/main.rs from its node ring, and
 * resolve once its symbols are off the canvas.
 */
async function collapseMainRs(page: Page): Promise<void> {
  const nodes = page.locator('.graph-node');
  const drawn = await nodes.count();
  const file = page.locator('.graph-node[data-node-id^="file::"][data-node-id$="blinky/src/main.rs"]').first();
  await file.evaluate((el) => (el.closest('[tabindex]') as HTMLElement | null)?.focus());
  const at = await pointOn(file);
  await page.mouse.click(at.x, at.y, { button: 'right' });
  const ring = page.locator('.rad-root');
  await expect(ring).toHaveAttribute('aria-label', 'node');
  await expect(ring.locator('[role="menuitem"][aria-label="Collapse"]')).not.toHaveAttribute('aria-disabled', 'true');
  // Collapse is the node ring's second wedge, after Expand.
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  await expect(ring).toHaveCount(0);
  await expect.poll(() => nodes.count()).toBeLessThan(drawn);
}

test("Collapse takes a file's outline away with its symbols", async ({ page }) => {
  await drawBundledExample(page);
  const outline = page.locator('.compound-group', { hasText: /^main\.rs$/ });
  await expect(outline).toHaveCount(1);
  await collapseMainRs(page);
  // Mutation: leave the outlines as drawn after a removal -- main.rs keeps
  // its outline around nothing, and this fails.
  await expect(outline).toHaveCount(0);
});

test('after a Collapse, no outline label covers another, or a node', async ({ page }) => {
  await drawBundledExample(page);
  await expect.poll(() => crowdedLabels(page), { timeout: 5_000 }).toEqual([]);
  await collapseMainRs(page);
  await expect(page.locator('.compound-group', { hasText: /^main\.rs$/ })).toHaveCount(0);
  // Mutation: place the labels on a fresh drawing only -- the redraw after
  // the removal sets each at the top of its outline, the nearly concentric
  // directories' labels are written over one another, and this fails.
  await expect.poll(() => crowdedLabels(page), { timeout: 5_000 }).toEqual([]);
});
