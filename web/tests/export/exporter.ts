/**
 * Draw one subject's showgraph in the real window, and write what it drew.
 *
 * `codecarto show export` writes a manifest of subjects and runs
 * `show-export.spec.ts` over it; `tests/e2e/show-export.spec.ts` runs the same
 * function over a fixture. For each view of a subject this opens the subject's
 * address, maximises the canvas (step 4, Read), waits for the fit to settle,
 * and writes:
 *
 * - **the picture**: the canvas's svg, its styles inlined so it draws the same
 *   outside the page, or, for the system view, which draws in HTML, a picture
 *   of the canvas as the page shows it;
 * - **the graph it drew**, as the window received it: the show route's gJGF,
 *   the code parse's streamed nodes and edges, or the composed system.
 *
 * A view the window cannot draw here is not drawn: the document carries the
 * window's own sentence for why (`/show/project/<name>/views`).
 *
 * NOTHING ABOUT THIS MACHINE IS WRITTEN. The show routes name the corpus they
 * read by its place on this disk; that field is replaced by the corpus's file
 * name, and the Python side refuses any document that still carries a path.
 */

import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { expect, type Page, type Response } from '@playwright/test';

export type View = 'estate' | 'code' | 'system' | 'full';

export interface ManifestSubject {
  kind: 'index' | 'family' | 'project';
  name: string;
  address: string;
  folder: string;
  views: View[];
  digest: string;
}

export interface Manifest {
  out: string;
  corpus: { repo: string; commit: string };
  drawn_by: { graph: string };
  drawn_at: string;
  sources: Record<string, { repo: string; commit: string | null }>;
  subjects: ManifestSubject[];
}

const SETTLED = 60_000;
/** The canvas a picture is drawn at: the dock at this size, step 4 maximising the canvas in it. */
export const VIEWPORT = { width: 1400, height: 900 };

interface ViewAnswer {
  available: boolean;
  problem?: string;
  remedy?: string;
  url?: string;
  depth?: number;
  floor?: number;
  components?: number;
}

/**
 * The view's sentence when the window cannot draw it here, as the document
 * states it. The window says a clone is not "beside this checkout", which is
 * true of one machine; a document is read on every machine, so it says what
 * the export read.
 */
function absence(subject: ManifestSubject, view: View, answer: ViewAnswer | undefined) {
  if (view === 'system' && answer?.problem?.startsWith('no clone of ')) {
    return {
      absent: true,
      problem: `${subject.name}'s system view is composed from a clone of it, and this export read none`,
      remedy: `export from a clone of ${subject.name} at its default branch's head`,
      where: `/show/project/${subject.name}/views`,
    };
  }
  return {
    absent: true,
    problem: answer?.problem ?? `the ${view} view of ${subject.name} could not be asked for`,
    remedy: answer?.remedy ?? '',
    where: `/show/project/${subject.name}/views`,
  };
}

/** The transform on the drawing, read until two reads 500 ms apart agree. */
async function settle(page: Page): Promise<void> {
  const view = page.locator('.graphRenderer > svg').first();
  let last = '';
  await expect.poll(async () => {
    const now = await view.evaluate((svg) => svg.querySelector('g')?.getAttribute('transform') ?? '');
    const still = now === last && now !== '';
    last = now;
    return still;
  }, { intervals: [500], timeout: SETTLED }).toBe(true);
}

/**
 * Every node the window was sent, drawn, and the drawing done. The canvas
 * draws a few nodes each frame after the stream has ended, then its edges,
 * then its outlines, tidies its names and fits again, and marks its svg
 * `data-drawn`. A picture taken as the zoom first stopped moving held four
 * nodes in five of a code map, with a hundred of its files' names over it; one
 * taken once every node was in held the whole corpus with its four thousand
 * edges still coming, no outline drawn, and two thousand names over it.
 */
async function drawnAll(page: Page, count: number): Promise<void> {
  const view = page.locator('.graphRenderer > svg').first();
  await expect(view.locator('g.graph-node')).toHaveCount(count, { timeout: SETTLED });
  await expect(view).toHaveAttribute('data-drawn', 'true', { timeout: SETTLED });
}

