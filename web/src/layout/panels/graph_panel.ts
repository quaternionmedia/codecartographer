/**
 * Graph Panel
 *
 * Mounts the D3 / vis-network graph visualisation into a Golden Layout panel.
 * Accepts a `LayoutContext` for shared state access, and returns a Mithril
 * component suitable for `m.mount(element, component)`.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { PlotComponent } from '../../components/codecarto/plot/plot';

export function createGraphPanel(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      const state = ctx.appState.state;
      const isLoading = ctx.panelState.isLoading;

      return m('div.gl-panel.gl-panel--graph', [
        // Main plot area
        m(PlotComponent, { graphs: state.graphContent }),

        // Emergency-stop button while a stream is active
        isLoading
          ? m('div.graph-estop', [
              m('button.graph-estop__btn', {
                onclick: () => ctx.cancel(),
                title: 'Emergency stop — cancel stream',
              }, '⏹'),
            ])
          : null,
      ]);
    },
  };
}
