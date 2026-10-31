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

import { exportSubject, svgOf, type Manifest, type ManifestSubject } from '../export/exporter';
import { stubWideCodeMap } from './helpers';

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

/**
 * A picture carries nothing its page does not show (`docs/scale.md`, rule 4).
 * Mutations, each in `svgOf`: keep the drawn style in a `style` beside the
 * attributes; keep the names the declutter hid; keep the marks' titles; keep
 * the window's `data-*`; write coordinates as drawn -- and this fails.
 */
function lean(picture: string): void {
  expect(picture).not.toMatch(/ style="/);
  expect(picture).not.toMatch(/visibility="hidden"/);
  expect(picture).not.toContain('<title');
  expect(picture).not.toMatch(/ data-[\w-]+="/);
  expect(picture).not.toMatch(/ (?:x|y|x1|y1|x2|y2|cx|cy|r|d|points)="[^"]*\d\.\d\d/);
  expect(picture).not.toMatch(/translate\([^)]*\d\.\d\d/);
}

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
  // No member has a clone beside this checkout, so the caveat says nothing was
  // measured for them. Mutation: keep the window's wording -- it says
  // "beside this one", and this fails.
  expect(shown.views.estate.metadata.caveat).toContain('had no clone this export could read');
  expect(shown.views.estate.metadata.caveat).not.toMatch(/beside this|this checkout|this disk/);
  expect(shown.files).toEqual({ estate: 'estate.svg' });

  // The picture draws on its own: a namespaced svg, the size it was drawn at,
  // and its styles written into it as attributes. Mutation: serialize the svg
  // without its computed styles -- its names lose their font, and this fails.
  const picture = read(join(out, 'index', 'estate.svg'));
  const root = /^<svg[^>]*>/.exec(picture)?.[0] ?? '';
  expect(root).toContain('xmlns="http://www.w3.org/2000/svg"');
  expect(root).toMatch(/viewBox="0 0 \d+ \d+"/);
  expect(root).toMatch(/font-family="[^"]+"/);
  expect((picture.match(/<g class="graph-node/g) ?? []).length).toBeGreaterThan(5);
  lean(picture);

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
  const code = read(join(out, 'project', 'carlos', 'code.svg'));
  expect(code.match(/<g class="graph-node/g) ?? []).toHaveLength(90);
  lean(code);
});

test("a family's code view is written as its picture, naming its projects' code maps rather than holding them again", async ({ page }) => {
  test.setTimeout(120_000);
  const out = test.info().outputPath('show');
  const performing: ManifestSubject = {
    kind: 'family', name: 'performing', address: 'family:performing', folder: 'family/performing',
    views: ['estate', 'code'], digest: 'sha256:performing',
  };
  await exportSubject(page, performing, manifest(out));
  const shown = JSON.parse(read(join(out, 'family', 'performing', 'show.json')));
  expect(shown.files).toEqual({ estate: 'estate.svg', code: 'code.svg' });
  // Each project's code map is its own document's. Mutation: keep the graph
  // the family's code view drew -- every project's code again, and this fails.
  expect(shown.views.code.graph).toBe("each project's code view's");
  // The pinned corpus holds no code maps: the family is drawn, and the
  // caveat says whose code is not. Mutation: draw the family's estate for
  // its code view -- no project's code is spoken of, and this fails.
  expect(shown.views.code.metadata.code).toEqual({});
  expect(shown.views.code.metadata.caveat).toContain('no code map drawn yet');
  const family = read(join(out, 'family', 'performing', 'code.svg'));
  expect(family).toContain('>performing</text>');
  lean(family);
});

test("a system view is drawn only from the default branch's head the document names", async ({ page }) => {
  /**
   * The system view is composed from the project's clone on this disk, which
   * may sit on another branch or hold commits nobody else has. A picture of
   * that, published, describes a state no reader can see: codecartographer's
   * own was composed at a local branch's commit. So the export draws it only
   * when the clone is at the default branch's head, and otherwise states why.
   */
  test.setTimeout(120_000);
  const out = test.info().outputPath('show');
  let composedAt = 'bbbbbbb';
  await page.route('**/show/project/*/views', (route) => route.fulfill({ json: { status: 200, results: {
    name: 'carlos',
    estate: { available: true },
    code: { available: false, problem: 'not here', remedy: '' },
    system: { available: true, components: 1 },
  } } }));
  // moat's own composition, at whichever commit the test says it was composed.
  const moat = JSON.parse(read('tests/e2e/fixtures/moat-system.json'));
  await page.route('**/system/compose*', (route) => route.fulfill({ json: { ...moat, commit: composedAt } }));

  // Mutation: draw the system view whatever commit it was composed at -- the
  // clone's own state is published, and this fails.
  await exportSubject(page, carlos, manifest(out));
  const elsewhere = JSON.parse(read(join(out, 'project', 'carlos', 'show.json')));
  expect(elsewhere.views.system.absent).toBe(true);
  // The default branch's head, and not the clone's commit, which may be one
  // only that clone holds.
  expect(elsewhere.views.system.problem).toContain('aaaaaaa');
  expect(elsewhere.views.system.problem).not.toContain('bbbbbbb');
  expect(elsewhere.views.system.problem).not.toContain('this disk');
  expect(existsSync(join(out, 'project', 'carlos', 'system.png'))).toBe(false);

  composedAt = 'aaaaaaa';
  const again = test.info().outputPath('again');
  await exportSubject(page, carlos, manifest(again));
  const atHead = JSON.parse(read(join(again, 'project', 'carlos', 'show.json')));
  expect(atHead.views.system.composed.commit).toBe('aaaaaaa');
  expect(atHead.files.system).toBe('system.png');
  expect(existsSync(join(again, 'project', 'carlos', 'system.png'))).toBe(true);

  // Drawn again into the same folder, with the clone moved off the head: the
  // folder holds what this export wrote and nothing older. Mutation: write
  // into the folder as it is -- the last export's system.png stays beside a
  // document that no longer names it, and this fails.
  composedAt = 'bbbbbbb';
  await exportSubject(page, carlos, manifest(again));
  expect(JSON.parse(read(join(again, 'project', 'carlos', 'show.json'))).views.system.absent).toBe(true);
  expect(existsSync(join(again, 'project', 'carlos', 'system.png'))).toBe(false);
});

test('a view with no clone to read says so of the export, not of the disk it ran on', async ({ page }) => {
  /**
   * The window says "no clone of carlos beside this checkout", which is true
   * of one machine and is how the window should say it. A committed document
   * is read on every machine, so it says what the export read.
   */
  test.setTimeout(120_000);
  const out = test.info().outputPath('show');
  await page.route('**/show/project/*/views', (route) => route.fulfill({ json: { status: 200, results: {
    name: 'carlos',
    estate: { available: true },
    code: { available: false, problem: 'not here', remedy: '' },
    system: { available: false, problem: 'no clone of carlos beside this checkout',
              remedy: 'clone it beside this one, or set CODECARTO_REPO_ROOTS' },
  } } }));
  await exportSubject(page, carlos, manifest(out));
  const system = JSON.parse(read(join(out, 'project', 'carlos', 'show.json'))).views.system;
  // Mutation: state the window's own sentence -- it names this checkout, and
  // this fails.
  expect(system.problem).toBe("carlos's system view is composed from a clone of it, and this export read none");
  expect(system.remedy).toBe("export from a clone of carlos at its default branch's head");
  expect(JSON.stringify(system)).not.toMatch(/this checkout|CODECARTO_REPO_ROOTS/);
});

test('a code map is pictured once every node it was sent is drawn, with none of its files named', async ({ page }) => {
  /**
   * The canvas draws a few nodes each frame after the stream has ended, then
   * fits the drawing again and tidies its names. A picture taken as the zoom
   * first stopped moving held four nodes in five of a code map, with a hundred
   * of its files' names written over it.
   */
  test.setTimeout(120_000);
  const out = test.info().outputPath('show');
  // Eight thousand imports among the files, which the canvas draws after the
  // last node and before the outlines.
  const count = await stubWideCodeMap(page, 30, 29, 8000);
  const codeOnly: ManifestSubject = { ...carlos, views: ['code'] };
  await exportSubject(page, codeOnly, manifest(out));
  const picture = read(join(out, 'project', 'carlos', 'code.svg'));
  // Mutation: take the picture once the zoom stops moving -- some of the
  // nodes are not in it, and this fails.
  expect(picture.match(/<g class="graph-node"/g) ?? []).toHaveLength(count);
  // And the drawing done: each directory's outline drawn round its files,
  // which the canvas draws once its edges are in. Mutation: take the picture
  // once every node is drawn -- its outlines are not in it, and this fails.
  expect((picture.match(/class="compound-group/g) ?? []).length).toBeGreaterThanOrEqual(30);
  // None of its files named. A name the declutter hid is left out of the
  // picture, so a name in it is one it shows. Mutation: picture the code map
  // before its names are tidied -- its files are named, and this fails.
  expect(picture).not.toMatch(/>module_\d+\.py</);
  lean(picture);
});

test("the index's and a family's imports views are written as pictures, naming what each read", async ({ page }) => {
  /**
   * What the members import in common grows with the projects, not with their
   * code (`docs/scale.md`, rule 8), so the index and each family draw it. The
   * backend reads whatever clones sit beside the checkout it runs from, so
   * this says what each document names, not how many modules it found.
   */
  test.setTimeout(120_000);
  const out = test.info().outputPath('show');
  const everyFamily: ManifestSubject = { ...index, views: ['estate', 'imports'] };
  const performing: ManifestSubject = {
    kind: 'family', name: 'performing', address: 'family:performing', folder: 'family/performing',
    views: ['imports'], digest: 'sha256:performing',
  };
  await exportSubject(page, everyFamily, manifest(out));
  await exportSubject(page, performing, manifest(out));

  for (const [folder, files] of [['index', { estate: 'estate.svg', imports: 'imports.svg' }],
                                 ['family/performing', { imports: 'imports.svg' }]] as const) {
    const shown = JSON.parse(read(join(out, ...folder.split('/'), 'show.json')));
    expect(shown.files).toEqual(files);
    // Mutation: draw the imports view from the estate's route -- it counts no
    // imports and names nothing read, and this fails.
    const counted = shown.views.imports.metadata.imports;
    expect(Object.keys(counted).sort()).toEqual(['alone', 'ambiguous', 'links', 'read', 'shared', 'unread']);
    expect(Object.keys(shown.views.imports.metadata.bases)).toContain('imported');
    expect(shown.views.imports.metadata.caveat).toContain('at the commit its show document was drawn from');
    expect(shown.views.imports.metadata.caveat).not.toMatch(/beside this|this checkout|this disk/);
    lean(read(join(out, ...folder.split('/'), 'imports.svg')));
  }
});

test('a drawing moved by less than a step writes the same picture', async ({ page }) => {
  /**
   * Two exports of the same sources differed, in most pictures, in
   * coordinates past the first decimal and in the transform that fits the
   * drawing to the window. So `svgOf` writes coordinates to one decimal and
   * settles the fit to fixed steps, and a redraw of an unchanged subject
   * writes the same bytes (`docs/scale.md`, rule 5).
   */
  test.setTimeout(120_000);
  await exportSubject(page, index, manifest(test.info().outputPath('show')));
  const drawn = await svgOf(page);
  // The fit a hair off where it was: a thousandth of a pixel, and a
  // hundred-thousandth of its scale. Mutation: write the fit's scale as the
  // canvas left it, or its offset as drawn -- and this fails.
  await page.locator('.graphRenderer > svg').first().evaluate((svg) => {
    const zoom = svg.querySelector('g')!;
    const [tx, ty, k] = /translate\(([-\d.e]+),\s*([-\d.e]+)\)\s*scale\(([-\d.e]+)\)/
      .exec(zoom.getAttribute('transform')!)!.slice(1).map(Number);
    zoom.setAttribute('transform', `translate(${tx + 0.001},${ty - 0.001}) scale(${k * 1.00001})`);
  });
  expect(await svgOf(page)).toBe(drawn);
  lean(drawn);
});
