/**
 * A saved arrangement of the dock is loaded only if Golden Layout can build it
 * and every panel in it can be found by its id; anything else is a sentence.
 *
 *   npm run test:pure
 *
 * The browser half -- that a refused layout boots the default and says why,
 * and that a saved one comes back -- is golden-layout-shell.spec.ts.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { checkSavedLayout } from '../../dist-pure/layout/saved_layout.js';

const PANELS = [
  { id: 'graph', title: '◈ Graph', label: 'Graph', closable: true },
  { id: 'file-tree', title: '◉ Files', label: 'Files', closable: true },
  { id: 'plotbar', title: '▶ Actions', label: 'Actions', closable: true },
];

const panel = (id, extra = {}) => ({ type: 'component', componentType: id, id, ...extra });

const refused = (saved) => {
  const check = checkSavedLayout(saved, PANELS);
  assert.equal(check.usable, false, `expected a refusal for ${JSON.stringify(saved)}`);
  return check.why;
};

test('a layout of registered panels, each once and under its id, is usable', () => {
  const saved = {
    root: {
      type: 'row',
      content: [
        { type: 'stack', activeItemIndex: 1, content: [panel('graph'), panel('plotbar')] },
        panel('file-tree', { size: '30%' }),
      ],
    },
  };
  const check = checkSavedLayout(saved, PANELS);
  assert.equal(check.usable, true);
  assert.equal(check.root.type, 'row');
  assert.equal(check.root.content[0].activeItemIndex, 1);
  assert.equal(check.root.content[1].size, '30%');
});

test('the tabs take the registry\'s titles and closability, not the saved ones', () => {
  const saved = { root: panel('graph', { title: 'An old title', isClosable: false }) };
  const check = checkSavedLayout(saved, PANELS);
  assert.equal(check.usable, true);
  assert.equal(check.root.title, '◈ Graph');
  assert.equal(check.root.isClosable, true);
  // A copy: the parsed layout the caller holds is not rewritten under it.
  assert.equal(saved.root.title, 'An old title');
});

test('a panel this version does not register is refused by name', () => {
  // `source-panel` is a panel an earlier version of this shell had.
  const why = refused({ root: { type: 'row', content: [panel('graph'), panel('source-panel')] } });
  assert.equal(why, 'it names "source-panel", which this version does not have');
});

test('a panel without its registry id, or under another, is refused', () => {
  const missing = { type: 'component', componentType: 'plotbar' };
  assert.equal(refused({ root: { type: 'stack', content: [missing] } }), 'its Actions panel is not under its id');
  const other = { type: 'component', componentType: 'plotbar', id: 'actions' };
  assert.equal(refused({ root: { type: 'stack', content: [other] } }), 'its Actions panel is not under its id');
});

test('a panel shown twice is refused', () => {
  const why = refused({ root: { type: 'row', content: [panel('graph'), { type: 'stack', content: [panel('graph')] }] } });
  assert.equal(why, 'it shows Graph twice');
});

test('panels in windows of their own are refused', () => {
  const why = refused({ root: panel('graph'), openPopouts: [{ root: panel('plotbar') }] });
  assert.equal(why, 'it has panels in windows of their own');
  // An empty list is what Golden Layout saves when nothing is popped out.
  assert.equal(checkSavedLayout({ root: panel('graph'), openPopouts: [] }, PANELS).usable, true);
});

test('what is not a layout, or has no panels, is refused', () => {
  assert.equal(refused(null), 'it is not a layout');
  assert.equal(refused([1, 2, 3]), 'it is not a layout');
  assert.equal(refused('a string'), 'it is not a layout');
  assert.equal(refused({}), 'it has no panels in it');
  assert.equal(refused({ root: [panel('graph')] }), 'it has no panels in it');
});

test('a malformed tree is refused before Golden Layout meets it', () => {
  assert.equal(refused({ root: { type: 'row', content: [] } }), 'it has an empty row');
  assert.equal(refused({ root: { type: 'column' } }), 'it has an empty column');
  assert.equal(
    refused({ root: { type: 'stack', content: [{ type: 'row', content: [panel('graph')] }] } }),
    'it has a stack holding something other than panels',
  );
  assert.equal(
    refused({ root: { type: 'ground', content: [panel('graph')] } }),
    'it has an item of a kind Golden Layout does not know ("ground")',
  );
  assert.equal(refused({ root: { type: 'row', content: [null] } }), 'it has an item that is not one');
});
