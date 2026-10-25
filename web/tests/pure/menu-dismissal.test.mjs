/**
 * The "+" menu closes on a click outside it or on Escape, and however it
 * closes, it leaves nothing listening.
 *
 * **THE DEFECT THIS PINS.** The outside-click listener was registered
 * `{ once: true }` and removed only by firing. Close the menu with Escape, or
 * with one of its own items, and it stayed armed: the next "+" click opened
 * the menu and that same click, reaching the document, closed it at once.
 *
 * The document is Node's own `EventTarget`, so the listeners are real ones.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { closeOnOutsideClickOrEscape } from '../../dist-pure/layout/components/menu_dismissal.js';

const now = (fn) => fn();
const key = (name) => Object.assign(new Event('keydown'), { key: name });

function menu() {
  const doc = new EventTarget();
  let closed = 0;
  const disarm = closeOnOutsideClickOrEscape(doc, () => { closed++; }, now);
  return { doc, disarm, get closed() { return closed; } };
}

test('a click outside closes the menu', () => {
  const m = menu();
  m.doc.dispatchEvent(new Event('click'));
  assert.equal(m.closed, 1);
});

test('Escape closes the menu, and the next click is not heard as an outside click', () => {
  /** Mutation: leave the click listener armed when Escape closes -- this fails. */
  const m = menu();
  m.doc.dispatchEvent(key('Escape'));
  assert.equal(m.closed, 1);
  m.doc.dispatchEvent(new Event('click'));
  assert.equal(m.closed, 1, 'the "+" click that opens the menu again closed it');
});

test('a click outside, then Escape, closes it once', () => {
  const m = menu();
  m.doc.dispatchEvent(new Event('click'));
  m.doc.dispatchEvent(key('Escape'));
  assert.equal(m.closed, 1);
});

test('closed another way, the menu hears neither a click nor Escape', () => {
  /**
   * An item's click stops at the menu, and "+" closes it by toggling; the
   * menu's removal disarms both. Mutation: a disarm that removes nothing --
   * this fails.
   */
  const m = menu();
  m.disarm();
  m.doc.dispatchEvent(new Event('click'));
  m.doc.dispatchEvent(key('Escape'));
  assert.equal(m.closed, 0);
});

test('disarmed before the listeners are armed, none is ever added', () => {
  /** The opening click is let pass a tick first; a menu gone by then listens to nothing. */
  const doc = new EventTarget();
  let later;
  let closed = 0;
  const disarm = closeOnOutsideClickOrEscape(doc, () => { closed++; }, (fn) => { later = fn; });
  disarm();
  later();
  doc.dispatchEvent(new Event('click'));
  assert.equal(closed, 0);
});

test('a key other than Escape leaves it open', () => {
  const m = menu();
  m.doc.dispatchEvent(key('Enter'));
  assert.equal(m.closed, 0);
});
