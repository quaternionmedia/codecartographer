/**
 * The page without a server (`view.html`): it draws the documents it is
 * handed, where their documents place them, and asks no codecarto route.
 *
 * Every test refuses, and counts, each request the page makes to a path the
 * backend mounts (`vite.config.js`'s `API_PATHS`, read from the file), on any
 * origin: a page that needed one fails here rather than quietly reaching the
 * backend this run starts. The documents are served from an origin of their
 * own (`https://docs.test`), as the corpus's site serves its own, and the
 * built page reads them from beside it, as GitHub Pages would serve both.
 *
 * Seen to fail, each against a mutation of what it names: the page asking
 * `/show/subjects` as it boots; a code view drawn in the compound layout,
 * which moves its nodes off the document's places; a pointer view not refused
 * as one; a dropped file left unread; a caveat written as markup; a `?doc=`
 * read from any scheme; the page's build naming its assets from the root of
 * the origin.
 */

import { existsSync, readFileSync } from 'node:fs';

import { expect, test, type Page } from '@playwright/test';

import { STATIC_SITE } from '../../playwright.config';

const API_PATHS = [...readFileSync('vite.config.js', 'utf8')
  .match(/const API_PATHS = \[([^\]]*)\]/)![1].matchAll(/'([^']+)'/g)].map((m) => m[1]);

const DOCS = 'https://docs.test/qm/show';
const FIXTURES = 'tests/e2e/fixtures/show';
const fixture = (subject: string): string => readFileSync(`${FIXTURES}/${subject}/show.json`, 'utf8');

