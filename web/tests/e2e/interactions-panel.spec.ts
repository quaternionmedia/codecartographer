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

import { readFileSync } from 'node:fs';

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

/** A reading that holds as many rows as the fixture graph was drawn from. */
const level = (rows = 8) => {
  const read = reading();
  return { ...read, interactions: { ...read.interactions, more: rows - read.interactions.shown } };
};

const node = (page: Page, id: string) => page.locator(`g.graph-node[data-node-id="${id}"]`);
const name = (page: Page, id: string) => page.locator(`svg text[data-node-id="${id}"]`);
const edge = (page: Page, from: string, to: string) =>
  page.locator(`line.stream-edge[data-from="${from}"][data-to="${to}"]`);

/** Where the canvas drew a node on screen: the centre of its shape. */
async function placeOf(page: Page, id: string): Promise<{ x: number; y: number }> {
  const box = await node(page, id).locator('path').boundingBox();
  if (!box) throw new Error(`no place for ${id}`);
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
}

test('the panel only reads: its button draws, its checkboxes say how, and it sends nothing but GET', async ({ page }) => {
  // Mutation: add a `button` to a row in `interactions_panel.ts` -- this fails.
  const sent: Request[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.includes('/harness')) sent.push(request);
  });
  await page.route('**/harness/gjgf*', (route) => route.fulfill(graphAnswer));
  await openInteractions(page, level());

  const panel = page.locator('.gl-panel--interactions');
  await expect(panel.locator('[data-ref="ins-1"]')).toBeVisible({ timeout: SETTLED });
  const controls = panel.locator('button, input, select, textarea, a[href]');
  await expect(controls).toHaveCount(3);
  await expect(controls.nth(0)).toHaveText('draw as a graph');
  await expect(controls.nth(1)).toHaveAttribute('type', 'checkbox');
  await expect(controls.nth(2)).toHaveAttribute('type', 'checkbox');

  await controls.nth(0).click();
  await expect(node(page, 'harness')).toHaveCount(1, { timeout: SETTLED });
  expect(sent.some((request) => new URL(request.url()).pathname.endsWith('/harness/gjgf'))).toBe(true);
  expect(sent.filter((request) => request.method() !== 'GET')).toEqual([]);
});

async function drawGraph(page: Page): Promise<void> {
  await page.route('**/harness/gjgf*', (route) => route.fulfill(graphAnswer));
  await openInteractions(page, level());
  await page.locator('.interactions__draw').click();
  await expect(node(page, 'harness')).toHaveCount(1, { timeout: SETTLED });
}

test('draw as a graph puts each thing a row names on the canvas, and a turn is a path of edges', async ({ page }) => {
  // Mutations: answer false from `drawInteractions` before it reads -- nothing
  // is drawn; ask `/harness/interactions` in `harnessGraph` -- what comes back
  // is a reading and no graph.
  await drawGraph(page);

  for (const id of ['nobody', 'name:detail.client:editor-7', 'instruction:ins-1', 'question:ask-1',
    'name:responded_by:ada', 'way:protocol', 'way:voice', 'way:typed', 'tool:echo', 'instructions:unnamed',
    'project:alpha', 'chat:c-1', 'session:s-1']) {
    await expect(node(page, id), id).toHaveCount(1);
  }
  await expect(page.locator('g.graph-node')).toHaveCount(14);

  // The turn: its client, the instruction, the consent question, who answered.
  await expect(edge(page, 'name:detail.client:editor-7', 'instruction:ins-1')).toHaveCount(1);
  await expect(edge(page, 'instruction:ins-1', 'question:ask-1')).toHaveCount(1);
  const answered = edge(page, 'question:ask-1', 'name:responded_by:ada');
  await expect(answered).toHaveCount(1);
  await expect(answered).toHaveAttribute('data-style', 'solid');
  await expect(answered.locator('title')).toHaveText('answered approve');
  await expect(page.locator('line.stream-edge')).toHaveCount(15);
});

