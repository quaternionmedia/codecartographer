/**
 * Overview Panel — dossier's reading of the estate, drawn here.
 *
 * The other window produces, this one consumes: `dossier overview --json`
 * writes a seam, the server reads it, and this panel lists what it carried —
 * the masthead figures and a row count per section — and offers to draw it as
 * the one relation the seam states, that a section lists a subject.
 *
 * REDACTION IS INHERITED, NEVER REPEATED. Every name here is whatever the
 * producer published. This panel invents no name and hides none.
 *
 * A MISSING SEAM IS THE ORDINARY CASE. The overview is one window's live
 * reading, generated on demand and not committed; a checkout that has not been
 * handed one legitimately has none, and that is shown as a sentence naming the
 * producer rather than as an estate of nothing.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import '../../features/estate/estate.css';

/** A masthead figure however the producer packed it: `{label, value}` or a
 *  single-key object. The producer's shape is the producer's to change. */
function figure(entry: Record<string, unknown>): { label: string; value: string } {
  if ('label' in entry || 'value' in entry) {
    return { label: String(entry.label ?? ''), value: String(entry.value ?? '') };
  }
  const [label, value] = Object.entries(entry)[0] ?? ['', ''];
  return { label, value: String(value) };
}

export function createOverviewPanel(ctx: LayoutContext): m.Component {
  let asked = false;

  const ask = () => {
    asked = true;
    void ctx.actions.plot.loadOverviewReading().catch(() => {
      asked = false;
    });
  };

  return {
    oninit: () => {
      if (!asked) ask();
    },

    view: () => {
      const state = ctx.appState.state;
      const reading = state.overviewReading;
      const problem = state.overviewProblem;
      const metadata = state.graphData?.metadata as EstateMetadata | undefined;

      return m('div.gl-panel.gl-panel--controls.gl-panel--overview', [
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'overview',
              onRetry: () => {
                ctx.appState.update({ overviewProblem: null });
                ask();
              },
            })
          : null,

        m(Provenance, { metadata, prefix: 'overview', kind: 'overview' }),

        reading
          ? m('div.estate-view__section', [
              m('h4.estate-view__heading', reading.scope ? `Scope ${reading.scope}` : 'Masthead'),
              reading.masthead.length
                ? m('div.estate-view__masthead', reading.masthead.map((entry) => {
                    const f = figure(entry);
                    return m('div.estate-view__figure', [
                      m('span.estate-view__figure-label', f.label),
                      m('span.estate-view__figure-value', f.value),
                    ]);
                  }))
                : m('p.estate-view__hint', 'the seam carries no masthead figures'),
            ])
          : null,

        m('div.estate-view__section', [
          m('h4.estate-view__heading', 'Sections'),
          reading === null && !problem
            ? m('p.estate-view__pending', 'reading the seam…')
            : null,
          reading
            ? [
                m('div.estate__rows', reading.sections.map((section) =>
                  m('div.estate__row.is-live', [
                    m('span.estate__dot'),
                    m('span.estate__name', String(section.title ?? 'untitled')),
                    m('span.estate__actions',
                      m('span.estate-view__rung', `${(section.rows ?? []).length} row(s)`)),
                  ]))),
                m('p.estate-view__hint', reading.caveat),
                m('p.estate__where', ['from ', m('code', reading.source),
                  reading.generated_from ? `, generated from ${reading.generated_from}` : '']),
                m('button.estate-view__draw', {
                  onclick: () => void ctx.actions.plot.drawOverview().then(() => ctx.focusDockPanel('graph')),
                }, 'draw the overview'),
              ]
            : null,
        ]),
      ]);
    },
  };
}
