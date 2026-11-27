/**
 * The Interactions panel, end to end.
 *
 * The harness is a separate process this suite does not start, so what the
 * window's own API answers for it is stubbed at the route:
 * `/harness/interactions` with a reading in the shape
 * `tests/test_harness_interactions.py` holds the real route to, and
 * `/harness/gjgf` with `fixtures/interactions-graph.json`, which is what the
 * real route, serializer and layout return for invented rows. The panel, the
 * state actions, the wording functions and the canvas all run as shipped.
 *
 * Each test names the mutation it was seen to fail under.
 */

import type { Page, Request } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 20_000;
/** Read from `web/`, where the suite runs, as the other specs' fixtures are. */
const GRAPH = 'tests/e2e/fixtures/interactions-graph.json';

const row = (over: Record<string, unknown>) => ({
  at: '2026-01-01T00:00:00', act: 'ran', way: null, who: null, who_from: null, what: 'echo',
  ref: 'run-1', project: null, session: null, chat: null, turn: null, ...over,
});

const INSTANCE = {
  identified: true, where: 'http://127.0.0.1:3999/health', pid: 4242, port: 3999,
  database_fingerprint: '0123456789abcdef', started_at: '2026-01-01T00:00:00+00:00',
  session: null, version: '0.1.0', problem: '', remedy: '',
};

/** A reading with one row of each kind; `over` replaces any part of it. */
function reading(over: Record<string, unknown> = {}) {
  const rows = [
    row({ at: '2026-01-01T00:00:40', act: 'answered', who: 'ada', who_from: 'responded_by', what: 'hold', ref: 'ask-1', project: 'alpha' }),
    row({ at: '2026-01-01T00:00:30', act: 'asked', what: 'Act on the instruction: tidy alpha', ref: 'ask-1', project: 'alpha' }),
    row({
      at: '2026-01-01T00:00:20', act: 'instructed', way: 'protocol', who: 'editor-7', who_from: 'detail.client',
      what: 'tidy alpha', ref: 'ins-1', project: 'alpha', session: 's-1', chat: 'c-1', turn: 't-1',
    }),
    row({ at: '2026-01-01T00:00:10', act: 'instructed', way: 'voice', what: 'review beta', ref: 'ins-2' }),
    row({}),
  ];
  return {
    instance: INSTANCE,
    interactions: { rows, shown: rows.length, more: 0, more_is_floor: false },
    who: {
      rows: [
        { who: 'ada', who_from: 'responded_by', act: 'answered', way: null, count: 1, last: '2026-01-01T00:00:40' },
        { who: null, who_from: null, act: 'asked', way: null, count: 1, last: '2026-01-01T00:00:30' },
        { who: 'editor-7', who_from: 'detail.client', act: 'instructed', way: 'protocol', count: 1, last: '2026-01-01T00:00:20' },
        { who: null, who_from: null, act: 'instructed', way: 'voice', count: 1, last: '2026-01-01T00:00:10' },
        { who: null, who_from: null, act: 'ran', way: null, count: 8, last: '2026-01-01T00:00:00' },
      ],
      shown: 5, more: 0,
    },
    over_time: {
      from: '2026-01-01T00:00:00', to: '2026-01-01T00:00:40', cells: 4, undated: 0,
      lanes: [
        { act: 'instructed', way: 'protocol', count: 1, cells: [0, 0, 1, 0] },
        { act: 'instructed', way: 'voice', count: 1, cells: [0, 1, 0, 0] },
        { act: 'asked', way: null, count: 1, cells: [0, 0, 0, 1] },
        { act: 'answered', way: null, count: 1, cells: [0, 0, 0, 1] },
        { act: 'ran', way: null, count: 8, cells: [8, 0, 0, 0] },
      ],
    },
    answers: { read: 1, unread: 0, limit: 20 },
    unread_lists: [],
    caveat: 'who is what a row says, unchecked',
    ...over,
  };
}

const envelope = (results: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ status: 200, message: 'Success', results }),
});

async function openInteractions(page: Page, results: unknown): Promise<void> {
  await page.route('**/harness/interactions*', (route) => route.fulfill(envelope(results)));
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Interactions$/ }).click();
  await page.locator('.gl-panel--interactions').waitFor({ state: 'visible' });
}

