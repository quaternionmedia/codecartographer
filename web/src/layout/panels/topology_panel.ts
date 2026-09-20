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
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import './topology_panel.css';

export function createTopologyPanel(ctx: LayoutContext): m.Component {
  /**
   * Whether this panel has asked the harness what it offers.
   *
   * **PER PANEL, AND CLEARED BY A FAILURE.** The first version was a
   * module-level flag set before the request: closing and reopening the panel
   * never asked again, and — worse — a harness that was down when the panel
   * first opened could never be retried, because the flag said the question
   * had been asked. It had; the answer was just "no".
   */
  let asked = false;

  const ask = () => {
    asked = true;
    void ctx.actions.plot
      .loadTopologyChoices()
      .catch(() => {
        asked = false;
      });
  };

  return {
    oninit: () => {
      if (!asked) ask();
    },

    view: () => {
      const state = ctx.appState.state;
      const choices = state.topologyChoices;
      const problem = state.topologyProblem;
      const metadata = state.graphData?.metadata as EstateMetadata | undefined;

      const draw = (over: Record<string, string>) => {
        ctx.appState.update({
          topologyKind: over.kind ?? state.topologyKind,
          topologySubject: over.subject ?? '',
        });
        const request = { kind: over.kind ?? state.topologyKind, subject: over.subject };
        // Through `plotWith`, so a layout chosen in Graph Settings re-draws
        // this topology rather than being kept for a draw nobody repeats.
        void ctx
          .plotWith(() => ctx.actions.plot.loadTopology(request))
          // The drawing goes where the reader can see it: this panel usually
          // sits in the same stack as the canvas, in front of it.
          .then(() => ctx.focusDockPanel('graph'))
          .catch(() => undefined);
      };

      return m('div.gl-panel.gl-panel--controls.gl-panel--topology', [
        // --- what is wrong, when something is -----------------------------
        // The one problem view every estate panel shares, wearing this
        // panel's prefix so its stylesheet and its browser tests still apply.
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'topology',
              onRetry: () => {
                ctx.appState.update({ topologyProblem: null });
                ask();
              },
            })
          : null,

        // --- how much of what is drawn was measured -----------------------
        // Only when the canvas holds a topology: a capability graph's caveat
        // must not appear here because it happens to be what is drawn.
        m(Provenance, { metadata, prefix: 'topology', kind: 'topology' }),

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
