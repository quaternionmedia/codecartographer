/**
 * The Compose panel, end to end, and the links into and out of it.
 *
 * The harness is a separate process this suite does not start, so what the
 * window's own API answers for it is stubbed at the route: `/designer/designs`
 * for the reading and for a save, `/designer/schema/{kind}` for a kind's
 * schema, `/designer/data` for the kinds, and `/designer/composition/gjgf`
 * with `fixtures/composition-graph.json`, which is what the real route,
 * serializer and layout return for the rows `tests/test_compose.py` invents.
 * The panel, the state actions, the wording functions and the canvas all run
 * as shipped. Nothing here reaches a harness, so nothing is saved anywhere.
 *
 * Each test names the mutation it was seen to fail under.
 */

import type { Page, Request, Route } from '@playwright/test';
import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const SETTLED = 20_000;
const GRAPH = 'tests/e2e/fixtures/composition-graph.json';
const TOPOLOGY = 'tests/e2e/fixtures/topology-alpha.json';

const design = (name: string, kind: string, config: Record<string, unknown> = {}, more: Record<string, unknown> = {}) => ({
  id: `id-${name}`, project: 'alpha', name, description: `about ${name}`, topology_type: kind, version: '1.0.0',
  config, address: `qm://alpha/topology/${name}`, capability: { status: 'runs', refusal: null }, ...more,
});

const held = (over: Record<string, unknown> = {}) => ({
  project: 'alpha',
  designs: [
    design('intake', 'delegation', { components: [{ name: 'reader', route_terms: [] }] }),
    design('review', 'council', { compose: ['intake'] }, {
      address: null, address_unknown: 'this checkout has no origin remote',
      capability: { status: 'refused', refusal: 'its arbiter decides', saved_anyway: 'designing a shape is not an act' },
    }),
  ],
  components: [{ name: 'reader', description: 'reads a page' }],
  components_read: { read: true, problem: '', remedy: '', where: 'http://127.0.0.1:3999/v1/topology-components' },
  saving: { available: true, problem: '', remedy: '' },
  where: 'http://127.0.0.1:3999/v1/topologies',
  ...over,
});

const SCHEMA = {
  schema: 1, topology: 'delegation', config_class: 'DelegationConfig', status: 'runs',
  json_schema: {
    $defs: { Strategy: { enum: ['capability_match', 'round_robin'], type: 'string' } },
    properties: {
      components: { type: 'array', items: { type: 'object' }, title: 'Components' },
      compose: { type: 'array', items: { type: 'string' }, title: 'Compose' },
      routing_strategy: { $ref: '#/$defs/Strategy', default: 'capability_match', title: 'Routing Strategy' },
      load_balance: { type: 'boolean', default: true, title: 'Load Balance' },
      max_queue_size: { type: 'integer', default: 100, minimum: 10, title: 'Max Queue Size' },
      slots: { type: 'object', title: 'Slots' },
    },
  },
};

const shape = (name: string) => ({
  name, options: [], missing: '', could_run: null,
  declared: { topology: name, status: 'runs', can_run: true, spends: false, writes: false, decides: false, why: `why ${name}`, needs: [] },
});

const KINDS = {
  instance: {
    identified: true, where: 'http://127.0.0.1:3999/health', pid: 1, port: 3999, database_fingerprint: 'a',
    started_at: null, session: null, version: '0', problem: '', remedy: '',
  },
  where: 'http://127.0.0.1:3999/v1/orchestration/plane',
  shapes: [shape('delegation'), shape('council')],
  could_run: { read: true, problem: '', remedy: '', where: '' },
  have: {}, never_supplied: null, statuses: ['runs'], needs: [], attested: [], drift: {}, reading: {},
};

const envelope = (results: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ status: 200, message: 'Success', results }),
});

interface Stubs {
  reading?: unknown;
  /** What a save answers; the default is the harness's row for what was posted. */
  save?: (posted: Record<string, unknown>) => unknown;
}