/** Serve the fixtures from their own origin; refuse, and count, every request to a codecarto route. */
async function served(page: Page): Promise<string[]> {
  const asked: string[] = [];
  await page.route(
    (url) => API_PATHS.some((path) => url.pathname === path || url.pathname.startsWith(`${path}/`)),
    (route) => {
      asked.push(route.request().url());
      return route.abort();
    },
  );
  await page.route(`${DOCS}/**`, (route) => {
    const subject = new URL(route.request().url()).pathname.replace(/^\/qm\/show\//, '').replace(/\/show\.json$/, '');
    if (!existsSync(`${FIXTURES}/${subject}/show.json`)) return route.fulfill({ status: 404, body: 'not found' });
    return route.fulfill({ body: fixture(subject), contentType: 'application/json',
                           headers: { 'access-control-allow-origin': '*' } });
  });
  return asked;
}

/** Each drawn node's place in the graph's own coordinates, by id. */
async function places(page: Page): Promise<Record<string, [number, number]>> {
  return page.locator('.view__canvas g.graph-node').evaluateAll((nodes) => Object.fromEntries(nodes.map((node) => {
    const at = /translate\(([-\d.e]+),\s*([-\d.e]+)\)/.exec(node.getAttribute('transform') ?? '');
    return [node.getAttribute('data-node-id'), at ? [Number(at[1]), Number(at[2])] : [0, 0]];
  })));
}

/** Where a show document's view places each node: in its metadata for an estate, on the node for code. */
function placedBy(nodes: Record<string, any>): Record<string, [number, number]> {
  return Object.fromEntries(Object.entries(nodes).map(([id, node]) => {
    const at = typeof node.x === 'number' ? node : node.metadata;
    return [id, [at.x, at.y]];
  }));
}

const drawn = (page: Page) => expect(page.locator('body[data-drawn="true"]')).toBeAttached({ timeout: 15_000 });

test("a show document's estate and code views are drawn where it places them, asking no codecarto route", async ({ page }) => {
  const asked = await served(page);
  const document = JSON.parse(fixture('project/ztgui'));
  for (const [view, title] of [['estate', 'ztgui · estate'], ['code', 'ztgui · code map']]) {
    await page.goto(`/view.html?doc=${DOCS}/project/ztgui/show.json&view=${view}`);
    await drawn(page);
    const want = placedBy(document.views[view].graph.nodes);
    const got = await places(page);
    expect(Object.keys(got).sort()).toEqual(Object.keys(want).sort());
    for (const [id, [x, y]] of Object.entries(got)) {
      expect(x, id).toBeCloseTo(want[id][0], 2);
      expect(y, id).toBeCloseTo(want[id][1], 2);
    }
    await expect(page.locator('.view__subject')).toHaveText(title);
    await expect(page.locator('.view__handed')).toHaveText(`read from ${DOCS}/project/ztgui/show.json`);
    await expect(page.locator('.view__drawn')).toContainText('from quaternionmedia/ztgui at c698ae0');
    await expect(page.locator('.view__canvas .graph-legend')).toHaveCount(1);
  }
  // The code view carries no caveat, and the page invents none; the estate's is shown as written,
  // folded under what the drawing can say.
  await expect(page.locator('.view__caveat')).toHaveText('');
  await page.goto(`/view.html?doc=${DOCS}/project/ztgui/show.json`);
  await drawn(page);
  await expect(page.locator('.view__caveat')).toBeHidden();
  await page.getByText('What this drawing can say').click();
  await expect(page.locator('.view__caveat')).toBeVisible();
  await expect(page.locator('.view__caveat')).toHaveText(document.views.estate.metadata.caveat);
  expect(asked).toEqual([]);
});

test('a pointer view, a composed system and a view its document lacks are each refused by name', async ({ page }) => {
  const asked = await served(page);
  for (const [subject, view, problem, remedy] of [
    ['family/core', 'code', 'the code view of family:core is not a graph in its document but a pointer', '?show=family:core&view=code'],
    ['project/moat', 'system', 'the system view of project:moat is a composed system', '?show=project:moat&view=system'],
    ['project/ztgui', 'imports', 'the show document of project:ztgui has no imports view', 'estate, code, system'],
  ]) {
    await page.goto(`/view.html?doc=${DOCS}/${subject}/show.json&view=${view}`);
    await expect(page.locator('.view__problem-what')).toContainText(`Not drawn, read from ${DOCS}/${subject}/show.json: ${problem}`);
    await expect(page.locator('.view__problem-remedy')).toContainText(remedy);
    // Under the refusal, the subject's first view the page draws, and the address says so.
    await drawn(page);
    await expect(page.locator('.view__views [aria-current="page"]')).toHaveAttribute('data-view', 'estate');
    expect(new URL(page.url()).searchParams.get('view')).toBe('estate');
  }
  await page.goto(`/view.html?doc=${DOCS}/project/none/show.json`);
  await expect(page.locator('.view__problem-what')).toContainText('answered 404');
  expect(asked).toEqual([]);
});

test('a file opened, a file dropped and a paste are each read as a document named by URL is', async ({ page }) => {
  const asked = await served(page);
  await page.goto('/view.html');
  await expect(page.locator('.view__empty')).toBeVisible();

  await page.locator('.view__chooser').setInputFiles(`${FIXTURES}/project/ztgui/show.json`);
  await expect(page.locator('.view__subject')).toHaveText('ztgui · estate');
  await drawn(page);
  await expect(page.locator('.view__handed')).toHaveText('opened from the file show.json');

  await page.evaluate((text) => {
    const carried = new DataTransfer();
    carried.items.add(new File([text], 'core.json', { type: 'application/json' }));
    window.dispatchEvent(new DragEvent('drop', { dataTransfer: carried, bubbles: true, cancelable: true }));
  }, fixture('family/core'));
  await expect(page.locator('.view__subject')).toHaveText('core · the family');
  await drawn(page);
  await expect(page.locator('.view__handed')).toHaveText('opened from the file core.json');

  const paste = (text: string) => page.evaluate((pasted) => {
    const carried = new DataTransfer();
    carried.setData('text/plain', pasted);
    document.dispatchEvent(new ClipboardEvent('paste', { clipboardData: carried, bubbles: true, cancelable: true }));
  }, text);
  const graph = {
    graph: { nodes: { a: { label: 'a', x: 0, y: 0 }, b: { label: 'b' } }, edges: [{ source: 'a', target: 'b' }] },
    metadata: { subject: 'an app', layout: 'Spring' },
  };
  await paste(JSON.stringify(graph));
  await expect(page.locator('.view__subject')).toHaveText('an app');
  await drawn(page);
  await expect(page.locator('.view__handed')).toHaveText('pasted');
  await expect(page.locator('.view__counts')).toHaveText(
    '2 nodes, 1 edges; 1 arrived with no position and are placed on their depth ring');

  // A document that is not one is refused, and what is drawn stays drawn.
  await paste('not a graph');
  await expect(page.locator('.view__problem-what')).toContainText('Not drawn, pasted: it is not JSON');
  await expect(page.locator('.view__canvas g.graph-node')).toHaveCount(2);
  expect(asked).toEqual([]);
});

test('nothing a document says is read as markup, and a ?doc= of another scheme is not read', async ({ page }) => {
  const asked = await served(page);
  await page.goto('/view.html');
  const marked = '<img src="x" onerror="window.__marked = true">';
  await page.evaluate((text) => {
    const carried = new DataTransfer();
    carried.setData('text/plain', text);
    document.dispatchEvent(new ClipboardEvent('paste', { clipboardData: carried }));
  }, JSON.stringify({
    graph: { nodes: { a: { label: marked, x: 0, y: 0 } }, edges: [] },
    metadata: { subject: marked, caveat: `<b id="marked">${marked}</b>` },
  }));
  await drawn(page);
  await expect(page.locator('.view__caveat')).toHaveText(`<b id="marked">${marked}</b>`);
  await expect(page.locator('.view__subject')).toHaveText(marked);
  await expect(page.locator('img, #marked')).toHaveCount(0);
  expect(await page.evaluate(() => (window as { __marked?: boolean }).__marked)).toBeUndefined();

  await page.goto('/view.html?doc=javascript:window.__ran=true');
  await expect(page.locator('.view__problem-what')).toContainText('is not an http or https address');
  expect(await page.evaluate(() => (window as { __ran?: boolean }).__ran)).toBeUndefined();
  expect(asked).toEqual([]);
});

test('the built page opens from a subfolder of a plain static server, its root the same page', async ({ page }) => {
  const asked = await served(page);
  const failed: string[] = [];
  page.on('response', (answer) => { if (answer.status() >= 400) failed.push(`${answer.status()} ${answer.url()}`); });
  // Its documents beside it, as the corpus's site and this repository's Pages share an origin.
  await page.goto(`${STATIC_SITE}/codecartographer/?doc=../qm/show/project/ztgui/show.json&view=code`);
  await drawn(page);
  await expect(page.locator('.view__canvas g.graph-node')).toHaveCount(39);
  await expect(page.locator('.view__handed')).toHaveText(`read from ${STATIC_SITE}/qm/show/project/ztgui/show.json`);
  await page.goto(`${STATIC_SITE}/codecartographer/view.html?doc=/qm/show/family/core/show.json`);
  await drawn(page);
  await expect(page.locator('.view__subject')).toHaveText('core · the family');
  expect(failed).toEqual([]);
  expect(asked).toEqual([]);
});

// ---------------------------------------------------------------------------
// The journeys `docs/journeys.md` names: each test below walks one, as a
// reader would, and `tests/test_journeys.py` holds the page to their titles.
// ---------------------------------------------------------------------------

/** The corpus's show folder, named as a reader names another one. */
const WALKED = `docs=${DOCS}/`;
const trailOf = (page: Page) => page.locator('.view__trail');
const viewNamed = (page: Page, label: string) => page.locator('.view__views').getByText(label, { exact: true });
const listed = (page: Page, name: string) => page.locator('.view__here').getByRole('link', { name, exact: true });

test("journey: a reader at the page's own address sees every family, and what can be opened from it", async ({ page }) => {
  const asked = await served(page);
  await page.goto(`${STATIC_SITE}/codecartographer/`);
  await drawn(page);
  await expect(trailOf(page)).toHaveText('every family');
  await expect(page.locator('.view__views [aria-current="page"]')).toHaveText('every family');
  await expect(viewNamed(page, 'shared imports')).toHaveAttribute('href', '?show=index&view=imports');
  const shown = new Set(Object.values(JSON.parse(fixture('index')).views.estate.graph.nodes)
    .map((node: any) => node.metadata.show as string).filter(Boolean));
  const families = [...shown].filter((show) => show.startsWith('family:')).length;
  await expect(page.locator('.view__here-summary'))
    .toHaveText(`${families} families and ${shown.size - families} projects to open`);
  await expect(page.locator('.view__hint')).toContainText('Double-click a family or a project to open it');
  // The page's own address is left as it is: it names every family already.
  expect(page.url()).toBe(`${STATIC_SITE}/codecartographer/`);
  expect(asked).toEqual([]);
});

test("journey: a reader walks down from every family to a project's code map, and Back walks up again", async ({ page }) => {
  const asked = await served(page);
  await page.goto(`/view.html?${WALKED}`);
  await drawn(page);

  await page.locator('.view__here-summary').click();
  await page.keyboard.type('infra');
  await listed(page, 'infra').click();
  await expect(page).toHaveTitle('infra · the family · Code Cartographer');
  await expect(trailOf(page)).toHaveText('every family›infra');
  expect(new URL(page.url()).searchParams.get('show')).toBe('family:infra');
  await drawn(page);

  // A double-click on a project opens it, as in the window.
  await page.locator('.view__canvas g.graph-node[data-node-id="repo::ztgui"]').dblclick();
  await expect(page).toHaveTitle('ztgui · estate · Code Cartographer');
  await expect(trailOf(page)).toHaveText('every family›infra›ztgui');
  await drawn(page);

  await viewNamed(page, 'code map').click();
  await expect(page).toHaveTitle('ztgui · code map · Code Cartographer');
  expect(new URL(page.url()).searchParams.get('view')).toBe('code');
  await drawn(page);
  const want = placedBy(JSON.parse(fixture('project/ztgui')).views.code.graph.nodes);
  expect(Object.keys(await places(page)).sort()).toEqual(Object.keys(want).sort());

  for (const title of ['ztgui · estate', 'infra · the family', 'the corpus · every family']) {
    await page.goBack();
    await expect(page).toHaveTitle(`${title} · Code Cartographer`);
    await drawn(page);
  }
  expect(page.url()).toMatch(/\/view\.html\?docs=/);
  expect(asked).toEqual([]);
});

test('journey: a reader who follows a link to a nested family steps up its trail', async ({ page }) => {
  const asked = await served(page);
  await page.goto(`/view.html?show=family:instruments&${WALKED}`);
  await drawn(page);
  // Its own document does not say what holds it; the index, read once, does.
  await expect(trailOf(page)).toHaveText('every family›performing›instruments');
  await trailOf(page).getByRole('link', { name: 'performing' }).click();
  await expect(page).toHaveTitle('performing · the family · Code Cartographer');
  await expect(trailOf(page)).toHaveText('every family›performing');
  await trailOf(page).getByRole('link', { name: 'every family' }).click();
  await expect(page).toHaveTitle('the corpus · every family · Code Cartographer');
  expect(asked).toEqual([]);
});

test('journey: a reader copies the address of what is drawn, and it opens the same drawing', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const asked = await served(page);
  await page.goto(`/view.html?${WALKED}`);
  await drawn(page);
  await page.locator('.view__here-summary').click();
  await listed(page, 'ztgui').click();
  await expect(page).toHaveTitle('ztgui · estate · Code Cartographer');
  await viewNamed(page, 'code map').click();
  await drawn(page);
  await page.getByRole('button', { name: 'copy link' }).click();
  await expect(page.locator('.view__copy')).toHaveText('copied');
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toBe(page.url());

  const again = await context.newPage();
  const askedAgain = await served(again);
  await again.goto(copied);
  await drawn(again);
  await expect(again).toHaveTitle('ztgui · code map · Code Cartographer');
  await expect(trailOf(again)).toHaveText('every family›infra›ztgui');
  expect([...asked, ...askedAgain]).toEqual([]);
});

