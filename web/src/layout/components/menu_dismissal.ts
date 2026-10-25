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
 * **ESCAPE IS HEARD FROM THE START.** `defer` holds back only the click
 * listener, until the click that opened the menu has passed
 * (`setTimeout(fn, 0)` in the browser). Escape was held back with it, and the
 * menu takes the focus before that timer runs: page work kept one 29ms late
 * while an Escape pressed into the focused menu came first, reached a
 * document with nothing listening, and left the menu open. No key is the
 * click that opened the menu, so the Escape listener is added at once.
 *
 * A menu disarmed before `defer` runs adds no click listener.
 */
export function closeOnOutsideClickOrEscape(
  doc: Listens,
  onClose: () => void,
  defer: (fn: () => void) => void,
): () => void {
  let open = true;
  let clickArmed = false;
  const disarm = (): void => {
    if (!open) return;
    open = false;
    doc.removeEventListener('keydown', onKeydown);
    if (clickArmed) doc.removeEventListener('click', onClick);
    clickArmed = false;
  };
  const close = (): void => {
    disarm();
    onClose();
  };
  const onClick: Listener = () => close();
  const onKeydown: Listener = (event) => {
    if ((event as { key?: unknown } | null)?.key === 'Escape') close();
  };
  doc.addEventListener('keydown', onKeydown);
  defer(() => {
    if (!open) return;
    clickArmed = true;
    doc.addEventListener('click', onClick);
  });
  return disarm;
}