/**
 * Every node and name at the opacity it ends at. The canvas fades each in as
 * it is drawn, and a name the declutter hides or shows again once a zoom
 * settles fades too; a picture taken as the transform stopped moving held a
 * dozen names part-way, written into the file at the opacity they were caught at.
 */
export async function faded(page: Page): Promise<void> {
  const view = page.locator('.graphRenderer > svg').first();
  await expect.poll(() => view.evaluate((svg) =>
    [...svg.querySelectorAll('g.graph-node, text')].filter((el) => {
      const opacity = Number(getComputedStyle(el).opacity);
      return opacity > 0.001 && opacity < 0.999;
    }).length), { intervals: [250, 250, 500], timeout: SETTLED }).toBe(0);
}

/** Step 4, Read: the canvas alone, the drawing framed in it once its resize lands. */
async function readStep(page: Page): Promise<void> {
  await page.locator('.gl-steps__step[data-step="read"]').click();
  await expect(page.locator('.lm_maximised')).toHaveCount(1);
}

/**
 * The canvas's svg as a file: each element's drawn style inlined, the size it
 * is drawn at, and the canvas's own background behind it.
 */
async function svgOf(page: Page): Promise<string> {
  return page.locator('.graphRenderer > svg').first().evaluate((svg: SVGSVGElement) => {
    // Inherited: written where an element's differs from its parent's.
    const INHERITED = [
      'fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray',
      'font-family', 'font-size', 'font-weight', 'text-anchor', 'visibility',
    ];
    // Not inherited: written where an element's is not the initial value.
    const OWN: Record<string, string> = { opacity: '1', display: 'inline', 'dominant-baseline': 'auto' };
    const copy = svg.cloneNode(true) as SVGSVGElement;
    const from = [svg, ...svg.querySelectorAll('*')];
    const to = [copy, ...copy.querySelectorAll('*')];
    const drawn = new Map(from.map((el) => [el, getComputedStyle(el)]));
    from.forEach((el, i) => {
      const own = drawn.get(el)!;
      const parent = el === svg ? null : drawn.get(el.parentElement!) ?? null;
      const style = [
        ...INHERITED.filter((p) => !parent || own.getPropertyValue(p) !== parent.getPropertyValue(p)),
        ...Object.keys(OWN).filter((p) => own.getPropertyValue(p) !== OWN[p]),
      ].map((p) => `${p}:${own.getPropertyValue(p)}`).join(';');
      if (style) (to[i] as SVGElement).setAttribute('style', style);
      else (to[i] as SVGElement).removeAttribute('style');
    });
    // A picture holds what is drawn: a name the canvas keeps but does not
    // draw -- every name on the whole corpus drawn with none -- is left out.
    from.forEach((el, i) => {
      if (el !== svg && drawn.get(el)!.display === 'none') to[i].remove();
    });
    const box = svg.getBoundingClientRect();
    const width = Math.round(box.width);
    const height = Math.round(box.height);
    copy.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    copy.setAttribute('width', String(width));
    copy.setAttribute('height', String(height));
    copy.setAttribute('viewBox', `0 0 ${width} ${height}`);
    let paper = getComputedStyle(svg.parentElement!).backgroundColor;
    for (let el: Element | null = svg.parentElement; el && /rgba\(0, 0, 0, 0\)|transparent/.test(paper); el = el.parentElement) {
      paper = getComputedStyle(el).backgroundColor;
    }
    const back = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    back.setAttribute('width', '100%');
    back.setAttribute('height', '100%');
    back.setAttribute('fill', paper);
    copy.insertBefore(back, copy.firstChild);
    return new XMLSerializer().serializeToString(copy);
  });
}

/** The code parse's stream, as the nodes and edges it carried, and what its end said. */
function streamed(body: string): { nodes: Record<string, unknown>; edges: unknown[]; done: Record<string, any> } {
  const nodes: Record<string, unknown> = {};
  const edges: unknown[] = [];
  let done: Record<string, any> = {};
  for (const block of body.split(/\r?\n\r?\n/)) {
    const event = /^event: (\w+)/m.exec(block)?.[1];
    const data = /^data: (.*)$/m.exec(block)?.[1];
    if (!event || !data) continue;
    const value = JSON.parse(data);
    if (event === 'node') nodes[value.id] = value;
    if (event === 'edge') edges.push(value);
    if (event === 'done') done = value;
  }
  return { nodes, edges, done };
}

