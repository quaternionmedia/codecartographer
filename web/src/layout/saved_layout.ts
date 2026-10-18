/**
 * The reader's saved arrangement of the dock, checked before Golden Layout
 * reads it.
 *
 * **GOLDEN LAYOUT THROWS ON WHAT IT CANNOT BUILD, AND THE SHELL LOADS THE SAVED
 * ARRANGEMENT AS IT STARTS.** A saved layout naming a panel this version does
 * not register stopped the shell with "Component type not registered", and the
 * page opened with no panels -- on every visit, until somebody found Reset in
 * the `+` menu. So the saved arrangement is read here first, as plain data, and
 * accepted only if it is a layout whose every panel is registered, appears
 * once, and is under its registry id: `findFirstComponentItemById` is how a
 * panel is focused, re-opened or known to be open, and a panel without its id,
 * or shown twice, is one those calls cannot find or find the wrong one of.
 * Anything else is dropped for the built-in default, and the reader is told
 * why (`LayoutContext.loadInitialLayoutConfig`).
 *
 * DOM-free and app-free, so `npm run test:pure` compiles and asserts it
 * directly. The caller parses the saved text, has Golden Layout convert its
 * own resolved form, and puts today's settings over the root this returns.
 * alfred's workspace, which copied this shell, checks a saved arrangement the
 * same way before Golden Layout sees it.
 */

/** A registered panel, as the check needs it. */
export interface KnownPanel {
  /** The registry id, which is also the panel's component type. */
  readonly id: string;
  /** The tab title the registry gives it. */
  readonly title: string;
  /** The name a sentence calls it by: the add-window menu's label. */
  readonly label: string;
  readonly closable: boolean;
}

/** A layout item as JSON has it: a row, column, stack or panel. */
export type SavedItem = Record<string, unknown>;

export type SavedLayoutCheck =
  | { readonly usable: true; readonly root: SavedItem }
  | { readonly usable: false; readonly why: string };

const CONTAINERS = new Set(['row', 'column', 'stack']);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Whether `saved`, a parsed layout, can be loaded, and the root to load.
 *
 * The root comes back as a copy whose panels carry the registry's titles and
 * closability, whatever was saved with them; `saved` itself is not changed.
 */
export function checkSavedLayout(saved: unknown, panels: readonly KnownPanel[]): SavedLayoutCheck {
  if (!isRecord(saved)) return { usable: false, why: 'it is not a layout' };
  if (!isRecord(saved.root)) return { usable: false, why: 'it has no panels in it' };
  // A popped-out panel would open a window with nothing in it: no panel here
  // can be drawn outside this window, which is why none offers to pop out.
  if (Array.isArray(saved.openPopouts) && saved.openPopouts.length > 0) {
    return { usable: false, why: 'it has panels in windows of their own' };
  }

  const known = new Map(panels.map((panel) => [panel.id, panel]));
  const seen: string[] = [];
  const checked = checkItem(saved.root, known, seen);
  if ('why' in checked) return { usable: false, why: checked.why };

  const twice = seen.find((id, index) => seen.indexOf(id) !== index);
  if (twice !== undefined) {
    return { usable: false, why: `it shows ${known.get(twice)?.label ?? twice} twice` };
  }
  return { usable: true, root: checked.item };
}

/** `item` checked and copied, or why it cannot be loaded; collects the panel ids it names. */
function checkItem(
  item: unknown,
  known: ReadonlyMap<string, KnownPanel>,
  seen: string[],
): { item: SavedItem } | { why: string } {
  if (!isRecord(item)) return { why: 'it has an item that is not one' };

  if (item.type === 'component') {
    const panel = typeof item.componentType === 'string' ? known.get(item.componentType) : undefined;
    if (!panel) {
      return { why: `it names ${JSON.stringify(item.componentType)}, which this version does not have` };
    }
    if (item.id !== panel.id) return { why: `its ${panel.label} panel is not under its id` };
    seen.push(panel.id);
    // The registry's title and closability, not the saved ones.
    return { item: { ...item, title: panel.title, isClosable: panel.closable } };
  }

  if (typeof item.type !== 'string' || !CONTAINERS.has(item.type)) {
    return { why: `it has an item of a kind Golden Layout does not know (${JSON.stringify(item.type)})` };
  }
  if (!Array.isArray(item.content) || item.content.length === 0) {
    return { why: `it has an empty ${item.type}` };
  }
  const content: SavedItem[] = [];
  for (const child of item.content) {
    if (item.type === 'stack' && !(isRecord(child) && child.type === 'component')) {
      return { why: 'it has a stack holding something other than panels' };
    }
    const checked = checkItem(child, known, seen);
    if ('why' in checked) return checked;
    content.push(checked.item);
  }
  return { item: { ...item, content } };
}
