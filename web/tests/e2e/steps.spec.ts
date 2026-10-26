/**
 * The four steps from opening source to reading its graph.
 *
 * The header's rail numbers them -- 1 Open, 2 Browse, 3 Tune, 4 Read -- fills
 * the one the reader is on and says what comes next, and the walkthrough card
 * is a page per step. Entering a step brings its windows forward and leaves
 * the canvas in view; step 4 maximises the canvas and hides every other
 * window, and the canvas alone is Read however it was maximised. A step that
 * resizes the canvas frames the drawing in it. A window the reader chooses
 * says which step they are on; a window that comes forward by itself does
 * not. `web/src/layout/steps.ts` decides what each step owns and brings
 * forward, and `tests/pure/steps.test.mjs` asserts it without a browser; this
 * sees it in one.
 */

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;

test.use({ viewport: { width: 1600, height: 1000 } });

const rail = (page: Page) => page.locator('nav.gl-steps');
const step = (page: Page, label: string) => rail(page).locator('.gl-steps__step', { hasText: label });
const current = (page: Page) => rail(page).locator('[aria-current="step"]');
const next = (page: Page) => rail(page).locator('.gl-steps__next');
const card = (page: Page) => page.locator('.cc-modal');

/**
 * The windows a reader can see, each by its panel's class (`open`,
 * `file-tree`, `controls-graph-settings`, ...): a window counts when a pointer
 * at its centre reaches it.
 *
 * **NOT `toBeVisible`.** Golden Layout maximises a stack by laying it over the
 * others, which keep their size and their place underneath, so a window step 4
 * hid is still visible to Playwright. Hit-testing is what a reader's eye does.
 */
async function windowsInView(page: Page): Promise<string[]> {
  return page.locator('.gl-panel').evaluateAll((panels) =>
    panels.flatMap((el) => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return [];
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      if (!hit || !el.contains(hit)) return [];
      const name = [...el.classList].filter((c) => c.startsWith('gl-panel--') && c !== 'gl-panel--controls').pop();
      return name ? [name.slice('gl-panel--'.length)] : [];
    }).sort());
}

/** The title of the tab in front of each stack, under the card where one is open. */
async function frontTabs(page: Page): Promise<string[]> {
  return page.locator('.lm_tab.lm_active').allTextContents();
}

/** The canvas's svg; its first group is the drawing, which the zoom moves. */
const canvas = (page: Page) => page.locator('.graphRenderer > svg');

/**
 * "framed" when the drawing is centred on the canvas and fills it on its
 * tighter side, as a fit leaves it; otherwise where it is, in fractions of
 * the canvas. The drawing is the zoomed group -- nodes, labels and group
 * outlines, which are what a fit frames. The canvas is the svg's container,
 * the space the reader sees: the svg is sized in pixels, and keeps the size
 * it had until the renderer hears of a new one.
 */
async function framing(page: Page): Promise<string> {
  return canvas(page).evaluate((svg) => {
    const c = svg.parentElement!.getBoundingClientRect();
    const g = svg.querySelector(':scope > g')!.getBoundingClientRect();
    const x = (g.left + g.width / 2 - c.left) / c.width;
    const y = (g.top + g.height / 2 - c.top) / c.height;
    const w = g.width / c.width;
    const h = g.height / c.height;
    const fills = Math.max(w, h);
    if (Math.abs(x - 0.5) <= 0.03 && Math.abs(y - 0.5) <= 0.03 && fills >= 0.9 && fills <= 1.01) return 'framed';
    const at = (v: number) => v.toFixed(2);
    return `centred at (${at(x)}, ${at(y)}), ${at(w)} × ${at(h)} of the canvas`;
  });
}

/** The zoom on the canvas, as its drawing's transform attribute. */
async function zoomOf(page: Page): Promise<string | null> {
  return canvas(page).evaluate((svg) => svg.querySelector(':scope > g')!.getAttribute('transform'));
}

