/**
 * The Harness panel and the run states on the canvas, end to end.
 *
 * The harness is a separate process this suite does not start, so what the
 * window's own API answers for it is stubbed at the route: `/harness/data`
 * with a reading, and `/topology/gjgf` with `fixtures/topology-alpha.json`,
 * which is what the real serializer returns for an invented payload. The
 * panel, the state actions, the join and the canvas extension all run as
 * shipped.
 *
 * Each test names the mutation it was seen to fail under.
 */

import type { Page, Request } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 20_000;
/** Read from `web/`, where the suite runs, as the other specs' fixtures are. */
const TOPOLOGY = 'tests/e2e/fixtures/topology-alpha.json';

const listing = (rows: unknown[], more = 0, floor = false) => ({
  rows, shown: rows.length, more, more_is_floor: floor, problem: '', remedy: '', where: 'http://harness',
});

/** A reading: alpha has a box in the fixture, beta has none. */
function reading(alpha: string) {
  return {
    runs: listing([{ id: 'run-1', tool_name: 'echo', status: 'success', created_at: '2026-01-01T00:00:01', duration_ms: 1, error: null }]),
    queue: listing([{
      id: 'ask-1', prompt: 'Act on the instruction: tidy alpha', status: 'pending',
      request_type: 'approval', options: ['approve', 'hold'], created_at: '2026-01-01T00:00:00',
      expires_at: '2026-01-01T00:10:00', project: 'alpha', instruction_id: 'ins-1', spend: null,
    }], 7),
    instructions: listing([{
      id: 'ins-1', text: 'tidy alpha', project: 'alpha', status: 'asking', source: 'typed',
      runtime: 'local', updated_at: '2026-01-01T00:00:01', outcome_text: null, exit_code: null,
    }]),
    states: [
      { project: 'alpha', state: alpha, because: `instruction ins-1 is ${alpha}` },
      { project: 'beta', state: 'failed', because: 'instruction ins-2 is failed' },
    ],
    unplaced: [{ what: 'tool runs', count: 1, why: 'a tool run names no project' }],
    caveat: 'a box\'s state comes from the newest instruction acted on for its project',
  };
}

const envelope = (results: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ status: 200, message: 'Success', results }),
});

async function stubTopology(page: Page): Promise<void> {
  await page.route('**/topology/available*', (route) => route.fulfill(envelope({
    topologies: [{ topology: 'alpha', caption: 'alpha', status: 'runs', boxes: 3, arrows: 2 }],
    encoding: [], layouts: ['Kamada Kawai'],
  })));
  await page.route('**/topology/gjgf*', (route) => route.fulfill({
    status: 200, contentType: 'application/json', path: TOPOLOGY,
  }));
}

async function openPanel(page: Page, label: RegExp, panelClass: string): Promise<void> {
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: label }).click();
  await page.locator(panelClass).waitFor({ state: 'visible' });
}

async function drawAlpha(page: Page): Promise<void> {
  await openPanel(page, /^Topology$/, '.gl-panel--topology');
  await page.locator('.topology__chip', { hasText: /^alpha$/ }).click();
  await expect(page.locator('g.graph-node[data-node-id="subject"]')).toHaveCount(1, { timeout: SETTLED });
}

const node = (page: Page, id: string) => page.locator(`g.graph-node[data-node-id="${id}"]`);

test('a state marks every box that names its project, and a project with no box is said', async ({ page }) => {
  // Mutations: return `unmatched: []` from `joinStates` -- beta's row loses its
  // sentence; skip `setAttribute` in `RunStateExtension.apply` -- no box is marked.
  await stubTopology(page);
  await page.route('**/harness/data*', (route) => route.fulfill(envelope(reading('active'))));
  await page.goto('/');
  await dismissOnboardingModal(page);

  await drawAlpha(page);
  await openPanel(page, /^Harness$/, '.gl-panel--harness');
  const panel = page.locator('.gl-panel--harness');

  const alpha = panel.locator('.harness__state[data-project="alpha"]');
  await expect(alpha).toHaveAttribute('data-run-state', 'active', { timeout: SETTLED });
  await expect(alpha).toHaveAttribute('data-on-canvas', 'yes');
  await expect(alpha).toContainText('instruction ins-1 is active');

  const beta = panel.locator('.harness__state[data-project="beta"]');
  await expect(beta).toHaveAttribute('data-on-canvas', 'no');
  await expect(beta.locator('.harness__unmatched')).toHaveText('no box drawn names this project');

  // Both boxes whose address names alpha, and not the one with no address.
  await expect(node(page, 'subject')).toHaveAttribute('data-run-state', 'active');
  await expect(node(page, 'r0')).toHaveAttribute('data-run-state', 'active');
  await expect(node(page, 'gate')).not.toHaveAttribute('data-run-state', /.*/);
  // One ring on each marked box and none on the other.
  await expect(node(page, 'subject').locator('.run-state-ring')).toHaveCount(1);
  await expect(node(page, 'r0').locator('.run-state-ring')).toHaveCount(1);
  await expect(node(page, 'gate').locator('.run-state-ring')).toHaveCount(0);

  await expect(panel.locator('.harness__unplaced')).toHaveText('tool runs lighting no box: 1. Why: a tool run names no project.');
});

