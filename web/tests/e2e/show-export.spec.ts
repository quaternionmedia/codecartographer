/**
 * `codecarto show export`'s browser half (`tests/export/exporter.ts`), run on
 * the browser suite's own servers: each view of a subject drawn in the window
 * and written as a picture, beside one show document saying what was drawn
 * and from what.
 *
 * The index is drawn from the pinned corpus. carlos's code view streams
 * carlos's own coarse parse (`fixtures/carlos-code.sse`), and its views are
 * stubbed, so nothing here needs the host. Everything is written under this
 * test's own output folder.
 */

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

import { expect, test } from '@playwright/test';

import { exportSubject, type Manifest, type ManifestSubject } from '../export/exporter';

const index: ManifestSubject = {
  kind: 'index', name: '', address: 'index', folder: 'index', views: ['estate'], digest: 'sha256:index',
};
const carlos: ManifestSubject = {
  kind: 'project', name: 'carlos', address: 'project:carlos', folder: 'project/carlos',
  views: ['estate', 'code', 'system'], digest: 'sha256:carlos',
};

function manifest(out: string): Manifest {
  return {
    out,
    corpus: { repo: 'quaternionmedia/qm', commit: '0'.repeat(40) },
    drawn_by: { graph: 'codecartographer@test' },
    drawn_at: '2026-01-01T00:00:00Z',
    sources: { carlos: { repo: 'quaternionmedia/carlos', commit: 'a'.repeat(40) } },
    subjects: [index, carlos],
  };
}

const read = (path: string) => readFileSync(path, 'utf8');

test('a subject is written as its pictures and one show document naming where each came from', async ({ page }) => {
  test.setTimeout(120_000);
  const out = test.info().outputPath('show');
  await page.route('**/show/project/*/views', (route) => route.fulfill({ json: { status: 200, results: {
    name: 'carlos',
    estate: { available: true },
    code: { available: true, url: 'https://github.com/quaternionmedia/carlos', depth: 1 },
    system: { available: false, problem: 'carlos declares no system this window reads', remedy: '' },
  } } }));
  await page.route('**/parse/stream-url', (route) => route.fulfill({
    status: 200, contentType: 'text/event-stream', path: 'tests/e2e/fixtures/carlos-code.sse',
  }));

  await exportSubject(page, index, manifest(out));
  await exportSubject(page, carlos, manifest(out));

  const shown = JSON.parse(read(join(out, 'index', 'show.json')));
  expect(shown.subject).toEqual({ kind: 'index', name: '' });
  expect(shown.provenance.claims).toEqual({ repo: 'quaternionmedia/qm', commit: '0'.repeat(40), digest: 'sha256:index' });
  expect(Object.keys(shown.views.estate.graph.nodes).length).toBeGreaterThan(5);
  // Mutation: copy the show route's metadata as it answered -- it names the
  // corpus by where the backend found it, and this fails.
  expect(shown.views.estate.metadata.source).toBe('families.json');
  expect(shown.views.estate.metadata.provenance.source).toBe('families.json');
  expect(shown.files).toEqual({ estate: 'estate.svg' });

  // The picture draws on its own: a namespaced svg, the size it was drawn at,
  // and its styles written into it. Mutation: serialize the svg without its
  // computed styles -- its names lose their font, and this fails.
  const picture = read(join(out, 'index', 'estate.svg'));
  const root = /^<svg[^>]*>/.exec(picture)?.[0] ?? '';
  expect(root).toContain('xmlns="http://www.w3.org/2000/svg"');
  expect(root).toMatch(/viewBox="0 0 \d+ \d+"/);
  expect(root).toMatch(/style="[^"]*font-family:[^"]*"/);
  expect(picture).toContain('data-node-id="family::');

  const project = JSON.parse(read(join(out, 'project', 'carlos', 'show.json')));
  expect(project.provenance.source).toEqual({ repo: 'quaternionmedia/carlos', commit: 'a'.repeat(40) });
  // Mutation: keep no node from the stream -- the code view's graph is empty,
  // and this fails.
  expect(Object.keys(project.views.code.graph.nodes)).toHaveLength(90);
  expect(project.views.code.graph.edges).toHaveLength(89);
  expect(project.views.code.metadata).toEqual({ url: 'https://github.com/quaternionmedia/carlos', depth: 1, truncated: 0 });
  // A view the window cannot draw is the window's sentence for why, not a picture.
  expect(project.views.system).toEqual({
    absent: true, problem: 'carlos declares no system this window reads', remedy: '',
    where: '/show/project/carlos/views',
  });
  expect(project.files).toEqual({ estate: 'estate.svg', code: 'code.svg' });
  expect(existsSync(join(out, 'project', 'carlos', 'system.png'))).toBe(false);
  expect(read(join(out, 'project', 'carlos', 'code.svg'))).toContain('data-node-id="dir::quaternionmedia/carlos/walkthrough"');
});