test('journey: a reader shown a view the page cannot draw is told why, and where it is drawn', async ({ page }) => {
  const asked = await served(page);
  // Linked to a family's code view, a pointer: the family is drawn under why not.
  await page.goto(`/view.html?show=family:core&view=code&${WALKED}`);
  await drawn(page);
  await expect(page).toHaveTitle('core · the family · Code Cartographer');
  await expect(page.locator('.view__problem-what'))
    .toContainText('the code view of family:core is not a graph in its document but a pointer');
  await expect(page.locator('.view__window')).toHaveAttribute('href', 'http://localhost:2718/app?show=family:core&view=code');
  expect(new URL(page.url()).searchParams.get('view')).toBeNull();

  // A view offered but not drawn here says so when pressed, and what is drawn stays drawn.
  await page.goto(`/view.html?show=project:moat&${WALKED}`);
  await drawn(page);
  await expect(page.locator('.view__problem')).toBeHidden();
  await viewNamed(page, 'system').click();
  await expect(page.locator('.view__problem-what')).toContainText('the system view of project:moat is a composed system');
  await expect(page.locator('.view__window')).toHaveAttribute('href', 'http://localhost:2718/app?show=project:moat&view=system');
  await expect(page).toHaveTitle('moat · estate · Code Cartographer');
  await expect(page.locator('.view__canvas g.graph-node')).toHaveCount(5);
  await page.getByRole('button', { name: 'dismiss' }).click();
  await expect(page.locator('.view__problem')).toBeHidden();

  // A project the show folder holds no document for: the window draws it from its clone.
  await page.goto(`/view.html?${WALKED}`);
  await drawn(page);
  await page.locator('.view__here-summary').click();
  await listed(page, 'benchmark').click();
  await expect(page.locator('.view__problem-what')).toContainText('the show folder holds no document for project:benchmark');
  await expect(page.locator('.view__window')).toHaveAttribute('href', 'http://localhost:2718/app?show=project:benchmark');
  await expect(page).toHaveTitle('the corpus · every family · Code Cartographer');
  expect(asked).toEqual([]);
});