test('a name is shown as the row gives it beside its field, and a row naming nobody says so', async ({ page }) => {
  // Mutations: write `who ?? ''` in the panel's `named` -- the voice row's
  // line is blank; drop the `code` of `named` -- no field stands beside a name.
  await openInteractions(page, reading());
  const rows = page.locator('[data-interactions="rows"]');

  const turn = rows.locator('[data-ref="ins-1"]');
  await expect(turn).toHaveAttribute('data-way', 'protocol', { timeout: SETTLED });
  await expect(turn.locator('.interactions__by')).toHaveText('editor-7 — detail.client');
  await expect(turn.locator('.interactions__by code')).toHaveText('detail.client');
  await expect(turn.locator('.interactions__through')).toHaveText('session s-1 · chat c-1 · turn t-1');
  await expect(turn.locator('.estate-view__rung')).toHaveText('instructed · protocol');

  const spoken = rows.locator('[data-ref="ins-2"]');
  await expect(spoken).toHaveAttribute('data-named', 'no');
  await expect(spoken.locator('.interactions__by')).toHaveText('nobody named');
  await expect(spoken.locator('.interactions__through')).toHaveCount(0);

  const answer = rows.locator('[data-act="answered"][data-ref="ask-1"]');
  await expect(answer.locator('.interactions__by')).toHaveText('ada — responded_by');
  await expect(answer.locator('.estate__where')).toHaveText('2026-01-01 00:00:40 UTC');

  // The newest is listed first.
  await expect(rows.locator('.interactions__row').first()).toHaveAttribute('data-act', 'answered');
  await expect(page.locator('.interactions__caveat')).toHaveText('who is what a row says, unchecked');
});

test('the who table counts the rows that name nobody beside the ones that name somebody', async ({ page }) => {
  // Mutation: filter the who rows to the named ones in the panel -- the tool
  // runs' row is gone.
  await openInteractions(page, reading({
    who: {
      ...reading().who, more: 4,
    },
  }));
  const who = page.locator('[data-interactions="who"]');

  const ada = who.locator('.interactions__who[data-who="ada"]');
  await expect(ada).toHaveAttribute('data-named', 'yes', { timeout: SETTLED });
  await expect(ada.locator('.interactions__count')).toHaveText('1');
  await expect(ada.locator('.estate__role')).toHaveText('answered');

  const runs = who.locator('.interactions__who[data-act="ran"]');
  await expect(runs).toHaveAttribute('data-named', 'no');
  await expect(runs.locator('.estate__name')).toHaveText('nobody named');
  await expect(runs.locator('.interactions__count')).toHaveText('8');

  const spoken = who.locator('.interactions__who[data-act="instructed"][data-way="voice"]');
  await expect(spoken.locator('.estate__role')).toHaveText('instructed · voice');
  await expect(who.locator('.interactions__more-names')).toHaveText(/^4 more the harness's rows give/);
});

test('the harness that answered is named by its health answer, and one that names no server says so', async ({ page }) => {
  // Mutations: render `instanceShown` whether or not the instance is
  // identified -- the second reading shows fields and no sentence; drop the
  // interval in the panel's `oncreate` -- the second reading never arrives.
  test.setTimeout(90_000);
  let asked = 0;
  await page.route('**/harness/interactions*', (route) => {
    asked += 1;
    return route.fulfill(envelope(asked === 1 ? reading() : reading({
      instance: {
        ...INSTANCE, identified: false, pid: null, port: null,
        problem: 'what answered names no pid and no port, so it does not say which server it is',
      },
    })));
  });
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Interactions$/ }).click();

  const instance = page.locator('.interactions__instance');
  await expect(instance).toHaveAttribute('data-identified', 'yes', { timeout: SETTLED });
  await expect(instance.locator('.estate__name')).toHaveText('http://127.0.0.1:3999/health');
  await expect(instance.locator('.estate__detail')).toHaveText(
    'pid 4242 · port 3999 · database 0123456789abcdef · started 2026-01-01 00:00:00 UTC · session not stated · version 0.1.0');

  // The panel asks again on its interval; the second reading names no server.
  await expect(instance).toHaveAttribute('data-identified', 'no', { timeout: 40_000 });
  await expect(instance.locator('.estate__problem')).toContainText('names no pid and no port');
  await expect(instance.locator('.estate__detail')).toHaveCount(0);
  expect(asked).toBeGreaterThan(1);
});

