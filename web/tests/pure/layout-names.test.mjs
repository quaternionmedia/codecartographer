/**
 * The menu's registry names reach the backend as the names it speaks, by one
 * rule and with no fallback.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { backendLayoutName } from '../../dist-pure/features/graph/services/layout_names.js';

test('every name the menu offers translates, including the one both tables dropped', () => {
  assert.equal(backendLayoutName('spring_layout'), 'Spring');
  assert.equal(backendLayoutName('kamada_kawai_layout'), 'Kamada_Kawai');
  assert.equal(backendLayoutName('sorted_square_layout'), 'Sorted_Square');
  assert.equal(backendLayoutName('compound_layout'), 'Compound');
  assert.equal(backendLayoutName('shell_layout'), 'Shell');
});

test('there is no silent fallback to Spring', () => {
  // An unknown name goes to the server as written, which answers with a sentence.
  assert.equal(backendLayoutName('nonsense_layout'), 'Nonsense');
  assert.equal(backendLayoutName('nonsense'), 'Nonsense');
  assert.equal(backendLayoutName(''), '');
});

test('a display name or a spaced name is left as its display form', () => {
  assert.equal(backendLayoutName('Kamada Kawai'), 'Kamada_Kawai');
  assert.equal(backendLayoutName('kamada-kawai'), 'Kamada_Kawai');
});