/** Stub every route the panel asks; return the requests made to `/designer`. */
async function stub(page: Page, how: Stubs = {}): Promise<Request[]> {
  const sent: Request[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.includes('/designer')) sent.push(request);
  });
  await page.route('**/designer/designs*', (route: Route) => {
    if (route.request().method() === 'POST') {
      const posted = route.request().postDataJSON() as Record<string, unknown>;
      const answer = how.save
        ? how.save(posted)
        : { saved: true, design: design(String(posted.name), String(posted.topology_type), posted.config as Record<string, unknown>), where: 'http://127.0.0.1:3999/v1/topologies' };
      return route.fulfill(envelope(answer));
    }
    return route.fulfill(envelope(how.reading ?? held()));
  });
  await page.route('**/designer/schema/*', (route) => route.fulfill(envelope(SCHEMA)));
  await page.route('**/designer/data*', (route) => route.fulfill(envelope(KINDS)));
  await page.route('**/designer/composition/gjgf*', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', path: GRAPH }));
  return sent;
}

async function openPanel(page: Page, label: RegExp, panelClass: string): Promise<void> {
  await page.locator('.gl-app-header__add-btn').click();
  await page.locator('.gl-add-panel-menu__item', { hasText: label }).click();
  await page.locator(panelClass).waitFor({ state: 'visible' });
}

async function openCompose(page: Page, how: Stubs = {}): Promise<Request[]> {
  const sent = await stub(page, how);
  await page.goto('/');
  await dismissOnboardingModal(page);
  await openPanel(page, /^Compose$/, '.gl-panel--compose');
  await expect(page.locator('.compose__form')).toBeVisible({ timeout: SETTLED });
  return sent;
}

const posts = (sent: Request[]) => sent.filter((request) => request.method() === 'POST');
const node = (page: Page, id: string) => page.locator(`g.graph-node[data-node-id="${id}"]`);
const field = (page: Page, name: string) => page.locator(`.compose__form [data-field="${name}"]`);

async function chooseKind(page: Page, kind = 'delegation'): Promise<void> {
  await page.locator('.compose__kind').selectOption(kind);
  await expect(field(page, 'max_queue_size')).toBeVisible({ timeout: SETTLED });
}

test('the form is built from the harness\'s schema for the kind chosen, at its defaults', async ({ page }) => {
  // Mutation: render a choice as a text input -- the strategy has no choices.
  await openCompose(page);
  await expect(page.locator('.compose__kind option')).toHaveText(['choose a kind', 'delegation', 'council']);
  await expect(page.locator('.compose__form [data-kind]')).toHaveCount(0);
  await chooseKind(page);

  await expect(field(page, 'routing_strategy').locator('select')).toHaveValue('capability_match');
  await expect(field(page, 'routing_strategy').locator('option')).toHaveText(['capability_match', 'round_robin']);
  await expect(field(page, 'load_balance').locator('input')).toBeChecked();
  await expect(field(page, 'max_queue_size').locator('input')).toHaveValue('100');
  await expect(field(page, 'max_queue_size').locator('input')).toHaveAttribute('min', '10');
  await expect(field(page, 'max_queue_size').locator('label')).toHaveText('Max Queue Size');
  await expect(page.locator('.compose__unoffered[data-field="slots"]')).toContainText('slots is not offered here');
  await expect(field(page, 'compose').locator('.compose__reference')).toHaveText([/^\s*intake/, /^\s*review/]);
  await expect(field(page, 'components').locator('.compose__reference')).toHaveText([/^\s*reader/]);
});

test('a reference ticked is drawn at once: the draft and what it names so far reach the canvas', async ({ page }) => {
  // Mutation: draw only on the button -- ticking a design asks for no graph.
  const sent = await openCompose(page);
  await chooseKind(page);
  await page.locator('.compose__name').fill('triage');
  const drawn = () => sent.filter((request) => new URL(request.url()).pathname.endsWith('/composition/gjgf'));
  expect(drawn()).toHaveLength(0);

  await field(page, 'compose').locator('[data-reference="intake"] input').check();
  await expect(node(page, 'draft')).toHaveCount(1, { timeout: SETTLED });
  await expect(node(page, 'design:intake')).toHaveCount(1);
  await expect(page.locator('line.stream-edge[data-from="draft"][data-to="design:intake"]')).toHaveCount(1);
  const asked = new URL(drawn()[0].url()).searchParams;
  expect(asked.get('draft')).toBe('true');
  expect(asked.get('name')).toBe('triage');
  expect(asked.get('kind')).toBe('delegation');
  expect(asked.get('compose')).toBe('intake');
  await expect(page.locator('.compose-graph__caveat')).toContainText('The draft is what is being composed');
  expect(posts(sent)).toEqual([]);
});

