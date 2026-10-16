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
