/**
 * The Cargo and Chrestomathy panels read and draw in the order they were asked.
 *
 * **WHAT THIS HOLDS THAT ONE ANSWER CANNOT SHOW.** Each defect here is a
 * sequence: two readings, two picks, a draw then a choice then a relayout, two
 * requests sharing one problem field. The host below applies patches with
 * mergerino, as `StateController.update` does, so a deep merge leaks here
 * exactly as it leaked on screen; the reads are promises the test resolves in
 * whatever order a slow network would.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import mergerino from 'mergerino';

import {
  CartographyActions,
  settlePatch,
  vocabularyShown,
} from '../../dist-pure/features/cartography/cartography_actions.js';

const merge = mergerino.default ?? mergerino;

const ok = (document) => ({ kind: 'ok', document });
const failed = (text) => ({
  kind: 'unreadable',
  problem: { kind: 'unreadable', problem: text, remedy: '', where: '/somewhere' },
});

/** A `/cargo/data` document, as much of one as these actions read. */
const workspace = (root, runners = {}) => ({
  root,
  engine: 'manifests',
  packages: [{ name: `${root}-crate`, version: '0.1.0', member: true }],
  documents: [],
  firmware: { build_targets: Object.keys(runners), runners, linker_scripts: [], memory_maps: [], config: '' },
  notes: [],
  caveat: '',
});
const reading = (id) => ({ construct: { id, name: id, gloss: '', facet: false, look: null }, languages: [], source: '', caveat: '' });
const index = () => ({ constructs: [{ id: 'type.product', name: 'Product type', gloss: '', facet: false, languages: [] }], languages: [], source: '', caveat: '' });
const graph = (name) => ({ graph: { nodes: { [name]: {} }, edges: [] }, metadata: { name } });

const flush = () => new Promise((resolve) => setImmediate(resolve));

function harness() {
  let state = {
    cargoPath: '', cargoReading: null, cargoProblem: null,
    constructIndex: null, constructIndexProblem: null, constructChosen: 'type.product',
    chrestomathyReading: null, chrestomathyProblem: null, graphData: null,
    chrestomathyCensus: null, censusProblem: null,
  };
  const asked = { cargoData: [], cargoGraph: [], constructs: [], chrestomathy: [], chrestomathyGraph: [], census: [] };
  const waiting = { cargoData: [], cargoGraph: [], constructs: [], chrestomathy: [], chrestomathyGraph: [], census: [] };
  const plotted = [];
  const route = (name) => (...args) => {
    asked[name].push(args);
    return new Promise((resolve) => waiting[name].push(resolve));
  };
  const host = {
    get state() { return state; },
    update: (patch) => { state = merge(state, patch); },
    redraw: () => {},
    clear: () => { state = merge(state, { graphData: () => null }); },
    plot: (document) => { plotted.push(document.metadata.name); },
    layout: () => 'spring_layout',
  };
  const actions = new CartographyActions(host, {
    cargoData: route('cargoData'),
    cargoGraph: route('cargoGraph'),
    constructs: route('constructs'),
    chrestomathy: route('chrestomathy'),
    chrestomathyGraph: route('chrestomathyGraph'),
    census: route('census'),
  });
  return {
    actions,
    asked,
    plotted,
    get state() { return state; },
    /** Answer the `nth` request made to `name`, counting from 0 in the order asked. */
    async answer(name, nth, outcome) {
      waiting[name][nth](outcome);
      await flush();
    },
  };
}

async function shown(h, path, document) {
  const read = h.actions.loadCargoReading(path);
  await h.answer('cargoData', h.asked.cargoData.length - 1, ok(document));
  await read;
}

async function chosen(h, construct) {
  const read = h.actions.loadChrestomathy(construct);
  await h.answer('chrestomathy', h.asked.chrestomathy.length - 1, ok(reading(construct)));
  await read;
}

// --- a reading replaces the one before it -------------------------------------

test('a reading replaces the one before it, nested fields and all', async () => {
  /**
   * A mergerino patch deep-merges, so workspace A's `firmware.runners` survived
   * into B's reading and the panel showed A's runner under B "(shown, never
   * run)". Mutation: settle with a plain object patch -- this fails.
   */
  const h = harness();
  await shown(h, 'a', workspace('a', { 'thumbv7em-none-eabihf': 'probe-rs run --chip STM32F411' }));
  await shown(h, 'b', workspace('b'));
  assert.deepEqual(h.state.cargoReading.firmware.runners, {});
  assert.equal(h.state.cargoReading.root, 'b');
});