/**
 * Hold back the canvas's own resize observer by `ms`, as a slow frame would.
 * Golden Layout sizes the canvas as it maximises or restores a stack, and the
 * renderer learns the new size only when its observer fires: a fit run as the
 * dock moves, or after a fixed delay shorter than this, frames the drawing in
 * the size the canvas had. Golden Layout's own observer is left alone.
 */
async function holdCanvasResizes(page: Page, ms: number): Promise<void> {
  await page.addInitScript((late: number) => {
    const Native = window.ResizeObserver;
    window.ResizeObserver = class extends Native {
      private readonly held: { canvas: boolean };
      constructor(callback: ResizeObserverCallback) {
        const held = { canvas: false };
        super((entries, observer) => {
          if (held.canvas) setTimeout(() => callback(entries, observer), late);
          else callback(entries, observer);
        });
        this.held = held;
      }
      observe(target: Element, options?: ResizeObserverOptions): void {
        if (target.matches('.graphRenderer')) this.held.canvas = true;
        super.observe(target, options);
      }
    };
  }, ms);
}

test('a first visit opens on step 1, and the walkthrough turns the steps with the rail', async ({ page }) => {
  await page.goto('/');
  await expect(card(page)).toHaveAttribute('data-step', 'open');
  await expect(card(page)).toContainText('Step 1 of 4 · Open');
  await expect(current(page)).toHaveText('1Open');

  // Mutation: let the card keep a page of its own again -- the rail stays
  // on Open as the card turns, and this fails.
  await card(page).getByRole('button', { name: 'Next: Browse →' }).click();
  await expect(card(page)).toHaveAttribute('data-step', 'browse');
  await expect(current(page)).toHaveText('2Browse');

  // The card's Next enters the step: its window comes forward behind it.
  await card(page).getByRole('button', { name: 'Next: Tune →' }).click();
  await expect(current(page)).toHaveText('3Tune');
  await expect.poll(() => frontTabs(page)).toContain('Graph Settings');

  await card(page).getByRole('button', { name: 'Next: Read →' }).click();
  await expect(card(page)).toHaveAttribute('data-step', 'read');
  await expect(page.locator('.lm_maximised .gl-panel--graph')).toHaveCount(1);
  await expect(card(page).getByRole('button', { name: /^Next/ })).toHaveCount(0);
  await expect(card(page).getByRole('button', { name: 'Got it!' })).toBeVisible();

  await card(page).getByRole('button', { name: '← Back' }).click();
  await expect(current(page)).toHaveText('3Tune');
  await expect(page.locator('.lm_maximised')).toHaveCount(0);

  // A dot is a step too.
  await card(page).locator('.cc-modal__dot').first().click();
  await expect(current(page)).toHaveText('1Open');
  await expect.poll(() => frontTabs(page)).toContain('⬇ Open');

  // Closed, it leaves the reader on the step it showed; ? opens it on the step they are on.
  await dismissOnboardingModal(page);
  await step(page, 'Tune').click();
  await page.locator('.gl-app-header__help-btn').click();
  await expect(card(page)).toHaveAttribute('data-step', 'tune');
  await expect(card(page)).toContainText('Step 3 of 4 · Tune');
});

test('each step brings its windows forward, says what comes next, and Read hides the rest', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await expect(current(page)).toHaveText('1Open');
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
  await expect(next(page)).toHaveText('Next 2 Browse →');

  await step(page, 'Tune').click();
  await expect(current(page)).toHaveText('3Tune');
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);
  await expect(next(page)).toHaveText('Next 4 Read →');

  // Mutation: set Read's `alone` to false in steps.ts -- Files and Graph
  // Settings stay in view, and this fails.
  await step(page, 'Read').click();
  await expect(current(page)).toHaveText('4Read');
  await expect.poll(() => windowsInView(page)).toEqual(['graph']);
  await expect(next(page)).toHaveCount(0);
  // With the Open panel hidden, the empty canvas names the step that has it.
  await expect(page.locator('.plot__empty-text')).toContainText('Step 1, Open, is where one starts');

  // Mutation: drop `dock.restore()` from steps.enterStep -- the canvas stays
  // over everything, and this fails.
  await step(page, 'Browse').click();
  await expect(current(page)).toHaveText('2Browse');
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);

  await next(page).click();
  await expect(current(page)).toHaveText('3Tune');
  await step(page, 'Open').click();
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
});

