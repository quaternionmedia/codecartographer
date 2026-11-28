/**
 * The Designer panel, end to end.
 *
 * The harness is a separate process this suite does not start, so what the
 * window's own API answers for it is stubbed at the route: `/designer/data`
 * with a reading in the shape `tests/test_designer.py` holds the real route
 * to, and `/designer/gjgf` with `fixtures/designer-graph.json`, which is what
 * the real route, serializer and layout return for that test's invented
 * documents. The panel, the state actions, the wording functions and the
 * canvas all run as shipped.
 *
 * Each test names the mutation it was seen to fail under.
 */

import type { Page, Request } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 20_000;
/** Read from `web/`, where the suite runs, as the other specs' fixtures are. */
const GRAPH = 'tests/e2e/fixtures/designer-graph.json';

const need = (key: string) => ({ key, because: `because of ${key}`, supplied_by: `supply ${key}` });

const shape = (name: string, status: string, needs: string[], marks: Record<string, boolean> = {}) => ({
  topology: name, status, can_run: status === 'runs', spends: false, writes: false, decides: false, ...marks,
  why: `why ${name}`, needs: needs.map(need),
});

const INSTANCE = {
  identified: true, where: 'http://127.0.0.1:3999/health', pid: 4242, port: 3999,
  database_fingerprint: '0123456789abcdef', started_at: '2026-01-01T00:00:00+00:00',
  session: null, version: '0.1.0', problem: '', remedy: '',
};

/** A reading with three shapes, one of them under a setting; `over` replaces any part of it. */
function reading(over: Record<string, unknown> = {}) {
  return {
    instance: INSTANCE,
    where: 'http://127.0.0.1:3999/v1/orchestration/plane',
    shapes: [
      {
        name: 'relay', declared: shape('relay', 'runs', ['workers']),
        could_run: { topology: 'relay', status: 'runs', runnable: true, unmet: [] }, options: [], missing: '',
      },
      {
        name: 'panel', declared: shape('panel', 'half-built', ['build', 'budget'], { spends: true, decides: true }),
        could_run: { topology: 'panel', status: 'half-built', runnable: false, unmet: [need('budget')] },
        options: [{ setting: 'quiet', value: false, declared: shape('panel', 'sketch', ['build'], { spends: true }) }],
        missing: '',
      },
      {
        name: 'solo', declared: shape('solo', 'runs', []), could_run: null, options: [],
        missing: "the harness's account of what could run does not name this shape",
      },
    ],
    could_run: { read: true, problem: '', remedy: '', where: 'http://127.0.0.1:3999/v1/orchestration/runnable' },
    have: { workers: 2, budget: 0, model: false, built: null },
    never_supplied: { key: 'person', because: 'a person decides' },
    statuses: ['runs', 'sketch'],
    needs: ['build', 'budget', 'workers'],
    attested: ['sign a record', 'cut a tag'],
    drift: { undeclared: [], stubs: ['panel'] },
    reading: { declared_not_discovered: 'every field is a claim' },
    ...over,
  };
}

const envelope = (results: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ status: 200, message: 'Success', results }),
});

async function openDesigner(page: Page): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Designer$/ }).click();
  await page.locator('.gl-panel--designer').waitFor({ state: 'visible' });
}

async function openWith(page: Page, results: unknown): Promise<void> {
  await page.route('**/designer/data*', (route) => route.fulfill(envelope(results)));
  await openDesigner(page);
}

const row = (page: Page, name: string) => page.locator(`.designer__shape[data-shape="${name}"]`);

test('a shape\'s row shows every field the plane gives, and only the marks it states', async ({ page }) => {
  // Mutation: render every mark for every shape -- `panel` shows three.
  await openWith(page, reading());

  const panel = row(page, 'panel');
  await expect(panel).toHaveAttribute('data-status', 'half-built', { timeout: SETTLED });
  await expect(panel.locator('> .estate__name')).toHaveText('panel');
  await expect(panel.locator('> .estate__actions .designer__status')).toHaveText('half-built');
  await expect(panel.locator('> .designer__marks .designer__mark')).toHaveText(['spends', 'decides']);
  await expect(panel.locator('> .designer__declared-run')).toHaveText('declared not able to run');
  await expect(panel.locator('> .designer__why')).toHaveText('why panel');
  const needs = panel.locator('> .designer__needs > .designer__need');
  await expect(needs).toHaveCount(2);
  await expect(needs.nth(0)).toHaveText('build — because of build Supplied by: supply build');
  await expect(needs.nth(1)).toHaveText('budget unmet — because of budget Supplied by: supply budget');

  const relay = row(page, 'relay');
  await expect(relay.locator('.designer__mark')).toHaveCount(0);
  await expect(relay.locator('> .designer__declared-run')).toHaveText('declared able to run');
  // The rows are in the order given.
  await expect(page.locator('.designer__shape')).toHaveCount(3);
  await expect(page.locator('.designer__shape').first()).toHaveAttribute('data-shape', 'relay');
});

