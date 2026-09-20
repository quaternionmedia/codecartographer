/**
 * The one way this application says "nothing was drawn".
 *
 * A seam that is down, a file the pin predates, a schema this window does not
 * know — each is a sentence with a remedy and the address that was tried, and
 * each panel used to write its own markup for it. One component, so a reader
 * learns the shape once and every panel offers the same way back.
 *
 * THE CLASS NAMES CARRY A PREFIX. The topology panel's selectors
 * (`.topology__problem`, `.topology__retry`) are what its browser tests find,
 * and its stylesheet is written against them. Rather than break those, every
 * element here carries both a shared class (`seam-problem…`) and the caller's
 * prefixed one, so the stylesheet that already exists applies and a new panel
 * gets the same look by naming its own prefix.
 */

import m from 'mithril';

import type { SeamProblem } from './seam_client';
import './estate.css';

export interface ProblemViewAttrs {
  problem: SeamProblem;
  /** The panel's own class prefix, e.g. `topology`. */
  prefix: string;
  /** What to do when the reader asks again. Omit to offer no retry. */
  onRetry?: () => void;
  /** The sentence under the address. Defaults to the one every seam shares. */
  note?: string;
}

const NOTE = 'Nothing was drawn. An empty graph would look like an answer.';

export const ProblemView: m.Component<ProblemViewAttrs> = {
  view: ({ attrs }) => {
    const p = attrs.prefix;
    const problem = attrs.problem;
    return m(`div.seam-problem.${p}__problem`, { 'data-kind': problem.kind }, [
      m(`p.seam-problem__what.${p}__problem-what`, problem.problem),
      problem.remedy
        ? m(`p.seam-problem__remedy.${p}__problem-remedy`, problem.remedy)
        : null,
      m(`p.seam-problem__where.${p}__problem-where`, ['tried ', m('code', problem.where)]),
      m(`p.seam-problem__note.${p}__problem-note`, attrs.note ?? NOTE),
      // A seam is usually brought up *after* somebody opens a panel and finds
      // it down. Without this they would have to close and reopen the panel,
      // which is not a thing anybody guesses.
      attrs.onRetry
        ? m(`button.seam-problem__retry.${p}__retry`, { onclick: attrs.onRetry }, 'try again')
        : null,
    ]);
  },
};