test('save posts the design once as filled in, and the harness\'s row and verdict are shown', async ({ page }) => {
  // Mutation: send the values without `configOf` -- the queue size is the
  // text "25".
  const sent = await openCompose(page);
  await chooseKind(page);
  await page.locator('.compose__name').fill('triage');
  await page.locator('.compose__description').fill('routes work');
  await field(page, 'max_queue_size').locator('input').fill('25');
  await field(page, 'load_balance').locator('input').uncheck();
  await field(page, 'components').locator('[data-reference="reader"] input').check();
  await page.locator('.compose__save').click();

  const outcome = page.locator('.compose__outcome');
  await expect(outcome).toHaveAttribute('data-kind', 'saved', { timeout: SETTLED });
  await expect(outcome.locator('.compose__saved')).toHaveText('the harness saved triage. Nothing ran.');
  await expect(outcome.locator('.compose__verdict')).toHaveText(['status runs', 'address qm://alpha/topology/triage']);
  expect(posts(sent)).toHaveLength(1);
  expect(posts(sent)[0].postDataJSON()).toEqual({
    name: 'triage', topology_type: 'delegation', description: 'routes work', project: '',
    config: {
      components: [{ name: 'reader' }], routing_strategy: 'capability_match', load_balance: false, max_queue_size: 25,
    },
  });
  // The list is read again, and the name is cleared for the next design.
  await expect(page.locator('.compose__name')).toHaveValue('');
  expect(sent.filter((request) => request.method() === 'GET'
    && new URL(request.url()).pathname.endsWith('/designer/designs')).length).toBeGreaterThan(1);
});

test('the harness\'s refusal stands beside each field it is about, and what was typed is kept', async ({ page }) => {
  // Mutation: drop the messages from a setting's control -- none stands beside the queue size.
  await openCompose(page, {
    save: () => ({
      refused: true, status: 422, problem: 'the harness did not save the design (422)', remedy: '',
      where: 'http://127.0.0.1:3999/v1/topologies',
      errors: [
        { field: 'config.max_queue_size', message: 'Input should be greater than or equal to 10' },
        { field: 'name', message: 'a name is lowercase with hyphens' },
        { field: 'version', message: 'not a version' },
      ],
    }),
  });
  await chooseKind(page);
  await page.locator('.compose__name').fill('Bad Name');
  await field(page, 'max_queue_size').locator('input').fill('3');
  await page.locator('.compose__save').click();

  await expect(page.locator('.compose__outcome')).toHaveAttribute('data-kind', 'refused', { timeout: SETTLED });
  await expect(page.locator('.compose__refused')).toHaveText('the harness did not save the design (422)');
  await expect(field(page, 'max_queue_size').locator('.compose__error'))
    .toHaveText('Input should be greater than or equal to 10');
  await expect(field(page, 'name').locator('.compose__error')).toHaveText('a name is lowercase with hyphens');
  await expect(page.locator('.compose__error--elsewhere')).toHaveText(['version: not a version']);
  await expect(field(page, 'load_balance').locator('.compose__error')).toHaveCount(0);
  await expect(page.locator('.compose__name')).toHaveValue('Bad Name');
  await expect(field(page, 'max_queue_size').locator('input')).toHaveValue('3');
});

test('where the window does not relay a save, the panel says so, lists the designs and posts nothing', async ({ page }) => {
  // Mutation: enable the button whatever the reading says -- a press posts a design.
  const sent = await openCompose(page, {
    reading: held({
      saving: {
        available: false, problem: 'a design is not saved from here: the request came from another machine',
        remedy: 'open this window on the machine the harness runs on',
      },
    }),
  });
  await chooseKind(page);
  await page.locator('.compose__name').fill('triage');

  await expect(page.locator('.compose__away')).toHaveText(
    'a design is not saved from here: the request came from another machine — open this window on the machine the harness runs on');
  // After the page has redrawn for what was typed: read at once, the button is
  // still disabled for the blank name it had before.
  await page.waitForTimeout(400);
  await expect(page.locator('.compose__save')).toBeDisabled();
  await page.locator('.compose__name').press('Enter');
  await expect(page.locator('.compose__design')).toHaveCount(2);
  await page.waitForTimeout(500);
  expect(posts(sent)).toEqual([]);
});

