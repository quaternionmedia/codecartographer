/**
 * A box that is clicked to do something is pressed from the keyboard as a
 * button is: it is in the tab order, it is announced as a button, and Enter
 * and Space press it.
 *
 * **THE DEFECT THIS PINS.** The Open panel's Local files box was a `div` with
 * only a click handler, and the file input it opens is hidden, so files could
 * be added with a pointer and never from the keyboard. The box is a drop
 * target holding that input, which a `<button>` may not hold; `pressable`
 * gives it what a button has. `tests/e2e/open-panel.spec.ts` presses it in
 * the browser.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { pressable } from '../../dist-pure/components/codecarto/control_panel/pressable.js';

function key(name) {
  return {
    key: name,
    prevented: false,
    preventDefault() { this.prevented = true; },
  };
}

function box() {
  let presses = 0;
  const attrs = pressable(() => { presses++; });
  return { attrs, get presses() { return presses; } };
}

test('the box is in the tab order and announced as a button', () => {
  /** Mutation: drop the tabindex -- Tab never reaches the box, and this fails. */
  const { attrs } = box();
  assert.equal(attrs.tabindex, 0);
  assert.equal(attrs.role, 'button');
});

test('Enter presses it once', () => {
  const b = box();
  const enter = key('Enter');
  b.attrs.onkeydown(enter);
  assert.equal(b.presses, 1);
  assert.ok(enter.prevented);
});

test('Space presses it once, and does not scroll the column it sits in', () => {
  /** Mutation: press on Enter alone, or leave Space its default -- this fails. */
  const b = box();
  const space = key(' ');
  b.attrs.onkeydown(space);
  assert.equal(b.presses, 1);
  assert.ok(space.prevented, 'Space was left to scroll the column');
});

test('no other key presses it, and Tab still moves on', () => {
  /** Mutation: press on any key, or prevent every key's default -- this fails. */
  const b = box();
  for (const name of ['Tab', 'Escape', 'a', 'ArrowDown']) {
    const other = key(name);
    b.attrs.onkeydown(other);
    assert.equal(other.prevented, false, `${JSON.stringify(name)} was prevented`);
  }
  assert.equal(b.presses, 0);
});
