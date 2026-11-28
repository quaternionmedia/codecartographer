/**
 * The Threads panel, end to end.
 *
 * The harness is a separate process this suite does not start, so what the
 * window's own API answers for it is stubbed at the route: `/harness/threads`
 * and `/harness/thread` with documents in the shape `tests/test_threads.py`
 * holds the real routes to, and `/harness/thread/gjgf` with
 * `fixtures/thread-graph.json`, which is what the real route, serializer and
 * layout return for an invented conversation of five turns. The panel, the
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
const GRAPH = 'tests/e2e/fixtures/thread-graph.json';
const WHERE = 'http://127.0.0.1:3999/v1/threads';

const listed = (source: string, id: string, title: string | null, turns: number) => ({
  source, id, title, turns, last_seen: '2026-01-02T00:00:00Z', diverged: false, address: `alpha/delta/thread-${id}`,
});

/** An archive of three conversations; `over` replaces any part of it. */
function archive(over: Record<string, unknown> = {}) {
  return {
    where: WHERE,
    threads: [listed('ink', 't-1', 'Tidy the Shed', 5), listed('quill', 't-2', null, 1), listed('ink', 't-3', 'shed roof', 12)],
    shown: 3, more: 0, sources: { ink: 2, quill: 1 }, totals: { threads: 3 },
    generated_at: '2026-01-03T00:00:00Z',
    reading: { the_index_is_a_reading: 'It counts what was exported and indexed.' },
    ...over,
  };
}

const TEXTS = ['How do I tidy the shed before winter?', 'Start by emptying it onto the lawn.',
  'Then sort what is there into keep, give and tip.', 'What about the roof?', 'Check the felt for tears and patch them.'];
const ROLES = ['asker', 'helper', 'helper', 'asker', 'helper'];

/** The conversation as the panel is given it, holding its first `count` turns. */
function conversation(count = 5, mark = '5 u-5 40') {
  const rows = [];
  for (let index = count; index >= 1; index -= 1) {
    rows.push({ index, id: `u-${index}`, role: ROLES[index - 1], at: `2026-01-01T00:00:0${index}Z`, text: TEXTS[index - 1], cut: false });
  }
  const roles: Record<string, number> = {};
  for (const role of ROLES.slice(0, count)) roles[role] = (roles[role] ?? 0) + 1;
  return {
    where: `${WHERE}/ink/t-1`, source: 'ink', id: 't-1', title: 'Tidy the Shed', url: null, started_at: null,
    partial: false, turns: { count, roles, rows, shown: count, more: 0 }, drawn: count, mark, caveat: 'the order of turns',
  };
}

const envelope = (results: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ status: 200, message: 'Success', results }),
});

const graphAnswer = { status: 200, contentType: 'application/json', path: GRAPH };

/** The fixture graph before the conversation held its fifth turn, marked as that reading is. */
function graphBefore() {
  const answer = JSON.parse(readFileSync(GRAPH, 'utf8'));
  const graph = answer.results.graph;
  delete graph.nodes['turn:u-5'];
  graph.edges = graph.edges.filter(
    (found: { source: string; target: string }) => found.source !== 'turn:u-5' && found.target !== 'turn:u-5');
  answer.results.metadata.mark = '4 u-4 20';
  return { status: 200, contentType: 'application/json', body: JSON.stringify(answer) };
}

const node = (page: Page, id: string) => page.locator(`g.graph-node[data-node-id="${id}"]`);
const edge = (page: Page, from: string, to: string) =>
  page.locator(`line.stream-edge[data-from="${from}"][data-to="${to}"]`);
const pathOf = (request: Request | string) => new URL(typeof request === 'string' ? request : request.url()).pathname;

async function openThreads(page: Page): Promise<void> {
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: /^Threads$/ }).click();
  await page.locator('.gl-panel--threads').waitFor({ state: 'visible' });
}

