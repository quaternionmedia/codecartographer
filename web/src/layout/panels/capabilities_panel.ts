/**
 * Capabilities Panel — what each named thing this estate can do has reached.
 *
 * Controls, not a canvas: the graph draws in the Graph panel through the same
 * path every other plot takes. This panel lists the declarations the registry
 * holds — the claim each makes and who made it — and offers to draw them.
 *
 * THE VOCABULARY IS THE CORPUS'S. The rungs come from the server's reading of
 * `governance/qm/ci/capability-registry.yaml`, not from a list here; a rung
 * that meant something different in this panel would give two readings of one
 * estate. `dossier` is the other window onto the same file.
 *
 * A PIN THAT PREDATES THE REGISTRY IS THE ORDINARY CASE, and it is shown as a
 * sentence with the propagation that would change it — never as an estate that
 * declares nothing.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import '../../features/estate/estate.css';

export function createCapabilitiesPanel(ctx: LayoutContext): m.Component {
  let asked = false;

  const ask = () => {
    asked = true;
    void ctx.actions.plot.loadCapabilitiesReading().catch(() => {
      asked = false;
    });
  };

  return {
    oninit: () => {
      if (!asked) ask();
    },

    view: () => {
      const state = ctx.appState.state;
      const reading = state.capabilitiesReading;
      const problem = state.capabilitiesProblem;
      const metadata = state.graphData?.metadata as EstateMetadata | undefined;

      return m('div.gl-panel.gl-panel--controls.gl-panel--capabilities', [
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'capabilities',
              onRetry: () => {
                ctx.appState.update({ capabilitiesProblem: null });
                ask();
              },
            })
          : null,

        // Only when the canvas holds *this* seam's graph. The topology panel
        // must not wear a capabilities caveat because a capability graph
        // happens to be drawn, and the reverse.
        m(Provenance, { metadata, prefix: 'capabilities', kind: 'capabilities' }),

        m('div.estate-view__section', [
          m('h4.estate-view__heading', 'Declarations'),
          reading === null && !problem
            ? m('p.estate-view__pending', 'reading the registry…')
            : null,
          reading
            ? [
                m('div.estate-view__rungs',
                  reading.rungs.map((rung) => m('span.estate-view__rung', rung))),
                m('div.estate__rows', reading.capabilities.map((cap) =>
                  m('div.estate__row.is-live', { 'data-capability': cap.id }, [
                    m('span.estate__dot'),
                    m('span.estate__name', cap.title || cap.id),
                    m('span.estate__actions',
                      m('span.estate-view__rung', `claims ${cap.phase}`)),
                    m('p.estate__role', [m('code', cap.id), cap.repo ? ` — ${cap.repo}` : '']),
                    cap.what ? m('p.estate__detail', cap.what) : null,
                    m('p.estate__where',
                      `stated by ${cap.stated_by || 'nobody'} on ${cap.stated_on || 'no date'}`),
                    cap.cannot_see
                      ? m('p.estate__where', ['cannot see: ', cap.cannot_see])
                      : null,
                  ]))),
                reading.capabilities.length === 0
                  ? m('p.estate-view__hint', 'the registry declares no capabilities')
                  : null,
                m('p.estate-view__hint', reading.caveat),
              ]
            : null,
          reading
            ? m('button.estate-view__draw', {
                onclick: () => void ctx.actions.plot.drawCapabilities().then(() => ctx.focusDockPanel('graph')),
              }, 'draw the registry')
            : null,
        ]),
      ]);
    },
  };
}