test("the estate panels' readings are replaced too", () => {
  /** `PlotActions._settle` is `settlePatch`, for Capabilities and Overview as well. */
  const before = { overviewReading: { sections: { a: { title: 'A' } } }, overviewProblem: null };
  const after = merge(before, settlePatch(ok({ sections: { b: { title: 'B' } } }), 'overviewReading', 'overviewProblem'));
  assert.deepEqual(after.overviewReading, { sections: { b: { title: 'B' } } });
});

// --- only the latest request is shown -----------------------------------------

test('a late answer to an earlier read is dropped, and "draw" draws what is shown', async () => {
  /**
   * Read A, then B; B answers first, A late. A's answer was shown -- the panel
   * listed A's crates -- while "draw" drew B. Mutation: drop the ticket check
   * in `loadCargoReading` -- this fails.
   */
  const h = harness();
  const a = h.actions.loadCargoReading('a');
  const b = h.actions.loadCargoReading('b');
  await h.answer('cargoData', 1, ok(workspace('b')));
  await h.answer('cargoData', 0, ok(workspace('a', { thumbv6m: 'probe-rs run' })));
  await Promise.all([a, b]);
  assert.equal(h.state.cargoReading.root, 'b');
  assert.deepEqual(h.state.cargoReading.firmware.runners, {});

  void h.actions.cargoDraw()();
  assert.equal(h.asked.cargoGraph[0][0].path, 'b');
});

test('a late problem for an earlier read does not replace a newer reading', async () => {
  const h = harness();
  const a = h.actions.loadCargoReading('a');
  const b = h.actions.loadCargoReading('b');
  await h.answer('cargoData', 1, ok(workspace('b')));
  await h.answer('cargoData', 0, failed('no Cargo.toml at a'));
  await Promise.all([a, b]);
  assert.equal(h.state.cargoReading.root, 'b');
  assert.equal(h.state.cargoProblem, null);
});

test('a late answer to an earlier construct pick is dropped', async () => {
  /** Mutation: drop the ticket check in `loadChrestomathy` -- this fails. */
  const h = harness();
  const x = h.actions.loadChrestomathy('type.product');
  const y = h.actions.loadChrestomathy('memory.volatile');
  await h.answer('chrestomathy', 1, ok(reading('memory.volatile')));
  await h.answer('chrestomathy', 0, ok(reading('type.product')));
  await Promise.all([x, y]);
  assert.equal(h.state.chrestomathyReading.construct.id, 'memory.volatile');
});

test('a late answer to an earlier draw is not drawn over a later one', async () => {
  /** Mutation: drop the ticket check in the Cargo draw -- this fails with both drawn. */
  const h = harness();
  await shown(h, 'a', workspace('a'));
  const first = h.actions.cargoDraw()();
  const second = h.actions.cargoDraw({ features: true })();
  await h.answer('cargoGraph', 1, ok(graph('with features')));
  await h.answer('cargoGraph', 0, ok(graph('without')));
  assert.deepEqual(h.plotted, ['with features']);
  assert.equal(await first, false, 'the superseded draw drew nothing');
  assert.equal(await second, true);
});

// --- a relayout redraws what was drawn ----------------------------------------

test('a relayout redraws the construct that was drawn, not the one chosen since', async () => {
  /**
   * Draw `type.product`, then choose `memory.volatile` (which loads its table
   * and draws nothing); a layout change re-ran a draw that read the choice at
   * that moment and drew `memory.volatile`. Mutation: read `constructChosen`
   * when the draw runs -- this fails.
   */
  const h = harness();
  await chosen(h, 'type.product');
  const drawn = h.actions.chrestomathyDraw();   // what `plotWith` remembers
  const first = drawn();
  await h.answer('chrestomathyGraph', 0, ok(graph('type.product')));
  await first;
  await chosen(h, 'memory.volatile');
  void drawn();                                  // what a layout change re-runs
  assert.equal(h.asked.chrestomathyGraph[1][0], 'type.product');
});

test('a relayout redraws the workspace that was drawn, not the one read since', async () => {
  const h = harness();
  await shown(h, 'a', workspace('a'));
  const drawn = h.actions.cargoDraw({ transitive: true });
  void drawn();
  await shown(h, 'b', workspace('b'));
  void drawn();
  assert.deepEqual(h.asked.cargoGraph.map(([r]) => [r.path, r.transitive]), [['a', true], ['a', true]]);
});

test('there is no chrestomathy draw before a table is shown', () => {
  assert.equal(harness().actions.chrestomathyDraw(), null);
});