test("journey: a reader's own document, opened from a file, has its views drawn in hand", async ({ page }) => {
  const asked = await served(page);
  await page.goto('/view.html');
  await expect(page.locator('.view__empty')).toBeVisible();
  await page.locator('.view__chooser').setInputFiles(`${FIXTURES}/project/ztgui/show.json`);
  await drawn(page);
  await expect(page.locator('.view__subject')).toHaveText('ztgui · estate');
  // A file has no address: no trail, nothing to copy, and its views are its own.
  await expect(trailOf(page)).toBeHidden();
  await expect(page.locator('.view__copy')).toBeHidden();
  await viewNamed(page, 'code map').click();
  await drawn(page);
  await expect(page.locator('.view__subject')).toHaveText('ztgui · code map');
  await expect(page.locator('.view__canvas g.graph-node')).toHaveCount(39);
  expect(new URL(page.url()).search).toBe('');
  expect(asked).toEqual([]);
});

test('journey: from the keyboard alone, a reader filters the list and opens a project', async ({ page }) => {
  const asked = await served(page);
  await page.goto(`/view.html?${WALKED}`);
  await drawn(page);
  await page.locator('.view__here-summary').focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.view__here-filter')).toBeFocused();
  await page.keyboard.type('ztg');
  await expect(page.locator('.view__here-item:not([hidden])')).toHaveCount(1);
  await page.keyboard.press('Enter');
  await expect(page).toHaveTitle('ztgui · estate · Code Cartographer');
  // Escape folds the list it opened, and gives the focus back.
  await page.locator('.view__here-summary').focus();
  await page.keyboard.press('Enter');
  await page.keyboard.press('Escape');
  await expect(page.locator('.view__here')).not.toHaveAttribute('open', '');
  await expect(page.locator('.view__here-summary')).toBeFocused();
  expect(asked).toEqual([]);
});