/** Stand in for the three routes, each matched by its own path. */
async function stand(page: Page, how: {
  list?: (url: URL) => unknown; thread?: () => unknown; graph?: (url: URL) => Record<string, unknown>;
} = {}): Promise<void> {
  await page.route(/\/harness\/threads(\?|$)/, (route) =>
    route.fulfill(envelope(how.list ? how.list(new URL(route.request().url())) : archive())));
  await page.route(/\/harness\/thread\?/, (route) =>
    route.fulfill(envelope(how.thread ? how.thread() : conversation())));
  await page.route(/\/harness\/thread\/gjgf/, (route) =>
    route.fulfill(how.graph ? how.graph(new URL(route.request().url())) : graphAnswer));
}

test('the archive is listed in its own order, with what it says of itself', async ({ page }) => {
  // Mutations: sort the rows by title in the panel -- the untitled row is no
  // longer second; leave the archive's sentences out -- nothing says the
  // index counts what was exported; print a blank for a missing title.
  await stand(page, { list: () => archive({ more: 180 }) });
  await openThreads(page);
  const rows = page.locator('.threads__thread');
  await expect(rows).toHaveCount(3, { timeout: SETTLED });
  await expect(rows.nth(0).locator('.estate__name')).toHaveText('Tidy the Shed');
  await expect(rows.nth(0).locator('.estate-view__rung')).toHaveText('ink');
  await expect(rows.nth(0).locator('.estate__role')).toHaveText('5 turns');
  await expect(rows.nth(1)).toHaveAttribute('data-thread', 't-2');
  await expect(rows.nth(1).locator('.estate__name')).toHaveText('no title');
  await expect(rows.nth(1).locator('.estate__role')).toHaveText('1 turn');
  await expect(page.locator('.threads__more')).toHaveText(/^180 more the archive lists are not shown/);
  await expect(page.locator('.threads__reading')).toHaveText('It counts what was exported and indexed.');
  await expect(page.locator('.threads__generated')).toHaveText("the archive's index is of 2026-01-03T00:00:00Z");
  await expect(page.locator('.threads__list-where')).toHaveAttribute('href', WHERE);
  await expect(page.locator('[data-threads="chosen"]')).toHaveCount(0);
});

test('a source and a text narrow the list, and the archive is asked for them', async ({ page }) => {
  // Mutations: ask for the list without the source chosen -- every source is
  // listed again; ask on every key typed -- the harness is asked per letter.
  const asked: string[] = [];
  await stand(page, {
    list: (url) => {
      asked.push(url.search);
      return url.searchParams.get('source') === 'quill'
        ? archive({ threads: [listed('quill', 't-2', null, 1)], shown: 1 })
        : archive();
    },
  });
  await openThreads(page);
  await expect(page.locator('.threads__thread')).toHaveCount(3, { timeout: SETTLED });
  expect(asked).toEqual(['']);
  await expect(page.locator('.threads__source option')).toHaveText(['every source', 'ink (2)', 'quill (1)']);

  await page.locator('.threads__source').selectOption('quill');
  await expect(page.locator('.threads__thread')).toHaveCount(1, { timeout: SETTLED });
  expect(asked[1]).toBe('?source=quill');

  await page.locator('.threads__titled').fill('the shed');
  await page.waitForTimeout(400);
  expect(asked.length).toBe(2);
  await page.locator('.threads__list').click();
  await expect.poll(() => asked.length, { timeout: SETTLED }).toBe(3);
  expect(asked[2]).toBe('?source=quill&titled=the%20shed');
});