/**
 * The show route's metadata, with the corpus named by its file rather than its
 * place on this disk, and the caveat's clones said of the export: the window
 * says a member "had no clone beside this one", which is true of one machine.
 * The Python side refuses a document that still says it, so a change in the
 * window's wording fails the export rather than reaching a page.
 */
function placeless(metadata: Record<string, any>): Record<string, any> {
  const out: Record<string, any> = { ...metadata, source: 'families.json' };
  if (out.provenance) out.provenance = { ...out.provenance, source: 'families.json' };
  if (typeof out.caveat === 'string') {
    out.caveat = out.caveat.replace(
      /had no clone beside this one, or one git could not read,/g, 'had no clone this export could read,');
  }
  return out;
}

async function drawEstate(page: Page, subject: ManifestSubject, dir: string) {
  const route = subject.kind === 'index' ? '/show/index/gjgf' : `/show/${subject.kind}/${subject.name}/gjgf`;
  return drawShowgraph(page, route, `./?show=${subject.address}`, join(dir, 'estate.svg'));
}

/**
 * The index's code view, the whole corpus: every family, each project's code
 * map in it, from the code maps this export has written (`CODECARTO_SHOW_DOCS`).
 */
async function drawCorpus(page: Page, dir: string) {
  return drawShowgraph(page, '/show/corpus/gjgf', './?show=index&view=code', join(dir, 'code.svg'));
}

/**
 * The index's full view: the whole corpus again, every node drawn and no
 * name. Its graph is the code view's, so the document keeps its metadata
 * alone rather than the same graph twice.
 */
async function drawFullCorpus(page: Page, dir: string) {
  const drawn = await drawShowgraph(page, '/show/corpus/gjgf', './?show=index&view=full', join(dir, 'full.svg'));
  return { graph: 'the code view\'s', metadata: { ...drawn.metadata, names: false } };
}

async function drawShowgraph(page: Page, route: string, address: string, file: string) {
  const answered = page.waitForResponse((r: Response) => r.url().includes(route), { timeout: SETTLED });
  await page.goto(address);
  const results = (await (await answered).json()).results;
  await expect(page.locator('.graph-node').first()).toBeAttached({ timeout: SETTLED });
  await readStep(page);
  await drawnAll(page, Object.keys(results.graph?.nodes ?? {}).length);
  await settle(page);
  await faded(page);
  writeFileSync(file, await svgOf(page));
  return { graph: results.graph, metadata: placeless(results.metadata ?? {}) };
}

async function drawCode(page: Page, subject: ManifestSubject, dir: string, answer: ViewAnswer) {
  const answered = page.waitForResponse((r: Response) => r.url().includes('/parse/stream-url'), { timeout: SETTLED });
  await page.goto(`./?show=${subject.address}&view=code`);
  const body = await (await answered).text();
  const { done, ...graph } = streamed(body);
  await expect(page.locator('.graph-node').first()).toBeAttached({ timeout: SETTLED });
  await readStep(page);
  await drawnAll(page, Object.keys(graph.nodes).length);
  await settle(page);
  await faded(page);
  writeFileSync(join(dir, 'code.svg'), await svgOf(page));
  // The depth the floor drew it to (`stream_floor.py`): a page says which.
  return { graph, metadata: { url: answer.url, depth: done.depth ?? answer.depth ?? 1, floor: answer.floor ?? null,
                              truncated: 0 } };
}

