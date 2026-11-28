/**
 * The least width, or height, a stack of tabs needs: that of its widest tab.
 *
 * Golden Layout bounds a splitter's drag by the least size of what stands on
 * each side of it, and for a stack it adds up the least size of every tab,
 * though a stack shows one tab at a time. A stack of many tabs then needs
 * more room than the dock has, the bound falls behind the splitter, and a
 * drag toward that stack moves the splitter the other way. `fitStackMinimum`
 * replaces the sum with the greatest for a stack's tabs, and leaves every
 * other sum to the library.
 *
 * What this cannot do: hold after an upgrade that renames the method it
 * replaces. `fitStackMinimum` then throws when the dock is built, so the
 * page says so before anybody drags.
 */

import { RowOrColumn } from 'golden-layout';

interface Item {
  isComponent: boolean;
}

interface Bounded {
  calculateContentItemMinSize(item: Item): number;
  calculateContentItemsTotalMinSize(items: Item[]): number;
}

/** The least size a set of tabs needs together: the greatest of theirs, or 0 for none. */
export function leastForTabs(sizes: readonly number[]): number {
  return sizes.reduce((most, size) => Math.max(most, size), 0);
}

let fitted = false;

/** Bound a splitter's drag beside a stack by its widest tab. Safe to call again. */
export function fitStackMinimum(): void {
  if (fitted) return;
  const bounded = RowOrColumn.prototype as unknown as Bounded;
  const summed = bounded.calculateContentItemsTotalMinSize;
  if (typeof summed !== 'function' || typeof bounded.calculateContentItemMinSize !== 'function') {
    throw new Error('golden-layout no longer bounds a splitter by `calculateContentItemsTotalMinSize`');
  }
  bounded.calculateContentItemsTotalMinSize = function (this: Bounded, items: Item[]): number {
    if (items.length > 0 && items.every((item) => item.isComponent)) {
      return leastForTabs(items.map((item) => this.calculateContentItemMinSize(item)));
    }
    return summed.call(this, items);
  };
  fitted = true;
}