test('the panel only reads: its controls list, draw and follow, and nothing is sent but GET', async ({ page }) => {
  // Mutation: post from a row's control -- this fails.
  const sent: Request[] = [];
  page.on('request', (request) => {
    if (pathOf(request).includes('/harness')) sent.push(request);
  });
  await stand(page);
  await openThreads(page);
  const panel = page.locator('.gl-panel--threads');
  await expect(panel.locator('.threads__thread')).toHaveCount(3, { timeout: SETTLED });
  const archiveControls = panel.locator('[data-threads="archive"]').locator('button, input, select, textarea, a[href]');
  // The select, the text, the list button, a control per row, and the address.
  await expect(archiveControls).toHaveCount(7);
  await expect(panel.locator('.threads__draw')).toHaveText(['draw its turns', 'draw its turns', 'draw its turns']);

  await panel.locator('.threads__draw').first().click();
  await expect(node(page, 'turn:u-1')).toHaveCount(1, { timeout: SETTLED });
  await page.locator('.lm_tab', { hasText: /Threads/ }).click();
  const chosenControls = panel.locator('[data-threads="chosen"]').locator('button, input, select, textarea, a[href]');
  // The address the conversation was read from, and the follow box.
  await expect(chosenControls).toHaveCount(2);
  expect(sent.some((request) => pathOf(request).endsWith('/harness/thread/gjgf'))).toBe(true);
  expect(sent.filter((request) => request.method() !== 'GET')).toEqual([]);
});

test('draw its turns puts each turn and role on the canvas, an exchange a path of edges', async ({ page }) => {
  // Mutations: ask for the list's first conversation whatever row is pressed
  // -- the third row draws `t-1`; ask for no layout on the press -- the graph
  // is drawn by the window's algorithm; leave the row unmarked -- nothing
  // says which conversation is on the canvas.
  const asked: string[] = [];
  await stand(page, {
    graph: (url) => {
      asked.push(url.search);
      return graphAnswer;
    },
  });
  await openThreads(page);
  await expect(page.locator('.threads__thread')).toHaveCount(3, { timeout: SETTLED });
  await page.locator('.threads__thread[data-thread="t-3"] .threads__draw').click();
  await expect.poll(() => asked.length, { timeout: SETTLED }).toBe(1);
  expect(asked[0]).toBe('?source=ink&id=t-3&layout=Reading_Order');

  await page.locator('.lm_tab', { hasText: /Threads/ }).click();
  await page.locator('.threads__thread[data-thread="t-1"] .threads__draw').click();
  await expect.poll(() => asked.length, { timeout: SETTLED }).toBe(2);
  expect(asked[1]).toBe('?source=ink&id=t-1&layout=Reading_Order');
  for (const id of ['said:asker', 'replied:helper', 'turn:u-1', 'turn:u-2', 'turn:u-3', 'turn:u-4', 'turn:u-5']) {
    await expect(node(page, id), id).toHaveCount(1, { timeout: SETTLED });
  }
  await expect(page.locator('g.graph-node')).toHaveCount(7);
  for (const [from, to] of [['said:asker', 'turn:u-1'], ['turn:u-1', 'turn:u-2'], ['turn:u-1', 'turn:u-3'],
    ['turn:u-2', 'replied:helper'], ['said:asker', 'turn:u-4'], ['turn:u-4', 'turn:u-5']]) {
    await expect(edge(page, from, to), `${from} -> ${to}`).toHaveCount(1);
  }

  await page.locator('.lm_tab', { hasText: /Threads/ }).click();
  await expect(page.locator('.threads__thread[data-thread="t-1"]')).toHaveAttribute('data-chosen', 'yes');
  await expect(page.locator('.threads__thread[data-thread="t-3"]')).toHaveAttribute('data-chosen', 'no');
});

