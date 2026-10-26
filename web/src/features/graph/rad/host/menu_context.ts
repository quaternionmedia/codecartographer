/**
 * Which ring a press or a key opens on the canvas.
 *
 * A pointer on a node opens that node's ring, or the selection's ring when
 * more than one node is selected, whichever node the press landed on. A
 * pointer anywhere else opens the canvas ring, whatever is selected, and the
 * canvas ring offers Deselect.
 *
 * A key (`m`, the context-menu key, Shift+F10) has no pointer, and the nodes
 * take no focus, so it opens on the selection: the canvas ring when nothing is
 * selected, the selected node's own ring when one is -- the only way a key
 * reaches Pin, Collapse and View -- and the selection's ring when several are.
 * The node's ring has no Deselect, so Escape on the canvas clears a selection
 * (`canvasKeyVerb`), and every item stays reachable without a pointer.
 *
 * No application imports and no DOM, so this compiles into the conformance
 * build and is asserted under `node --test`.
 */
import type { MenuContext } from '../core/types.js';

export interface MenuInput {
  /** True for a pointer press, false for a key. */
  pointer: boolean;
  /** The id of the node under the pointer, or null. A key has none. */
  underPointer: string | null;
  /** The ids of the selected nodes. */
  selected: readonly string[];
  /** Where the ring opens, in the host's coordinates. */
  position: { x: number; y: number };
}

export function menuContextFor(input: MenuInput): MenuContext {
  const { pointer, underPointer, selected, position } = input;
  const selection: MenuContext = { type: 'selection', targetIds: [...selected], position };
  const canvas: MenuContext = { type: 'canvas', targetIds: [], position };
  if (!pointer) {
    if (selected.length === 1) return { type: 'node', targetIds: [selected[0]], position };
    return selected.length ? selection : canvas;
  }
  if (!underPointer) return canvas;
  if (selected.length > 1) return selection;
  return { type: 'node', targetIds: [underPointer], position };
}

/**
 * The verb a key commits on the canvas when no ring is open, or null. Escape
 * clears a selection, of one node or several; with nothing selected it is left
 * to whatever else hears it.
 */
export function canvasKeyVerb(key: string, selected: readonly string[]): string | null {
  return key === 'Escape' && selected.length > 0 ? 'clear-selection' : null;
}