test('whether a shape could run now is the harness\'s account, beside what the plane declares', async ({ page }) => {
  // Mutation: take `data-runnable` from `declared.can_run` -- a shape
  // declared able and reported unable reads as able.
  const read = reading();
  read.shapes[0].could_run = { topology: 'relay', status: 'runs', runnable: false, unmet: [need('workers')] };
  await openWith(page, read);

  const relay = row(page, 'relay');
  await expect(relay).toHaveAttribute('data-runnable', 'no', { timeout: SETTLED });
  await expect(relay.locator('> .designer__could-run')).toHaveText('could not run now: workers unmet');
  await expect(relay.locator('> .designer__declared-run')).toHaveText('declared able to run');
  await expect(relay.locator('.designer__need[data-need="workers"]')).toHaveAttribute('data-unmet', 'yes');

  const panel = row(page, 'panel');
  await expect(panel.locator('> .designer__could-run')).toHaveText('could not run now: budget unmet');
  await expect(panel.locator('> .designer__needs > .designer__need[data-need="build"]')).toHaveAttribute('data-unmet', 'no');

  const solo = row(page, 'solo');
  await expect(solo).toHaveAttribute('data-runnable', '');
  await expect(solo.locator('> .designer__could-run')).toHaveCount(0);
  await expect(solo.locator('> .designer__missing')).toHaveText(/does not name this shape/);
  await expect(solo.locator('> .designer__no-needs')).toHaveText('states no need');
});

test('an account of what could run that was not read is said once, and no row says either way', async ({ page }) => {
  // Mutation: show `have` whether or not the account was read -- the reason
  // nothing says which could run is not shown.
  const read = reading({
    could_run: {
      read: false, problem: 'the harness is running but does not serve /v1/orchestration/runnable',
      remedy: 'start a newer one', where: 'http://127.0.0.1:3999/v1/orchestration/runnable',
    },
    have: null, never_supplied: null,
  });
  for (const found of read.shapes) { found.could_run = null; found.missing = ''; }
  await openWith(page, read);

  await expect(page.locator('.designer__could-run-unread')).toHaveText(
    'which shapes could run was not read: the harness is running but does not serve /v1/orchestration/runnable — start a newer one',
    { timeout: SETTLED });
  await expect(page.locator('.designer__have')).toHaveCount(0);
  await expect(page.locator('.designer__could-run')).toHaveCount(0);
  await expect(page.locator('.designer__need[data-unmet="yes"]')).toHaveCount(0);
  await expect(page.locator('.designer__shape')).toHaveCount(3);
});

test('an option is a row under the shape it varies, with the setting that makes it', async ({ page }) => {
  // Mutation: leave a shape's options out of its row -- `panel` holds none.
  await openWith(page, reading());

  const option = row(page, 'panel').locator('.designer__option');
  await expect(option).toHaveCount(1, { timeout: SETTLED });
  await expect(option).toHaveAttribute('data-setting', 'quiet');
  await expect(option.locator('.designer__option-name code')).toHaveText('quiet = false');
  await expect(option.locator('.designer__status')).toHaveText('sketch');
  await expect(option.locator('.designer__mark')).toHaveText(['spends']);
  await expect(option.locator('.designer__need')).toHaveCount(1);
  await expect(row(page, 'relay').locator('.designer__option')).toHaveCount(0);
});

test('what the harness has, its caveat, its drift, a person\'s acts and its words are shown as given', async ({ page }) => {
  // Mutation: leave out an empty drift list -- `undeclared` is not said to
  // be empty.
  await openWith(page, reading());

  await expect(page.locator('.designer__have')).toHaveText(
    'workers 2 · budget 0 · model false · built not stated', { timeout: SETTLED });
  await expect(page.locator('.designer__never')).toHaveText('person is never supplied: a person decides');
  await expect(page.locator('.designer__caveat')).toHaveText(['every field is a claim']);

  const empty = page.locator('.designer__drift[data-drift="undeclared"]');
  await expect(empty.locator('.estate-view__hint')).toHaveText('empty');
  await expect(page.locator('.designer__drift[data-drift="stubs"] .estate-view__rung')).toHaveText(['panel']);
  await expect(page.locator('.designer__attested li')).toHaveText(['sign a record', 'cut a tag']);
  await expect(page.locator('[data-status-word]')).toHaveText(['runs', 'sketch']);
  await expect(page.locator('[data-need-word]')).toHaveText(['build', 'budget', 'workers']);

  const instance = page.locator('.designer__instance');
  await expect(instance).toHaveAttribute('data-identified', 'yes');
  await expect(instance.locator('.estate__name')).toHaveText('http://127.0.0.1:3999/health');
});

