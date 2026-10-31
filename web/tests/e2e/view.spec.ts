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
  for (const view of ['estate', 'code']) {
    await page.goto(`/view.html?doc=${DOCS}/project/ztgui/show.json&view=${view}`);
    await drawn(page);
    const want = placedBy(document.views[view].graph.nodes);
    const got = await places(page);
    expect(Object.keys(got).sort()).toEqual(Object.keys(want).sort());
    for (const [id, [x, y]] of Object.entries(got)) {
      expect(x, id).toBeCloseTo(want[id][0], 2);
      expect(y, id).toBeCloseTo(want[id][1], 2);
    }
    await expect(page.locator('.view__subject')).toHaveText(`project:ztgui · ${view}`);
    await expect(page.locator('.view__handed')).toHaveText(`read from ${DOCS}/project/ztgui/show.json`);
    await expect(page.locator('.view__drawn')).toContainText('from quaternionmedia/ztgui at c698ae0');
    await expect(page.locator('.view__canvas .graph-legend')).toHaveCount(1);
  }
  // The code view carries no caveat, and the page invents none; the estate's is shown as written.
  await expect(page.locator('.view__caveat')).toBeHidden();
  await page.goto(`/view.html?doc=${DOCS}/project/ztgui/show.json`);
  await drawn(page);
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
    await expect(page.locator('.view__canvas')).toBeHidden();
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
  await expect(page.locator('.view__subject')).toHaveText('project:ztgui · estate');
  await drawn(page);
  await expect(page.locator('.view__handed')).toHaveText('opened from the file show.json');

  await page.evaluate((text) => {
    const carried = new DataTransfer();
    carried.items.add(new File([text], 'core.json', { type: 'application/json' }));
    window.dispatchEvent(new DragEvent('drop', { dataTransfer: carried, bubbles: true, cancelable: true }));
  }, fixture('family/core'));
  await expect(page.locator('.view__subject')).toHaveText('family:core · estate');
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
  await expect(page.locator('.view__subject')).toHaveText('family:core · estate');
  expect(failed).toEqual([]);
  expect(asked).toEqual([]);
});
