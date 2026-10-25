/**
 * Whether a saved layout is loaded, or dropped for the default.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { RENAMED_PANELS, componentTypesIn, readSavedLayout } from '../../dist-pure/layout/saved_layout.js';

const REGISTERED = ['graph', 'file-tree', 'estate-panel'];

const layout = (...types) => JSON.stringify({
  root: { type: 'row', content: types.map((t) => ({ type: 'component', componentType: t, id: t })) },
});

test('nothing saved is nothing to load', () => {
  assert.deepEqual(readSavedLayout(null, REGISTERED), { kind: 'none' });
  assert.deepEqual(readSavedLayout('', REGISTERED), { kind: 'none' });
});

test('a layout naming only registered windows is loaded as saved', () => {
  const saved = readSavedLayout(layout('graph', 'estate-panel'), REGISTERED);
  assert.equal(saved.kind, 'usable');
  assert.deepEqual(componentTypesIn(saved.config), ['graph', 'estate-panel']);
});

test('a layout naming a window this version does not have is dropped, and says which', () => {
  /* Mutation: return 'usable' without comparing against the registry -- Golden
     Layout is handed a type it throws on, and this fails. */
  const saved = readSavedLayout(layout('graph', 'gone-panel', 'gone-panel'), REGISTERED);
  assert.equal(saved.kind, 'unusable');
  assert.match(saved.why, /'gone-panel'/);
  assert.equal(saved.why.match(/gone-panel/g).length, 1, 'each unknown window named once');
});

test('a window nested in stacks, rows and an open popout is found', () => {
  const config = {
    root: { type: 'column', content: [
      { type: 'stack', content: [{ type: 'component', componentType: 'graph' }] },
      { type: 'row', content: [{ type: 'stack', content: [{ type: 'component', componentType: 'file-tree' }] }] },
    ] },
    openPopouts: [{ root: { type: 'stack', content: [{ type: 'component', componentType: 'gone' }] } }],
  };
  assert.deepEqual(componentTypesIn(config), ['graph', 'file-tree', 'gone']);
  assert.equal(readSavedLayout(JSON.stringify(config), REGISTERED).kind, 'unusable');
});

test('text that is not a layout is dropped rather than handed on', () => {
  assert.equal(readSavedLayout('{not json', REGISTERED).kind, 'unusable');
  assert.equal(readSavedLayout('[]', REGISTERED).kind, 'unusable');
  assert.equal(readSavedLayout('42', REGISTERED).kind, 'unusable');
});

test('Upload, Repository and Actions in a saved layout become one Open window', () => {
  /* Mutation: drop the renames -- the layout names three windows this
     version lacks, is dropped for the default, and this fails. */
  const saved = {
    root: { type: 'column', content: [
      { type: 'stack', content: [{ type: 'component', componentType: 'graph', id: 'graph' }] },
      { type: 'row', content: [
        { type: 'stack', content: [{ type: 'component', componentType: 'file-tree', id: 'file-tree' }] },
        { type: 'stack', activeItemIndex: 3, content: [
          { type: 'component', componentType: 'upload-panel', id: 'upload-panel', title: '↑ Upload' },
          { type: 'component', componentType: 'repo-panel', id: 'repo-panel', title: '⬇ Repository' },
          { type: 'component', componentType: 'graph-settings-panel', id: 'graph-settings-panel' },
          { type: 'component', componentType: 'plotbar', id: 'plotbar', title: '▶ Actions' },
          { type: 'component', componentType: 'estate-panel', id: 'estate-panel' },
        ] },
      ] },
    ] },
  };
  const read = readSavedLayout(JSON.stringify(saved), ['graph', 'file-tree', 'open', 'graph-settings-panel', 'estate-panel']);
  assert.equal(read.kind, 'usable');
  assert.deepEqual(read.renamed.sort(), ['plotbar', 'repo-panel', 'upload-panel']);
  assert.deepEqual(componentTypesIn(read.config), ['graph', 'file-tree', 'open', 'graph-settings-panel', 'estate-panel']);
  const dock = read.config.root.content[1].content[1];
  assert.equal(dock.content[0].id, 'open');
  // Actions was the active tab, and Open is what it became.
  assert.equal(dock.activeItemIndex, 0);
});

test('a stack holding only windows merged away goes with them', () => {
  const saved = {
    root: { type: 'row', content: [
      { type: 'stack', content: [{ type: 'component', componentType: 'upload-panel' }] },
      { type: 'stack', content: [{ type: 'component', componentType: 'plotbar' }] },
      { type: 'stack', activeItemIndex: 1, content: [
        { type: 'component', componentType: 'graph' },
        { type: 'component', componentType: 'estate-panel' },
      ] },
    ] },
  };
  const read = readSavedLayout(JSON.stringify(saved), ['graph', 'open', 'estate-panel']);
  assert.equal(read.kind, 'usable');
  assert.equal(read.config.root.content.length, 2);
  assert.deepEqual(componentTypesIn(read.config), ['open', 'graph', 'estate-panel']);
  assert.equal(read.config.root.content[1].activeItemIndex, 1);
});

test('a layout with nothing to rename is read unchanged', () => {
  const text = layout('graph', 'estate-panel');
  const read = readSavedLayout(text, REGISTERED);
  assert.deepEqual(read.renamed, []);
  assert.deepEqual(read.config, JSON.parse(text));
});

test('the renames name only windows this version lacks, onto one it has', () => {
  assert.deepEqual(Object.keys(RENAMED_PANELS).sort(), ['plotbar', 'repo-panel', 'upload-panel']);
  assert.deepEqual([...new Set(Object.values(RENAMED_PANELS))], ['open']);
});

test('a legacy layout, its root written as `content[0]`, is read as Golden Layout reads it', () => {
  /**
   * Golden Layout 2.6 takes `content[0]` as the root when `root` is absent
   * (`LayoutConfig.resolve`), and so does a popout (`PopoutLayoutConfig.resolve`).
   * The check read `root` alone, so a legacy layout naming a window this version
   * lacks passed it, and Golden Layout was handed a type it throws on.
   * Mutation: read `root` only -- this fails.
   */
  const gone = { type: 'stack', content: [{ type: 'component', componentType: 'gone' }] };
  const legacy = { content: [{ type: 'row', content: [{ type: 'component', componentType: 'graph' }, gone] }] };
  assert.deepEqual(componentTypesIn(legacy), ['graph', 'gone']);
  assert.equal(readSavedLayout(JSON.stringify(legacy), REGISTERED).kind, 'unusable');

  const popout = {
    root: { type: 'component', componentType: 'graph' },
    openPopouts: [{ content: [gone] }],
  };
  assert.deepEqual(componentTypesIn(popout), ['graph', 'gone']);
});

test("a popout's own open popouts are read too", () => {
  /** `PopoutLayoutConfig.resolve` resolves a popout's `openPopouts` in turn. */
  const config = {
    root: { type: 'component', componentType: 'graph' },
    openPopouts: [{
      root: { type: 'component', componentType: 'file-tree' },
      openPopouts: [{ root: { type: 'component', componentType: 'gone' } }],
    }],
  };
  assert.deepEqual(componentTypesIn(config), ['graph', 'file-tree', 'gone']);
});

test('`content` beside a `root` is not read, since Golden Layout does not read it', () => {
  const both = {
    root: { type: 'component', componentType: 'graph' },
    content: [{ type: 'component', componentType: 'gone' }],
  };
  assert.deepEqual(componentTypesIn(both), ['graph']);
  assert.equal(readSavedLayout(JSON.stringify(both), REGISTERED).kind, 'usable');
});
