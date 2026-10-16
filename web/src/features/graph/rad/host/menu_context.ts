/**
 * Which ring a press or a key opens on the canvas.
 *
 * A pointer on a node opens that node's ring, or the selection's ring when
 * more than one node is selected, whichever node the press landed on. A
 * pointer anywhere else opens the canvas ring, whatever is selected, and the
 * canvas ring offers Deselect.
 *
 * A key has no pointer. It opens the selection's ring when anything is
 * selected, a single node included, and the canvas ring when nothing is. Both
 * offer Deselect, so a selection can be cleared without a pointer.
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
  if (!pointer) return selected.length ? selection : canvas;
  if (!underPointer) return canvas;
  if (selected.length > 1) return selection;
  return { type: 'node', targetIds: [underPointer], position };
}