test('each act and way in is a lane, and a span is shaded by how many fall in it', async ({ page }) => {
  // Mutations: pass `lane.count` as `most` in `laneRow` -- the voice lane's
  // one interaction is shaded as the busiest span; drop a lane's `data-way`
  // -- the two instructed lanes cannot be told apart.
  await openInteractions(page, reading());
  const lanes = page.locator('[data-interactions="over-time"] .interactions__lane');

  await expect(lanes).toHaveCount(5, { timeout: SETTLED });
  const levels = (lane: ReturnType<Page['locator']>) =>
    lane.locator('.interactions__cell').evaluateAll((cells) => cells.map((cell) => cell.getAttribute('data-level')));

  const runs = page.locator('.interactions__lane[data-act="ran"]');
  expect(await levels(runs)).toEqual(['4', '0', '0', '0']);
  await expect(runs.locator('.interactions__lane-count')).toHaveText('8');

  const spoken = page.locator('.interactions__lane[data-act="instructed"][data-way="voice"]');
  expect(await levels(spoken)).toEqual(['0', '1', '0', '0']);
  await expect(spoken.locator('.interactions__lane-name')).toHaveText('instructed · voice');

  await expect(page.locator('.interactions__span')).toHaveText(
    'from 2026-01-01 00:00:00 UTC to 2026-01-01 00:00:40 UTC, in 4 equal spans');
  await expect(page.locator('.interactions__undated')).toHaveCount(0);
});

test('what was held back, not read or undated is said under the list it belongs to', async ({ page }) => {
  // Mutation: drop the `interactions__answers` paragraph from the panel --
  // the unread answers go unsaid.
  const full = reading();
  await openInteractions(page, reading({
    interactions: { ...full.interactions, more: 95, more_is_floor: true },
    answers: { read: 20, unread: 3, limit: 20 },
    unread_lists: [{
      what: 'instructions', problem: 'the harness is running and has no /v1/instructions',
      remedy: 'the harness serves this route only on a loopback bind', where: 'http://127.0.0.1:3999/v1/instructions?limit=500',
    }],
    over_time: { ...full.over_time, undated: 2 },
  }));

  await expect(page.locator('.interactions__more')).toHaveText(/^at least 95 more the harness holds/, { timeout: SETTLED });
  await expect(page.locator('.interactions__answers')).toHaveText(
    'answered questions whose answer was not read: 3. An answer is one read of the harness each, and at most 20 are read.');
  await expect(page.locator('.interactions__unread-list')).toHaveText(
    'instructions not read: the harness is running and has no /v1/instructions — the harness serves this route only on a loopback bind');
  await expect(page.locator('.interactions__undated')).toHaveText('interactions with no readable time, in no span: 2.');
});

test('a harness that is not answering is a sentence with a way back, and lists nothing', async ({ page }) => {
  // Mutation: never render the panel's `ProblemView` -- the panel shows no
  // problem and no way back.
  await openInteractions(page, {
    unreachable: true,
    problem: 'nothing is answering at http://127.0.0.1:3141',
    remedy: 'start it with `uv run qm dashboard --start harness`',
    where: 'http://127.0.0.1:3141/health',
  });

  const problem = page.locator('.interactions__problem');
  await expect(problem).toBeVisible({ timeout: SETTLED });
  await expect(problem).toHaveAttribute('data-kind', 'unreachable');
  await expect(problem).toContainText('dashboard --start harness');
  await expect(page.locator('.interactions__retry')).toBeVisible();
  await expect(page.locator('.gl-panel--interactions .interactions__row')).toHaveCount(0);
  await expect(page.locator('.gl-panel--interactions .interactions__instance')).toHaveCount(0);
});

const graphAnswer = { status: 200, contentType: 'application/json', path: GRAPH };

const node = (page: Page, id: string) => page.locator(`g.graph-node[data-node-id="${id}"]`);
const edge = (page: Page, from: string, to: string) =>
  page.locator(`line.stream-edge[data-from="${from}"][data-to="${to}"]`);

test('the panel only reads: its one control draws, and it sends nothing but GET', async ({ page }) => {
  // Mutation: add a `button` to a row in `interactions_panel.ts` -- this fails.
  const sent: Request[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.includes('/harness')) sent.push(request);
  });
  await page.route('**/harness/gjgf*', (route) => route.fulfill(graphAnswer));
  await openInteractions(page, reading());

  const panel = page.locator('.gl-panel--interactions');
  await expect(panel.locator('[data-ref="ins-1"]')).toBeVisible({ timeout: SETTLED });
  const controls = panel.locator('button, input, select, textarea, a[href]');
  await expect(controls).toHaveCount(1);
  await expect(controls).toHaveText('draw as a graph');

  await controls.click();
  await expect(node(page, 'harness')).toHaveCount(1, { timeout: SETTLED });
  expect(sent.some((request) => new URL(request.url()).pathname.endsWith('/harness/gjgf'))).toBe(true);
  expect(sent.filter((request) => request.method() !== 'GET')).toEqual([]);
});

async function drawGraph(page: Page): Promise<void> {
  await page.route('**/harness/gjgf*', (route) => route.fulfill(graphAnswer));
  await openInteractions(page, reading());
  await page.locator('.interactions__draw').click();
  await expect(node(page, 'harness')).toHaveCount(1, { timeout: SETTLED });
}

