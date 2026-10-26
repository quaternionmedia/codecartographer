/**
 * What a box that is clicked to do something needs to be pressed from the
 * keyboard as a button is: a place in the tab order, the button role, and
 * Enter and Space pressing it.
 *
 * For a box that cannot be a `<button>`: the Open panel's Local files box is
 * a drop target holding the hidden file input it opens, and a `<button>` may
 * hold no input. With only a click handler it was reached by a pointer and
 * never from the keyboard.
 *
 * No DOM types, so this compiles under `tsconfig.pure.json` and is asserted
 * under `node --test` (`tests/pure/pressable.test.mjs`).
 */

/** As much of a `KeyboardEvent` as a press reads. */
export interface KeyPress {
  key: string;
  preventDefault(): void;
}

/** The attributes that make a box `press` on Enter and Space, beside its click. */
export function pressable(press: () => void): {
  role: 'button';
  tabindex: 0;
  onkeydown: (event: KeyPress) => void;
} {
  return {
    role: 'button',
    tabindex: 0,
    onkeydown: (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      // Space would scroll the column the box sits in.
      event.preventDefault();
      press();
    },
  };
}
