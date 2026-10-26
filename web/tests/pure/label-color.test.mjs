// The canvas's names take the theme's font colour unless the reader chose one.
//
// Mutation: return `chosen` whenever it is set -- the starting value is drawn
// as the Terminal theme's green on every theme, and the first case fails.
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { THEME_LABEL_COLOR, labelColorOf } from '../../dist-pure/features/graph/services/label_color.js';

const QM_FONT = '#fbf1c7';

test("the starting colour is the theme's font colour, in any case", () => {
  assert.equal(labelColorOf(THEME_LABEL_COLOR, QM_FONT), QM_FONT);
  assert.equal(labelColorOf(' #00FF41 ', QM_FONT), QM_FONT);
});

test("no colour at all is the theme's too", () => {
  assert.equal(labelColorOf(undefined, QM_FONT), QM_FONT);
  assert.equal(labelColorOf('', QM_FONT), QM_FONT);
});

test('a colour the reader chose is drawn as chosen', () => {
  assert.equal(labelColorOf('#ff8800', QM_FONT), '#ff8800');
});

test('with no theme font to read, the starting colour stands', () => {
  assert.equal(labelColorOf(THEME_LABEL_COLOR, ''), THEME_LABEL_COLOR);
});