async function drawSystem(page: Page, subject: ManifestSubject, dir: string, answer: ViewAnswer) {
  const answered = page.waitForResponse((r: Response) => r.url().includes(`/system/compose?repo=${encodeURIComponent(subject.name)}`), { timeout: SETTLED });
  await page.goto(`./?show=${subject.address}&view=system`);
  const composed = await (await answered).json();
  // The system view lays out its components in HTML once composed, and draws
  // its edges between them once they are laid out.
  await expect(page.locator('.sys-node').first()).toBeVisible({ timeout: SETTLED });
  await readStep(page);
  const canvas = page.locator('.lm_maximised .gl-panel--graph');
  await expect(canvas.locator('.sys-node').first()).toBeVisible();
  await page.waitForTimeout(1_500);
  await canvas.screenshot({ path: join(dir, 'system.png') });
  // The system view draws from the composed system, not from a graph.
  return { composed, metadata: { components: answer.components ?? 0 } };
}

/**
 * The system view's sentence when the clone it is composed from is not at the
 * default branch's head the document names, or null when it is. The view is
 * composed from the project's clone on this disk, which may be on another
 * branch or hold commits nobody else has; published, its picture would
 * describe a state no reader can see. The sentence names neither the disk nor
 * the clone's commit, which may be one only that clone holds.
 */
async function notAtHead(page: Page, subject: ManifestSubject, manifest: Manifest) {
  const where = `/system/compose?repo=${encodeURIComponent(subject.name)}`;
  const composed = await page.evaluate(async (url) => (await fetch(url)).json(), where);
  const at = String(composed?.commit ?? '');
  const head = manifest.sources[subject.name]?.commit ?? '';
  if (at && head.startsWith(at)) return null;
  return {
    absent: true,
    problem: `${subject.name}'s system view is composed from a clone of it, and the clone this export `
      + `read was not at its default branch's head, ${head.slice(0, 7) || 'unknown'}`,
    remedy: `export from a clone of ${subject.name} at its default branch's head`,
    where,
  };
}

/** Draw every view of `subject` and write its pictures and its show document under `manifest.out`. */
export async function exportSubject(page: Page, subject: ManifestSubject, manifest: Manifest): Promise<void> {
  const dir = join(manifest.out, ...subject.folder.split('/'));
  // The folder holds what this export writes and nothing older: a picture a
  // view no longer has would sit beside a document that does not name it.
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  await page.setViewportSize(VIEWPORT);
  await page.goto('./');
  // The walkthrough opens on a first visit; it is not part of any picture.
  await page.evaluate(() => localStorage.setItem('cc:help-dismissed', '1'));

  let answers: Record<string, ViewAnswer> = {};
  if (subject.kind === 'project') {
    // Asked from the page, as the window asks: what a page's routes answer is what it draws.
    answers = await page.evaluate(async (name) => {
      const asked = await fetch(`/show/project/${encodeURIComponent(name)}/views`);
      return (await asked.json()).results ?? {};
    }, subject.name);
  }

  const views: Record<string, unknown> = {};
  const files: Record<string, string> = {};
  for (const view of subject.views) {
    if (view === 'estate') {
      views.estate = await drawEstate(page, subject, dir);
      files.estate = 'estate.svg';
    } else if (subject.kind === 'index' && view === 'code') {
      views.code = await drawCorpus(page, dir);
      files.code = 'code.svg';
    } else if (subject.kind === 'index' && view === 'full') {
      views.full = await drawFullCorpus(page, dir);
      files.full = 'full.svg';
    } else if (!answers[view]?.available) {
      views[view] = absence(subject, view, answers[view]);
    } else if (view === 'code') {
      views.code = await drawCode(page, subject, dir, answers.code);
      files.code = 'code.svg';
    } else {
      const elsewhere = await notAtHead(page, subject, manifest);
      if (elsewhere) {
        views.system = elsewhere;
        continue;
      }
      views.system = await drawSystem(page, subject, dir, answers.system);
      files.system = 'system.png';
    }
  }

  const source = manifest.sources[subject.name];
  const document = {
    schema: 1,
    subject: { kind: subject.kind, name: subject.name },
    provenance: {
      claims: { ...manifest.corpus, digest: subject.digest },
      ...(source ? { source } : {}),
      drawn_by: manifest.drawn_by,
      drawn_at: manifest.drawn_at,
    },
    views,
    files,
  };
  writeFileSync(join(dir, 'show.json'), `${JSON.stringify(document, null, 1)}\n`);
}