// --- the construct list and the reading keep their own problems ---------------

test('a construct list that failed is a problem with a way back, not "reading…" forever', async () => {
  /**
   * The list and the reading shared `chrestomathyProblem`: the list failed, the
   * reading succeeded and cleared it, and the panel said "reading the
   * vocabulary…" with nothing to retry. Mutation: put the list's problem in
   * `chrestomathyProblem` again -- this fails.
   */
  const h = harness();
  const list = h.actions.loadConstructIndex();
  const read = h.actions.loadChrestomathy('type.product');
  await h.answer('constructs', 0, failed('the vocabulary did not load'));
  await h.answer('chrestomathy', 0, ok(reading('type.product')));
  await Promise.all([list, read]);
  assert.equal(vocabularyShown(h.state), 'problem');
  assert.equal(h.state.constructIndexProblem.problem, 'the vocabulary did not load');
});

test('a construct list read after a failure clears that failure', async () => {
  /** Mutation: leave the problem field out of the list's success patch -- this fails. */
  const h = harness();
  const first = h.actions.loadConstructIndex();
  await h.answer('constructs', 0, failed('the vocabulary did not load'));
  await first;
  const again = h.actions.loadConstructIndex();
  await h.answer('constructs', 1, ok(index()));
  await again;
  assert.equal(h.state.chrestomathyProblem, null, 'no stale problem over the list');
  assert.equal(h.state.constructIndexProblem, null);
  assert.equal(vocabularyShown(h.state), 'list');
});

test("a reading's problem outlives the list arriving", async () => {
  const h = harness();
  const read = h.actions.loadChrestomathy('no.such');
  await h.answer('chrestomathy', 0, failed('no construct no.such'));
  await read;
  const list = h.actions.loadConstructIndex();
  await h.answer('constructs', 0, ok(index()));
  await list;
  assert.equal(h.state.chrestomathyProblem.problem, 'no construct no.such');
});

// --- "try again" repeats what failed ------------------------------------------

test('after a failed draw, "try again" draws that draw again, and nothing comes forward', async () => {
  /**
   * The retry re-read the workspace, and the panel brought the cleared canvas
   * to the front over the problem. Mutation: resolve a failed draw `true`, or
   * offer the read as its retry -- this fails.
   */
  const h = harness();
  await shown(h, 'a', workspace('a'));
  const draw = h.actions.cargoDraw({ features: true })();
  await h.answer('cargoGraph', 0, failed('the serializer refused'));
  assert.equal(await draw, false, 'nothing reached the canvas, so it is not brought forward');

  const again = h.actions.cargoRetry();
  assert.equal(again.op, 'draw');
  const redraw = again.run();
  await h.answer('cargoGraph', 1, ok(graph('a')));
  assert.equal(await redraw, true);
  assert.equal(h.asked.cargoData.length, 1, 'the workspace was not read again');
  assert.deepEqual(h.asked.cargoGraph[1][0], h.asked.cargoGraph[0][0]);
  assert.equal(h.actions.cargoRetry(), null, 'nothing left to retry');
});

test('after a failed read, "try again" reads that path again', async () => {
  const h = harness();
  const read = h.actions.loadCargoReading('docs');
  await h.answer('cargoData', 0, failed('no Cargo.toml at docs'));
  await read;
  const again = h.actions.cargoRetry();
  assert.equal(again.op, 'read');
  void again.run();
  assert.deepEqual(h.asked.cargoData.map(([path]) => path), ['docs', 'docs']);
});

test('after a failed chrestomathy draw, "try again" draws that construct again', async () => {
  const h = harness();
  await chosen(h, 'type.product');
  const draw = h.actions.chrestomathyDraw()();
  await h.answer('chrestomathyGraph', 0, failed('no layout spring'));
  assert.equal(await draw, false);
  void h.actions.loadChrestomathy('memory.volatile');   // chosen, its table not yet back
  const again = h.actions.chrestomathyRetry();
  assert.equal(again.op, 'draw');
  void again.run();
  assert.equal(h.asked.chrestomathyGraph[1][0], 'type.product');
});

// --- the census of the canvas -------------------------------------------------

/** A `/lexicon/chrestomathy/census` answer, as much of one as the panel reads. */
const census = (graphName, construct) => ({
  nodes: 1,
  constructs: [{ id: construct, name: construct, gloss: '', facet: false, look: null, count: 1,
                 languages: [{ language: 'rust', display_name: 'Rust', count: 1 }], ids: [`${graphName}:n`] }],
  facets: [], walk: [], not_constructs: [], unplaced: [], outside: [], unknown: [], unlabelled: 0,
  source: '', caveat: '', graph: graphName,
});

