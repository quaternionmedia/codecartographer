/**
 * The four kinds of window, and which a panel is.
 *
 * A panel belongs to one group by whose data it shows: the canvas and its
 * settings are this window's own; code is read from a repository or a disk;
 * the harness panels read the harness; the organisation panels read the
 * corpus and dossier. The "+" menu lists panels under these headings, each
 * with the sentence its definition gives for what it answers, so two panels
 * with near names are told apart by source before either is opened.
 *
 * Pure: no DOM, so `web/tests/pure/panel-groups.test.mjs` runs it under node.
 */

export type PanelGroup = 'canvas' | 'code' | 'harness' | 'organisation';

export interface GroupHeading {
  readonly group: PanelGroup;
  readonly title: string;
  /** Whose data the group's panels show. */
  readonly reads: string;
}

/** The headings, in the order the menu draws them. */
export const GROUPS: readonly GroupHeading[] = [
  { group: 'canvas', title: 'Canvas', reads: 'this window' },
  { group: 'code', title: 'Code', reads: 'a repository or this disk' },
  { group: 'harness', title: 'Harness', reads: 'the harness, live' },
  { group: 'organisation', title: 'Organisation', reads: 'the corpus and dossier' },
];

export interface Grouped<T> {
  readonly heading: GroupHeading;
  readonly panels: readonly T[];
}

/**
 * Panels under their headings, in heading order, each group keeping the order
 * it was given. A heading with no panel is left out. A panel whose group no
 * heading names is kept, under a last heading that says so, so a definition
 * with a mistyped group is still reachable.
 */
export function grouped<T extends { readonly group: string }>(panels: readonly T[]): Grouped<T>[] {
  const found: Grouped<T>[] = GROUPS
    .map((heading) => ({ heading, panels: panels.filter((panel) => panel.group === heading.group) }))
    .filter((entry) => entry.panels.length > 0);
  const known = new Set<string>(GROUPS.map((heading) => heading.group));
  const stray = panels.filter((panel) => !known.has(panel.group));
  if (stray.length > 0) {
    found.push({
      heading: { group: 'canvas', title: 'Ungrouped', reads: 'a group no heading names' },
      panels: stray,
    });
  }
  return found;
}