test('a harness that is not answering is a sentence with a way back, and lists nothing', async ({ page }) => {
  // Mutation: drop `ask()` from the retry -- the rows never arrive.
  let asked = 0;
  await page.route('**/designer/data*', (route) => {
    asked += 1;
    return route.fulfill(envelope(asked === 1
      ? {
          unreachable: true, problem: 'nothing is answering at http://127.0.0.1:3999',
          remedy: 'start it with `uv run qm dashboard --start harness`',
          where: 'http://127.0.0.1:3999/v1/orchestration/plane',
        }
      : reading()));
  });
  await openDesigner(page);

  const problem = page.locator('.designer__problem');
  await expect(problem).toHaveAttribute('data-kind', 'unreachable', { timeout: SETTLED });
  await expect(problem.locator('.designer__problem-what')).toHaveText('nothing is answering at http://127.0.0.1:3999');
  await expect(problem.locator('.designer__problem-remedy')).toContainText('--start harness');
  await expect(page.locator('.designer__shape')).toHaveCount(0);
  await expect(page.locator('.gl-panel--designer .estate-view__heading')).toHaveCount(0);

  await problem.locator('.designer__retry').click();
  await expect(row(page, 'relay')).toBeVisible({ timeout: SETTLED });
  await expect(page.locator('.designer__problem')).toHaveCount(0);
});

const node = (page: Page, id: string) => page.locator(`g.graph-node[data-node-id="${id}"]`);
const edge = (page: Page, from: string, to: string) =>
  page.locator(`line.stream-edge[data-from="${from}"][data-to="${to}"]`);

test('the panel only reads: two buttons, one read until asked again, and nothing sent but GET', async ({ page }) => {
  // Mutation: ask on an interval in `designer_panel.ts` -- a second read
  // arrives unasked.
  const sent: Request[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.includes('/designer')) sent.push(request);
  });
  await page.route('**/designer/gjgf*', (route) => route.fulfill({ status: 200, contentType: 'application/json', path: GRAPH }));
  await openWith(page, reading());
  const panel = page.locator('.gl-panel--designer');
  const reads = () => sent.filter((request) => new URL(request.url()).pathname.endsWith('/designer/data')).length;

  await expect(row(page, 'relay')).toBeVisible({ timeout: SETTLED });
  const controls = panel.locator('button, input, select, textarea, a[href]');
  await expect(controls).toHaveCount(2);
  await expect(controls.nth(0)).toHaveText('draw shapes against needs');
  await expect(controls.nth(1)).toHaveText('read again');

  // Nothing asks again by itself.
  await page.waitForTimeout(2_500);
  expect(reads()).toBe(1);
  await controls.nth(1).click();
  await expect.poll(reads, { timeout: SETTLED }).toBe(2);

  await controls.nth(0).click();
  await expect(node(page, 'shape:relay')).toHaveCount(1, { timeout: SETTLED });
  expect(sent.some((request) => new URL(request.url()).pathname.endsWith('/designer/gjgf'))).toBe(true);
  expect(sent.filter((request) => request.method() !== 'GET')).toEqual([]);
});

test('draw puts each shape and each need on the canvas, an unmet need dashed, with the caveat in the panel', async ({ page }) => {
  // Mutation: answer false from `drawDesigner` before it reads -- nothing is
  // drawn.
  await page.route('**/designer/gjgf*', (route) => route.fulfill({ status: 200, contentType: 'application/json', path: GRAPH }));
  await openWith(page, reading());
  await expect(page.locator('.designer-graph__caveat')).toHaveCount(0);
  await page.locator('.designer__draw').click();

  for (const id of ['shape:relay', 'shape:panel', 'shape:solo', 'need:workers', 'need:build', 'need:budget']) {
    await expect(node(page, id), id).toHaveCount(1, { timeout: SETTLED });
  }
  await expect(page.locator('g.graph-node')).toHaveCount(6);
  await expect(page.locator('line.stream-edge')).toHaveCount(3);
  await expect(edge(page, 'shape:panel', 'need:budget')).toHaveAttribute('data-style', 'dashed');
  await expect(edge(page, 'shape:panel', 'need:build')).toHaveAttribute('data-style', 'solid');
  await expect(edge(page, 'shape:relay', 'need:workers')).toHaveAttribute('data-style', 'solid');
  await expect(page.locator('.designer-graph__caveat')).toContainText('A dashed line is a need the harness reports unmet');
});

test('a harness that does not answer the graph is the problem in the panel, and nothing is drawn', async ({ page }) => {
  // Mutation: hand an unreachable answer to the canvas -- an empty graph is drawn.
  await page.route('**/designer/gjgf*', (route) => route.fulfill(envelope({
    unreadable: true, problem: 'the harness is running but does not serve /v1/orchestration/plane',
    remedy: 'start a newer one', where: 'http://127.0.0.1:3999/v1/orchestration/plane',
  })));
  await openWith(page, reading());
  await page.locator('.designer__draw').click();

  const problem = page.locator('.designer__problem');
  await expect(problem).toHaveAttribute('data-kind', 'unreadable', { timeout: SETTLED });
  await expect(problem.locator('.designer__problem-remedy')).toHaveText('start a newer one');
  await expect(page.locator('g.graph-node')).toHaveCount(0);
});
