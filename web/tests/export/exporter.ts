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

export type View = 'estate' | 'code' | 'system' | 'imports';

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
 * The canvas's svg as a file: what it draws, at the size it is drawn at, on
 * the canvas's own background -- and nothing a page showing it as an image
 * does not show (`docs/scale.md`, rules 4 and 5):
 *
 * - **each colour once.** An element's drawn style is written as its
 *   presentation attributes, where it differs from what it inherits or from
 *   the initial value, and never again in a `style` beside them;
 * - **no hidden element**, by `display` or by `visibility`, unless something
 *   inside it is shown: the declutter keeps every name it hides, and core's
 *   family code map hid fifteen thousand;
 * - **no `<title>`**, which a browser shows only on hovering a picture opened
 *   on its own, and **no `data-*`**, the window's interaction data;
 * - **one decimal** for every coordinate, and **the fit settled to fixed
 *   steps** -- its scale to steps of 1%, held about the canvas's centre, and
 *   its offset to the pixel -- so the same drawing writes the same bytes.
 */
export async function svgOf(page: Page): Promise<string> {
  return page.locator('.graphRenderer > svg').first().evaluate((svg: SVGSVGElement) => {
    // Inherited: written where an element's differs from its parent's.
    const INHERITED = [
      'fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray',
      'font-family', 'font-size', 'font-weight', 'text-anchor', 'visibility',
    ];
    // Not inherited: written where an element's is not the initial value.
    const OWN: Record<string, string> = { opacity: '1', display: 'inline', 'dominant-baseline': 'auto' };
    // Coordinates, to one decimal. A scale is not one, and keeps its digits.
    const GEOMETRY = ['x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'dx', 'dy',
      'width', 'height', 'd', 'points'];
    const tenth = (text: string) =>
      text.replace(/-?\d*\.\d+(?:e[-+]?\d+)?/gi, (n) => String(Math.round(Number(n) * 10) / 10));
    // `rgb(r, g, b)` as `#rrggbb`: the same colour in under half the bytes.
    const hex = (value: string) => value.replace(/^rgb\((\d+), (\d+), (\d+)\)$/, (_, ...rgb: string[]) =>
      `#${rgb.slice(0, 3).map((c) => Number(c).toString(16).padStart(2, '0')).join('')}`);
    const copy = svg.cloneNode(true) as SVGSVGElement;
    const from = [svg, ...svg.querySelectorAll('*')];
    const to = [copy, ...copy.querySelectorAll('*')];
    const drawn = new Map(from.map((el) => [el, getComputedStyle(el)]));
    from.forEach((el, i) => {
      const own = drawn.get(el)!;
      const parent = el === svg ? null : drawn.get(el.parentElement!) ?? null;
      const target = to[i] as SVGElement;
      for (const p of INHERITED) {
        if (!parent || own.getPropertyValue(p) !== parent.getPropertyValue(p)) target.setAttribute(p, hex(own.getPropertyValue(p)));
        else target.removeAttribute(p);
      }
      for (const p of Object.keys(OWN)) {
        if (own.getPropertyValue(p) !== OWN[p]) target.setAttribute(p, hex(own.getPropertyValue(p)));
        else target.removeAttribute(p);
      }
      target.removeAttribute('style');
      for (const name of target.getAttributeNames()) {
        if (name.startsWith('data-')) target.removeAttribute(name);
        else if (GEOMETRY.includes(name)) target.setAttribute(name, tenth(target.getAttribute(name)!));
        else if (name === 'transform') {
          target.setAttribute(name, target.getAttribute(name)!.replace(/translate\(([^)]*)\)/g, (_, at) => `translate(${tenth(at)})`));
        }
      }
    });
    // A picture holds what is drawn. Ancestors come before what they hold, so
    // walking the elements backwards meets what an element holds first.
    const shows = new Set<Element>();
    for (let i = from.length - 1; i > 0; i--) {
      const style = drawn.get(from[i])!;
      const shown = style.display !== 'none' && (style.visibility !== 'hidden' || shows.has(from[i]));
      if (shown && from[i].tagName !== 'title') shows.add(from[i].parentElement!);
      if (!shown || from[i].tagName === 'title') to[i].remove();
    }
    const box = svg.getBoundingClientRect();
    const width = Math.round(box.width);
    const height = Math.round(box.height);
    // The fit, settled: its scale to the nearest step of 1%, its offset moved to
    // keep the point under the canvas's centre there, and rounded to the pixel.
    const zoom = copy.querySelector('g');
    const fit = /^translate\(([-\d.e]+),\s*([-\d.e]+)\)\s*scale\(([-\d.e]+)\)$/i.exec(zoom?.getAttribute('transform') ?? '');
    if (zoom && fit) {
      const [tx, ty, k] = fit.slice(1).map(Number);
      const step = Math.log(1.01);
      const settled = Number(Math.exp(Math.round(Math.log(k) / step) * step).toPrecision(6));
      const x = Math.round(width / 2 - (width / 2 - tx) * settled / k);
      const y = Math.round(height / 2 - (height / 2 - ty) * settled / k);
      zoom.setAttribute('transform', `translate(${x},${y}) scale(${settled})`);
    }
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
 * A family's code view: the family with each of its projects' code map in it,
 * its subfamilies' too, from the code maps this export has just written
 * (`CODECARTO_SHOW_DOCS`). The document names each project whose code it drew
 * and the commit its map was drawn from (`metadata.code`), and keeps none of
 * their graphs again: each is its own project's document's.
 */
async function drawFamilyCode(page: Page, subject: ManifestSubject, dir: string) {
  const drawn = await drawShowgraph(page, `/show/family/${subject.name}/code/gjgf`,
    `./?show=${subject.address}&view=code`, join(dir, 'code.svg'));
  return { graph: "each project's code view's", metadata: drawn.metadata };
}

/**
 * What the index's or a family's members import in common, and of each
 * other (`docs/scale.md`, rule 8). The server reads each project at the
 * commit its code map was drawn from, which the document names
 * (`metadata.imports.read`), so the picture shows no state only a clone on
 * this machine holds; a member whose clone lacks that commit is named unread.
 */
async function drawImports(page: Page, subject: ManifestSubject, dir: string) {
  const route = subject.kind === 'index' ? '/show/index/imports/gjgf' : `/show/family/${subject.name}/imports/gjgf`;
  return drawShowgraph(page, route, `./?show=${subject.address}&view=imports`, join(dir, 'imports.svg'));
}

async function drawShowgraph(page: Page, route: string, address: string, file: string) {
  // **READ ON ITS WAY TO THE PAGE, NOT FROM THE PAGE'S NETWORK LOG.** The log
  // keeps ten megabytes of an answer, and the whole corpus's was several
  // times that: "evicted from inspector cache", and no picture.
  let results: { graph?: { nodes?: object }; metadata?: Record<string, unknown> } | null = null;
  const asked = (url: URL) => url.pathname.endsWith(route);
  await page.route(asked, async (request) => {
    const response = await request.fetch();
    results = (await response.json()).results;
    await request.fulfill({ response });
  });
  try {
    await page.goto(address);
    await expect.poll(() => results !== null, { timeout: SETTLED }).toBe(true);
  } finally {
    await page.unroute(asked);
  }
  const answer = results!;
  await expect(page.locator('.graph-node').first()).toBeAttached({ timeout: SETTLED });
  await readStep(page);
  await drawnAll(page, Object.keys(answer.graph?.nodes ?? {}).length);
  await settle(page);
  await faded(page);
  writeFileSync(file, await svgOf(page));
  return { graph: answer.graph, metadata: placeless(answer.metadata ?? {}) };
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
  return { graph, metadata: { url: answer.url, depth: done.depth ?? answer.depth ?? 1,
                              ...(answer.floor ? { floor: answer.floor } : {}), truncated: 0 } };
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
    } else if (subject.kind === 'family' && view === 'code') {
      views.code = await drawFamilyCode(page, subject, dir);
      files.code = 'code.svg';
    } else if (view === 'imports') {
      views.imports = await drawImports(page, subject, dir);
      files.imports = 'imports.svg';
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
