/**
 * Topology Panel
 *
 * Choose a flow from the harness and draw it. The drawing itself happens in the
 * Graph panel, because a topology *is* graph data — this panel decides what to
 * plot, not how it looks.
 *
 * WHY THIS IS CONTROLS AND NOT A CANVAS. The first version of this view was a
 * server-rendered page with its own SVG, its own CSS and its own legend, living
 * beside this application rather than in it. Everything it hand-drew already
 * existed here: the renderer, the styling, zoom and drag and tooltips, the
 * radial menu. So the panel that survives is the half that was actually new —
 * picking a topology — and the drawing goes where drawing goes.
 *
 * THE CAVEAT IS PART OF THE PANEL, NOT DECORATION. A topology's edges may carry
 * no measurement, and a picture cannot say "nobody looked" on its own. The
 * sentence the harness sends travels in the graph metadata and is shown here,
 * above the controls, so it is read before the shape is believed.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import './topology_panel.css';

/** Asked once per panel mount, so opening the panel fills its own picker. */
let asked = false;

export function createTopologyPanel(ctx: LayoutContext): m.Component {
  return {
    oninit: () => {
      if (asked) return;
      asked = true;
      void ctx.actions.plot.loadTopologyChoices();
    },

    view: () => {
      const state = ctx.appState.state;
      const choices = state.topologyChoices;
      const problem = state.topologyProblem;
      const metadata = state.graphData?.metadata as
        | { caveat?: string; unmeasured?: number; source?: string; surveyed?: number }
        | undefined;

      const draw = (over: Record<string, string>) => {
        ctx.appState.update({
          topologyKind: over.kind ?? state.topologyKind,
          topologySubject: over.subject ?? '',
        });
        void ctx.actions.plot.loadTopology({
          kind: over.kind ?? state.topologyKind,
          subject: over.subject,
        });
      };

      return m('div.gl-panel.gl-panel--controls.gl-panel--topology', [
        // --- what is wrong, when something is -----------------------------
        problem
          ? m('div.topology__problem', [
              m('p.topology__problem-what', problem.problem),
              problem.remedy
                ? m('p.topology__problem-remedy', problem.remedy)
                : null,
              m('p.topology__problem-where', ['tried ', m('code', problem.where)]),
              m('p.topology__problem-note',
                'Nothing was drawn. An empty graph would look like an answer.'),
            ])
          : null,

        // --- how much of what is drawn was measured -----------------------
        metadata?.caveat
          ? m(
              'p.topology__caveat',
              { class: metadata.unmeasured ? 'is-partial' : 'is-complete' },
              metadata.caveat,
            )
          : null,

        metadata?.source
          ? m('p.topology__provenance',
              `from the ${metadata.source}` +
                (metadata.surveyed ? `, ${metadata.surveyed} thread(s) read` : ''))
          : null,

        // --- the harness's own shapes -------------------------------------
        m('div.topology__section', [
          m('h4.topology__heading', 'Flows'),
          choices === null && !problem
            ? m('p.topology__pending', 'asking the harness…')
            : null,
          choices && choices.topologies.length === 0
            ? m('p.topology__pending', 'the harness offers no topologies')
            : null,
          choices
            ? m(
                'div.topology__chips',
                choices.topologies.map((choice) =>
                  m(
                    'button.topology__chip',
                    {
                      class:
                        choice.topology === state.topologyKind && !state.topologySubject
                          ? 'is-on'
                          : '',
                      title: `${choice.caption} — ${choice.boxes} boxes, ${choice.arrows} arrows`,
                      onclick: () => draw({ kind: choice.topology }),
                    },
                    choice.topology,
                  ),
                ),
              )
            : null,
        ]),

        // --- what the archive says about one project ----------------------
        m('div.topology__section', [
          m('h4.topology__heading', 'What the archive says about'),
          m('form.topology__subject', {
            onsubmit: (event: Event) => {
              event.preventDefault();
              const value = state.topologySubject.trim();
              if (value) draw({ subject: value });
            },
          }, [
            m('input.topology__input', {
              placeholder: 'a project name',
              value: state.topologySubject,
              oninput: (event: Event) =>
                ctx.appState.update({
                  topologySubject: (event.target as HTMLInputElement).value,
                }),
            }),
            m('button.topology__go', { type: 'submit' }, 'read'),
          ]),
          m('p.topology__hint',
            'Weighted by how much of each conversation was about it. ' +
            'A relation nobody measured is drawn dashed, never thin.'),
        ]),
      ]);
    },
  };
}