test('Read fills the dock with the canvas when a focus has scrolled it', async ({ page }) => {
  /**
   * The dock's host clips and does not scroll, but a focus or a
   * scrollIntoView inside it scrolls it anyway -- Playwright's own click on
   * Load Demo did, by 8 pixels -- and Golden Layout pins a maximised stack to
   * the top of the host's content. Chrome's scroll anchoring then moved the
   * host by another 336 to keep the focused button in place, and step 4 drew
   * the canvas 344 pixels up, with Files and Open showing under it.
   * Mutation: drop the scroll reset from the step dock's `maximise` -- this
   * fails.
   */
  await page.goto('/');
  await dismissOnboardingModal(page);
  const body = page.locator('.gl-shell__body');
  await body.evaluate((el) => { el.scrollTop = 8; });
  await page.getByRole('button', { name: /Load Demo/i }).first().focus();

  await step(page, 'Read').click();
  await expect(page.locator('.lm_maximised')).toHaveCount(1);
  const [dock, canvas] = await Promise.all([body.boundingBox(), page.locator('.lm_maximised').boundingBox()]);
  expect(canvas, 'the maximised canvas').not.toBeNull();
  expect(Math.round(canvas!.y - dock!.y), 'how far the canvas starts from the top of the dock').toBe(0);
  expect(Math.round(canvas!.height - dock!.height), 'how much of the dock the canvas leaves').toBe(0);
  await expect.poll(() => windowsInView(page)).toEqual(['graph']);
});