test('every name is drawn with no setting changed, and a turn runs left to right on one line', async ({ page }) => {
  // Mutations: have `namedGraph` answer for a showgraph alone -- the names
  // stay off until Graph Settings turns them on; drop a node's `x` and `y`
  // in `flattenNodes` -- the canvas places the turn on a ring.
  await drawGraph(page);

  const names = page.locator('svg text[data-node-id]');
  await expect(names).toHaveCount(14);
  const hidden = await names.evaluateAll((texts) =>
    texts.filter((text) => (text as SVGElement).style.display === 'none').length);
  expect(hidden).toBe(0);
  await expect(name(page, 'name:detail.client:editor-7')).toHaveText('editor-7');
  await expect(name(page, 'question:ask-1')).toHaveText('consent · responded');
  await expect(name(page, 'instructions:unnamed')).toHaveText('2 instructions');
  // Outward at the ends of the reading, above in the middle of it.
  await expect(name(page, 'name:detail.client:editor-7')).toHaveAttribute('text-anchor', 'end');
  await expect(name(page, 'name:responded_by:ada')).toHaveAttribute('text-anchor', 'start');
  await expect(name(page, 'instruction:ins-1')).toHaveAttribute('text-anchor', 'middle');

  const turn = [];
  for (const id of ['name:detail.client:editor-7', 'instruction:ins-1', 'question:ask-1', 'name:responded_by:ada']) {
    turn.push(await placeOf(page, id));
  }
  const across = turn.map((at) => at.x);
  expect(across).toEqual([...across].sort((a, b) => a - b));
  expect(across[1] - across[0]).toBeGreaterThan(20);
  // The middle gap is the widest: the two names written above it need the room.
  expect(across[2] - across[1]).toBeGreaterThan(across[1] - across[0]);
  for (const at of turn) expect(Math.abs(at.y - turn[0].y)).toBeLessThan(1);
  // Its chat and session are tucked under it; what names nobody is lower.
  expect((await placeOf(page, 'chat:c-1')).y).toBeGreaterThan(turn[0].y);
  expect((await placeOf(page, 'instructions:unnamed')).y).toBeGreaterThan((await placeOf(page, 'chat:c-1')).y);
  expect((await placeOf(page, 'way:protocol')).y).toBeLessThan(turn[0].y);
});

test('an edge of a row that names nobody is dashed, a counted edge is wider, and the reading is coloured', async ({ page }) => {
  // Mutations, all where the canvas draws an edge: read `edge.style` and not
  // `metadata.style` -- no line is dashed; take the width from the styling
  // alone -- the counted edge is as wide as the rest; read `edge.color` and
  // not `metadata.color` -- every edge is the one default grey.
  await drawGraph(page);

  const unnamed = edge(page, 'nobody', 'instructions:unnamed');
  await expect(unnamed).toHaveAttribute('data-style', 'dashed');
  await expect(unnamed).toHaveAttribute('stroke-dasharray', '6,4');
  await expect(unnamed).toHaveAttribute('stroke-width', '3.25');
  await expect(unnamed.locator('title')).toHaveText('instructed ×2');
  const named = edge(page, 'name:detail.client:editor-7', 'instruction:ins-1');
  await expect(named).not.toHaveAttribute('stroke-dasharray', /.*/);
  await expect(named).toHaveAttribute('stroke-width', '1.5');
  await expect(page.locator('line.stream-edge[data-style="dashed"]')).toHaveCount(2);

  // The fixture's three tool runs are one edge from nobody.
  const ran = edge(page, 'nobody', 'tool:echo');
  await expect(ran).toHaveAttribute('data-style', 'dashed');
  await expect(ran).toHaveAttribute('stroke-width', '5');
  await expect(ran.locator('title')).toHaveText('ran ×3');

  // The three edges of the reading have a colour each; the rest are one grey.
  await expect(named).toHaveAttribute('stroke', '#6db2ff');
  await expect(edge(page, 'instruction:ins-1', 'question:ask-1')).toHaveAttribute('stroke', '#e0c069');
  await expect(edge(page, 'question:ask-1', 'name:responded_by:ada')).toHaveAttribute('stroke', '#5ac8b0');
  await expect(edge(page, 'instruction:ins-1', 'way:protocol')).toHaveAttribute('stroke', '#6b7480');
  await expect(ran).toHaveAttribute('stroke', '#6b7480');
});

