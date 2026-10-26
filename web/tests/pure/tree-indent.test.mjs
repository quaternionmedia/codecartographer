/**
 * The Files panel's tree indents each folder's contents, and keeps each
 * folder's row to one line as it keeps each file's.
 *
 * **THE DEFECT THIS PINS.** No rule styled `.folder_content` once 1ead5b4
 * deleted `directory_nav.css` with its margin, padding and border, so every
 * level of the tree was drawn at one x: `crates/a/src/lib.rs` and
 * `crates/b/src/lib.rs` sat flush with `crates` itself, and nothing said which
 * folder a file was in. The indent is CSS, so this reads the stylesheet; the
 * geometry is measured in the browser by `tests/e2e/file-tree.spec.ts`.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const css = readFileSync('src/layout/golden_layout_theme.css', 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');

/** The declarations of every rule whose selector list names `selector`, as one map. */
function declarations(selector) {
  const found = new Map();
  for (const [, selectors, body] of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (!selectors.split(',').map((s) => s.trim().replace(/\s+/g, ' ')).includes(selector)) continue;
    for (const decl of body.split(';')) {
      const at = decl.indexOf(':');
      if (at > 0) found.set(decl.slice(0, at).trim(), decl.slice(at + 1).trim());
    }
  }
  return found;
}

/** A length in em or px, as a number; 0 for anything else. */
function length(value) {
  const found = /^(-?\d*\.?\d+)(em|px|rem)$/.exec(value ?? '');
  return found ? Number(found[1]) : 0;
}

test("a folder's contents sit a step in from its name", () => {
  /** Mutation: drop the step's padding and margin -- every level is drawn at one x, and this fails. */
  const rule = declarations('.gl-file-tree__tree .folder_content');
  const step = ['margin-left', 'padding-left', 'margin-inline-start', 'padding-inline-start']
    .reduce((sum, name) => sum + length(rule.get(name)), 0);
  assert.ok(step > 0, `.folder_content is not indented: ${JSON.stringify([...rule])}`);
});

test("a folder's name is one line, cut short rather than wrapped", () => {
  /** Mutation: let the name wrap -- a long folder name takes two lines, and this fails. */
  const name = declarations('.gl-file-tree__tree .folder_name');
  assert.equal(name.get('white-space'), 'nowrap');
  assert.equal(name.get('text-overflow'), 'ellipsis');
  assert.equal(name.get('overflow'), 'hidden');
});
