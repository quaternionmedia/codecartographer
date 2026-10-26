/**
 * A button's label stays readable with the pointer on it.
 *
 * The global `button:hover` (styles/index.css) fills a button with the
 * secondary colour and sets its label in the inverse colour, a pair. A
 * component hover rule that sets its own background and not the label's
 * colour keeps the inverse label over that background: on the dark themes,
 * dark on dark, and the label disappears (⚡ Load Demo, the lexicons, ▶ Plot,
 * the + menu's items).
 *
 * This hovers every enabled button in the states most of the window is seen
 * in, and measures the contrast between each label and what is behind it,
 * translucent backgrounds composited over their ancestors. Only a browser
 * resolves the cascade that decides it.
 */

import { expect, test, type Locator, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 30_000;
/** WCAG's least contrast for large text and interface components. */
const READABLE = 3;

test.use({ viewport: { width: 1600, height: 1000 } });

/** The least contrast between any label text in `button` and what is behind it. */
function labelContrast(button: Element): number {
  // Chromium reports rgb() and rgba() with channels to 255, and a
  // color-mix() as color(srgb r g b / a) with channels to 1. A colour in any
  // other notation is named, not read as transparent and skipped.
  const parse = (c: string): number[] => {
    const rgb = c.match(/^rgba?\(([^)]+)\)$/);
    const srgb = c.match(/^color\(srgb ([^)]+)\)$/);
    const m = rgb ?? srgb;
    if (!m) throw new Error(`labelContrast cannot read the colour ${c}`);
    const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    const to255 = rgb ? 1 : 255;
    return [p[0] * to255, p[1] * to255, p[2] * to255, p.length > 3 ? p[3] : 1];
  };
  const over = (top: number[], under: number[]): number[] =>
    [0, 1, 2].map((i) => top[i] * top[3] + under[i] * (1 - top[3])).concat(1);
  const backdrop = (node: Element): number[] => {
    const layers: number[][] = [];
    for (let e: Element | null = node; e; e = e.parentElement) {
      const bg = parse(getComputedStyle(e).backgroundColor);
      if (bg[3] > 0) layers.push(bg);
      if (bg[3] >= 1) break;
    }
    return layers.reverse().reduce((under, top) => over(top, under), [255, 255, 255, 1]);
  };
  const luminance = (c: number[]): number => {
    const [r, g, b] = c.slice(0, 3).map((v) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const ratio = (a: number[], b: number[]): number => {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  };
  // Every element that holds a label character. An emoji (⚡, 📖, or a
  // symbol a variation selector asks to be one) draws in its own colours
  // whatever the text colour is, so it is not one. A symbol drawn as text
  // by default (▶, ★, ☰) is drawn in the text colour, and is one.
  const emoji = /\p{Extended_Pictographic}\uFE0F|\p{Emoji_Presentation}|\uFE0F/gu;
  const holders = new Set<Element>();
  const walker = document.createTreeWalker(button, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (/\S/.test((n.textContent ?? '').replace(emoji, '')) && n.parentElement) {
      holders.add(n.parentElement);
    }
  }
  let worst = Infinity;
  for (const holder of holders) {
    let alpha = 1;
    for (let e: Element | null = holder; e && e !== button.parentElement; e = e.parentElement) {
      alpha *= Number(getComputedStyle(e).opacity);
    }
    const behind = backdrop(holder);
    const text = parse(getComputedStyle(holder).color);
    worst = Math.min(worst, ratio(over([text[0], text[1], text[2], text[3] * alpha], behind), behind));
  }
  return worst;
}

/** Wait for the window's CSS transitions to end; a hover colour fades in. */
async function transitionsDone(page: Page): Promise<void> {
  await page.waitForFunction(() => document.getAnimations().every((a) =>
    a.playState !== 'running' || a.effect?.getComputedTiming().endTime === Infinity));
}

/** Hover each enabled button in `scope`; name every one whose label is not readable. */
async function unreadableOnHover(page: Page, scope: Locator): Promise<string[]> {
  const unreadable: string[] = [];
  const buttons = scope.locator('button:visible:enabled');
  // A redraw is asynchronous: wait for what was opened to be drawn.
  await expect(buttons.first(), `buttons to hover in ${scope}`).toBeVisible();
  const count = await buttons.count();
  for (let i = 0; i < count; i++) {
    const button = buttons.nth(i);
    await button.hover();
    await transitionsDone(page);
    const contrast = await button.evaluate(labelContrast);
    if (contrast < READABLE) {
      const name = ((await button.getAttribute('title')) || (await button.innerText())).trim().split('\n')[0];
      unreadable.push(`${name} ${contrast.toFixed(2)}:1`);
    }
  }
  await page.mouse.move(1, 999);
  return unreadable;
}

test('every button in the default dock keeps its label readable on hover', async ({ page }) => {
  await page.goto('/');
  // The walkthrough a first visit opens with: Next, then Back beside it.
  const walkthrough = page.locator('.cc-modal-backdrop');
  expect.soft(await unreadableOnHover(page, walkthrough)).toEqual([]);
  await walkthrough.getByRole('button', { name: /Next/i }).click();
  expect.soft(await unreadableOnHover(page, walkthrough)).toEqual([]);
  await dismissOnboardingModal(page);

  const open = page.locator('.gl-panel--open');
  await expect(open.locator('[data-example="blinky (recorded)"]')).toBeAttached({ timeout: SETTLED });
  await expect(open.getByRole('button', { name: /Lexicon$/ }).first()).toBeAttached({ timeout: SETTLED });
  // The parse options' chips too.
  await open.locator('.panel-open__parse-toggle').click();

  // Mutation: drop the label colour from the Open panel's button-option
  // hover -- Load Demo and the lexicons go dark on dark, and this fails.
  expect.soft(await unreadableOnHover(page, page.locator('.gl-app-header'))).toEqual([]);
  expect.soft(await unreadableOnHover(page, open)).toEqual([]);

  await page.locator('.gl-app-header__add-btn').click();
  expect.soft(await unreadableOnHover(page, page.locator('.gl-add-panel-menu'))).toEqual([]);
  await page.keyboard.press('Escape');

  await page.locator('.lm_tab', { hasText: 'Estate' }).click();
  expect.soft(await unreadableOnHover(page, page.locator('.gl-panel--estate'))).toEqual([]);
});

test('every button a drawn graph brings keeps its label readable on hover', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);
  const open = page.locator('.gl-panel--open');
  await open.locator('[data-example="blinky (recorded)"]').click();
  await expect(page.locator('.graph-node[data-node-id*="region::FLASH"]')).toHaveCount(1, { timeout: SETTLED });

  // The hint the first draw raises, with its ×, and the legend's header.
  expect.soft(await unreadableOnHover(page, page.locator('.cc-toasts'))).toEqual([]);
  expect.soft(await unreadableOnHover(page, page.locator('.graph-legend'))).toEqual([]);

  // The Cargo panel came forward with the example.
  expect.soft(await unreadableOnHover(page, page.locator('.gl-panel--cargo'))).toEqual([]);
  expect.soft(await unreadableOnHover(page, page.locator('.gl-panel--file-tree'))).toEqual([]);

  // With a repository loaded: its ✕ in the Open panel, and Plot enabled.
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await expect(open.locator('button.panel-plotbar__plot')).toBeEnabled({ timeout: SETTLED });
  expect.soft(await unreadableOnHover(page, open)).toEqual([]);

  await page.locator('.lm_tab', { hasText: 'Graph Settings' }).click();
  const settings = page.locator('.gl-panel--controls-graph-settings');
  await settings.getByText('Theme', { exact: true }).click();
  expect.soft(await unreadableOnHover(page, settings)).toEqual([]);

  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Chrestomathy$/ }).click();
  const chrestomathy = page.locator('.gl-panel--chrestomathy');
  await expect(chrestomathy.locator('tr[data-construct]').first()).toBeVisible({ timeout: SETTLED });
  expect.soft(await unreadableOnHover(page, chrestomathy)).toEqual([]);
});