test('draw as a graph puts each thing a row names on the canvas, and a turn is a path of edges', async ({ page }) => {
  // Mutations: answer false from `drawInteractions` before it reads -- nothing
  // is drawn; ask `/harness/interactions` in `harnessGraph` -- what comes back
  // is a reading and no graph.
  await drawGraph(page);

  for (const id of ['nobody', 'name:detail.client:editor-7', 'instruction:ins-1', 'question:ask-1',
    'name:responded_by:ada', 'way:protocol', 'way:voice', 'tool:echo', 'project:alpha', 'chat:c-1', 'session:s-1']) {
    await expect(node(page, id), id).toHaveCount(1);
  }
  await expect(page.locator('g.graph-node')).toHaveCount(13);

  // The turn: its client, the instruction, the consent question, who answered.
  await expect(edge(page, 'name:detail.client:editor-7', 'instruction:ins-1')).toHaveCount(1);
  await expect(edge(page, 'instruction:ins-1', 'question:ask-1')).toHaveCount(1);
  const answered = edge(page, 'question:ask-1', 'name:responded_by:ada');
  await expect(answered).toHaveCount(1);
  await expect(answered).toHaveAttribute('data-style', 'solid');
  await expect(answered.locator('title')).toHaveText('answered approve');
  await expect(page.locator('line.stream-edge')).toHaveCount(14);
});

test('an edge of a row that names nobody is dashed, and a counted edge is wider', async ({ page }) => {
  // Mutations, both where the canvas draws an edge: read `edge.style` and not
  // `metadata.style` -- no line is dashed; take the width from the styling
  // alone -- the counted edge is as wide as the rest.
  await drawGraph(page);

  const unnamed = edge(page, 'nobody', 'instruction:ins-2');
  await expect(unnamed).toHaveAttribute('data-style', 'dashed');
  await expect(unnamed).toHaveAttribute('stroke-dasharray', '6,4');
  await expect(unnamed).toHaveAttribute('stroke-width', '1');
  await expect(edge(page, 'name:detail.client:editor-7', 'instruction:ins-1')).not.toHaveAttribute('stroke-dasharray', /.*/);
  await expect(page.locator('line.stream-edge[data-style="dashed"]')).toHaveCount(2);

  // The fixture's three tool runs are one edge from nobody and one to the harness.
  const ran = edge(page, 'nobody', 'tool:echo');
  await expect(ran).toHaveAttribute('data-style', 'dashed');
  await expect(ran).toHaveAttribute('stroke-width', '5');
  await expect(ran.locator('title')).toHaveText('ran ×3');
  await expect(edge(page, 'tool:echo', 'harness')).toHaveAttribute('stroke-width', '5');
  await expect(edge(page, 'tool:echo', 'harness')).toHaveAttribute('data-style', 'solid');
});

test('the caveat and the harness it was read from sit in the panel only while its graph is drawn', async ({ page }) => {
  // Mutation: pass `kind: 'topology'` to the panel's `Provenance` -- the strip
  // never shows for this graph.
  await page.route('**/harness/gjgf*', (route) => route.fulfill(graphAnswer));
  await openInteractions(page, reading());
  const strip = page.locator('.gl-panel--interactions .interactions-graph__caveat');
  await expect(page.locator('.interactions__draw')).toBeVisible({ timeout: SETTLED });
  await expect(strip).toHaveCount(0);

  await page.locator('.interactions__draw').click();
  await expect(strip).toContainText('A name is what a row says, unchecked', { timeout: SETTLED });
  await expect(strip).toContainText('No node is a machine, an address or an account');
  await expect(page.locator('.interactions-graph__provenance')).toHaveText('from http://127.0.0.1:3999/health');
});

test('a harness that does not answer the graph is the problem in the panel, and nothing is drawn', async ({ page }) => {
  // Mutation: draw whatever came back in `drawInteractions` instead of
  // calling `_draw` -- the problem is never shown.
  await page.route('**/harness/gjgf*', (route) => route.fulfill(envelope({
    unreachable: true,
    problem: 'nothing is answering at http://127.0.0.1:3141',
    remedy: 'start it with `uv run qm dashboard --start harness`',
    where: 'http://127.0.0.1:3141/health',
  })));
  await openInteractions(page, reading());
  await page.locator('.interactions__draw').click();

  const problem = page.locator('.interactions__problem');
  await expect(problem).toBeVisible({ timeout: SETTLED });
  await expect(problem).toHaveAttribute('data-kind', 'unreachable');
  await expect(problem).toContainText('dashboard --start harness');
  await expect(page.locator('g.graph-node')).toHaveCount(0);
});
