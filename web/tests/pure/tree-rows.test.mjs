/**
 * Each row of the Files panel's tree says which entry it is, whole, and is
 * reached and pressed from the keyboard.
 *
 * **THE DEFECTS THIS PINS.** A file's row is one line, and a long name is cut
 * short with an ellipsis (`golden_layout_theme.css`), with no `title` to read
 * the rest from. In a narrow panel `test_streaming_renderer_fit_after_stream.ts`
 * and `test_streaming_renderer_fit_after_relayout.ts` both read
 * `test_streaming_renderer_fit_af…`. The uploaded-files list beside it titles
 * each entry with its name; the tree did not.
 *
 * And the tree could be used only with a pointer. A file or folder row was a
 * `div` with a click handler and no role, tabindex or key handler, so a
 * keyboard never reached one and a screen reader read it as text; in a GitHub
 * tree the only tab stops were the raw links, each named "raw", with nothing
 * to say which file's. `tests/e2e/file-tree.spec.ts` presses them in the
 * browser.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { entryPath, fileRow, folderRow, rawLink } from '../../dist-pure/components/qm_comp_lib/directory/tree_rows.js';

const STREAM = 'test_streaming_renderer_fit_after_stream.ts';
const RELAYOUT = 'test_streaming_renderer_fit_after_relayout.ts';

function key(name) {
  return {
    key: name,
    prevented: false,
    preventDefault() { this.prevented = true; },
  };
}

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

test("a folder's row is titled with its whole name, as it is cut short too", () => {
  /** Mutation: drop the folder's title -- this fails. */
  const name = 'a_folder_whose_name_runs_past_a_narrow_panel';
  assert.equal(folderRow(name, false, () => {}).title, name);
});

test('a file whose extension is allowed opens on a click', () => {
  let opened = 0;
  const row = fileRow('main.ts', () => { opened++; }, ['.ts']);
  assert.doesNotMatch(row.class, /\bdisabled\b/);
  row.onclick();
  assert.equal(opened, 1);
});

test("a file's row is a button in the tab order, and Enter and Space open it", () => {
  /** Mutation: drop the row's role, tabindex or key handler -- a keyboard never opens a file, and this fails. */
  let opened = 0;
  const row = fileRow('main.rs', () => { opened++; });
  assert.equal(row.role, 'button');
  assert.equal(row.tabindex, 0);
  for (const name of ['Enter', ' ']) {
    const press = key(name);
    row.onkeydown(press);
    assert.ok(press.prevented, `${JSON.stringify(name)} kept its default`);
  }
  assert.equal(opened, 2);
  const tab = key('Tab');
  row.onkeydown(tab);
  assert.equal(tab.prevented, false);
  assert.equal(opened, 2);
});

test('a disabled file is said to be disabled, and is no tab stop', () => {
  const row = fileRow('notes.txt', () => { throw new Error('opened'); }, ['ts']);
  assert.equal(row['aria-disabled'], 'true');
  assert.equal(row.tabindex, undefined);
  assert.equal(row.onkeydown, undefined);
});

test("a folder's row is a button that says whether it is open, and Enter and Space toggle it", () => {
  /** Mutation: drop aria-expanded, or the key handler -- this fails. */
  let toggled = 0;
  const toggle = () => { toggled++; };
  const closed = folderRow('crates', false, toggle);
  assert.equal(closed.role, 'button');
  assert.equal(closed.tabindex, 0);
  assert.equal(closed['aria-expanded'], 'false');
  assert.equal(folderRow('crates', true, toggle)['aria-expanded'], 'true');
  closed.onkeydown(key('Enter'));
  closed.onkeydown(key(' '));
  closed.onclick();
  assert.equal(toggled, 3);
});

test('a folder with nothing to open is no button and no tab stop', () => {
  const row = folderRow('empty', false, null);
  assert.equal(row.role, undefined);
  assert.equal(row.tabindex, undefined);
  assert.equal(row['aria-expanded'], undefined);
  assert.equal(row.onclick, undefined);
});

test("a raw link is named for the file whose contents it opens", () => {
  /** Mutation: leave the link named by its text alone -- every tab stop reads "raw", and this fails. */
  const url = 'https://raw.githubusercontent.com/example/small/main/crates/a/src/lib.rs';
  const link = rawLink(entryPath('crates/a/src', 'lib.rs'), url);
  assert.equal(link.href, url);
  assert.equal(link['aria-label'], 'raw contents of crates/a/src/lib.rs');
  assert.equal(rawLink(entryPath('', 'Cargo.toml'), url)['aria-label'], 'raw contents of Cargo.toml');
});

test('a file read from disk has no raw link', () => {
  assert.equal(rawLink('src/lib.rs', '/work/small/src/lib.rs'), null);
});
