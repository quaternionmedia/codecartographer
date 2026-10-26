/**
 * Each row of the Files panel's tree says which file it is, whole.
 *
 * **THE DEFECT THIS PINS.** A file's row is one line, and a long name is cut
 * short with an ellipsis (`golden_layout_theme.css`), with no `title` to read
 * the rest from. In a narrow panel `test_streaming_renderer_fit_after_stream.ts`
 * and `test_streaming_renderer_fit_after_relayout.ts` both read
 * `test_streaming_renderer_fit_af…`. The uploaded-files list beside it titles
 * each entry with its name; the tree did not. `tests/e2e/file-tree.spec.ts`
 * reads the title in the browser.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { fileRow } from '../../dist-pure/components/qm_comp_lib/directory/tree_rows.js';

const STREAM = 'test_streaming_renderer_fit_after_stream.ts';
const RELAYOUT = 'test_streaming_renderer_fit_after_relayout.ts';

test("a file's row is titled with its whole name", () => {
  /** Mutation: drop the title -- a name cut short has nowhere to be read whole, and this fails. */
  const open = () => {};
  assert.equal(fileRow(STREAM, open).title, STREAM);
  assert.equal(fileRow(RELAYOUT, open).title, RELAYOUT);
});

test('a disabled file is titled too, and opens nothing', () => {
  const row = fileRow('notes.txt', () => { throw new Error('opened'); }, ['ts']);
  assert.equal(row.title, 'notes.txt');
  assert.match(row.class, /\bdisabled\b/);
  assert.equal(row.onclick, undefined);
});

test('a file whose extension is allowed opens on a click', () => {
  let opened = 0;
  const row = fileRow('main.ts', () => { opened++; }, ['.ts']);
  assert.doesNotMatch(row.class, /\bdisabled\b/);
  row.onclick();
  assert.equal(opened, 1);
});
