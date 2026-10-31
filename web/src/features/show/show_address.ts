/**
 * The address of a showgraph, in a page's query string.
 *
 *   ?show  or  ?show=index             every family at once: the default
 *   ?show=index&view=code              every family with each project's code: the whole corpus
 *   ?show=index&view=full              the whole corpus, every node drawn and no name
 *   ?show=index&view=imports           every family with what its projects import in common
 *   ?show=family:performing            one family
 *   ?show=family:performing&view=code  the same family with each of its projects' code
 *   ?show=family:performing&view=imports  the same family with what its projects import in common
 *   ?show=project:carlos               one project's estate view
 *   ?show=project:carlos&view=code     the same project's code map
 *
 * **THE WINDOW HAD NO ADDRESS.** Nothing could link to a graph: the page ignored
 * its query string, and every drawing started from a click in a panel. A
 * family page in the corpus's docs site that wants to open its own showgraph
 * needs a URL that means "this family", and this is that URL's grammar.
 *
 * PURE ON PURPOSE. Parsing and formatting touch no DOM and no state, so
 * `web/tests/pure/show-address.test.mjs` exercises both under node.
 *
 * A name is a repository or family name as the corpus writes it. The grammar
 * refuses anything else rather than passing it to a route, the same rule the
 * server's clone lookup keeps: one path segment, nothing hidden.
 */

export type ShowKind = 'index' | 'family' | 'project';
export type ShowView = 'estate' | 'code' | 'system';
/** What an address may name: a project's view, the index's `full`, the whole corpus with no
 *  names, or an index's or a family's `imports`, what its projects import in common. */
export type AddressView = ShowView | 'full' | 'imports';

export interface ShowAddress {
  kind: ShowKind;
  /** Empty for the index. */
  name: string;
  /** A project has three views, a family three (its code view is the family
   *  with each of its projects' code, its imports view the family with what
   *  they import in common) and the index four (its code view is the whole
   *  corpus, its full view the same with no names, and an imports view). */
  view: AddressView;
}

export const VIEWS: readonly ShowView[] = ['estate', 'code', 'system'];

const NAME = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

/**
 * The query string's parameters. Written out rather than `URLSearchParams`,
 * which the DOM-free build this is tested in does not have.
 */
export function parameters(search: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const pair of (search.startsWith('?') ? search.slice(1) : search).split('&')) {
    if (!pair) continue;
    const at = pair.indexOf('=');
    const key = at < 0 ? pair : pair.slice(0, at);
    const value = at < 0 ? '' : pair.slice(at + 1);
    try {
      out.set(decodeURIComponent(key), decodeURIComponent(value.replace(/\+/g, ' ')));
    } catch {
      // A malformed escape names nothing.
    }
  }
  return out;
}

/** The address a query string names, or `null` when it names none or a bad one. */
export function parseShow(search: string): ShowAddress | null {
  const params = parameters(search);
  if (!params.has('show')) return null;
  const raw = params.get('show');
  // A showgraph named by nothing more is every family at once, with
  // `view=code` every family with each project's code in it, and with
  // `view=full` that again, every node drawn and no name; with
  // `view=imports` every family with what its projects import in common.
  if (!raw || raw === 'index') {
    const asked = params.get('view');
    return {
      kind: 'index', name: '',
      view: asked === 'code' || asked === 'full' || asked === 'imports' ? asked : 'estate',
    };
  }

  const colon = raw.indexOf(':');
  if (colon < 0) return null;
  const kind = raw.slice(0, colon);
  const name = raw.slice(colon + 1);
  if ((kind !== 'family' && kind !== 'project') || !NAME.test(name)) return null;

  const asked = params.get('view');
  const view: AddressView = kind === 'project' && asked && (VIEWS as readonly string[]).includes(asked)
    ? asked as ShowView
    : kind === 'family' && (asked === 'code' || asked === 'imports') ? asked : 'estate';
  return { kind, name, view };
}

