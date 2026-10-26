import { expect } from '@playwright/test';
import type { Locator, Page } from '@playwright/test';

/**
 * A point of the node that a pointer there reaches, as the browser hit-tests
 * it, once the node has stopped moving.
 *
 * **A NODE'S CENTRE IS OFTEN UNDER SOMETHING ELSE.** A file node's is often
 * under one of its symbols or its label, and the canvas lets two nodes
 * overlap: the demo has drawn `dir::codecarto/routers` 7.5 units from
 * `dir::codecarto`, two diamonds 12 units from centre to corner, with routers
 * on top. Playwright's own click aims at the centre and waits for nothing to
 * be over it, which on a settled layout is never, so the test waited out its
 * timeout. A real press, hit-tested where the pointer is, is also what a
 * synthetic event dispatched to the node is not: that reaches it whatever is
 * drawn over it.
 *
 * Settled is the node's box unchanged over three animation frames running:
 * a point read while the canvas still zooms to fit is not where the node is
 * when the press arrives.
 */
export async function pointOn(node: Locator): Promise<{ x: number; y: number }> {
  const found = await node.evaluate(async (el) => {
    const frame = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    let last = '';
    let unchanged = 0;
    for (let i = 0; i < 600 && unchanged < 3; i++) {
      await frame();
      const r = el.getBoundingClientRect();
      const box = `${r.left},${r.top},${r.width},${r.height}`;
      unchanged = box === last ? unchanged + 1 : 0;
      last = box;
    }
    if (unchanged < 3) return 'the node did not stop moving';
    const r = el.getBoundingClientRect();
    const steps = [0.5, 0.35, 0.65, 0.2, 0.8, 0.1, 0.9];
    for (const fy of steps) {
      for (const fx of steps) {
        const x = r.left + r.width * fx;
        const y = r.top + r.height * fy;
        const hit = document.elementFromPoint(x, y);
        if (hit && el.contains(hit)) return { x, y };
      }
    }
    return 'no point of the node is reached by a pointer';
  });
  expect(typeof found === 'string' ? found : null).toBeNull();
  return found as { x: number; y: number };
}

/**
 * Dismiss the onboarding modal if it is covering the app.
 *
 * Its backdrop (`.cc-modal-backdrop`) intercepts pointer events, so any test
 * that clicks anything must call this first. The modal opens with the page on
 * a first visit -- synchronously, in the shell's `oncreate`, before any network
 * probe -- so a short wait for it to attach is enough, and its absence after
 * that means the visit is not a first one.
 *
 * ESCAPE CLOSES IT, AND THE CLOSE IS A REDRAW AWAY. The first version of this
 * pressed Escape and re-counted the backdrop in the same tick, found it still
 * there (Mithril redraws asynchronously), and went looking for a `×` that had
 * just been removed -- every test then waited thirty seconds for a button that
 * no longer existed. So: press Escape, wait for the backdrop to detach, and
 * only if it does not, press the `×`.
 */
export async function dismissOnboardingModal(page: Page): Promise<void> {
  const backdrop = page.locator('.cc-modal-backdrop');
  await backdrop.waitFor({ state: 'attached', timeout: 1_500 }).catch(() => undefined);
  if ((await backdrop.count()) === 0) return;
  await page.keyboard.press('Escape');
  const gone = await backdrop
    .waitFor({ state: 'detached', timeout: 2_000 })
    .then(() => true)
    .catch(() => false);
  if (gone) return;
  await backdrop.locator('button', { hasText: '×' }).first().click({ force: true });
  await backdrop.waitFor({ state: 'detached', timeout: 5_000 });
}

/**
 * A parse of `dirs` directories of `files` files each under one root, spread
 * wide enough that the fit framing it draws each file under a pixel.
 */
export function wideStream(dirs: number, files: number): string {
  const lines: string[] = [];
  const event = (name: string, data: unknown) => lines.push(`event: ${name}\ndata: ${JSON.stringify(data)}\n`);
  const nodes: unknown[] = [];
  const edges: unknown[] = [];
  const root = 'dir::example/wide';
  nodes.push({ id: root, label: 'example/wide', depth: 0, kind: 'directory', file: '', line: 0, meta: {}, x: 0, y: 0, size: 80 });
  for (let d = 0; d < dirs; d++) {
    const dir = `${root}/d${d}`;
    const cx = (d % 6) * 6000 - 15000;
    const cy = Math.floor(d / 6) * 6000 - 9000;
    nodes.push({ id: dir, label: `d${d}`, depth: 0, kind: 'directory', file: '', line: 0, meta: {}, x: cx, y: cy, size: 80 });
    edges.push({ source: root, target: dir, metadata: { kind: 'contains', weight: 1 } });
    for (let f = 0; f < files; f++) {
      const a = (2 * Math.PI * f) / files;
      nodes.push({
        id: `file::example/wide/d${d}/module_${f}.py`, label: `module_${f}.py`, depth: 1, kind: 'file',
        file: `module_${f}.py`, line: 0, meta: {}, x: cx + 900 * Math.cos(a), y: cy + 900 * Math.sin(a), size: 10,
      });
      edges.push({ source: dir, target: `file::example/wide/d${d}/module_${f}.py`, metadata: { kind: 'contains', weight: 1 } });
    }
  }
  event('meta', { nodeCount: nodes.length, edgeCount: edges.length, layout: 'Map', from_cache: true });
  for (const n of nodes) event('node', n);
  for (const e of edges) event('edge', e);
  event('done', { elapsed_ms: 0, from_cache: true });
  return `${lines.join('\n')}\n`;
}

/** carlos's views stubbed so that its code view is the wide stream above. Returns its node count. */
export async function stubWideCodeMap(page: Page, dirs: number, files: number): Promise<number> {
  await page.route('**/show/project/*/views', (route) => route.fulfill({ json: { status: 200, results: {
    name: 'carlos',
    estate: { available: true },
    code: { available: true, url: 'https://github.com/example/wide', depth: 1 },
    system: { available: false, problem: 'carlos declares no system this window reads', remedy: '' },
  } } }));
  await page.route('**/parse/stream-url', (route) => route.fulfill({
    status: 200, contentType: 'text/event-stream', body: wideStream(dirs, files),
  }));
  return 1 + dirs * (1 + files);
}