test('every button in Topology and Graphbase keeps its label readable on hover', async ({ page }) => {
  // Neither panel shows its buttons without a service this suite does not
  // start: Topology's flows come from the harness, Graphbase's entries from
  // its database. Each is stubbed with what it answers when it is up.
  const json = (body: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  await page.route('**/topology/available*', (route) => route.fulfill(json({
    status: 200,
    message: 'Success',
    results: {
      topologies: [
        { topology: 'pair', caption: 'two boxes', status: 'runs', boxes: 2, arrows: 2 },
        { topology: 'chain', caption: 'three boxes', status: 'runs', boxes: 3, arrows: 2 },
      ],
      layouts: ['Spring'],
      encoding: [],
    },
  })));
  await page.route(/\/db\/$/, (route) => route.fulfill(json({ available: true })));
  await page.route(/\/db\/bookmarks$/, (route) => route.fulfill(json([
    { name: 'kept', url: 'https://github.com/octocat/hello-world', layout: 'Spring', depth: 1, extensions: [], saved_at: 0 },
  ])));
  await page.route(/\/db\/snapshots$/, (route) => route.fulfill(json([
    { name: 'drawn', saved_at: 0, meta: { nodeCount: 3 } },
  ])));
  await page.goto('/');
  await dismissOnboardingModal(page);

  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Topology$/ }).click();
  const topology = page.locator('.gl-panel--topology');
  await expect(topology.locator('.topology__chip')).toHaveCount(2, { timeout: SETTLED });
  // Mutation: drop the background from the Topology chips' hover -- the
  // global secondary fill comes back under their label, and this fails.
  expect.soft(await unreadableOnHover(page, topology)).toEqual([]);

  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Graphbase$/ }).click();
  const graphbase = page.locator('.gl-graphbase-panel');
  await expect(graphbase.locator('.gl-graphbase-panel__load-btn')).toHaveCount(2, { timeout: SETTLED });
  // Mutation: drop the background from Graphbase's ▶ hover -- its secondary
  // label is drawn on the secondary fill, and this fails.
  expect.soft(await unreadableOnHover(page, graphbase)).toEqual([]);
});

