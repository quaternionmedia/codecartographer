/**
 * Whether a saved layout can be loaded, and what it names in this version.
 *
 * The reader's arrangement is kept in localStorage under
 * `cc:gl-layout:default`. Golden Layout 2.6 throws a `BindError` on a component
 * type nobody registered, and the shell loads the layout while it boots: a
 * saved layout naming a window this version lacks would leave the page with
 * no windows. This reads the saved text before Golden Layout does: it renames
 * the windows that were merged into another, and says whether to load the
 * result.
 *
 * No Golden Layout import: the layout is read as plain JSON, so this compiles
 * under `tsconfig.pure.json` and is asserted under `node --test`.
 */

/**
 * Window ids a saved layout may hold that this version calls something else.
 * Upload, Repository and Actions are one Open window.
 */
export const RENAMED_PANELS: Readonly<Record<string, string>> = {
  'upload-panel': 'open',
  'repo-panel': 'open',
  plotbar: 'open',
};

export type SavedLayout =
  | { kind: 'none' }
  | { kind: 'usable'; config: Record<string, unknown>; renamed: string[] }
  | { kind: 'unusable'; why: string };

type Item = { type?: unknown; componentType?: unknown; id?: unknown; content?: unknown; activeItemIndex?: unknown };

/** Every `componentType` a layout names, in its root and in any open popout. */
export function componentTypesIn(config: unknown): string[] {
  const found: string[] = [];
  const walk = (item: unknown): void => {
    if (!item || typeof item !== 'object') return;
    const { componentType, content } = item as Item;
    if (typeof componentType === 'string') found.push(componentType);
    if (Array.isArray(content)) content.forEach(walk);
  };
  const { root, openPopouts } = (config ?? {}) as { root?: unknown; openPopouts?: unknown };
  walk(root);
  if (Array.isArray(openPopouts)) {
    for (const popout of openPopouts) walk((popout as { root?: unknown } | null)?.root);
  }
  return found;
}

/**
 * Rename the windows in `renamed`. Where several land on one id, the first in
 * the layout stays and the rest go, and a stack, row or column they leave
 * empty goes too. A stack's active tab stays on the window it showed: the one
 * it merged into when that is in the same stack, else the one before it. Returns the old ids found. Mutates `config`, which the caller
 * has just parsed.
 */
export function renamePanels(config: Record<string, unknown>, renamed: Readonly<Record<string, string>>): string[] {
  const found = new Set<string>();
  const targets = new Set(Object.values(renamed));
  const seen = new Set<string>();

  /** The item as it stays, or null when it goes. */
  const visit = (item: unknown): unknown => {
    if (!item || typeof item !== 'object') return item;
    const it = item as Item;
    if (typeof it.componentType === 'string') {
      const was = it.componentType;
      const now = renamed[was];
      if (now !== undefined) {
        found.add(was);
        it.componentType = now;
        if (it.id === was) it.id = now;
      }
      const type = it.componentType as string;
      if (targets.has(type) && seen.has(type)) return null;
      seen.add(type);
      return it;
    }
    if (!Array.isArray(it.content)) return it;
    const active = typeof it.activeItemIndex === 'number' ? it.activeItemIndex : undefined;
    const kept: unknown[] = [];
    let keptActive = 0;
    it.content.forEach((child, index) => {
      const stays = visit(child);
      if (stays === null) {
        // The active tab merged into one already kept here: that one shows.
        const same = kept.findIndex((k) => (k as Item).componentType === (child as Item).componentType);
        if (index === active && same >= 0) keptActive = same;
        return;
      }
      if (active !== undefined && index <= active) keptActive = kept.length;
      kept.push(stays);
    });
    const emptied = kept.length === 0 && it.content.length > 0;
    it.content = kept;
    if (active !== undefined) it.activeItemIndex = keptActive;
    return emptied ? null : it;
  };

  config.root = visit(config.root) ?? undefined;
  const popouts = config.openPopouts;
  if (Array.isArray(popouts)) {
    for (const popout of popouts) {
      if (popout && typeof popout === 'object') {
        const p = popout as { root?: unknown };
        p.root = visit(p.root) ?? undefined;
      }
    }
  }
  return [...found];
}

/**
 * Read the saved text: nothing saved, a layout to load (with the old ids it
 * renamed), or a reason not to load it. `registered` is every component type
 * the shell registers.
 */
export function readSavedLayout(
  raw: string | null,
  registered: Iterable<string>,
  renamed: Readonly<Record<string, string>> = RENAMED_PANELS,
): SavedLayout {
  if (raw === null || raw === '') return { kind: 'none' };
  let config: unknown;
  try {
    config = JSON.parse(raw);
  } catch {
    return { kind: 'unusable', why: 'it is not JSON' };
  }
  if (!config || typeof config !== 'object' || Array.isArray(config)) {
    return { kind: 'unusable', why: 'it is not a layout' };
  }
  const layout = config as Record<string, unknown>;
  const found = renamePanels(layout, renamed);
  const known = new Set(registered);
  const unknown = [...new Set(componentTypesIn(layout).filter((t) => !known.has(t)))];
  if (unknown.length) {
    return { kind: 'unusable', why: `it names ${unknown.map((t) => `'${t}'`).join(', ')}, which this version does not have` };
  }
  return { kind: 'usable', config: layout, renamed: found };
}
