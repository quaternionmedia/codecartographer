/**
 * Whether a saved layout is loaded, or dropped for the default.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { componentTypesIn, readSavedLayout } from '../../dist-pure/layout/saved_layout.js';

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
  const saved = readSavedLayout(layout('graph', 'upload-panel', 'upload-panel'), REGISTERED);
  assert.equal(saved.kind, 'unusable');
  assert.match(saved.why, /'upload-panel'/);
  assert.equal(saved.why.match(/upload-panel/g).length, 1, 'each unknown window named once');
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
