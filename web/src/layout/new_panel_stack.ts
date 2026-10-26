/**
 * Where `LayoutContext.openPanel` adds a window that is not in the layout.
 *
 * No Golden Layout import: the dock is read through the three things this
 * needs of its items, so this compiles under `tsconfig.pure.json` and is
 * asserted under `node --test`.
 */

/** As much of a Golden Layout content item as the choice reads. */
export interface DockItem {
  readonly isStack: boolean;
  readonly contentItems: readonly DockItem[];
  /** The item's DOM element; a stack's is the `.lm_stack` a tab sits in. */
  readonly element?: unknown;
}

/**
 * The stack a new window joins: the one whose tab the reader last clicked,
 * else the one holding the most windows -- and never the canvas's own stack,
 * where the new tab would hide the graph, while another stack exists. Null
 * when the canvas's is the only stack, leaving the place to Golden Layout.
 *
 * **WHAT THE READER CLICKED, NOT GOLDEN LAYOUT'S FOCUS.** Golden Layout
 * focuses a component on a tab click and from code, and every draw focuses
 * the Graph panel (`focusDockPanel('graph')`), so its focused stack was the
 * canvas's after each draw, whatever the reader had clicked. `clicked` is the
 * `.lm_stack` element of the tab last clicked, recorded apart from that, and
 * a stack since closed matches no element here and is passed over.
 *
 * **THE FULLEST, NOT THE FIRST.** In the default layout the first stack after
 * the canvas's is the narrow Files column; the fullest is the dock's tabs.
 */
export function stackForNewPanel<T extends DockItem>(
  root: T | null | undefined,
  canvas: T | null,
  clicked: unknown,
): T | null {
  const stacks: T[] = [];
  const visit = (item: DockItem | null | undefined): void => {
    if (!item) return;
    if (item.isStack && item !== canvas) stacks.push(item as T);
    item.contentItems.forEach(visit);
  };
  visit(root);
  if (clicked) {
    const chosen = stacks.find((s) => s.element === clicked);
    if (chosen) return chosen;
  }
  let fullest: T | null = null;
  for (const s of stacks) {
    if (s.contentItems.length > (fullest?.contentItems.length ?? 0)) fullest = s;
  }
  return fullest;
}

/** As much of a DOM element as `stackOfTabClicked` reads. */
interface Closest {
  closest(selector: string): unknown;
}

/**
 * The `.lm_stack` element of the tab a click landed on, or null when it
 * landed off the tabs or on a tab's close button: closing a tab chooses no
 * stack. Golden Layout focuses on a tab's `click`, so this is read from the
 * same event.
 */
export function stackOfTabClicked(target: unknown): unknown {
  if (!target || typeof (target as Closest).closest !== 'function') return null;
  const at = target as Closest;
  if (!at.closest('.lm_tab') || at.closest('.lm_close_tab')) return null;
  return at.closest('.lm_stack') ?? null;
}