test('the key to the edges is in the panel while the graph is drawn, in the colours drawn', async ({ page }) => {
  // Mutations: leave `keyShown` out of the panel -- there is no key; draw
  // every sample in the text's colour -- the key does not show the colours
  // the edges are drawn in.
  await page.route('**/harness/gjgf*', (route) => route.fulfill(graphAnswer));
  await openInteractions(page, level());
  const key = page.locator('.gl-panel--interactions .interactions__key');
  await expect(page.locator('.interactions__draw')).toBeVisible({ timeout: SETTLED });
  await expect(key).toHaveCount(0);

  await page.locator('.interactions__draw').click();
  await expect(key).toBeVisible({ timeout: SETTLED });
  const entries = key.locator('.interactions__key-entry');
  await expect(entries).toHaveCount(5);
  for (const [kinds, colour] of [['instructed', '#6db2ff'], ['asked', '#e0c069'], ['answered', '#5ac8b0']]) {
    const entry = key.locator(`[data-kinds="${kinds}"]`);
    await expect(entry).toHaveText(kinds);
    await expect(entry.locator('line')).toHaveAttribute('stroke', colour);
  }
  const rest = key.locator('[data-kinds="recorded by,way in,for,turn,in session,ran"]');
  await expect(rest).toHaveText('recorded by, way in, for, turn, in session, ran');
  await expect(rest.locator('line')).toHaveAttribute('stroke', '#6b7480');
  const dashed = key.locator('.interactions__key-dashed');
  await expect(dashed).toHaveText('names nobody');
  await expect(dashed.locator('line')).toHaveAttribute('stroke-dasharray', '6,4');
});

test('the graph is asked for in reading order on the press, and by the algorithm Graph Settings then names', async ({ page }) => {
  // Mutations: ask for reading order on every run of the action -- choosing
  // Circular draws reading order again; ask for no layout on the press -- the
  // graph is drawn by whatever algorithm the window had, Spring.
  const asked: string[] = [];
  await page.route('**/harness/gjgf*', (route) => {
    asked.push(new URL(route.request().url()).searchParams.get('layout') ?? '');
    return route.fulfill(graphAnswer);
  });
  await openInteractions(page, level());
  await page.locator('.interactions__draw').click();
  await expect(node(page, 'harness')).toHaveCount(1, { timeout: SETTLED });
  expect(asked).toEqual(['Reading_Order']);

  // The reader's next choice of algorithm applies, as it does to any drawing.
  await page.locator('.lm_tab', { hasText: /Graph Settings/ }).click();
  const algorithm = page.locator('.panel-settings__group', { hasText: 'Algorithm' }).locator('select');
  await algorithm.waitFor({ timeout: SETTLED });
  await algorithm.selectOption('circular_layout');
  await expect.poll(() => asked.length, { timeout: SETTLED }).toBe(2);
  expect(asked[1]).toBe('Circular');

  // And the press asks for reading order again.
  await page.locator('.lm_tab', { hasText: /Interactions/ }).click();
  await page.locator('.interactions__draw').click();
  await expect.poll(() => asked.length, { timeout: SETTLED }).toBe(3);
  expect(asked[2]).toBe('Reading_Order');
});

