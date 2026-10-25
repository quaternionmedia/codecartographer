/**
 * Whether a saved layout can be loaded.
 *
 * The reader's arrangement is kept in localStorage under
 * `cc:gl-layout:default`. Golden Layout 2.6 throws a `BindError` on a component
 * type nobody registered, and the shell loads the layout while it boots: a
 * saved layout naming a window this version lacks would leave the page with
 * no windows. This reads the saved text before Golden Layout does and says
 * whether to load it.
 *
 * No Golden Layout import: the layout is read as plain JSON, so this compiles
 * under `tsconfig.pure.json` and is asserted under `node --test`.
 */

export type SavedLayout =
  | { kind: 'none' }
  | { kind: 'usable'; config: Record<string, unknown> }
  | { kind: 'unusable'; why: string };

/**
 * The root Golden Layout 2.6 loads from a layout or a popout: `root`, or when
 * that is absent the legacy `content[0]` (`LayoutConfig.resolve` and
 * `PopoutLayoutConfig.resolve` both read it so). `content` beside a `root` is
 * not read.
 */
function rootOf(config: { root?: unknown; content?: unknown }): unknown {
  if (config.root !== undefined) return config.root;
  return Array.isArray(config.content) && config.content.length > 0 ? config.content[0] : undefined;
}

/**
 * Every `componentType` a layout names, in its root and in any open popout,
 * a popout's own popouts included, wherever Golden Layout reads a root.
 */
export function componentTypesIn(config: unknown): string[] {
  const found: string[] = [];
  const walk = (item: unknown): void => {
    if (!item || typeof item !== 'object') return;
    const { componentType, content } = item as { componentType?: unknown; content?: unknown };
    if (typeof componentType === 'string') found.push(componentType);
    if (Array.isArray(content)) content.forEach(walk);
  };
  const layout = (config: unknown): void => {
    if (!config || typeof config !== 'object') return;
    const { openPopouts } = config as { openPopouts?: unknown };
    walk(rootOf(config as { root?: unknown; content?: unknown }));
    if (Array.isArray(openPopouts)) openPopouts.forEach(layout);
  };
  layout(config);
  return found;
}

/**
 * Read the saved text: nothing saved, a layout to load, or a reason not to
 * load it. `registered` is every component type the shell registers.
 */
export function readSavedLayout(raw: string | null, registered: Iterable<string>): SavedLayout {
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
  const known = new Set(registered);
  const unknown = [...new Set(componentTypesIn(config).filter((t) => !known.has(t)))];
  if (unknown.length) {
    return { kind: 'unusable', why: `it names ${unknown.map((t) => `'${t}'`).join(', ')}, which this version does not have` };
  }
  return { kind: 'usable', config: config as Record<string, unknown> };
}
