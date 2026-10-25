/**
 * When the provenance strip is drawn, and when it is already saying the
 * caveat a panel would say. Decided here, with no Mithril, so `node --test`
 * reads it (`provenance.ts` draws it).
 */

/** The two fields of a graph's metadata these decide on. */
export interface ShownMetadata {
  kind?: string;
  caveat?: string;
}

/** Whether the strip is drawn for this panel: there is metadata, and it is
 *  this seam's. */
export function stripShown<M extends ShownMetadata>(md: M | null | undefined, kind?: string): md is M {
  return !!md && !(kind && md.kind !== undefined && md.kind !== kind);
}

/** Whether the strip is already saying *caveat*, the panel's reading's own, so
 *  the panel says it once. **THE SAME SENTENCE, NOT ANY CAVEAT**: reading
 *  another workspace or construct does not redraw, so the strip can be saying
 *  the drawn graph's while the panel lists another reading, whose caveat is
 *  then the panel's to say. Before a draw the strip is empty. */
export function caveatShown(md: ShownMetadata | null | undefined, kind: string | undefined,
                            caveat: string | null | undefined): boolean {
  return stripShown(md, kind) && !!md.caveat && md.caveat === caveat;
}