test('the graph is asked for as rows, and with every node once the checkbox is ticked', async ({ page }) => {
  // Mutations: ask for no detail on the press -- the route draws every node;
  // drop the detail when Graph Settings redraws -- a graph drawn as rows
  // gains its sources and projects on a change of algorithm; ignore the
  // checkbox -- the ticked press asks for rows again.
  const asked: string[] = [];
  await page.route('**/harness/gjgf*', (route) => {
    asked.push(new URL(route.request().url()).searchParams.get('detail') ?? '');
    return route.fulfill(graphAnswer);
  });
  await openInteractions(page, level());
  const every = page.locator('.interactions__every-node');
  await expect(every).not.toBeChecked();
  await page.locator('.interactions__draw').click();
  await expect(node(page, 'harness')).toHaveCount(1, { timeout: SETTLED });
  expect(asked).toEqual(['rows']);

  // A change of algorithm redraws the same rows.
  await page.locator('.lm_tab', { hasText: /Graph Settings/ }).click();
  const algorithm = page.locator('.panel-settings__group', { hasText: 'Algorithm' }).locator('select');
  await algorithm.waitFor({ timeout: SETTLED });
  await algorithm.selectOption('circular_layout');
  await expect.poll(() => asked.length, { timeout: SETTLED }).toBe(2);
  expect(asked[1]).toBe('rows');

  await page.locator('.lm_tab', { hasText: /Interactions/ }).click();
  await every.check();
  await page.locator('.interactions__draw').click();
  await expect.poll(() => asked.length, { timeout: SETTLED }).toBe(3);
  expect(asked[2]).toBe('all');
});

test('unticked, a drawn graph stays as drawn while the panel reads again, and says when the harness has moved on', async ({ page }) => {
  // Mutations: leave the stale sentence out of the panel -- a graph of an
  // older reading says nothing; follow whether or not the box is ticked --
  // the graph is asked for more than once and a reader's place on the canvas
  // is lost.
  test.setTimeout(90_000);
  let read = 0;
  let drawn = 0;
  await page.route('**/harness/gjgf*', (route) => {
    drawn += 1;
    return route.fulfill(graphAnswer);
  });
  await page.route('**/harness/interactions*', (route) => {
    read += 1;
    return route.fulfill(envelope(level(read === 1 ? 8 : 9)));
  });
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Interactions$/ }).click();
  await page.locator('.interactions__follow').uncheck();
  await expect(page.locator('.interactions__draw-hint')).toContainText('stays as drawn until it is drawn again');
  await page.locator('.interactions__draw').click();
  await expect(node(page, 'harness')).toHaveCount(1, { timeout: SETTLED });
  const stale = page.locator('.interactions__stale');
  await expect(stale).toHaveCount(0);

  // The panel reads again on its interval; the harness now holds one row more.
  await expect(stale).toHaveText(
    'The harness held 8 rows when this graph was drawn and holds 9 now. Draw again to read them.',
    { timeout: 40_000 });
  expect(read).toBeGreaterThan(1);
  expect(drawn).toBe(1);
  await expect(page.locator('g.graph-node')).toHaveCount(14);
  await expect(page.locator('.interactions__followed')).toHaveCount(0);
});

/** The fixture graph before the harness held its tool run: one node and its edges fewer. */
function graphBefore() {
  const answer = JSON.parse(readFileSync(GRAPH, 'utf8'));
  const graph = answer.results.graph;
  delete graph.nodes['tool:echo'];
  graph.edges = graph.edges.filter(
    (found: { source: string; target: string }) => found.source !== 'tool:echo' && found.target !== 'tool:echo');
  return { status: 200, contentType: 'application/json', body: JSON.stringify(answer) };
}

/** A reading whose newest row is one the first reading did not list. */
const moved = () => {
  const read = level(9);
  const rows = [row({ at: '2026-01-01T00:00:50', act: 'ran', what: 'echo', ref: 'run-2' }), ...read.interactions.rows];
  return { ...read, interactions: { ...read.interactions, rows, shown: rows.length, more: 9 - rows.length } };
};