test("a late census of an earlier graph is not shown for the graph drawn since", async () => {
  /**
   * The crate graph is drawn, then a code map: the panel asks for each one's
   * census, and the crate graph's answering last showed Package under the
   * code map. Mutation: drop the ticket check in `loadCensus` -- this fails.
   */
  const h = harness();
  const a = h.actions.loadCensus([{ id: 'crate::a', language: 'cargo', kind: 'crate' }]);
  const b = h.actions.loadCensus([{ id: 'src::f', language: 'rust', kind: 'function' }]);
  await h.answer('census', 1, ok(census('code map', 'callable.function')));
  await h.answer('census', 0, ok(census('crate graph', 'namespace.package')));
  await Promise.all([a, b]);
  assert.equal(h.state.chrestomathyCensus.graph, 'code map');
  assert.deepEqual(h.state.chrestomathyCensus.constructs.map((r) => r.id), ['callable.function']);
});

test('a census replaces the one before it, and is sent each node with what places it', async () => {
  /** A stamped node goes with its stamp; an unstamped one with its whole `meta`. */
  const h = harness();
  const read = h.actions.loadCensus([
    { id: 's', language: 'rust', kind: 'struct', construct: 'type.product', meta: { facets: ['memory.unsafe'], x: 1 } },
    { id: 'u', language: 'c', kind: 'variable', meta: { automatic: true } },
  ]);
  assert.deepEqual(h.asked.census[0][0], [
    { id: 's', language: 'rust', kind: 'struct', construct: 'type.product', meta: { facets: ['memory.unsafe'] } },
    { id: 'u', language: 'c', kind: 'variable', construct: undefined, meta: { automatic: true } },
  ]);
  await h.answer('census', 0, ok({ ...census('one', 'type.product'), outside: [{ language: 'javascript', count: 3 }] }));
  await read;
  const again = h.actions.loadCensus([]);
  await h.answer('census', 1, ok(census('two', 'callable.function')));
  await again;
  assert.deepEqual(h.state.chrestomathyCensus.outside, [], "one graph's gaps are not carried into the next");
});

const codeMap = { graph: { nodes: {} }, metadata: { nodeCount: 1 } };
const construct = { graph: { nodes: {} }, metadata: { kind: 'chrestomathy', construct: 'type.product' } };

async function counted(h, graph, name, id) {
  const read = h.actions.readCanvas(graph, () => [{ id: `${name}:n`, language: 'rust', kind: 'function' }]);
  await h.answer('census', h.asked.census.length - 1, ok(census(name, id)));
  await read;
}

test("drawing the construct leaves no census of the graph drawn before it", async () => {
  /**
   * "draw the construct" puts the vocabulary's drawing on the canvas, and the
   * code map's census stayed, its *show* framing 0 nodes and emptying the
   * selection. Mutation: keep the census when the canvas shows a construct --
   * this fails with the code map's census still shown.
   */
  const h = harness();
  await counted(h, codeMap, 'code map', 'callable.function');
  assert.equal(h.state.chrestomathyCensus.graph, 'code map');
  await h.actions.readCanvas(construct, () => { throw new Error('the vocabulary drawing is not read'); });
  assert.equal(h.state.chrestomathyCensus, null);
  assert.equal(h.asked.census.length, 1, 'no census is asked for the drawing of the vocabulary');
});

test('a census on its way for a graph that has gone is dropped when it answers', async () => {
  /** Mutation: forget the census without taking a ticket -- this fails. */
  const h = harness();
  const read = h.actions.readCanvas(codeMap, () => [{ id: 'f', language: 'rust', kind: 'function' }]);
  await h.actions.readCanvas(null, () => []);
  await h.answer('census', 0, ok(census('code map', 'callable.function')));
  await read;
  assert.equal(h.state.chrestomathyCensus, null);
});

test("while a new graph's census is read, the old graph's is not shown", async () => {
  /** Mutation: drop the at-once clearing from `loadCensus` -- this fails. */
  const h = harness();
  await counted(h, codeMap, 'crate graph', 'namespace.package');
  const read = h.actions.readCanvas({ ...codeMap }, () => []);
  assert.equal(h.state.chrestomathyCensus, null, 'pending: no census, not the one before');
  await h.answer('census', 1, ok(census('code map', 'callable.function')));
  await read;
  assert.equal(h.state.chrestomathyCensus.graph, 'code map');
});