test('a selected parse-option chip keeps its label and its fill in the Light theme', async ({ page }) => {
  // The dark themes' accent is light, and their inverse colour reads on it.
  // Light's accent is a mid orange, and its inverse colour is white.
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));
  const open = page.locator('.gl-panel--open');
  await open.locator('.panel-open__parse-toggle').click();
  const chip = open.locator('.panel-settings__chip--active').first();
  await expect(chip).toBeVisible();

  await page.mouse.move(1, 999);
  await transitionsDone(page);
  // Mutation: give Light's text on accent its inverse colour, #fff on
  // #ff9800 -- this fails at 2.16:1.
  expect.soft(await chip.evaluate(labelContrast), 'at rest').toBeGreaterThanOrEqual(READABLE);

  await chip.hover();
  await transitionsDone(page);
  // Mutation: let the chips' transparent hover reach the selected one -- its
  // fill goes, its accent label is left on the panel, and both of these fail.
  expect.soft(await chip.evaluate(labelContrast), 'under the pointer').toBeGreaterThanOrEqual(READABLE);
  expect.soft(await chip.evaluate((e) => getComputedStyle(e).backgroundColor), 'its fill under the pointer')
    .not.toBe('rgba(0, 0, 0, 0)');
});

test('the contrast measure reads a color-mix() fill, and names a colour it cannot read', async ({ page }) => {
  // Every translucent fill above is a color-mix(), and Chromium reports one
  // as color(srgb r g b / a). Read as transparent, a fill drops out of the
  // composite and its label is measured against the panel behind it.
  await page.setContent(`
    <div style="background: #000">
      <button id="mixed" style="border: 0; color: #fff;
        background: color-mix(in srgb, #fff 90%, transparent)">Label</button>
      <button id="oklch" style="border: 0; color: #fff;
        background: oklch(0.9 0 0)">Label</button>
    </div>`);
  const mixed = page.locator('#mixed');
  expect(await mixed.evaluate((e) => getComputedStyle(e).backgroundColor)).toMatch(/^color\(srgb /);
  // Mutation: read color(srgb ...) as transparent, as a parse of rgb() and
  // rgba() alone did -- the near-white fill drops out, the white label
  // measures 21:1 against the black, and this fails.
  expect(await mixed.evaluate(labelContrast)).toBeLessThan(READABLE);
  // Mutation: read a colour in another notation as transparent -- this fails.
  await expect(page.locator('#oklch').evaluate(labelContrast)).rejects.toThrow(/oklch/);
});