test('the queue says how many rows the harness holds beyond the ones shown', async ({ page }) => {
  // Mutation: return '' from `heldBack` -- the sentence is absent.
  await page.route('**/harness/data*', (route) => route.fulfill(envelope(reading('active'))));
  await page.goto('/');
  await dismissOnboardingModal(page);
  await openPanel(page, /^Harness$/, '.gl-panel--harness');

  const queue = page.locator('[data-harness-list="queue"]');
  await expect(queue.locator('[data-ask="ask-1"]')).toContainText('tidy alpha', { timeout: SETTLED });
  await expect(queue.locator('.harness__more')).toHaveText(/^7 more the harness holds/);
  await expect(page.locator('[data-harness-list="runs"] .harness__more')).toHaveCount(0);
});

test('a newer reading moves the mark, and a drawing made after a reading is marked', async ({ page }) => {
  // Mutations: drop the interval in the panel's `oncreate` -- the mark stays
  // `active`; drop the extension from `_mountRad` -- the fresh drawing is bare.
  let asked = 0;
  await stubTopology(page);
  await page.route('**/harness/data*', (route) => {
    asked += 1;
    return route.fulfill(envelope(reading(asked === 1 ? 'active' : 'success')));
  });
  await page.goto('/');
  await dismissOnboardingModal(page);

  // The reading first, with nothing drawn that names alpha.
  await openPanel(page, /^Harness$/, '.gl-panel--harness');
  const alpha = page.locator('.harness__state[data-project="alpha"]');
  await expect(alpha).toHaveAttribute('data-on-canvas', 'no', { timeout: SETTLED });

  // Then the drawing: marked as it arrives, from the reading already held.
  await drawAlpha(page);
  await expect(node(page, 'subject')).toHaveAttribute('data-run-state', /active|success/);

  // And the next reading moves it.
  await expect(node(page, 'subject')).toHaveAttribute('data-run-state', 'success', { timeout: SETTLED });
  await expect(node(page, 'r0')).toHaveAttribute('data-run-state', 'success');
  expect(asked).toBeGreaterThan(1);
});

test('a harness that is not answering is a sentence with a way back, and marks nothing', async ({ page }) => {
  // Mutation: never render the panel's `ProblemView` -- the panel shows no
  // problem and no way back.
  await stubTopology(page);
  await page.route('**/harness/data*', (route) => route.fulfill(envelope({
    unreachable: true,
    problem: 'nothing is answering at http://127.0.0.1:3141',
    remedy: 'start it with `uv run qm dashboard --start harness`',
    where: 'http://127.0.0.1:3141/v1/invocations?limit=500',
  })));
  await page.goto('/');
  await dismissOnboardingModal(page);
  await drawAlpha(page);
  await openPanel(page, /^Harness$/, '.gl-panel--harness');

  const problem = page.locator('.harness__problem');
  await expect(problem).toBeVisible({ timeout: SETTLED });
  await expect(problem).toHaveAttribute('data-kind', 'unreachable');
  await expect(problem).toContainText('dashboard --start harness');
  await expect(page.locator('.harness__retry')).toBeVisible();
  await expect(page.locator('.gl-panel--harness .harness__state')).toHaveCount(0);
  await expect(node(page, 'subject')).not.toHaveAttribute('data-run-state', /.*/);
});

test('the panel only reads: it offers no control and sends nothing but GET', async ({ page }) => {
  // Mutation: add a `button` to a queue row in `harness_panel.ts` -- this fails.
  const sent: Request[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.includes('/harness')) sent.push(request);
  });
  await page.route('**/harness/data*', (route) => route.fulfill(envelope(reading('active'))));
  await page.goto('/');
  await dismissOnboardingModal(page);
  await openPanel(page, /^Harness$/, '.gl-panel--harness');

  const panel = page.locator('.gl-panel--harness');
  await expect(panel.locator('[data-ask="ask-1"]')).toBeVisible({ timeout: SETTLED });
  await expect(panel.locator('button, input, select, textarea, a[href]')).toHaveCount(0);
  await expect(panel.locator('.harness__answer-where')).toContainText('qmcp human respond');

  expect(sent.length).toBeGreaterThan(0);
  expect(sent.filter((request) => request.method() !== 'GET')).toEqual([]);
});
