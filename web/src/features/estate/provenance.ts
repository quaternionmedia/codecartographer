/**
 * Where a drawn graph came from, and the sentence to read before believing it.
 *
 * Every estate view puts its caveat, its source and what it could not see into
 * the graph metadata, because the side that measured is the side that should
 * say. This strip reads those fields and renders them above a panel's controls,
 * so they are read before the shape is — a picture where most lines are dashed
 * is a different artefact from one where none are, and a reader should not have
 * to count.
 *
 * IT READS METADATA AND INVENTS NOTHING. A field the producer did not send is
 * not shown; there is no default caveat, because a reassuring sentence nobody
 * wrote is worse than none.
 */

import m from 'mithril';

import './estate.css';

/** The estate fields a graph's metadata may carry. All optional: this is what
 *  each seam's `metadata()` puts there, and each puts a different subset. */
export interface EstateMetadata {
  kind?: string;
  source?: string;
  caveat?: string;
  unmeasured?: number;
  measured?: number;
  surveyed?: number;
  generated_from?: string;
  generated_at?: string;
  written_at?: string;
  scope?: string;
  capabilities?: number;
  sections?: number;
  nodeCount?: number;
  edgeCount?: number;
  [key: string]: unknown;
}

export interface ProvenanceAttrs {
  metadata: EstateMetadata | null | undefined;
  /** The panel's class prefix, for the stylesheet that already exists. */
  prefix: string;
  /** Only show when the drawn graph is this seam's. A topology panel must not
   *  show a capabilities caveat because the canvas happens to hold one. */
  kind?: string;
}

export const Provenance: m.Component<ProvenanceAttrs> = {
  view: ({ attrs }) => {
    const md = attrs.metadata;
    if (!md) return null;
    if (attrs.kind && md.kind !== undefined && md.kind !== attrs.kind) return null;
    const p = attrs.prefix;
    const partial = typeof md.unmeasured === 'number' && md.unmeasured > 0;

    const from: string[] = [];
    if (md.source) from.push(`from ${md.source}`);
    if (md.generated_from) from.push(String(md.generated_from));
    // The producer's stamp when it gave one; the file's time otherwise, and
    // named as the file's -- a copied seam carries a new time.
    if (md.generated_at) from.push(`generated ${md.generated_at}`);
    else if (md.written_at) from.push(`file written ${md.written_at}`);
    if (md.scope) from.push(`scope ${md.scope}`);
    if (typeof md.surveyed === 'number') from.push(`${md.surveyed} thread(s) read`);

    return m(`div.seam-provenance.${p}__provenance-block`, [
      md.caveat
        ? m(`p.seam-caveat.${p}__caveat`, { class: partial ? 'is-partial' : 'is-complete' }, md.caveat)
        : null,
      from.length
        ? m(`p.seam-source.${p}__provenance`, from.join(', '))
        : null,
    ]);
  },
};
