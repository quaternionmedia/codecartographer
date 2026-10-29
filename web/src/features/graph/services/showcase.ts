/**
 * The Showcase: a code graph drawn to show what a repository holds rather than
 * only how it is filed.
 *
 * Its directories and files are laid out as the Map lays them out, but every
 * node is a dot -- a directory's and a file's a little wider -- and below the
 * files every function, class, variable and call is one, packed tight round
 * what holds it (`show_layout.showcase` on the server). So a file is a cluster
 * as large as what it holds, coloured by what each dot is, in an outline a few
 * dots past it. Over the dots run the links the parse found between them
 * (`python_links.py`): what a function calls, the names it uses, and how
 * values flow from one variable to another; and, off at first, what a file
 * imports. The lines that only say what holds what are not drawn: the
 * clusters say it.
 *
 * PURE ON PURPOSE: the settings, their defaults and the layout's name with its
 * settings, read by the panel, the renderer and the requests alike.
 */

/** A link between two dots, by the parse's edge kind (`linkOf`). */
export type ShowcaseLink = 'calls' | 'uses' | 'flows' | 'imports';

export interface ShowcaseOptions {
  /** A dot's radius, in the canvas's units. Laid out by the server. */
  dot: number;
  /** The gap between two dots. Laid out by the server. */
  gap: number;
  /** Each symbol's members clustered round it, or a file's all in one disc. Laid out by the server. */
  nest: boolean;
  /** Which links are drawn. Drawn in place. */
  links: Record<ShowcaseLink, boolean>;
  /** How strongly the links are drawn, 0 to 1. Drawn in place. */
  linkOpacity: number;
  /** Whether a dot carries its name. Drawn in place. */
  names: boolean;
}

export const SHOWCASE_DEFAULTS: ShowcaseOptions = {
  dot: 2,
  gap: 0.5,
  nest: true,
  // A file's imports run the width of the map, to modules drawn beside it:
  // drawn, they cross every cluster on the way.
  links: { calls: true, uses: true, flows: true, imports: false },
  linkOpacity: 0.35,
  names: false,
};

export const SHOWCASE_LAYOUT = 'showcase_layout';

/** Each link's colour: none a pink or a red, which the canvas keeps for what is to be noticed. */
export const LINK_COLOURS: Record<ShowcaseLink, string> = {
  calls: '#f2aa4c',
  uses: '#74a8f6',
  flows: '#43c6bf',
  imports: '#9aa3b5',
};

export const LINK_KINDS: readonly ShowcaseLink[] = ['calls', 'uses', 'flows', 'imports'];

/**
 * A member's colour on a Showcase, by its kind. The canvas draws a member it
 * is given no colour for -- a variable, a constant, an argument -- grey, as
 * part of what holds it; on a Showcase the members are most of the dots, and
 * grey left three of every four of them saying nothing. None is a pink or a
 * red.
 */
export const MEMBER_COLOURS: Readonly<Record<string, string>> = {
  name: '#6f9cff',
  constant: '#b39ddb',
  argument: '#f7a072',
  symbol: '#8ecae6',
  string: '#e8d48b',
};

/** A member's colour on a Showcase, or none for a kind the canvas colours itself. */
export function memberColour(kind: unknown): string | undefined {
  return typeof kind === 'string' && Object.prototype.hasOwnProperty.call(MEMBER_COLOURS, kind)
    ? MEMBER_COLOURS[kind] : undefined;
}

/** The edges that say only what holds what: not drawn, as the clusters say it. */
export const HOLDING_KINDS: ReadonlySet<string> = new Set(['contains', 'field_of']);

/**
 * A dot's radius by its depth, in a member's: a directory's twice as wide, a
 * file's half again. The server lays them out at these sizes
 * (`show_layout.SHOWCASE_SCALE`, which a test holds equal).
 */
export const DOT_SCALE: Readonly<Record<number, number>> = { 0: 2, 1: 1.5 };

/**
 * How far an outline is drawn past what it encloses, in dots: a directory's
 * this, and a file's half, as `computeGroupBounds` halves it
 * (`show_layout.SHOWCASE_PAD`).
 */
export const SHOWCASE_PAD = 4;

/** The link an edge is drawn as, or none for one that only says what holds what. */
export function linkOf(kind: string): ShowcaseLink | null {
  if (HOLDING_KINDS.has(kind)) return null;
  // Whatever else joins two nodes -- an import, a dependency, a declaration --
  // joins two files or modules, and is drawn as one.
  return kind === 'calls' || kind === 'uses' || kind === 'flows' ? kind : 'imports';
}

/** A node's radius on a Showcase, by its depth. */
export function dotRadius(depth: unknown, dot: number): number {
  return dot * (typeof depth === 'number' ? DOT_SCALE[depth] ?? 1 : 1);
}

/** The outline padding a Showcase is drawn with: a directory's, of which a file's is half. */
export function showcasePadding(options: ShowcaseOptions): number {
  return SHOWCASE_PAD * options.dot;
}

/** Some of the Showcase's settings: as the styling holds them, or a change to them, a link at a time. */
export type ShowcaseSettings = Partial<Omit<ShowcaseOptions, 'links'>> & { links?: Partial<Record<ShowcaseLink, boolean>> };

/** The Showcase's settings as the styling holds them, every one filled in. */
export function showcaseOf(styling: { showcase?: ShowcaseSettings } | undefined): ShowcaseOptions {
  return withShowcase(SHOWCASE_DEFAULTS, styling?.showcase ?? {});
}

/**
 * The settings held with a change made to them: what it sets, and every
 * other setting and link as it was. The panel sends what changed alone --
 * built from the settings it last drew, a change to one link set every other
 * back to how they were then.
 */
export function withShowcase(held: ShowcaseSettings | undefined, change: ShowcaseSettings): ShowcaseOptions {
  const base = { ...SHOWCASE_DEFAULTS, ...held, links: { ...SHOWCASE_DEFAULTS.links, ...(held?.links ?? {}) } };
  return { ...base, ...change, links: { ...base.links, ...(change.links ?? {}) } };
}

/** The layout's name with the settings the server lays it out by (`position_service.layout_spec`). */
export function showcaseSpec(options: ShowcaseOptions): string {
  return `Showcase(dot=${options.dot},gap=${options.gap},nest=${options.nest})`;
}

/** Whether a change to the settings needs the server to lay the graph out again. */
export function laysOutAgain(before: ShowcaseOptions, after: ShowcaseOptions): boolean {
  return before.dot !== after.dot || before.gap !== after.gap || before.nest !== after.nest;
}
