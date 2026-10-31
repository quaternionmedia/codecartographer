/**
 * What the page without a server reads, and what it refuses.
 *
 *   npm run test:pure
 *
 * Every way into `view.html` -- a URL, a file, a paste -- hands its document to
 * `readDocument`, so these are the page's checks whatever brought the document.
 * The show documents are real, as `codecarto show export` wrote them
 * (`tests/e2e/fixtures/show/`); the gJGF ones are written here, each to the
 * point it makes.
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { SHOW_SCHEMA, readDocument, readableUrl } from '../../dist-pure/features/view/view_document.js';

const fixture = (subject) => JSON.parse(readFileSync(`tests/e2e/fixtures/show/${subject}/show.json`, 'utf8'));

const drawn = (reading) => {
  assert.ok('drawing' in reading, `refused: ${JSON.stringify(reading.refused)}`);
  return reading.drawing;
};
const refused = (reading) => {
  assert.ok('refused' in reading, 'it was drawn');
  return reading.refused;
};

test("a show document's estate view is drawn unless another is asked for, as the window draws an estate", () => {
  const document = fixture('project/ztgui');
  const shown = drawn(readDocument(document));
  assert.equal(shown.view, 'estate');
  assert.equal(shown.subject, 'project:ztgui');
  assert.equal(shown.layout, 'compound_layout');
  assert.equal(shown.document.graph.nodes, document.views.estate.graph.nodes);
  assert.equal(shown.nodes, 5);
  assert.equal(shown.edges, 4);
  assert.equal(shown.unplaced, 0);
  // The producer's caveat, as it wrote it, and where the drawing came from.
  assert.equal(shown.caveat, document.views.estate.metadata.caveat);
  assert.match(shown.drawn, /^drawn 2026-10-31T00:52:12Z, by codecartographer@9ba33d6\w+\+changes, from quaternionmedia\/ztgui at c698ae0$/);
});

test("a project's code view is drawn as a Showcase, the layout the window opens it in", () => {
  const shown = drawn(readDocument(fixture('project/ztgui'), 'code'));
  assert.equal(shown.view, 'code');
  assert.equal(shown.layout, 'showcase_layout');
  assert.equal(shown.nodes, 39);
  assert.equal(shown.edges, 45);
  assert.equal(shown.unplaced, 0);
  // A code view's metadata carries no caveat; the page invents none.
  assert.equal(shown.caveat, null);
});

test("a family's views other than its code view are drawn as compound outlines", () => {
  for (const view of ['estate', 'imports']) {
    const shown = drawn(readDocument(fixture('family/core'), view));
    assert.equal(shown.subject, 'family:core');
    assert.equal(shown.layout, 'compound_layout', view);
  }
});

test("a family's code view, a pointer to its projects' code views, is refused by name", () => {
  const why = refused(readDocument(fixture('family/core'), 'code'));
  assert.match(why.problem, /^the code view of family:core is not a graph in its document but a pointer \("each project's code view's"\)/);
  assert.match(why.remedy, /\?show=family:core&view=code/);
});

test('a composed system is refused, naming where it opens', () => {
  const why = refused(readDocument(fixture('project/moat'), 'system'));
  assert.match(why.problem, /^the system view of project:moat is a composed system/);
  assert.match(why.remedy, /\?show=project:moat&view=system$/);
});

test("a view its document marks absent is refused in the document's own words", () => {
  const document = fixture('project/ztgui');
  const why = refused(readDocument(document, 'system'));
  assert.equal(why.problem, document.views.system.problem);
  assert.equal(why.remedy, document.views.system.remedy);
  // With no remedy, it says none rather than inventing one.
  const silent = { ...document, views: { ...document.views, system: { absent: true, problem: 'no system', remedy: '' } } };
  assert.deepEqual(refused(readDocument(silent, 'system')), { problem: 'no system', remedy: '' });
});

test('a view the document does not hold is refused, naming the views it does', () => {
  const why = refused(readDocument(fixture('project/ztgui'), 'imports'));
  assert.equal(why.problem, 'the show document of project:ztgui has no imports view');
  assert.match(why.remedy, /estate, code, system/);
});

test('a show document of another schema is refused, naming both', () => {
  const document = { ...fixture('project/ztgui'), schema: SHOW_SCHEMA + 1 };
  assert.match(refused(readDocument(document)).problem, new RegExp(`schema ${SHOW_SCHEMA + 1}, and this page reads schema ${SHOW_SCHEMA}`));
});

test('a gJGF document is drawn as given, its layout read from its metadata', () => {
  const graph = (layout) => ({
    graph: {
      nodes: { a: { label: 'a', metadata: { x: 0, y: 0 } }, b: { label: 'b', x: 10, y: 5 } },
      edges: [{ source: 'a', target: 'b' }],
    },
    metadata: layout ? { layout, subject: 'project:a' } : {},
  });
  const shown = drawn(readDocument(graph('Compound')));
  assert.equal(shown.layout, 'compound_layout');
  assert.equal(shown.subject, 'project:a');
  assert.equal(shown.view, null);
  assert.equal(shown.unplaced, 0);
  assert.equal(drawn(readDocument(graph('Showcase(dot=2,gap=0.5,nest=true,sized=true)'))).layout, 'showcase_layout');
  assert.equal(drawn(readDocument(graph('Kamada_Kawai'))).layout, 'kamada_kawai_layout');
  assert.equal(drawn(readDocument(graph(null))).layout, 'spring_layout');
});

test('a node with no position is counted, for the canvas places it on its depth ring', () => {
  const document = {
    graph: {
      nodes: [
        { id: 'a', x: 1, y: 2 },
        { id: 'b' },
        { id: 'c', x: 3 },
        { id: 'd', x: '4', y: 5 },
      ],
      edges: [],
    },
  };
  const shown = drawn(readDocument(document));
  assert.equal(shown.nodes, 4);
  assert.equal(shown.unplaced, 3);
  // Read without metadata, as an app may send it.
  assert.deepEqual(shown.document.metadata, {});
});

test('anything else is refused, saying the shapes the page reads', () => {
  for (const [document, problem] of [
    [null, 'it is not a JSON object'],
    [[1, 2], 'it is not a JSON object'],
    [{ nodes: [] }, 'it is neither a show document nor a gJGF graph: it has no "views" and no "graph"'],
    [{ graph: [] }, 'its graph is not an object'],
    [{ graph: { nodes: 'x', edges: [] } }, 'its graph has no "nodes" object or list, or no "edges" list'],
    [{ graph: { nodes: {}, edges: {} } }, 'its graph has no "nodes" object or list, or no "edges" list'],
    [{ views: { estate: {} }, schema: 1 }, 'it is a show document that names no subject'],
  ]) {
    const why = refused(readDocument(document));
    assert.equal(why.problem, problem);
    assert.match(why.remedy, /show document .* or a gJGF graph/);
  }
  assert.equal(refused(readDocument({ graph: { nodes: {}, edges: [] } })).problem, 'its graph holds no nodes');
});

test('a document is read from an http or https address only', () => {
  assert.equal(readableUrl('https://quaternionmedia.github.io/qm/show/index/show.json'), null);
  assert.equal(readableUrl('http://localhost:8000/show.json'), null);
  for (const url of ['javascript:alert(1)', 'data:application/json,{}', 'file:///etc/passwd', 'ftp://host/x.json']) {
    assert.match(readableUrl(url).problem, /is not an http or https address$/, url);
  }
});
