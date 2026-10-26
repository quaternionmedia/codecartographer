/**
 * The step the reader is on is one copy, and only the reader moves it.
 *
 * **WHAT THIS PINS.** The rail and the walkthrough card both show a step. Two
 * copies of it disagree the moment either moves alone: the card on its own
 * page 1 while the rail says Tune. So the card keeps no step and reads the
 * shell's, and the shell passes `ctx.step`. And a step is the reader's: a
 * draw brings the canvas forward (`focusDockPanel('graph')`) after every
 * plot, and if that moved the step, the rail would jump to Read under a
 * reader who never chose it. Only entering a step, and a window the reader
 * chose, assign it.
 *
 * Read as text: the card, the shell and `layout_context.ts` are application
 * code no test build compiles. `steps.test.mjs` asserts what entering a step
 * does; steps.spec.ts sees all of it in a browser.
 *
 *   npm run test:state
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const card = readFileSync('src/components/codecarto/help/help_modal.ts', 'utf8');
const shell = readFileSync('src/layout/golden_layout_shell.ts', 'utf8');
const context = readFileSync('src/layout/layout_context.ts', 'utf8');

/** The body of method `name` in `layout_context.ts`, to the next method at its indent. */
function method(name) {
  const found = new RegExp(`\\n  (?:public |private )?${name}\\([^)]*\\)[^{]*\\{\\n([\\s\\S]*?)\\n  \\}\\n`).exec(context);
  assert.ok(found, `${name} was not found in layout_context.ts; the pattern is stale`);
  return found[1];
}

test('the card keeps no step of its own, and shows the one the shell passes', () => {
  /** Mutation: `let _step = 0;` in help_modal.ts and page through it -- this fails. */
  assert.doesNotMatch(card, /^let _step\b/m, 'help_modal.ts keeps a step of its own');
  assert.match(card, /stepNamed\(attrs\.step\)/, 'the card does not show the step it is passed');
  assert.match(shell, /m\(HelpModalComponent, \{ step: ctx\.step, onStep: \(id\) => ctx\.enterStep\(id\) \}\)/,
    'the shell does not pass the card the step the rail shows, or does not enter the step the card asks for');
});

test('only entering a step and a window the reader chose move it', () => {
  /** Mutation: `this.step = 'read';` in focusDockPanel, as if a draw chose Read -- this fails. */
  const assigned = [...context.matchAll(/\n  (?:public |private )?(\w+)\([^)]*\)[^{]*\{\n([\s\S]*?)\n  \}\n/g)]
    .filter(([, , body]) => /\bthis\.step = /.test(body))
    .map(([, name]) => name)
    .sort();
  assert.deepEqual(assigned, ['_followWindow', 'enterStep']);
});

test('a window the reader chose follows its step, and a window brought forward by a draw does not', () => {
  /** Mutation: call `_followWindow` from openPanel -- View ▸ Compare moves the rail, and this fails. */
  assert.match(method('noteClick'), /this\._followWindow\(panelId\)/, 'a tab chosen does not move the step');
  assert.match(method('chooseWindow'), /this\._followWindow\(panelId\)/, 'a window chosen from + does not move the step');
  for (const name of ['openPanel', 'focusDockPanel']) {
    assert.doesNotMatch(method(name), /_followWindow|enterStep/, `${name} moves the step`);
  }
  const menu = readFileSync('src/layout/components/add_panel_menu.ts', 'utf8');
  assert.match(menu, /ctx\.chooseWindow\(def\.id\)/, 'the + menu opens a window without following its step');
});

test('a window brought forward restores a stack maximised elsewhere', () => {
  /**
   * Every window that comes forward comes through focusDockPanel; one that
   * openPanel adds is restored by Golden Layout, whose `addItem` minimises a
   * maximised stack first. Mutation: drop `this._restoreAllBut(stack);` from
   * focusDockPanel -- a window shown behind step 4's canvas stays hidden, and
   * this fails.
   */
  assert.match(method('focusDockPanel'), /this\._restoreAllBut\(stack\);/);
});

test('the page opens on step 1, and a reset of the layout goes back to it', () => {
  /** Mutation: drop the `enterStep(FIRST_STEP)` after the layout loads -- a saved layout's maximised stack outlives the rail's step 1, and this fails. */
  const boot = /glInstance\.loadLayout\(DEFAULT_LAYOUT_CONFIG\);\n    \}\n([\s\S]*?)\n    \/\/ A `\?show=`/.exec(shell);
  assert.ok(boot, 'the shell does not load its layout as this test reads it; the pattern is stale');
  assert.match(boot[1], /ctx\.enterStep\(FIRST_STEP\);/);
  assert.match(method('resetLayoutToBuiltinDefault'), /this\.enterStep\(FIRST_STEP\);/);
});