test('the conversation drawn shows its roles, how much is drawn and its newest turns first', async ({ page }) => {
  // Mutations: list the turns oldest first in the panel -- turn 1 heads the
  // list; leave out how many are drawn -- a cut picture reads as whole; show
  // the caveat strip for any graph -- it shows before this one is drawn.
  await stand(page, { thread: () => ({ ...conversation(), drawn: 3, partial: true }) });
  await openThreads(page);
  await expect(page.locator('.threads__thread')).toHaveCount(3, { timeout: SETTLED });
  await expect(page.locator('.threads-graph__caveat')).toHaveCount(0);
  await page.locator('.threads__draw').first().click();
  await expect(node(page, 'turn:u-1')).toHaveCount(1, { timeout: SETTLED });
  await page.locator('.lm_tab', { hasText: /Threads/ }).click();

  const chosen = page.locator('.threads__chosen');
  await expect(chosen.locator('.estate__name')).toHaveText('Tidy the Shed', { timeout: SETTLED });
  await expect(chosen.locator('.threads__roles')).toHaveText('asker 2 · helper 3');
  await expect(chosen.locator('.threads__drawn')).toHaveText('the newest 3 of 5 turns are drawn');
  await expect(chosen.locator('.threads__partial')).toHaveText('the harness says this conversation is partial');
  await expect(chosen.locator('.threads__where')).toHaveAttribute('href', `${WHERE}/ink/t-1`);
  const turns = page.locator('.threads__turn');
  await expect(turns).toHaveCount(5);
  await expect(turns.first()).toHaveAttribute('data-turn', '5');
  await expect(turns.first().locator('.estate__name')).toHaveText('5 · helper');
  await expect(turns.first().locator('.threads__said')).toHaveText('Check the felt for tears and patch them.');
  await expect(turns.first().locator('.estate__where')).toHaveText('2026-01-01T00:00:05Z');
  await expect(page.locator('.threads-graph__caveat')).toContainText('not which turn answers which');
});

test('a conversation the harness does not serve is its sentence in the panel, and nothing is drawn', async ({ page }) => {
  // Mutation: answer false from `drawThread` for a problem without holding it
  // -- the sentence is never shown.
  const gone = { unreadable: true, problem: "no ink thread 't-1'", remedy: '', where: `${WHERE}/ink/t-1` };
  await stand(page, { graph: () => envelope(gone) });
  await openThreads(page);
  await expect(page.locator('.threads__thread')).toHaveCount(3, { timeout: SETTLED });
  await page.locator('.threads__draw').first().click();
  const problem = page.locator('[data-threads="chosen"] .threads__problem');
  await expect(problem).toContainText("no ink thread 't-1'", { timeout: SETTLED });
  await expect(problem).toContainText('Nothing was drawn.');
  await expect(page.locator('g.graph-node')).toHaveCount(0);
});

test('a conversation whose turns are not read says so beside its drawing', async ({ page }) => {
  // Mutation: leave the reading's problem out of the panel -- the panel
  // waits on the harness for good.
  const unread = { unreachable: true, problem: 'nothing is answering at the harness', remedy: 'start it', where: `${WHERE}/ink/t-1` };
  await stand(page, { thread: () => unread });
  await openThreads(page);
  await expect(page.locator('.threads__thread')).toHaveCount(3, { timeout: SETTLED });
  await page.locator('.threads__draw').first().click();
  await expect(node(page, 'turn:u-1')).toHaveCount(1, { timeout: SETTLED });
  await page.locator('.lm_tab', { hasText: /Threads/ }).click();
  const problem = page.locator('[data-threads="chosen"] .threads-read__problem');
  await expect(problem).toContainText('nothing is answering at the harness', { timeout: SETTLED });
  await expect(problem).toContainText('Its turns are not listed.');
  await expect(page.locator('.threads__turn')).toHaveCount(0);
  await expect(page.locator('[data-threads="chosen"] .estate-view__pending')).toHaveCount(0);
});

