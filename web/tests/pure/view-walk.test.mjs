/**
 * Where a reader goes in the page without a server, and what each step's
 * address is.
 *
 *   npm run test:pure
 *
 * The show documents are the corpus's own, as `codecarto show export` wrote
 * them (`tests/e2e/fixtures/show/`): the index, three families and two
 * projects, so the walk is the one a reader of the published page takes.
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import {
  CORPUS_SHOW, WINDOW_APP, atView, documentUrl, formatPage, learn, learnFrom, nesting, openables, readPage,
  trailSubjects, viewsOf, windowLink,
} from '../../dist-pure/features/view/view_walk.js';
import { crumbLabel, trail } from '../../dist-pure/features/show/show_address.js';

const fixture = (subject) => JSON.parse(readFileSync(`tests/e2e/fixtures/show/${subject}/show.json`, 'utf8'));

const INDEX = { kind: 'index', name: '', view: 'estate' };

test("the page's own address asks for every family, from the corpus's show folder beside it", () => {
  assert.deepEqual(readPage(''), { address: { show: INDEX, docs: null }, bare: true });
  assert.deepEqual(readPage('?docs=https://docs.test/qm/show/'),
    { address: { show: INDEX, docs: 'https://docs.test/qm/show/' }, bare: true });
  assert.equal(documentUrl(null, INDEX), `${CORPUS_SHOW}index/show.json`);
  assert.equal(CORPUS_SHOW, '../qm/show/');
});

test('a ?show= address is the window\'s grammar, read from the folder &docs= names', () => {
  const reading = readPage('?show=project:ztgui&view=code&docs=https://docs.test/qm/show');
  assert.deepEqual(reading, {
    address: { show: { kind: 'project', name: 'ztgui', view: 'code' }, docs: 'https://docs.test/qm/show' },
    bare: false,
  });
  assert.equal(documentUrl(reading.address.docs, reading.address.show), 'https://docs.test/qm/show/project/ztgui/show.json');
  assert.equal(documentUrl(null, { kind: 'family', name: 'core', view: 'imports' }), '../qm/show/family/core/show.json');
  // Written back as it was read, so a copied address reopens the drawing.
  assert.equal(formatPage(reading.address), '?show=project:ztgui&view=code&docs=https%3A%2F%2Fdocs.test%2Fqm%2Fshow');
  assert.deepEqual(readPage(formatPage(reading.address)), reading);
  assert.equal(formatPage(atView(reading.address, 'estate')), '?show=project:ztgui&docs=https%3A%2F%2Fdocs.test%2Fqm%2Fshow');
  assert.deepEqual(readPage('?show=nobody'), { refused: {
    problem: '?show=nobody names no subject',
    remedy: 'name index, family:<name> or project:<name>, as ?show=project:carlos',
  } });
});

test('a ?doc= address is read before any ?show=, and keeps its view', () => {
  const reading = readPage('?doc=https://docs.test/qm/show/family/core/show.json&view=imports&show=index');
  assert.deepEqual(reading, { address: { doc: 'https://docs.test/qm/show/family/core/show.json', view: 'imports' }, bare: false });
  assert.deepEqual(readPage(formatPage(atView(reading.address, 'estate'))).address,
    { doc: 'https://docs.test/qm/show/family/core/show.json', view: 'estate' });
});

test("a subject's views are offered in the window's order and by its names, each it cannot draw with why", () => {
  const core = viewsOf(fixture('family/core'));
  assert.deepEqual(core.map((v) => [v.view, v.label]),
    [['estate', 'the family'], ['code', "with each project's code"], ['imports', 'shared imports']]);
  assert.equal(core[0].refused, null);
  assert.equal(core[2].refused, null);
  assert.match(core[1].refused.problem, /^the code view of family:core is not a graph in its document but a pointer/);
  assert.equal(core[1].refused.window, '?show=family:core&view=code');

  const moat = viewsOf(fixture('project/moat'));
  assert.deepEqual(moat.map((v) => v.label), ['estate', 'code map', 'system']);
  assert.equal(moat[2].refused.window, '?show=project:moat&view=system');

  // A view the document marks absent is not drawn in the window either: no way there is offered.
  const ztgui = viewsOf(fixture('project/ztgui'));
  assert.ok(ztgui[2].refused);
  assert.equal(ztgui[2].refused.window, undefined);

  // Whatever order its document holds them in, they are offered as the window offers them.
  const project = fixture('project/ztgui');
  const reordered = { ...project, views: { system: project.views.system, code: project.views.code, estate: project.views.estate } };
  assert.deepEqual(viewsOf(reordered).map((v) => v.view), ['estate', 'code', 'system']);

  assert.deepEqual(viewsOf(fixture('index')).map((v) => [v.view, v.label, v.refused]),
    [['estate', 'every family', null], ['imports', 'shared imports', null]]);
  assert.deepEqual(viewsOf({ graph: { nodes: {}, edges: [] }, metadata: {} }), []);
});

test('every family and project a drawing names is listed to open, families first, but the subject itself', () => {
  const index = fixture('index');
  const estate = index.views.estate;
  const named = new Set(Object.values(estate.graph.nodes).map((node) => node.metadata.show).filter(Boolean));
  const listed = openables(estate, 'index');
  assert.equal(listed.length, named.size);
  const families = listed.filter((one) => one.address.kind === 'family');
  assert.equal(families.length, 9);
  assert.ok(listed.slice(0, 9).every((one) => one.address.kind === 'family'), 'families come first');
  assert.deepEqual(families.map((one) => one.label),
    [...families.map((one) => one.label)].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' })));
  assert.deepEqual(listed.find((one) => one.label === 'ztgui').address, { kind: 'project', name: 'ztgui', view: 'estate' });

  const core = openables(fixture('family/core').views.estate, 'family:core');
  assert.deepEqual(core.map((one) => one.label),
    ['codecartographer', 'dossier', 'looksatwords', 'qm', 'qmcp', 'rad', 'vox']);
  // A code map names no family or project: nothing to open from it.
  assert.deepEqual(openables(fixture('project/ztgui').views.code, 'project:ztgui'), []);
});

test("the trail is the window's, told what nests in what by the documents read", () => {
  const instruments = { kind: 'family', name: 'instruments', view: 'estate' };
  const carlos = { kind: 'project', name: 'carlos', view: 'code' };
  const labels = (address, known) => trail(address, trailSubjects(known)).map((level) => level.map(crumbLabel).join(' · '));

  // Opened by its own address, a family's document names what it holds, not what holds it.
  const alone = nesting();
  learnFrom(alone, fixture('family/instruments'));
  assert.deepEqual(labels(instruments, alone), ['every family', 'instruments']);
  assert.deepEqual(labels(carlos, alone), ['every family', 'instruments', 'carlos']);

  // The index names every family and what sits within it.
  learnFrom(alone, fixture('index'));
  assert.deepEqual(labels(instruments, alone), ['every family', 'performing', 'instruments']);
  assert.deepEqual(labels(carlos, alone), ['every family', 'performing', 'instruments', 'carlos']);

  // A project's own document names its families by its member_of edges.
  const ztgui = nesting();
  learnFrom(ztgui, fixture('project/ztgui'));
  assert.deepEqual(labels({ kind: 'project', name: 'ztgui', view: 'estate' }, ztgui), ['every family', 'infra', 'ztgui']);

  // Only an estate view says; a code map nests nothing.
  const code = nesting();
  learn(code, fixture('project/ztgui').views.code);
  assert.deepEqual(trailSubjects(code), { families: [], projects: [] });
});

test('a view the page cannot draw links to the window on this machine, at its default port', () => {
  assert.equal(WINDOW_APP, 'http://localhost:2718/app');
  assert.equal(windowLink('?show=project:moat&view=system'), 'http://localhost:2718/app?show=project:moat&view=system');
});