test('Read frames the drawing in the canvas it fills once the canvas has its size, and so does leaving it', async ({ page }) => {
  /**
   * Step 4 maximises the canvas, and the drawing kept the framing it had in
   * the canvas it was drawn in -- the dock's top two thirds -- so it sat in
   * the upper half with the lower half empty, until the ring's Fit. Leaving
   * Read shrank the canvas under a drawing framed for the whole dock.
   *
   * The canvas's resize lands a second and a half late here, so the fit has
   * to wait for it however long it takes.
   */
  await holdCanvasResizes(page, 1_500);
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  await expect(page.locator('.graph-node[data-node-id]').first()).toBeVisible({ timeout: SETTLED });
  await expect.poll(() => framing(page), { timeout: SETTLED }).toBe('framed');

  await step(page, 'Read').click();
  await expect.poll(() => windowsInView(page)).toEqual(['graph']);
  // The canvas fills the dock, and its resize has not landed: the drawing is
  // where the smaller canvas framed it.
  expect(await framing(page)).not.toBe('framed');
  // Mutation: fit as the dock moves rather than when the resize lands -- the
  // drawing is framed in the smaller canvas's size, and this fails.
  await expect.poll(() => framing(page), { timeout: 10_000 }).toBe('framed');

  await step(page, 'Browse').click();
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
  await expect.poll(() => framing(page), { timeout: 10_000 }).toBe('framed');

  // A step that leaves the canvas its size leaves the reader's zoom as well.
  // Mutation: fit on every step -- the zoom is undone, and this fails.
  const box = (await canvas(page).boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.wheel(0, -600);
  await expect.poll(() => framing(page)).not.toBe('framed');
  const zoomed = await zoomOf(page);
  await step(page, 'Open').click();
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
  // Longer than the held resize and the fit's 0.7 s transition together.
  await page.waitForTimeout(2_500);
  expect(await zoomOf(page)).toBe(zoomed);

  // Into Read and out again within one frame: the canvas is back at its size
  // before its observer saw it change, so the observer does not fire, and no
  // fit may be left waiting for the next resize -- here the reader's own,
  // dragging the splitter under the canvas. Mutation: leave the fit asked
  // for when the canvas comes back to its size -- the drag undoes the zoom,
  // and this fails.
  await page.evaluate(() => {
    for (const id of ['read', 'open']) {
      document.querySelector<HTMLButtonElement>(`.gl-steps__step[data-step="${id}"]`)!.click();
    }
  });
  const room = page.locator('.graphRenderer');
  const tall = (await room.boundingBox())!.height;
  const splitter = (await page.locator('.lm_splitter.lm_vertical').first().boundingBox())!;
  await page.mouse.move(splitter.x + splitter.width / 2, splitter.y + splitter.height / 2);
  await page.mouse.down();
  await page.mouse.move(splitter.x + splitter.width / 2, splitter.y - 80, { steps: 8 });
  await page.mouse.up();
  await expect.poll(async () => (await room.boundingBox())!.height).toBeLessThan(tall - 40);
  await page.waitForTimeout(2_500);
  expect(await zoomOf(page)).toBe(zoomed);
});

test("the canvas maximised by Golden Layout's own control is Read, and restored it is the step the reader came from", async ({ page }) => {
  /**
   * Read is the canvas alone, and the canvas's stack has Golden Layout's own
   * maximise control as well as the rail. Maximised with it, the rail still
   * said Tune, and Next pointed at Read, over a canvas hiding every window;
   * restored after the rail's Read, the rail said Read over every window back
   * in view.
   */
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  await expect(page.locator('.graph-node[data-node-id]').first()).toBeVisible({ timeout: SETTLED });
  await expect.poll(() => framing(page), { timeout: SETTLED }).toBe('framed');
  const stackOf = (tab: string) => page.locator('.lm_stack', { has: page.locator('.lm_tab', { hasText: tab }) });
  const canvasControl = stackOf('◈ Graph').locator('.lm_maximise');

  // Mutation: stop the rail following the stack the dock maximises -- it
  // stays on Tune, and this fails.
  await step(page, 'Tune').click();
  await canvasControl.click();
  await expect.poll(() => windowsInView(page)).toEqual(['graph']);
  await expect(current(page)).toHaveText('4Read');
  await expect(next(page)).toHaveCount(0);
  // Read as the rail's Read is: the drawing framed in the canvas it fills.
  await expect.poll(() => framing(page), { timeout: 10_000 }).toBe('framed');

  // The same control restores it. Mutation: leave the rail where it is when
  // the canvas is restored -- it says Read over every window, and this fails.
  await canvasControl.click();
  await expect(current(page)).toHaveText('3Tune');
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);
  await expect.poll(() => framing(page), { timeout: 10_000 }).toBe('framed');

  // Read entered from the rail is left the same way, for the step before it.
  await step(page, 'Browse').click();
  await step(page, 'Read').click();
  await expect(page.locator('.lm_maximised')).toHaveCount(1);
  await canvasControl.click();
  await expect(page.locator('.lm_maximised')).toHaveCount(0);
  await expect(current(page)).toHaveText('2Browse');

  // Another stack maximised is the window in front of it chosen -- Graph
  // Settings, in front since Tune -- and stays chosen when it is restored.
  const settingsStack = stackOf('Graph Settings');
  await settingsStack.locator('.lm_maximise').click();
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings']);
  await expect(current(page)).toHaveText('3Tune');
  await settingsStack.locator('.lm_maximise').click();
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);
  await expect(current(page)).toHaveText('3Tune');
});

test("a step opens its window again when it was closed, and a stack maximised by Golden Layout's own control gives way", async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);

  // Closed from another step. Mutation: drop the step dock's `openPanel` for
  // a window not in the layout -- Tune finds nothing to show, and this fails.
  const settings = page.locator('.lm_tab', { hasText: 'Graph Settings' });
  await settings.locator('.lm_close_tab').click();
  await expect(settings).toHaveCount(0);
  await step(page, 'Tune').click();
  await expect(settings).toHaveCount(1);
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);

  // Closed on the step itself, which closing a tab does not move: the step
  // already on is a button too. Mutation: have `enterStep` return when asked
  // for the step already on -- this fails.
  await page.locator('.lm_tab', { hasText: 'Graph Settings' }).locator('.lm_close_tab').click();
  await expect(settings).toHaveCount(0);
  await expect(current(page)).toHaveText('3Tune');
  await step(page, 'Tune').click();
  await expect(settings).toHaveCount(1);
  await expect.poll(() => windowsInView(page)).toEqual(['controls-graph-settings', 'file-tree', 'graph']);

  // Mutation: drop the restore from both `steps.enterStep` and
  // `focusDockPanel` -- Files stays over everything, and this fails.
  const files = page.locator('.lm_stack', { has: page.locator('.lm_tab', { hasText: 'Files' }) });
  await files.locator('.lm_maximise').click();
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree']);
  await step(page, 'Open').click();
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
});