test('an archive that is not answering is a sentence with a way back, and lists nothing', async ({ page }) => {
  // Mutation: show an empty list for a problem -- a harness that is down
  // reads as an archive that holds nothing.
  let down = true;
  await stand(page, {
    list: () => (down
      ? { unreachable: true, problem: 'nothing is answering at the harness', remedy: 'start it', where: WHERE }
      : archive()),
  });
  await openThreads(page);
  const panel = page.locator('.gl-panel--threads');
  await expect(panel).toContainText('nothing is answering at the harness', { timeout: SETTLED });
  await expect(panel).toContainText('An empty list would look like an archive that holds nothing.');
  await expect(panel.locator('.threads__thread')).toHaveCount(0);
  await expect(panel.locator('.threads__none')).toHaveCount(0);

  down = false;
  await panel.locator('.threads-list__retry').click();
  await expect(panel.locator('.threads__thread')).toHaveCount(3, { timeout: SETTLED });
});

test('followed, a reading with another turn draws the conversation again as it was asked for', async ({ page }) => {
  // Mutations: never draw again from a reading -- the graph is asked for once
  // and the fifth turn never arrives; ask for no layout when following --
  // the graph leaves reading order; compare nothing -- the graph is asked
  // for again for turns it already holds.
  test.setTimeout(120_000);
  let read = 0;
  const asked: string[] = [];
  await stand(page, {
    thread: () => {
      read += 1;
      return read === 1 ? conversation(4, '4 u-4 20') : conversation();
    },
    graph: (url) => {
      asked.push(url.search);
      return asked.length === 1 ? graphBefore() : graphAnswer;
    },
  });
  await openThreads(page);
  await expect(page.locator('.threads__thread')).toHaveCount(3, { timeout: SETTLED });
  await page.locator('.threads__draw').first().click();
  await expect(node(page, 'turn:u-4')).toHaveCount(1, { timeout: SETTLED });
  await expect(node(page, 'turn:u-5')).toHaveCount(0);
  await page.locator('.lm_tab', { hasText: /Threads/ }).click();
  await expect(page.locator('.threads__follow')).toBeChecked();
  await expect(page.locator('.threads__hint')).toContainText('drawn again when its turns change');

  // The panel reads the conversation again on its interval; it holds a turn more.
  await expect(node(page, 'turn:u-5')).toHaveCount(1, { timeout: 60_000 });
  expect(asked).toEqual(['?source=ink&id=t-1&layout=Reading_Order', '?source=ink&id=t-1&layout=Reading_Order']);
  await expect(page.locator('.threads__followed')).toContainText('for turns it had not held');
  await expect(page.locator('.threads__turn')).toHaveCount(5);

  // Another reading holds the same turns, and nothing is asked for again.
  const then = read;
  await expect.poll(() => read, { timeout: 60_000 }).toBeGreaterThan(then);
  await page.waitForTimeout(600);
  expect(asked.length).toBe(2);
});

test('unticked, the conversation drawn stays as drawn while the panel reads again', async ({ page }) => {
  // Mutation: follow whether or not the box is ticked -- the graph is asked
  // for a second time.
  test.setTimeout(120_000);
  let grown = false;
  let drawn = 0;
  await stand(page, {
    thread: () => (grown ? conversation() : conversation(4, '4 u-4 20')),
    graph: () => {
      drawn += 1;
      return graphBefore();
    },
  });
  await openThreads(page);
  await expect(page.locator('.threads__thread')).toHaveCount(3, { timeout: SETTLED });
  await page.locator('.threads__draw').first().click();
  await expect(node(page, 'turn:u-4')).toHaveCount(1, { timeout: SETTLED });
  await page.locator('.lm_tab', { hasText: /Threads/ }).click();
  await page.locator('.threads__follow').uncheck();
  await expect(page.locator('.threads__hint')).toContainText('stays as drawn until it is drawn again');
  grown = true;

  // The panel still reads: its list gains the fifth turn, and the canvas does not.
  await expect(page.locator('.threads__turn')).toHaveCount(5, { timeout: 60_000 });
  await page.waitForTimeout(600);
  expect(drawn).toBe(1);
  await expect(node(page, 'turn:u-5')).toHaveCount(0);
  await expect(page.locator('.threads__followed')).toHaveCount(0);
});