/** The query string for an address, with the view left out when it is `estate`. */
export function formatShow(address: ShowAddress): string {
  if (address.kind === 'index') return address.view === 'estate' ? '?show=index' : `?show=index&view=${address.view}`;
  const view = address.view !== 'estate' ? `&view=${address.view}` : '';
  return `?show=${address.kind}:${encodeURIComponent(address.name)}${view}`;
}

/** The address a node's `show` attribute names (`family:core`), or `null`. */
export function fromNode(show: unknown): ShowAddress | null {
  return typeof show === 'string' ? parseShow(`show=${show}`) : null;
}

/** Whether two addresses name the same drawing. */
export function sameShow(a: ShowAddress | null | undefined, b: ShowAddress | null | undefined): boolean {
  return !!a && !!b && a.kind === b.kind && a.name === b.name && a.view === b.view;
}

/** What a breadcrumb needs to know of the corpus: which family sits within which, and who claims a project. */
export interface TrailSubjects {
  families: readonly { name: string; within: string | null }[];
  projects: readonly { name: string; families: readonly string[] }[];
}

/**
 * The way from every family down to `address`, one level per step.
 *
 * Each level is the addresses a reader can step back to at that depth --
 * usually one. A project two families claim ends its families' level with
 * both, so the trail asserts no single home for it any more than the index
 * does. The last level is `address` itself.
 */
export function trail(address: ShowAddress, subjects: TrailSubjects | null): ShowAddress[][] {
  const index: ShowAddress = { kind: 'index', name: '', view: 'estate' };
  if (address.kind === 'index') return address.view === 'estate' ? [[index]] : [[index], [address]];
  const within = new Map((subjects?.families ?? []).map((f) => [f.name, f.within]));
  const family = (name: string): ShowAddress => ({ kind: 'family', name, view: 'estate' });

  /** `name`'s enclosing families, outermost first, `name` last. */
  const chain = (name: string): string[] => {
    const out = [name];
    const seen = new Set(out);
    for (let up = within.get(name); up && within.has(up) && !seen.has(up); up = within.get(up)) {
      out.unshift(up);
      seen.add(up);
    }
    return out;
  };

  if (address.kind === 'family') {
    // A family's code view ends the trail as itself.
    const levels = chain(address.name).map((name) => [family(name)]);
    levels[levels.length - 1] = [address];
    return [[index], ...levels];
  }
  const claims = subjects?.projects.find((p) => p.name === address.name)?.families ?? [];
  if (!claims.length) return [[index], [address]];
  const levels = chain(claims[0]).map((name) => [family(name)]);
  levels[levels.length - 1].push(...claims.slice(1).map(family));
  return [[index], ...levels, [address]];
}

type Named = { label: string; title: string };

/**
 * How each subject's views are named, and what drawing one does, in the order
 * they are offered: the Show panel's buttons and the page's views say the same.
 */
export const VIEW_NAMES: {
  readonly index: Readonly<Record<'estate' | 'code' | 'full' | 'imports', Named>>;
  readonly family: Readonly<Record<'estate' | 'code' | 'imports', Named>>;
  readonly project: Readonly<Record<ShowView, Named>>;
} = {
  index: {
    estate: { label: 'every family', title: 'draw every family' },
    code: { label: "with each project's code", title: "draw every family with each project's code in it" },
    full: { label: 'every node, no names', title: 'draw the whole corpus, every node, with no names' },
    imports: { label: 'shared imports', title: 'draw every family with what its projects import in common' },
  },
  family: {
    estate: { label: 'the family', title: 'draw the family' },
    code: { label: "with each project's code", title: "draw the family with each of its projects' code in it" },
    imports: { label: 'shared imports', title: 'draw the family with what its projects import in common' },
  },
  project: {
    estate: { label: 'estate', title: 'draw the estate' },
    code: { label: 'code map', title: 'draw the code map' },
    system: { label: 'system', title: 'draw the system' },
  },
};

/** How a step of the trail is named. */
export function crumbLabel(address: ShowAddress): string {
  if (address.kind === 'index') {
    return {
      estate: 'every family', code: 'the whole corpus', full: 'every node, no names', imports: 'shared imports',
    }[address.view as string] ?? 'every family';
  }
  return address.name;
}
