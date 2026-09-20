/**
 * The one translation between the menu's layout names and the backend's.
 *
 * The menu is keyed by the registry's own names (`spring_layout`,
 * `kamada_kawai_layout`, `compound_layout`); the backend's `PlotOptions` and its
 * metadata speak display names (`Spring`, `Kamada_Kawai`, `Compound`). Two
 * hand-written tables did this translation — one in `state/actions.ts`, one in
 * `layout/layout_context.ts` — and both fell back to `'Spring'` for any name
 * they did not list, which included `compound_layout`. Choosing Compound for an
 * estate graph drew Spring, silently.
 *
 * ONE RULE, NOT A TABLE: strip the `_layout` suffix, capitalise each segment,
 * join with `_`. Every registered name goes through it and none is special, so
 * a layout added to the registry needs no edit here. There is no fallback: an
 * unknown name goes to the server as written, and the server answers with a
 * sentence naming what is registered — which is its job, not this file's.
 *
 * The server normalises spellings itself (`position_service.layout_key`), so
 * the registry name would also be accepted verbatim; the display form is kept
 * so `metadata.layout` reads the way the settings panel labels it.
 */

export function backendLayoutName(registryName: string): string {
  const trimmed = (registryName ?? '').trim();
  if (!trimmed) return '';
  const stem = trimmed.endsWith('_layout') ? trimmed.slice(0, -'_layout'.length) : trimmed;
  return stem
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join('_');
}