test('choosing a tab says which step the reader is on, and moves no other window', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);

  // Mutation: stop `noteClick` following the tab's window -- the rail stays
  // on Open, and this fails.
  await page.locator('.lm_tab', { hasText: 'Graph Settings' }).click();
  await expect(current(page)).toHaveText('3Tune');
  await page.locator('.lm_tab', { hasText: 'Files' }).click();
  await expect(current(page)).toHaveText('2Browse');
  await page.locator('.lm_tab', { hasText: 'Estate' }).click();
  await expect(current(page)).toHaveText('1Open');

  // The canvas's tab says Read, and maximises nothing: only the rail's step does.
  await page.locator('.lm_tab', { hasText: '◈ Graph' }).click();
  await expect(current(page)).toHaveText('4Read');
  await expect(page.locator('.lm_maximised')).toHaveCount(0);
  await expect.poll(() => windowsInView(page)).toEqual(['estate', 'file-tree', 'graph']);

  // Closing a window chooses nothing.
  await page.locator('.lm_tab', { hasText: 'Estate' }).locator('.lm_close_tab').click();
  await expect(page.locator('.lm_tab', { hasText: 'Estate' })).toHaveCount(0);
  await expect(current(page)).toHaveText('4Read');
});

test('a draw leaves the step where it is, and a window chosen over the canvas comes into view', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);

  await page.getByRole('button', { name: /Load Demo/i }).first().click();
  const node = page.locator('.graph-node[data-node-id]').first();
  await expect(node).toBeVisible({ timeout: SETTLED });
  await expect(current(page)).toHaveText('1Open');

  await step(page, 'Read').click();
  await expect.poll(() => windowsInView(page)).toEqual(['graph']);
  await expect(node).toBeVisible();

  // A window added from + comes into view over step 4's canvas -- Golden
  // Layout restores a maximised stack before it adds an item -- and the rail
  // follows it. Mutation: have the + menu call `openPanel` rather than
  // `chooseWindow` -- the rail stays on Read, and this fails.
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Cargo$/ }).click();
  await expect.poll(() => windowsInView(page)).toContain('cargo');
  await expect(page.locator('.lm_maximised')).toHaveCount(0);
  await expect(current(page)).toHaveText('1Open');

  // A reset puts the dock back as a page opens it, on step 1.
  await step(page, 'Read').click();
  await expect(page.locator('.lm_maximised')).toHaveCount(1);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: 'Reset to built-in default' }).click();
  await expect(current(page)).toHaveText('1Open');
  await expect.poll(() => windowsInView(page)).toEqual(['file-tree', 'graph', 'open']);
});

test("a draw brings the canvas into view over a stack maximised with Golden Layout's own control", async ({ page }) => {
  /**
   * The Overview panel brings the canvas forward when it has drawn
   * (`focusDockPanel('graph')`). With the panel's own stack maximised, the
   * canvas was brought to the front of a stack nobody could see, and the
   * drawing stayed out of sight behind the panel that asked for it.
   * Mutation: drop `this._restoreAllBut(stack)` from focusDockPanel -- this
   * fails. The backend serves `fixtures/overview.json` (playwright.config.ts).
   */
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Overview$/ }).click();
  const panel = page.locator('.gl-panel--overview');
  await panel.locator('.estate-view__draw').waitFor({ timeout: SETTLED });

  const overview = page.locator('.lm_stack', { has: page.locator('.lm_tab', { hasText: 'Overview' }) });
  await overview.locator('.lm_maximise').click();
  await expect.poll(() => windowsInView(page)).toEqual(['overview']);

  await panel.locator('.estate-view__draw').click();
  await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: SETTLED });
  await expect(page.locator('.lm_maximised')).toHaveCount(0);
  await expect.poll(() => windowsInView(page)).toContain('graph');
});

