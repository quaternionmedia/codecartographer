/**
 * How the "+" menu closes on a click outside it or on Escape.
 *
 * No DOM types: the document is read as something to add and remove
 * listeners on, so this compiles under `tsconfig.pure.json` and is asserted
 * under `node --test` against Node's own `EventTarget`.
 */

type Listener = (event: unknown) => void;

/** As much of `document` as this listens on. */
export interface Listens {
  addEventListener(type: string, listener: Listener): void;
  removeEventListener(type: string, listener: Listener): void;
}

/**
 * Call `onClose` on the next click on `doc` or on Escape, once. Returns the
 * disarm, which removes both listeners and which every way the menu closes
 * must reach: the menu calls it when it is removed.
 *
 * **NOTHING IS LEFT LISTENING.** The click listener was `{ once: true }` and
 * went only by firing, so a menu closed with Escape or by one of its own
 * items (whose click stops at the menu) left it armed, and the next "+" click
 * opened the menu and closed it with the same click. Either listener firing
 * removes both; so does the disarm.
 *
 * `defer` runs the arming after the click that opened the menu has passed
 * (`setTimeout(fn, 0)` in the browser); a menu disarmed before then arms
 * nothing.
 */
export function closeOnOutsideClickOrEscape(
  doc: Listens,
  onClose: () => void,
  defer: (fn: () => void) => void,
): () => void {
  let armed = true;
  let listening = false;
  const disarm = (): void => {
    armed = false;
    if (!listening) return;
    listening = false;
    doc.removeEventListener('click', onClick);
    doc.removeEventListener('keydown', onKeydown);
  };
  const close = (): void => {
    disarm();
    onClose();
  };
  const onClick: Listener = () => close();
  const onKeydown: Listener = (event) => {
    if ((event as { key?: unknown } | null)?.key === 'Escape') close();
  };
  defer(() => {
    if (!armed) return;
    listening = true;
    doc.addEventListener('click', onClick);
    doc.addEventListener('keydown', onKeydown);
  });
  return disarm;
}