test('followed, a reading that lists another row draws the graph again as it was asked for', async ({ page }) => {
  // Mutations: never draw again from a reading -- the graph is asked for once
  // and the tool's node never arrives; ask for no layout when following --
  // the graph leaves reading order for the window's algorithm; drop the
  // detail when following -- a graph drawn with every node comes back as
  // rows; draw again on every reading -- the graph is asked for a third time
  // for rows it already holds.
  test.setTimeout(90_000);
  let read = 0;
  const asked: string[] = [];
  await page.route('**/harness/gjgf*', (route) => {
    const params = new URL(route.request().url()).searchParams;
    asked.push(`${params.get('layout')} ${params.get('detail')}`);
    return route.fulfill(asked.length === 1 ? graphBefore() : graphAnswer);
  });
  await page.route('**/harness/interactions*', (route) => {
    read += 1;
    return route.fulfill(envelope(read === 1 ? level(8) : moved()));
  });
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Interactions$/ }).click();
  await expect(page.locator('.interactions__follow')).toBeChecked({ timeout: SETTLED });
  await expect(page.locator('.interactions__draw-hint')).toContainText(
    'the graph is drawn again when the rows the harness lists change');
  await page.locator('.interactions__every-node').check();
  await page.locator('.interactions__draw').click();
  await expect(node(page, 'harness')).toHaveCount(1, { timeout: SETTLED });
  await expect(page.locator('g.graph-node')).toHaveCount(13);
  await expect(node(page, 'tool:echo')).toHaveCount(0);

  // The panel reads again on its interval; the harness lists a tool run more.
  await expect(node(page, 'tool:echo')).toHaveCount(1, { timeout: 40_000 });
  await expect(page.locator('g.graph-node')).toHaveCount(14);
  expect(asked).toEqual(['Reading_Order all', 'Reading_Order all']);
  await page.locator('.lm_tab', { hasText: /Interactions/ }).click();
  await expect(page.locator('.interactions__followed')).toContainText('for rows the harness had not listed');
  await expect(page.locator('.interactions__stale')).toHaveCount(0);

  // Two more readings list the same rows, and nothing is asked for again.
  const then = read;
  await expect.poll(() => read, { timeout: 40_000 }).toBeGreaterThan(then + 1);
  expect(asked.length).toBe(2);
});

test('followed, a graph the harness does not answer for again stays on the canvas, with the problem in the panel', async ({ page }) => {
  // Mutation: clear the canvas before following -- a harness that stops
  // answering empties the graph a reader was looking at.
  test.setTimeout(90_000);
  let read = 0;
  let drawn = 0;
  await page.route('**/harness/gjgf*', (route) => {
    drawn += 1;
    return route.fulfill(drawn === 1 ? graphAnswer : envelope({
      unreachable: true, problem: 'nothing is answering at the harness', remedy: 'start it',
      where: 'http://127.0.0.1:3999/v1/instructions',
    }));
  });
  await page.route('**/harness/interactions*', (route) => {
    read += 1;
    return route.fulfill(envelope(read === 1 ? level(8) : moved()));
  });
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Interactions$/ }).click();
  await page.locator('.interactions__draw').click();
  await expect(node(page, 'harness')).toHaveCount(1, { timeout: SETTLED });

  await expect.poll(() => drawn, { timeout: 40_000 }).toBeGreaterThan(1);
  await page.waitForTimeout(600);
  await expect(page.locator('g.graph-node')).toHaveCount(14);
  await page.locator('.lm_tab', { hasText: /Interactions/ }).click();
  await expect(page.locator('.gl-panel--interactions')).toContainText('nothing is answering at the harness');
});

test('the caveat and the harness it was read from sit in the panel only while its graph is drawn', async ({ page }) => {
  // Mutation: pass `kind: 'topology'` to the panel's `Provenance` -- the strip
  // never shows for this graph.
  await page.route('**/harness/gjgf*', (route) => route.fulfill(graphAnswer));
  await openInteractions(page, level());
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
  await openInteractions(page, level());
  await page.locator('.interactions__draw').click();

  const problem = page.locator('.interactions__problem');
  await expect(problem).toBeVisible({ timeout: SETTLED });
  await expect(problem).toHaveAttribute('data-kind', 'unreachable');
  await expect(problem).toContainText('dashboard --start harness');
  await expect(page.locator('g.graph-node')).toHaveCount(0);
});