/**
 * The header's shape: its height, how many lines its title takes, whether what
 * the rail paints ends before the controls at the header's right end, and
 * whether Next is whole inside the rail. A rail that clips paints no further
 * than its own box; one that does not paints as far as its last button.
 */
async function headerShape(page: Page) {
  return page.evaluate(() => {
    const box = (selector: string) => document.querySelector(selector)?.getBoundingClientRect() ?? null;
    const header = box('.gl-app-header')!;
    const title = box('.gl-app-header__title')!;
    const nav = document.querySelector('nav.gl-steps')!;
    const rail = nav.getBoundingClientRect();
    const clips = getComputedStyle(nav).overflowX !== 'visible';
    const painted = Math.max(...[...nav.querySelectorAll('button')].map((b) => {
      const right = b.getBoundingClientRect().right;
      return clips ? Math.min(right, rail.right) : right;
    }));
    const controls = box('.gl-app-header__gh-auth') ?? box('.gl-app-header__help-btn')!;
    const next = box('.gl-steps__next');
    return {
      height: Math.round(header.height),
      titleLines: Math.round(title.height / 18),
      railClearOfControls: painted <= controls.left,
      nextWhole: next ? next.left >= rail.left && next.right <= rail.right : null,
    };
  });
}

/**
 * The header in its own font, Consolas, and in a wider one. A machine with no
 * Consolas draws the header in its own monospace: the CI runner's is wider,
 * and Next, which fitted at 700 pixels here, ran past the rail's end there.
 */
for (const [inFont, font] of [['its own font', null], ['a wider font', "'Lucida Console', 'DejaVu Sans Mono', monospace"]]) {
  test(`the header is one line, of one height on every step, in a narrow window, in ${inFont}`, async ({ page }) => {
    /**
     * At 700 pixels the rail and Next left the title too little room, and it
     * wrapped onto a second line while Next was shown: the header was 50
     * pixels tall on steps 1 to 3 and 45 on Read, so the dock under it moved
     * with the step, and the rail ran on under the controls at the header's
     * right end. The title keeps its line, and the steps the reader is not on,
     * and Next, give their names to their numbers; narrower still, the rail
     * scrolls rather than run under the controls.
     */
    await page.setViewportSize({ width: 700, height: 600 });
    await page.goto('/');
    if (font) await page.addStyleTag({ content: `* { font-family: ${font} !important; }` });
    await dismissOnboardingModal(page);
    const oneLine = { height: 45, titleLines: 1, railClearOfControls: true };
    for (const id of ['open', 'browse', 'tune', 'read']) {
      await rail(page).locator(`.gl-steps__step[data-step="${id}"]`).click();
      await expect(current(page)).toHaveAttribute('data-step', id);
      // Mutations: keep every step's name in a narrow window, or Next's (in
      // the wider font) -- Next runs past the rail's end, and this fails.
      expect(await headerShape(page), `on ${id}`).toEqual({ ...oneLine, nextWhole: id === 'read' ? null : true });
    }
    // The names are still the buttons', to a screen reader and a test.
    // Mutation: hide them with `display: none` -- the Browse button is named
    // "2", and this fails.
    await expect(step(page, 'Browse')).toHaveAccessibleName(/Browse/);

    // Narrower than the rail can fit. Mutations: let the rail overflow its
    // box -- it runs under the controls -- or let the title wrap, giving it
    // the room -- the header is 50 pixels tall -- and this fails.
    await page.setViewportSize({ width: 560, height: 600 });
    await rail(page).locator('.gl-steps__step[data-step="open"]').click();
    // Next comes back with the redraw that moves the rail; measured before
    // it, the rail is short enough to fit, and nothing here is tested.
    await expect(current(page)).toHaveAttribute('data-step', 'open');
    await expect(next(page)).toBeVisible();
    await expect(next(page)).toHaveAccessibleName(/Next 2 Browse/);
    expect(await headerShape(page)).toMatchObject(oneLine);
  });
}