test('each saved design is listed with what the harness says of it, what it references, and where it leads', async ({ page }) => {
  // Mutation: leave the link to the harness's row without its address.
  await openCompose(page);
  const review = page.locator('.compose__design[data-design="review"]');
  await expect(review.locator('.compose__verdict')).toHaveText([
    'status refused', 'refused to run: its arbiter decides', 'designing a shape is not an act',
    'no address: this checkout has no origin remote',
  ], { timeout: SETTLED });
  await expect(review.locator('.compose__composes')).toHaveText('composes intake');
  await expect(review.locator('.estate-view__rung')).toHaveText('council');

  const intake = page.locator('.compose__design[data-design="intake"]');
  await expect(intake.locator('.compose__verdict')).toHaveText(['status runs', 'address qm://alpha/topology/intake']);
  await expect(intake.locator('.compose__uses')).toHaveText('uses reader');
  await expect(intake.locator('a.compose__link')).toHaveAttribute('href', 'http://127.0.0.1:3999/v1/topologies/intake');
  // No kind is chosen yet, so nothing can be composed of it.
  await expect(intake.locator('.compose__add')).toHaveCount(0);

  await chooseKind(page);
  await intake.locator('.compose__add').click();
  await expect(field(page, 'compose').locator('[data-reference="intake"] input')).toBeChecked();
  await expect(node(page, 'draft')).toHaveCount(1, { timeout: SETTLED });

  await review.locator('.compose__to-kind').click();
  await expect(page.locator('.gl-panel--designer')).toBeVisible({ timeout: SETTLED });
});

test('a shape\'s row in the Designer panel leads to a design of that kind and to its drawing', async ({ page }) => {
  // Mutations: open the Compose panel without the kind -- its form stays on
  // "choose a kind"; drop the kind from the drawing's request -- the harness
  // is asked for whichever shape was drawn last.
  await stub(page);
  const drawn: string[] = [];
  await page.route('**/topology/gjgf*', (route) => {
    drawn.push(new URL(route.request().url()).searchParams.get('kind') ?? '');
    return route.fulfill({ status: 200, contentType: 'application/json', path: TOPOLOGY });
  });
  await page.goto('/');
  await dismissOnboardingModal(page);
  await openPanel(page, /^Designer$/, '.gl-panel--designer');

  const council = page.locator('.designer__shape[data-shape="council"]');
  await expect(council.locator('.designer__links button')).toHaveText(['draw this shape', 'compose one'], { timeout: SETTLED });
  await expect(page.locator('.designer__where a')).toHaveAttribute('href', 'http://127.0.0.1:3999/v1/orchestration/plane');

  await council.locator('.designer__to-compose').click();
  await expect(page.locator('.gl-panel--compose')).toBeVisible({ timeout: SETTLED });
  await expect(page.locator('.compose__kind')).toHaveValue('council');
  await expect(field(page, 'max_queue_size')).toBeVisible({ timeout: SETTLED });

  await page.locator('.lm_tab', { hasText: 'Designer' }).click();
  await council.locator('.designer__to-drawing').click();
  await expect.poll(() => drawn, { timeout: SETTLED }).toEqual(['council']);
});

test('a harness that is not answering is a sentence with a way back, and offers no form', async ({ page }) => {
  // Mutation: drop `readHeld()` from the retry -- the form never arrives.
  let asked = 0;
  await stub(page);
  await page.route('**/designer/designs*', (route) => {
    asked += 1;
    return route.fulfill(envelope(asked === 1
      ? {
          unreachable: true, problem: 'nothing is answering at http://127.0.0.1:3999',
          remedy: 'start it with `uv run qm dashboard --start harness`', where: 'http://127.0.0.1:3999/v1/topologies',
        }
      : held()));
  });
  await page.goto('/');
  await dismissOnboardingModal(page);
  await openPanel(page, /^Compose$/, '.gl-panel--compose');

  const problem = page.locator('.compose__problem');
  await expect(problem).toHaveAttribute('data-kind', 'unreachable', { timeout: SETTLED });
  await expect(problem.locator('.compose__problem-remedy')).toContainText('--start harness');
  await expect(page.locator('.compose__form')).toHaveCount(0);

  await problem.locator('.compose__retry').click();
  await expect(page.locator('.compose__form')).toBeVisible({ timeout: SETTLED });
  await expect(page.locator('.compose__problem')).toHaveCount(0);
});
