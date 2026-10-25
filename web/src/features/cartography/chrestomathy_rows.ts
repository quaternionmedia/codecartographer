/**
 * What the Chrestomathy panel says about one construct, decided without a DOM.
 *
 * A chrestomathy sets one thing beside itself in every language so a reader
 * learns by the difference. The panel's table is that comparison, and what it
 * must get right is not markup but meaning: which tokens a language spells the
 * construct with, which abstraction layer each token sits on, and -- the row
 * most easily lost -- that a language has *no* spelling for it. A row dropped
 * because it was empty would teach the opposite of the truth, so a silent
 * language is a row that says so.
 *
 * Compiled by `tsconfig.pure.json` and asserted under `node --test`. The
 * document's shape is restated structurally here rather than imported, because
 * the service that fetches it pulls in browser types this build refuses.
 */

export interface TokenContextLike {
  layer_ordinal: number;
  layer_name: string;
  group: string;
}

export interface ChrestomathyLanguageLike {
  language: string;
  display_name: string;
  has_lexicon: boolean;
  tokens: Array<{ token: string; contexts: TokenContextLike[] }>;
  kinds: string[];
  carried_by: string[];
  note: string;
}

export interface ChrestomathyRow {
  language: string;
  label: string;
  /** The tokens, in the vocabulary's order, or an em dash when there are none. */
  spelling: string;
  /** Each distinct layer the tokens sit on, machine-facing first. */
  layers: string[];
  /** The parser kinds that realise the construct, or the source marks that carry a facet. */
  parsedAs: string;
  note: string;
  /** Nothing spells it, nothing parses as it: the row is the absence. */
  silent: boolean;
}

/** `L2 Aggregate & user-defined types · aggregate`, each distinct once, by ordinal. */
export function layerLabels(contexts: readonly TokenContextLike[]): string[] {
  const seen = new Map<string, number>();
  for (const c of contexts) {
    seen.set(`L${c.layer_ordinal} ${c.layer_name} · ${c.group}`, c.layer_ordinal);
  }
  return [...seen.entries()].sort((a, b) => a[1] - b[1]).map(([label]) => label);
}

export interface CensusRowLike {
  id: string;
  name: string;
  facet: boolean;
  count: number;
  languages: Array<{ language: string; display_name: string; count: number }>;
  ids: string[];
}

export interface CensusLike {
  constructs: CensusRowLike[];
  facets: CensusRowLike[];
  walk: Array<{ kind: string; count: number }>;
  not_constructs: Array<{ language: string; display_name: string; kind: string; count: number; reason: string }>;
  unplaced: Array<{ language: string; display_name: string; kind: string; count: number }>;
  outside: Array<{ language: string; count: number }>;
  unknown: Array<{ construct: string; count: number }>;
  unlabelled: number;
}

export interface CensusLine {
  id: string;
  name: string;
  count: number;
  /** `Rust 12 · C 3`, most first. */
  spread: string;
  /** Written in more than one language on this canvas: the comparison is right here. */
  shared: boolean;
  facet: boolean;
  ids: string[];
}

/** The constructs on the canvas, then what they can also be, as the panel lists them. */
export function censusLines(census: CensusLike): CensusLine[] {
  return [...census.constructs, ...census.facets].map((row) => ({
    id: row.id,
    name: row.name,
    count: row.count,
    spread: row.languages.map((l) => `${l.display_name || l.language} ${l.count}`).join(' · '),
    shared: row.languages.length > 1,
    facet: row.facet,
    ids: row.ids,
  }));
}

/**
 * What *show* did, as the panel says it. `found` is how many of the row's
 * nodes were on the canvas to frame; none is said as none, and the selection
 * was left as it was rather than emptied.
 */
export function shownSentence(found: number, line: Pick<CensusLine, 'name' | 'count'>): string {
  return found
    ? `${found} ${line.name} node(s) framed and selected`
    : `none of the ${line.count} ${line.name} node(s) is on the canvas now; the selection is as it was`;
}

/**
 * What the census could not place, each as a sentence saying what it is. A
 * graph read as only its placed nodes would claim the vocabulary covers what
 * it does not, so the rest is said, never dropped -- and said truly: a file
 * the walk drew is a file, not a kind the vocabulary failed to place, and a
 * kind the vocabulary lists as no construct says why.
 */
export function censusGaps(census: CensusLike): string[] {
  const gaps = census.unplaced.map((u) =>
    `${u.count} ${u.display_name || u.language} ${u.kind} node(s): a kind the vocabulary does not place`);
  for (const n of census.not_constructs) {
    gaps.push(`${n.count} ${n.display_name || n.language} ${n.kind} node(s): not a construct. ${n.reason}`);
  }
  for (const o of census.outside) {
    gaps.push(`${o.count} ${o.language} node(s): a language the vocabulary does not list`);
  }
  for (const u of census.unknown) {
    gaps.push(`${u.count} node(s) stamped ${u.construct}: a construct constructs.yaml does not hold`);
  }
  for (const w of census.walk) {
    const what = w.kind === 'directory' ? 'folder' : w.kind;
    gaps.push(`${w.count} ${what} node(s): the parse's walk of the tree, a ${what} and no construct`);
  }
  if (census.unlabelled) {
    gaps.push(`${census.unlabelled} node(s) with no language: a graph that is not code`);
  }
  return gaps;
}

export function chrestomathyRows(languages: readonly ChrestomathyLanguageLike[]): ChrestomathyRow[] {
  return languages.map((row) => {
    const tokens = row.tokens.map((t) => t.token);
    const layers = layerLabels(row.tokens.flatMap((t) => t.contexts));
    const parsed = [...row.kinds.map((k) => `${k} (parsed)`), ...row.carried_by];
    return {
      language: row.language,
      label: row.display_name || row.language,
      spelling: tokens.length ? tokens.join(', ') : '—',
      layers,
      parsedAs: parsed.join(', '),
      note: row.note,
      silent: tokens.length === 0 && row.kinds.length === 0 && row.carried_by.length === 0,
    };
  });
}
